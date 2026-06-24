#!/usr/bin/env python3
"""edu 입문 커리큘럼 freshness 파이프라인.

정제 SoT(refined_outputs ⋈ filtered_signals, domain=edu_consulting)에서 '생성형 AI 입문/사용법'
컨텐츠를 추려, 변화속도가 다른 두 층으로 커리큘럼을 유지한다.

  1층 Evergreen 척추   : 버전 무관(프롬프트 원리·활용 사고법). 전기간 누적, 합의(반복)빈도=신뢰도.
  2층 신선 팩트 오버레이: 버전 민감(모델/UI/요금). 최근 WINDOW_DAYS 윈도우 + freshness decay로 최신 우선.

왜 두 층인가:
  생성형 LLM 은 버전업·기능추가가 수시로 일어난다. 커리큘럼을 통째로 재생성하면 안정적인 교습 골격까지
  매번 흔들린다. 그래서 거의 안 변하는 척추(주간 재생성)와, 빠르게 썩는 팩트 오버레이(최근 윈도우/감지 시
  핫픽스)를 분리한다. 모델이 버전업하면 척추는 그대로, 오버레이만 갱신한다.

서브커맨드:
  ingest : 정제 SoT 증분(워터마크 이후)만 분류해 edu_curriculum_evidence 에 upsert. 신규 모델 등장 감지.
           (edu_daily.sh 가 매일 호출 — 0.x초)
  build  : 누적 evidence → 두 층 커리큘럼 산출물(runtime/edu_curriculum.json + .md) 원자적 작성.
           (edu_daily.sh 가 주 1회=월요일 호출. 커리큘럼이 매일 바뀔 필요는 없음)

prod 쓰기는 새 테이블 edu_curriculum_evidence 에만 한정한다(기존 데이터 무변경).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "runtime"
OUT_JSON = RUNTIME_DIR / "edu_curriculum.json"
OUT_MD = RUNTIME_DIR / "edu_curriculum_brief.md"

from core.database import execute_query  # noqa: E402

DOMAIN = "edu_consulting"
WINDOW_DAYS = 30        # 오버레이 신선 윈도우
HALFLIFE_DAYS = 30.0    # perishable freshness 반감기
NEW_MODEL_RECENT_DAYS = 7    # 버전 변화 트리거 윈도우(첫 등장 기준)

AI = ["생성형 ai", "chatgpt", "챗gpt", "챗 gpt", "gpt", "제미나이", "gemini", "클로드", "claude",
      "copilot", "뤼튼", "prompt", "프롬프트", "llm", "미드저니", "midjourney"]
TEACH = ["사용법", "쓰는 법", "쓰는법", "입문", "초보", "왕초보", "처음", "기초", "튜토리얼", "가이드",
         "따라하기", "배우기", "익히기", "시작하기", "활용법", "활용 방법", "beginner", "tutorial",
         "basics", "입문자", "초심자", "무작정"]
# 걱정-프레임(교습 의도 아님)만 배제한다. '위험/규제'는 "위험성 알고 안전하게 쓰기" 같은
# 정당한 입문 안전 가이드도 통째로 탈락시켜 커리큘럼을 편향시키므로 NEG 에서 뺀다(red-team MINOR).
NEG = ["의존", "중독", "걱정", "불안", "해롭", "부작용", "금지"]

BUCKETS: dict[str, list[str]] = {
    "도구 선택/소개": ["챗gpt", "chatgpt", "제미나이", "gemini", "클로드", "claude", "뤼튼", "copilot", "어떤 ai", "ai 종류", "ai 비교", "ai 도구"],
    "가입/설치/첫 접속": ["가입", "회원가입", "설치", "로그인", "접속", "앱 설치", "다운로드", "계정", "무료로 시작"],
    "무료/유료 요금제": ["무료", "유료", "요금", "플러스", "plus", "구독", "가격", "결제", "버전 차이"],
    "첫 질문/기본 사용": ["첫 질문", "질문하기", "물어보", "기본 사용", "기본 기능", "뭘 물어", "말 걸", "대화하"],
    "프롬프트 기초": ["프롬프트", "질문법", "질문하는 법", "질문 작성", "명령어", "지시문"],
    "기법-역할 부여": ["역할", "처럼 설명", "전문가", "컨설턴트", "선생님처럼", "페르소나"],
    "기법-출력 형식 지정": ["표로", "형식", "요약", "3줄", "글자수", "불릿", "리스트", "정리해", "형태로"],
    "기법-예시/구체화": ["예시", "예를 들어", "구체적", "상황 설명", "조건"],
    "기법-눈높이 설명": ["초등학생도", "중학생도", "쉽게 설명", "쉬운 말", "눈높이", "이해하기 쉽게"],
    "후속질문/맥락 이어가기": ["이어서", "후속", "다시 물", "맥락", "대화 이어", "추가 질문", "꼬리"],
    "활용-업무": ["보고서", "이메일", "메일", "회의록", "엑셀", "ppt", "문서", "기획서", "업무"],
    "활용-학습/숙제": ["숙제", "공부", "학습", "문제풀이", "독후감", "과제", "수행평가", "시험"],
    "활용-일상": ["여행", "요리", "레시피", "카톡", "일상", "장보기", "육아", "살림"],
    "활용-글쓰기/자기계발": ["블로그", "글쓰기", "자기소개", "카피", "sns", "콘텐츠 작성", "자기계발"],
    "이미지/멀티모달": ["이미지 생성", "그림", "사진", "미드저니", "midjourney", "달리", "dall", "로고", "썸네일", "파일 첨부", "pdf"],
    "음성/모바일/앱": ["음성", "말로", "모바일", "앱에서", "스마트폰", "위젯"],
    "주의점/한계(환각·개인정보)": ["환각", "거짓", "틀린", "검증", "출처", "사실 확인", "개인정보", "주의", "한계", "오답"],
    "자동화/GPTs/챗봇": ["자동화", "gpts", "에이전트", "챗봇 만들", "나만의 gpt", "워크플로"],
}

PERISH = [
    re.compile(r"gpt-?\s*\d"),
    re.compile(r"(최신|신규|출시|업데이트|업뎃|새 기능|새로운 기능|업그레이드)"),
    re.compile(r"(요금|플러스\b|\bplus\b|구독료|무료 한도|월 \d)"),
    re.compile(r"(메뉴|버튼|우측 상단|좌측 상단|설정에서|탭에서)"),
    re.compile(r"(gpt-4o|4o|o1\b|o3\b|gemini ?2|gemini ?1\.5|claude ?3|sonnet|opus|haiku)"),
]
MODEL_TAG = re.compile(
    r"(gpt-?5\.?\d?|gpt-?4o|gpt-?4|o1|o3|gemini ?2(?:\.\d)?|gemini ?1\.5|claude ?3(?:\.\d)?|"
    r"클로드|제미나이|챗gpt|copilot|뤼튼|midjourney|미드저니|dall-?e|달리)", re.I)


def _has(t: str, sigs: list[str]) -> bool:
    return any(s in t for s in sigs)


def _perishable(t: str) -> bool:
    return any(p.search(t) for p in PERISH)


def _model_tags(t: str) -> list[str]:
    return sorted({m.group(0).lower().replace(" ", "") for m in MODEL_TAG.finditer(t)})


def _ensure_table() -> None:
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS edu_curriculum_evidence (
            content_hash     TEXT PRIMARY KEY,
            refined_id       INTEGER,
            source           TEXT,
            title            TEXT,
            klass            TEXT NOT NULL,            -- evergreen | perishable
            buckets          JSONB NOT NULL DEFAULT '[]'::jsonb,
            model_tags       JSONB NOT NULL DEFAULT '[]'::jsonb,
            item_created_at  TIMESTAMP,               -- 원천 신선도 기준(filtered_signals.created_at)
            ingested_at      TIMESTAMP NOT NULL DEFAULT now(),
            score            DOUBLE PRECISION
        )
        """
    )
    execute_query(
        "CREATE INDEX IF NOT EXISTS idx_ece_created ON edu_curriculum_evidence (item_created_at)"
    )
    execute_query(
        "CREATE INDEX IF NOT EXISTS idx_ece_klass ON edu_curriculum_evidence (klass)"
    )


def _classify(title: str, body: str) -> dict[str, Any] | None:
    blob = (title + " " + body).lower()
    if not _has(blob, AI) or not _has(blob, TEACH):
        return None
    if _has(blob, NEG):
        return None
    return {
        "klass": "perishable" if _perishable(blob) else "evergreen",
        "buckets": [b for b, kw in BUCKETS.items() if _has(blob, kw)],
        "model_tags": _model_tags(blob),
    }


def _watermark_id() -> int:
    """증분 워터마크 = 이미 적재한 refined_outputs.id 의 최대값.

    왜 f.created_at 이 아니라 r.id 인가(red-team BLOCKER, 2026-06-24 r2):
      파이프라인은 filtered_signals(Tier2) → refined_outputs(Tier3, *나중에* 생성)다.
      오래된 filtered_signal 이 backlog 로 오늘 Tier3 정제되면 그 행의 f.created_at 은 과거다.
      f.created_at 기준 워터마크면 이 '늦게 도착한' 행은 워터마크보다 과거라 영구 누락된다.
      refined_outputs.id 는 정제 산출의 *도착 순서*를 단조 증가로 반영하므로, r.id > 워터마크는
      늦은 정제까지 빠짐없이 포착한다. (id 는 유일·단조라 동률 없음 → '>' 로 충분, 재처리 0.)
    """
    rows = execute_query(
        "SELECT max(refined_id) AS w FROM edu_curriculum_evidence", fetch=True)
    w = rows[0]["w"] if rows else None
    return int(w) if w is not None else 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """정제 SoT 증분을 분류·upsert.

    반환코드(edu_daily.sh 가 stdout 문자열이 아니라 exit code 로 분기한다 — red-team MAJOR 반영):
      0  = 정상, 신규 모델/버전 신호 없음
      10 = 정상, 신규 모델/버전 신호 등장(→ 호출자가 그날 즉시 build 로 오버레이 핫픽스)
      그 외(예외) = 실패(비0). edu_daily.sh 가 이를 묻지 않고 경고로 표면화한다.
    """
    _ensure_table()
    wm = _watermark_id()
    if wm == 0:
        print("[curriculum:ingest] 부트스트랩(테이블 비어있음): edu 정제분 전체를 id 순으로 1회 적재한다 "
              "— 이후로는 refined_outputs.id 증분만 처리(분류 통과분만 INSERT 되므로 실제 쓰기는 소량)")

    # 늦은 Tier3 정제까지 포착하려 r.id(도착 순서) 기준 증분. id 는 유일·단조라 '>' 로 충분.
    # 행당 upsert 는 execute_query(호출마다 commit)로 개별 커밋되지만, ASC 처리 + r.id>wm 재실행이
    # 중단 지점부터 빠짐없이 이어받아 partial-commit 을 자가복구한다(content_hash 재upsert 는 무해).
    rows = execute_query(
        """
        SELECT r.id AS refined_id, r.final_title, r.final_body,
               f.source, f.created_at, f.content_hash, f.score
        FROM refined_outputs r
        JOIN filtered_signals f ON r.filtered_signal_id = f.id
        WHERE f.domain = %s AND r.id > %s
        ORDER BY r.id ASC
        """, (DOMAIN, wm), fetch=True) or []

    upserts = 0
    for r in rows:
        title = str(r["final_title"] or "")
        body = str(r["final_body"] or "")
        ch = r["content_hash"]
        if not ch:
            continue
        c = _classify(title, body)
        if c is None:
            continue
        execute_query(
            """
            INSERT INTO edu_curriculum_evidence
                (content_hash, refined_id, source, title, klass, buckets, model_tags, item_created_at, score)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
            ON CONFLICT (content_hash) DO UPDATE SET
                refined_id = EXCLUDED.refined_id,
                source = EXCLUDED.source,
                title = EXCLUDED.title,
                klass = EXCLUDED.klass,
                buckets = EXCLUDED.buckets,
                model_tags = EXCLUDED.model_tags,
                item_created_at = EXCLUDED.item_created_at,
                score = EXCLUDED.score
            """,
            (ch, r["refined_id"], r["source"], title[:500], c["klass"],
             json.dumps(c["buckets"], ensure_ascii=False),
             json.dumps(c["model_tags"], ensure_ascii=False),
             r["created_at"], r["score"]),
        )
        upserts += 1

    # 신규 모델/버전 감지는 batch 차분(=crash 시 유실)이 아니라, *durable 테이블 상태*에서 age 로 판정한다.
    # "처음 등장 시점(min item_created_at)이 최근 NEW_MODEL_RECENT_DAYS 이내"인 모델 → 신규.
    # 매 실행이 테이블에서 재계산하므로 ingest 가 중간에 죽어도 다음 실행이 동일 결론에 도달한다
    # (red-team MAJOR 반영: exit-10 트리거 유실 방지).
    cutoff = datetime.now(timezone.utc) - timedelta(days=NEW_MODEL_RECENT_DAYS)
    newly_rows = execute_query(
        """
        SELECT m FROM (
            SELECT jsonb_array_elements_text(model_tags) AS m,
                   min(item_created_at) AS first_seen
            FROM edu_curriculum_evidence
            GROUP BY 1
        ) t
        WHERE first_seen >= %s
        ORDER BY m
        """, (cutoff,), fetch=True) or []
    newly = [r["m"] for r in newly_rows]
    print(f"[curriculum:ingest] 워터마크 refined_id>{wm} 처리: upsert {upserts}건")
    if newly:
        print(f"[curriculum:ingest] ⚠️ 신규 모델/버전 신호(최근 {NEW_MODEL_RECENT_DAYS}일 첫 등장): {newly} "
              "→ 오버레이 핫픽스(build) 트리거 [exit 10]")
        return 10
    print("[curriculum:ingest] 신규 모델/버전 신호 없음")
    return 0


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        # 부모 디렉터리 fsync — rename 자체의 내구성을 확정한다(red-team MAJOR: 크래시/전원장애
        # 직후에도 교체가 디스크에 반영되도록). 디렉터리 fd 열기/ fsync 실패는 치명적이지 않아 무시.
        try:
            dfd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except OSError:
            pass
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise


def cmd_build(args: argparse.Namespace) -> int:
    _ensure_table()
    now = datetime.now(timezone.utc)
    rows = execute_query(
        "SELECT klass, buckets, model_tags, item_created_at FROM edu_curriculum_evidence",
        fetch=True) or []
    ever = [r for r in rows if r["klass"] == "evergreen"]
    per = [r for r in rows if r["klass"] == "perishable"]

    def _buckets(r) -> list[str]:
        b = r["buckets"]
        return b if isinstance(b, list) else json.loads(b or "[]")

    def _models(r) -> list[str]:
        m = r["model_tags"]
        return m if isinstance(m, list) else json.loads(m or "[]")

    def _age(r) -> int:
        c = r["item_created_at"]
        if not c:
            return 999
        if c.tzinfo is None:
            c = c.replace(tzinfo=timezone.utc)
        return (now - c).days

    # 1층 척추: evergreen 버킷별 합의빈도
    spine = []
    for b in BUCKETS:
        cnt = sum(1 for r in ever if b in _buckets(r))
        if cnt:
            spine.append({"topic": b, "consensus": cnt,
                          "share_pct": round(100 * cnt / max(len(ever), 1), 1)})
    spine.sort(key=lambda x: -x["consensus"])

    # 2층 오버레이: 최근 윈도우 perishable, freshness decay 모델 점수
    fresh = [r for r in per if _age(r) <= WINDOW_DAYS]
    model_score: dict[str, float] = defaultdict(float)
    model_recent: dict[str, int] = defaultdict(int)
    for r in fresh:
        w = math.pow(0.5, _age(r) / HALFLIFE_DAYS)
        for m in _models(r):
            model_score[m] += w
            model_recent[m] += 1
    overlay = [{"model": m, "freshness_score": round(s, 2), "recent_count": model_recent[m]}
               for m, s in sorted(model_score.items(), key=lambda x: -x[1])]

    # 버전 변화 트리거: 최근 N일에만 등장한 모델
    recent: set[str] = set()
    older: set[str] = set()
    for r in per:
        for m in _models(r):
            (recent if _age(r) <= NEW_MODEL_RECENT_DAYS else older).add(m)
    newly = sorted(recent - older)

    payload = {
        "generated_at": now.isoformat(timespec="seconds"),
        "input_counts": {"total": len(rows), "evergreen": len(ever), "perishable": len(per)},
        "window_days": WINDOW_DAYS,
        "evergreen_spine": spine,
        "fresh_overlay": {"window_perishable": len(fresh), "current_models": overlay},
        "version_change_trigger": {"recent_days": NEW_MODEL_RECENT_DAYS, "newly_appeared_models": newly},
        "artifact_version": "v1",
    }
    lines = [
        "# edu 입문 커리큘럼 (freshness 2층 구조)",
        f"_생성: {payload['generated_at']} · 입력 {len(rows)}건 (evergreen {len(ever)} / perishable {len(per)})_",
        "",
        "## 1층 · Evergreen 척추 (버전 무관, 합의빈도순)",
    ]
    for s in spine:
        lines.append(f"- **{s['topic']}** — {s['consensus']}건 ({s['share_pct']}%)")
    lines += ["", f"## 2층 · 신선 팩트 오버레이 (최근 {WINDOW_DAYS}일, freshness 가중)",
              f"- 윈도우 내 perishable: {len(fresh)}건", "- 현재 우세 모델/도구:"]
    for o in overlay[:10]:
        lines.append(f"  - {o['model']} — {o['freshness_score']}pt ({o['recent_count']}건)")
    lines += ["", f"## 버전 변화 트리거 (최근 {NEW_MODEL_RECENT_DAYS}일 신규 등장)",
              f"- {newly if newly else '없음'}", ""]
    # MD(부수 산출물) 먼저, canonical JSON 을 마지막에. 쌍이 완전 원자적이진 않지만 JSON 기준
    # reader 는 항상 일관된 최신 상태를 본다(red-team MINOR 반영).
    _atomic_write(OUT_MD, "\n".join(lines))
    _atomic_write(OUT_JSON, json.dumps(payload, ensure_ascii=False, indent=2))

    print(f"[curriculum:build] 척추 {len(spine)}주제 + 오버레이 {len(overlay)}모델 → {OUT_JSON.name}, {OUT_MD.name}")
    if newly:
        print(f"[curriculum:build] ⚠️ 신규 모델/버전: {newly}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="edu 입문 커리큘럼 freshness 파이프라인")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest", help="정제 SoT 증분 분류·적재 (daily)")
    sub.add_parser("build", help="누적 evidence → 두 층 커리큘럼 산출 (weekly)")
    args = ap.parse_args()
    if args.cmd == "ingest":
        return cmd_ingest(args)
    if args.cmd == "build":
        return cmd_build(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
