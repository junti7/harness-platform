#!/usr/bin/env python3
"""
교육 컨설팅 상담사 근거 뱅크(evidence_bank.json) 자동 갱신기.

목적:
  상담사(/api/edu/diagnose)가 대화 중 인용하는 근거가 '같은 말만 반복'하지 않도록,
  매일 파이프라인(Tier 1~4)이 수집·정제한 최신 edu_consulting refined_outputs를
  자연스러운 구어체 cite로 변환해 evidence_bank.json에 합친다.

구성:
  1) evergreen 앵커 (data/edu_research/evidence_anchors.json) — 만료되지 않는 랜드마크 사례
  2) 파이프라인 최신 항목 — refined_outputs 중 edu_consulting, 최근 N일 이내 (recency window)

원칙:
  - 통계 수치를 새로 지어내지 않는다. refined_output의 hook/parent_insight 문장을 그대로 활용한다.
  - 출처(source)는 실제 raw_signals.source를 보존한다.
  - 재실행 가능(idempotent). 매 실행마다 evidence_bank.json을 통째로 재생성한다.
  - 모든 항목에 collected_at, provenance를 남겨 추적 가능하게 한다.

사용:
  python scripts/refresh_edu_evidence_bank.py
  python scripts/refresh_edu_evidence_bank.py --window-days 30 --max-fresh 25 --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import execute_query  # noqa: E402

EDU_DIR = PROJECT_ROOT / "data" / "edu_research"
ANCHORS_PATH = EDU_DIR / "evidence_anchors.json"
BANK_PATH = EDU_DIR / "evidence_bank.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | edu-evidence | %(levelname)s | %(message)s",
)
log = logging.getLogger("refresh_edu_evidence_bank")


_COMMUNITY_SOURCE_MARKERS = (
    "naver", "맘카페", "카페", "블로그", "blind", "reddit", "dcinside", "디시", "brunch", "maily",
)
_RESEARCH_POLICY_SOURCE_MARKERS = (
    "eric", "semantic scholar", "oecd", "unesco", "common sense", "educationweek", "edsurge",
    "world economic forum", "ted-ed", "ted education", "교육부", "교육청", "kedi", "nih", "who",
    "pew", "report", "policy", "학회", "연구", "논문",
)
_MEDIA_CASE_SOURCE_MARKERS = (
    "youtube", "기사", "news", "podcast", "방송", "kbs", "mbc", "sbs", "조선", "중앙", "한겨레",
)
_YOUTUBE_LOW_SIGNAL_TITLE_PATTERNS = (
    "official video", "mv", "뮤직비디오", "직캠", "cover", "reaction", "trailer", "예고편",
    "drama", "드라마", "ost", "fan cam", "lyrics", "anime", "multi sub", "신번", "新番",
    "神仙", "娇妻", "逆袭", "打猎", "白富美", "고블린",
)


def infer_source_kind(source_label: str, raw_data=None, source_name: str | None = None) -> str:
    """상담 근거를 말투/용도 기준으로 거칠게 분류한다.

    - community_voice: 맘카페, 블로그, 커뮤니티 관찰처럼 생활어/현장감이 강한 소스
    - research_policy: 연구, 정책, 기관 보고서처럼 사실성/권위가 강한 소스
    - media_case: 기사, 방송, 인터뷰, 유튜브 사례형
    - general_reference: 그 외
    """
    rd = raw_data
    if isinstance(rd, str):
        try:
            rd = json.loads(rd)
        except Exception:
            rd = {}
    if not isinstance(rd, dict):
        rd = {}
    blob = " ".join(
        part for part in [
            str(source_label or ""),
            str(source_name or ""),
            str(rd.get("channel") or ""),
            str(rd.get("source_name") or ""),
            str(rd.get("url") or ""),
        ] if part
    ).lower()
    if any(marker in blob for marker in _COMMUNITY_SOURCE_MARKERS):
        return "community_voice"
    if any(marker in blob for marker in _RESEARCH_POLICY_SOURCE_MARKERS):
        return "research_policy"
    if any(marker in blob for marker in _MEDIA_CASE_SOURCE_MARKERS):
        return "media_case"
    return "general_reference"


def normalize_raw_data(raw_data) -> dict:
    rd = raw_data
    if isinstance(rd, str):
        try:
            rd = json.loads(rd)
        except Exception:
            rd = {}
    return rd if isinstance(rd, dict) else {}


def extract_source_url(raw_data=None) -> str:
    rd = normalize_raw_data(raw_data)
    for key in ("source_url", "url", "link", "canonical_url", "webpage_url", "doi", "pdf_url"):
        value = str(rd.get(key) or "").strip()
        if value.startswith(("http://", "https://")):
            return value
        if key == "doi" and value:
            return f"https://doi.org/{value.removeprefix('doi:').strip()}"
        match = re.search(r"https?://[^\s)>\]\"']+", value)
        if match:
            return match.group(0)
    return ""


def infer_segment(raw_data=None, source_name: str | None = None) -> str:
    rd = normalize_raw_data(raw_data)
    cluster = str(rd.get("topic_cluster") or "").strip().lower()
    src = str(source_name or "").strip().lower()
    if cluster in {"worker_ai", "job_seeker_ai"}:
        return "worker"
    if "worker" in src or "job_seeker" in src:
        return "worker"
    return "parent"


def is_low_quality_evidence(cite: str, source_label: str, raw_data=None, source_name: str | None = None) -> bool:
    """RAG 근거 레이어에서만 쓰는 저품질 판정.

    수집 자체를 막지 않는다. 다만 상담 근거로 쓸 때 명백히 무관한 엔터테인먼트/홍보성
    유튜브 조각이 섞이면 자연스러움이 크게 무너져서 evidence layer에서 제외한다.
    """
    rd = normalize_raw_data(raw_data)
    title = str(rd.get("title") or rd.get("video_title") or "").strip().lower()
    cite_norm = str(cite or "").strip().lower()
    source_norm = str(source_label or "").strip().lower()
    blob = " ".join([title, cite_norm, source_norm, str(source_name or "").lower()])
    if "youtube" in source_norm and any(pattern in title for pattern in _YOUTUBE_LOW_SIGNAL_TITLE_PATTERNS):
        return True
    if re.search(r"[一-龥]{4,}", title) and not any(token in blob for token in ("ai", "교육", "진로", "직장", "부모", "학생", "취업")):
        return True
    if "youtube" in source_norm and len(re.findall(r"[\u3040-\u30ff]", title)) >= 4:
        return True
    if len(cite_norm) < 18:
        return True
    return False


def _load_anchors() -> list[dict]:
    """에버그린 앵커 로드 (없으면 빈 리스트)."""
    try:
        data = json.loads(ANCHORS_PATH.read_text(encoding="utf-8"))
        items = data.get("items", [])
        for it in items:
            it["evergreen"] = True
            it.setdefault("provenance", "anchor")
        log.info("앵커 %d개 로드", len(items))
        return items
    except FileNotFoundError:
        log.warning("앵커 파일 없음: %s", ANCHORS_PATH)
        return []
    except Exception as exc:
        log.error("앵커 로드 실패: %s", exc)
        return []


def _first_sentence(text: str, limit: int = 180) -> str:
    """첫 문장(또는 limit 이내)을 깔끔히 추출 (마크다운 서식 제거)."""
    import re
    text = (text or "").strip().replace("\n", " ")
    if not text:
        return ""
    # 마크다운/머리표 제거: **굵게**, `코드`, 머리 불릿/번호, '소제목: '
    text = re.sub(r"[*`#>_]+", "", text)
    text = re.sub(r"^\s*[-•\d.]+\s*", "", text)
    text = re.sub(r"^[^:：]{2,20}[:：]\s*", "", text)  # '감정 코칭으로 불안 다루기: ' 같은 소제목 제거
    text = re.sub(r"\s{2,}", " ", text).strip()
    for end in ("다. ", "요. ", "죠. ", "다.\n", "요.\n"):
        idx = text.find(end)
        if 0 < idx <= limit:
            return text[: idx + 2].strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last = max(cut.rfind("."), cut.rfind("요"), cut.rfind("다"))
    return (cut[: last + 1] if last > limit * 0.5 else cut).strip()


# 알맹이 없는 일반적 공감/도입 문구 — cite로 부적합 (이런 것만 반복되면 '고리타분')
_GENERIC_MARKERS = (
    "걱정되시죠", "걱정이", "불안하신가요", "불안감", "고민이 많", "고민이 깊",
    "많이 들으시죠", "들어보셨", "마음이 앞", "막연한", "느끼시", "하시죠?",
)
# 구체성 신호 — 이게 들어가면 cite로서 가치가 있다 (사례·연구·도구·정책·행동)
_SPECIFIC_MARKERS = (
    "연구", "조사", "전문가", "정책", "교육부", "입시", "수능", "디지털 교과서",
    "챗GPT", "챗봇", "AI 도구", "도구를", "방식", "능력", "역량", "비판적",
    "활용", "질문", "오히려", "실제로", "바뀌", "중요해", "%",
)


# LLM 메타 발화 — 자료를 '설명'하는 문장. 상담사가 그대로 말하면 어색하므로 제외.
_META_MARKERS = ("원문은", "원문에", "이 기사", "이 영상", "이 자료", "본 자료", "해당 기사", "해당 영상")


def _is_generic(text: str) -> bool:
    """알맹이 없는 일반 공감문 또는 메타 발화면 True (구체성 신호가 있으면 통과)."""
    if any(m in text for m in _META_MARKERS):
        return True
    if any(m in text for m in _SPECIFIC_MARKERS):
        return False
    return any(m in text for m in _GENERIC_MARKERS)


def _cite_from_refined(body: dict) -> str | None:
    """refined_output JSON에서 상담사가 흘릴 '알맹이 있는' 한 줄 cite를 구성.

    일반적 공감 도입문(hook)보다 실제 인사이트(what_changed)·구체 행동(action_now)을
    우선한다. 알맹이 없는 일반문은 제외해 '같은 소리 반복'을 방지한다.
    """
    pi = body.get("parent_insight") if isinstance(body.get("parent_insight"), dict) else {}
    action = pi.get("action_now")
    if isinstance(action, list) and action:
        action = action[0]
    elif not isinstance(action, str):
        action = None

    # 우선순위: 실제 변화(what_changed) → 구체 행동(action_now) → hook → 제목
    candidates = [pi.get("what_changed"), action, body.get("hook"), body.get("final_title")]
    fallback: str | None = None
    for c in candidates:
        s = _first_sentence(c or "")
        if len(s) < 15:
            continue
        if any(m in s for m in _META_MARKERS):
            continue  # 메타 발화는 fallback으로도 쓰지 않는다 (하드 제외)
        if _is_generic(s):
            fallback = fallback or s  # 일반 공감문은 최후의 보루로만
            continue
        return s
    return fallback


def _strip_trailing_source(text: str) -> str:
    """문장 끝의 '(근거: …)', '(출처: …)' 등 괄호 메타를 제거."""
    import re
    return re.sub(r"\s*[\(（](근거|출처|참고|예)\s*[:：].*$", "", (text or "").strip())


_MAX_CITES_PER_ITEM = 4  # 항목당 추출 cite 상한 (다양성↑, 코퍼스 비대화 방지)


def _cites_from_refined(body: dict) -> list[str]:
    """refined_output에서 '서로 다른' 알맹이 cite를 여러 개 추출(다양성 강화).

    기존 _cite_from_refined는 항목당 what_changed 1개만 뽑아 일반론이 반복됐다.
    여기서는 구체 행동(action_now 각 항목)·한국 맥락(korea_context)·주의점(wait_and_see)·
    관찰 포인트(watchlist)까지 폭넓게 끌어와, 일반/메타/중복을 걸러 다양한 cite 집합을 만든다.
    """
    pi = body.get("parent_insight") if isinstance(body.get("parent_insight"), dict) else {}
    raw: list = []
    an = pi.get("action_now")
    if isinstance(an, list):
        raw.extend(an)            # 구체 행동들 — 가장 다양함
    elif isinstance(an, str):
        raw.append(an)
    raw.append(pi.get("korea_context"))   # 한국 입시·정책 맥락
    raw.append(pi.get("what_changed"))    # 큰 변화(반복되기 쉬움 → 뒤로)
    raw.append(pi.get("wait_and_see"))    # 보류·주의 신호
    wl = body.get("watchlist")
    if isinstance(wl, list):
        raw.extend(wl)
    raw.append(body.get("hook"))

    cites: list[str] = []
    seen_prefix: set[str] = set()
    for c in raw:
        if not isinstance(c, str):
            continue
        s = _first_sentence(_strip_trailing_source(c))
        if len(s) < 15:
            continue
        if any(m in s for m in _META_MARKERS):
            continue
        if _is_generic(s):
            continue
        prefix = s[:16]
        if prefix in seen_prefix:
            continue
        seen_prefix.add(prefix)
        cites.append(s)
        if len(cites) >= _MAX_CITES_PER_ITEM:
            break
    if not cites:  # 다 걸러지면 기존 단일 로직으로 최소 1개 확보
        one = _cite_from_refined(body)
        if one:
            cites.append(one)
    return cites


def _fetch_fresh_items(window_days: int, max_fresh: int) -> list[dict]:
    """최근 window_days 이내 edu_consulting refined_outputs를 cite 항목으로 변환."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    rows = execute_query(
        """
        SELECT ro.id, ro.final_title, ro.final_body, ro.created_at,
               rs.source, rs.raw_data
        FROM refined_outputs ro
        JOIN filtered_signals fs ON fs.id = ro.filtered_signal_id
        JOIN raw_signals rs ON rs.id = fs.raw_signal_id
        WHERE COALESCE(fs.domain, 'physical_ai') = 'edu_consulting'
          AND ro.created_at >= %s
        ORDER BY ro.created_at DESC
        LIMIT %s
        """,
        (cutoff, max_fresh * 3),  # 변환 실패분 고려해 넉넉히 조회
        fetch=True,
    ) or []

    candidates: list[dict] = []
    seen_cites: set[str] = set()
    seen_prefix: set[str] = set()  # 첫머리 유사 cite 중복 방지
    for r in rows:
        body = r["final_body"]
        try:
            body = json.loads(body) if isinstance(body, str) else (body or {})
        except Exception:
            continue
        # 비관련/저관련 항목은 제외
        if body.get("is_relevant") is False:
            continue
        cite = _cite_from_refined(body)
        if not cite or cite in seen_cites:
            continue
        src_label = _source_label(r["source"], r["raw_data"])
        if is_low_quality_evidence(cite, src_label, r["raw_data"], r["source"]):
            continue
        prefix = cite[:18]
        if prefix in seen_prefix:  # 첫머리가 같은 거의-동일 문구 제외
            continue
        seen_cites.add(cite)
        seen_prefix.add(prefix)
        created = r["created_at"]
        source_url = extract_source_url(r["raw_data"])
        candidates.append({
            "id": f"fresh-{r['id']}",
            "type": "최신 동향",
            "segment": infer_segment(r["raw_data"], r["source"]),
            "evergreen": False,
            "cite": cite,
            "source": src_label,
            "source_name": r["source"],
            "source_url": source_url,
            "source_ref": source_url or f"refined_output:{r['id']}",
            "source_kind": infer_source_kind(src_label, r["raw_data"], r["source"]),
            "provenance": "pipeline",
            "refined_output_id": r["id"],
            "collected_at": created.isoformat() if hasattr(created, "isoformat") else str(created),
        })
    # community > research > media > general 순서로 quota를 배분해 맘카페/지식iN/블로그의 생활어를 더 살린다.
    quotas = {
        "community_voice": max(1, int(max_fresh * 0.5)),
        "research_policy": max(1, int(max_fresh * 0.25)),
        "media_case": max(1, int(max_fresh * 0.15)),
        "general_reference": max(1, int(max_fresh * 0.10)),
    }
    buckets: dict[str, list[dict]] = {key: [] for key in quotas}
    for item in candidates:
        buckets.setdefault(item["source_kind"], []).append(item)
    items: list[dict] = []
    for kind, limit in quotas.items():
        items.extend(buckets.get(kind, [])[:limit])
    if len(items) < max_fresh:
        leftovers: list[dict] = []
        for kind, bucket in buckets.items():
            leftovers.extend(bucket[quotas.get(kind, 0):])
        items.extend(leftovers[: max_fresh - len(items)])
    items = items[:max_fresh]
    log.info("파이프라인 최신 항목 %d개 변환 (window=%d일, 조회 %d행)", len(items), window_days, len(rows))
    return items


def _clean_title(title: str) -> str:
    """HTML 엔티티 디코드 + 잘린 해시태그/공백 정리."""
    import html
    import re
    t = html.unescape(title or "").strip()
    t = re.sub(r"\s*#\w*$", "", t)          # 끝의 (잘린) 해시태그 제거
    t = re.sub(r"\s{2,}", " ", t).strip()
    if len(t) > 60:                          # 너무 길면 다듬어 깔끔히
        t = t[:60].rstrip() + "…"
    return t


def _source_label(source: str | None, raw_data) -> str:
    """수집 메타에서 사람이 읽을 수 있는 출처 라벨 생성 (예: 'YouTube 채널명 — 영상 제목')."""
    rd = raw_data
    if isinstance(rd, str):
        try:
            rd = json.loads(rd)
        except Exception:
            rd = {}
    if not isinstance(rd, dict):
        rd = {}
    title = _clean_title(rd.get("title") or rd.get("video_title") or "")
    channel = (rd.get("channel") or rd.get("source_name") or "").strip()
    src = (source or "").lower()
    if "youtube" in src or rd.get("channel"):
        parts = ["YouTube"]
        if channel:
            parts.append(channel)
        label = " · ".join(parts)
        return f"{label} — '{title}'" if title else label
    if title:
        return f"{channel + ' — ' if channel else ''}'{title}'"
    return source or "수집 자료"


def build_bank(window_days: int, max_fresh: int) -> dict:
    anchors = _load_anchors()
    for it in anchors:
        it.setdefault("source_kind", infer_source_kind(it.get("source", "")))
    fresh = _fetch_fresh_items(window_days, max_fresh)

    # dedup: 동일 cite 텍스트 제거 (앵커 우선)
    seen: set[str] = set()
    merged: list[dict] = []
    for it in anchors + fresh:
        key = (it.get("cite") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(it)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "_meta": {
            "purpose": "AI 부모/직장인 상담사가 대화 중 인용하는 실제 근거 뱅크. 절대 목록 밖 출처를 지어내지 않는다.",
            "rule": "각 cite는 실제 수집/사례에 근거. 통계 수치를 새로 지어내지 않는다.",
            "refreshed_at": now,
            "refreshed_by": "scripts/refresh_edu_evidence_bank.py",
            "window_days": window_days,
            "counts": {
                "total": len(merged),
                "evergreen_anchors": sum(1 for x in merged if x.get("evergreen")),
                "fresh_pipeline": sum(1 for x in merged if x.get("provenance") == "pipeline"),
                "community_voice": sum(1 for x in merged if x.get("source_kind") == "community_voice"),
                "research_policy": sum(1 for x in merged if x.get("source_kind") == "research_policy"),
                "media_case": sum(1 for x in merged if x.get("source_kind") == "media_case"),
            },
        },
        "items": merged,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="교육 상담사 근거 뱅크 자동 갱신")
    ap.add_argument("--window-days", type=int, default=45,
                    help="파이프라인 최신 항목 수집 기간(일). 이보다 오래된 자동 항목은 제외 (기본 45)")
    ap.add_argument("--max-fresh", type=int, default=25,
                    help="파이프라인 최신 항목 최대 개수 (기본 25)")
    ap.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 결과만 출력")
    args = ap.parse_args()

    bank = build_bank(args.window_days, args.max_fresh)
    meta = bank["_meta"]["counts"]
    log.info("뱅크 구성: 총 %d (앵커 %d + 최신 %d)",
             meta["total"], meta["evergreen_anchors"], meta["fresh_pipeline"])

    if args.dry_run:
        log.info("[dry-run] 파일 미작성. 미리보기 ↓")
        for it in bank["items"][:5]:
            log.info("  · (%s) %s … [%s]", it["type"], it["cite"][:60], it["source"])
        return 0

    if meta["total"] == 0:
        log.error("항목이 0개 — 기존 뱅크를 덮어쓰지 않고 종료")
        return 1

    BANK_PATH.write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("저장 완료: %s (총 %d개)", BANK_PATH, meta["total"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
