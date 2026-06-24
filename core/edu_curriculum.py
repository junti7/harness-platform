"""edu 입문 커리큘럼 개인화 — 공유 로직.

CLI(scripts/build_edu_curriculum.py)와 백엔드(harness-os/backend/main.py)가 함께 쓴다.
요청 시점에 '미리 적재된 evidence 풀'을 사용자 속성으로 재가중·재정렬하는 순수 함수가 핵심.
파이프라인을 재실행하지 않으므로 밀리초 단위로 즉시 재편된다.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Any

WINDOW_DAYS = 30        # 신선 오버레이 윈도우
HALFLIFE_DAYS = 30.0    # perishable freshness 반감기
SEGMENT_MIN_ROWS = 20   # 세그먼트 기준 풀 사용 최소 표본(미만이면 글로벌 폴백)

# 속성 → 버킷 곱셈 가중(1.0=중립). 없는 버킷은 1.0.
LEVEL_WEIGHTS: dict[str, dict[str, float]] = {
    "beginner": {
        "가입/설치/첫 접속": 3.0, "첫 질문/기본 사용": 2.5, "도구 선택/소개": 1.3,
        "프롬프트 기초": 1.5, "무료/유료 요금제": 1.5, "주의점/한계(환각·개인정보)": 1.4,
        "기법-눈높이 설명": 1.3, "자동화/GPTs/챗봇": 0.2, "기법-출력 형식 지정": 0.8,
    },
    "intermediate": {
        "프롬프트 기초": 1.3, "기법-역할 부여": 1.4, "기법-예시/구체화": 1.4,
        "기법-출력 형식 지정": 1.4, "후속질문/맥락 이어가기": 1.3,
        "가입/설치/첫 접속": 0.3, "첫 질문/기본 사용": 0.6,
    },
    "advanced": {
        "자동화/GPTs/챗봇": 2.5, "후속질문/맥락 이어가기": 1.5, "기법-역할 부여": 1.2,
        "가입/설치/첫 접속": 0.1, "첫 질문/기본 사용": 0.2, "도구 선택/소개": 0.5,
    },
}
MOTIVATION_WEIGHTS: dict[str, dict[str, float]] = {
    "work": {"활용-업무": 2.5, "기법-출력 형식 지정": 1.3},
    "child_study": {"활용-학습/숙제": 2.5, "기법-눈높이 설명": 1.8},
    "daily": {"활용-일상": 2.5},
    "writing": {"활용-글쓰기/자기계발": 2.5},
}
ENV_WEIGHTS: dict[str, dict[str, float]] = {
    "mobile": {"음성/모바일/앱": 2.0},
    "voice": {"음성/모바일/앱": 2.5},
    "pc": {},
}
# 직업/역할 자유입력 → 원천 segment(데이터 존재값: parent|worker)
JOB_TO_SEGMENT = {
    "parent": "parent", "학부모": "parent", "주부": "parent", "엄마": "parent", "아빠": "parent",
    "worker": "worker", "직장인": "worker", "회사원": "worker", "사무직": "worker",
}
# intake current_device → env
DEVICE_TO_ENV = {"iphone": "mobile", "android": "mobile", "mobile": "mobile",
                 "mac": "pc", "windows": "pc", "pc": "pc"}
# intake ai_experience → level
EXPERIENCE_TO_LEVEL = {"beginner": "beginner", "novice": "beginner",
                       "intermediate": "intermediate", "advanced": "advanced", "expert": "advanced"}
# 사용자 LLM 선택값 → 데이터 model_tag 동의어(한/영, 버전 변형 매칭). 오버레이 필터용.
LLM_ALIASES: dict[str, list[str]] = {
    "chatgpt": ["chatgpt", "챗gpt", "gpt"],
    "gpt": ["gpt", "chatgpt", "챗gpt"],
    "제미나이": ["제미나이", "gemini"],
    "gemini": ["gemini", "제미나이"],
    "클로드": ["클로드", "claude"],
    "claude": ["claude", "클로드"],
    "copilot": ["copilot"],
    "뤼튼": ["뤼튼", "wrtn"],
}

AI_TERMS = (
    "ai", "chatgpt", "gpt", "gemini", "claude", "인공지능", "생성형", "챗gpt", "챗지피티",
    "人工知能", "生成ai", "inteligencia artificial",
)
EDU_TERMS = (
    "교육", "학습", "공부", "숙제", "학생", "아이", "자녀", "부모", "학부모", "학교", "교사", "수업", "교과서",
    "education", "learning", "student", "school", "teacher", "classroom", "homework", "parent", "parents",
    "教育", "勉強", "学習", "子供", "学生", "父母", "家長", "教育", "pendidikan", "educacao", "educação",
)


def _as_list(v: Any) -> list[str]:
    if isinstance(v, list):
        return v
    if not v:
        return []
    try:
        return json.loads(v)
    except (ValueError, TypeError):
        return []


def _age_days(created: Any, now: datetime) -> int:
    if not created:
        return 999
    if isinstance(created, str):
        try:
            created = datetime.fromisoformat(created)
        except ValueError:
            return 999
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (now - created).days


def _media_kind(source: str, url: str) -> str:
    blob = f"{source} {url}".lower()
    host = urlparse(url).netloc.lower() if url else ""
    if "youtube" in blob or "youtu.be" in host:
        return "video"
    if "arxiv" in blob or "semanticscholar" in blob or "scholar" in blob or "pubmed" in blob or "eric" in blob:
        return "paper"
    if "rss" in blob or "blog" in blob or "newsletter" in blob or url:
        return "article"
    return "reference"


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(term.lower() in low for term in terms)


def _video_source_is_relevant(r: dict[str, Any]) -> bool:
    source = str(r.get("source") or "")
    url = str(r.get("url") or "")
    if _media_kind(source, url) != "video":
        return True
    raw_title = str(r.get("raw_title") or "")
    # 정제 body/final_title/query 는 LLM 재작성 또는 검색어일 수 있으므로 YouTube URL 검증에는 쓰지 않는다.
    return _has_any(raw_title, AI_TERMS) and _has_any(raw_title, EDU_TERMS)


def personalize(
    rows: list[dict[str, Any]],
    *,
    llm: str = "",
    level: str = "",
    motivation: str = "",
    env: str = "",
    job: str = "",
    media_preference: str = "mixed",
    now: datetime | None = None,
) -> dict[str, Any]:
    """evidence 풀(rows)을 속성으로 재편. rows 각 항목: klass, buckets, model_tags, item_created_at, segment.

    반환: {attrs, segment, base_pool, order:[{topic,weight}], overlay:[{model,freshness}]}.
    """
    now = now or datetime.now(timezone.utc)
    seg = JOB_TO_SEGMENT.get((job or "").strip().lower()) if job else None

    ever = [r for r in rows if r.get("klass") == "evergreen"]
    seg_rows = [r for r in ever if r.get("segment") == seg] if seg else []
    use_seg = len(seg_rows) >= SEGMENT_MIN_ROWS
    base_pool = seg_rows if use_seg else ever

    base: dict[str, float] = {}
    for r in base_pool:
        for b in _as_list(r.get("buckets")):
            base[b] = base.get(b, 0.0) + 1.0

    mults: list[dict[str, float]] = []
    if level in LEVEL_WEIGHTS:
        mults.append(LEVEL_WEIGHTS[level])
    if motivation in MOTIVATION_WEIGHTS:
        mults.append(MOTIVATION_WEIGHTS[motivation])
    if env in ENV_WEIGHTS:
        mults.append(ENV_WEIGHTS[env])

    order = []
    for b, w0 in base.items():
        w = w0
        for mp in mults:
            w *= mp.get(b, 1.0)
        if w > 0:
            order.append({"topic": b, "weight": round(w, 1)})
    order.sort(key=lambda x: -x["weight"])

    # 오버레이: 사용자 LLM 으로 필터, freshness decay.
    mscore: dict[str, float] = {}
    for r in rows:
        if r.get("klass") != "perishable":
            continue
        age = _age_days(r.get("item_created_at"), now)
        if age > WINDOW_DAYS:
            continue
        wt = math.pow(0.5, age / HALFLIFE_DAYS)
        for m in _as_list(r.get("model_tags")):
            mscore[m] = mscore.get(m, 0.0) + wt
    llm_n = (llm or "").lower().replace(" ", "")
    aliases = LLM_ALIASES.get(llm_n, [llm_n]) if llm_n else []

    def _llm_match(m: str) -> bool:
        if not llm_n:
            return True
        return any(a in m or m in a for a in aliases)

    overlay = [{"model": m, "freshness": round(s, 2)}
               for m, s in sorted(mscore.items(), key=lambda x: -x[1])
               if _llm_match(m)]

    # ── '감흥' 레이어: 추상 라벨이 아니라 수집 데이터의 구체적 알맹이 ──────────────
    # 콘텐츠 풀 = 세그먼트의 *모든* 행(evergreen+perishable). 가중 기준풀(base_pool, evergreen)과 달리
    # 실제 고민·최신글을 끌어오는 용도라 신선한 perishable 도 포함한다.
    def _row_has_media(r: dict[str, Any]) -> bool:
        source = str(r.get("source") or "")
        url = str(r.get("url") or "")
        body = str(r.get("body") or "")
        if _media_kind(source, url) == "video" and not _video_source_is_relevant(r):
            return False
        return bool(url or body or _media_kind(source, url) in {"video", "paper", "article"})

    content_pool = [r for r in rows if (not seg) or r.get("segment") == seg]
    if seg and len(content_pool) < SEGMENT_MIN_ROWS:
        content_pool = rows
    media_pool = [r for r in rows if _row_has_media(r)]
    if media_pool:
        merged: list[dict[str, Any]] = []
        seen_row_keys: set[str] = set()
        for r in [*content_pool, *media_pool]:
            key = str(r.get("refined_id") or r.get("title") or id(r))
            if key in seen_row_keys:
                continue
            seen_row_keys.add(key)
            merged.append(r)
        content_pool = merged

    # (1) 요즘 같은 분들의 실제 고민 — collect_query 빈도 상위
    concern_count: dict[str, int] = {}
    for r in content_pool:
        if not _video_source_is_relevant(r):
            continue
        q = (r.get("collect_query") or "").strip()
        if q:
            concern_count[q] = concern_count.get(q, 0) + 1
    top_concerns = [{"concern": q, "count": c}
                    for q, c in sorted(concern_count.items(), key=lambda x: -x[1])[:6]]

    # (2) 최근 들어온 관련 글 — 동기(motivation) 버킷에 맞고 최신순. title 중복 제거.
    focus_topics = set(MOTIVATION_WEIGHTS.get(motivation, {}).keys()) or (
        {order[0]["topic"]} if order else set())
    cand = []
    for r in content_pool:
        if not _video_source_is_relevant(r):
            continue
        if not (str(r.get("url") or "").strip() or str(r.get("body") or "").strip()):
            continue
        title = (r.get("title") or "").strip()
        if not title:
            continue
        if focus_topics and not (set(_as_list(r.get("buckets"))) & focus_topics):
            continue
        cand.append(r)
    # 최신순(나이 오름차순). datetime/str 혼합 비교를 피하려 _age_days 정수 키로 정렬.
    pref = (media_preference or "mixed").strip().lower()

    def _highlight_rank(r: dict[str, Any]) -> tuple[int, int, int, int]:
        source = str(r.get("source") or "")
        url = str(r.get("url") or "")
        kind = _media_kind(source, url)
        body = str(r.get("body") or "")
        preferred = int(
            (pref == "video" and kind == "video")
            or (pref == "text" and kind in {"article", "paper"})
            or (pref == "visual" and kind == "video")
            or pref == "mixed"
        )
        media_bonus = int(bool(url)) + int(bool(body)) + int(kind in {"video", "paper", "article"})
        segment_bonus = int((not seg) or r.get("segment") == seg)
        return (-preferred, -media_bonus, -segment_bonus, _age_days(r.get("item_created_at"), now))

    cand.sort(key=_highlight_rank)
    highlights = []
    seen_titles: set[str] = set()
    for r in cand:
        source = (r.get("source") or "").strip()
        url = (r.get("url") or "").strip()
        kind = _media_kind(source, url)
        raw_title = str(r.get("raw_title") or "").strip()
        generated_title = (r.get("title") or "").strip()
        t = raw_title if kind == "video" and raw_title else generated_title
        key = t[:30]
        if key in seen_titles:
            continue
        seen_titles.add(key)
        body = str(r.get("body") or "").strip()
        highlights.append({
            "title": t,
            "generated_title": generated_title if generated_title != t else "",
            "days_ago": _age_days(r.get("item_created_at"), now),
            "models": _as_list(r.get("model_tags"))[:3],
            "concern": (r.get("collect_query") or "").strip(),
            "source": source,
            "url": url,
            "media_kind": kind,
            "refined_id": r.get("refined_id"),
            "body": body[:4000],
            "excerpt": body[:700],
        })
        if len(highlights) >= 12:
            break

    # (3) 최신성 노트 — 최근 글이 며칠 전 들어왔나(신뢰·생동감)
    ages = [_age_days(r.get("item_created_at"), now) for r in content_pool if r.get("item_created_at")]
    recent_30 = sum(1 for a in ages if a <= WINDOW_DAYS)
    fresh_note = {
        "pool_total": len(content_pool),
        "recent_30d": recent_30,
        "newest_days_ago": min(ages) if ages else None,
    }

    return {
        "attrs": {
            "llm": llm,
            "level": level,
            "motivation": motivation,
            "env": env,
            "job": job,
            "media_preference": media_preference,
        },
        "segment": seg,
        "base_pool": (f"segment:{seg}:{len(seg_rows)}" if use_seg
                      else f"global:{len(ever)}") + ("" if (use_seg or not seg) else " (fallback)"),
        "order": order,
        "overlay": overlay,
        "top_concerns": top_concerns,
        "highlights": highlights,
        "fresh_note": fresh_note,
    }


def load_evidence_rows() -> list[dict[str, Any]]:
    """edu_curriculum_evidence 전체를 개인화에 필요한 컬럼만 읽어온다."""
    from core.database import execute_query
    return execute_query(
        """
        SELECT
            e.klass,
            e.buckets,
            e.model_tags,
            e.item_created_at,
            e.segment,
            e.title,
            e.collect_query,
            e.refined_id,
            e.source,
            rs.raw_data->>'title' AS raw_title,
            rs.raw_data->>'description' AS raw_description,
            rs.raw_data->>'query' AS raw_query,
            rs.raw_data->>'channel' AS raw_channel,
            COALESCE(
                NULLIF(rs.raw_data->>'body', ''),
                NULLIF(rs.raw_data->>'content', ''),
                NULLIF(rs.raw_data->>'text', ''),
                NULLIF(rs.raw_data->>'description', ''),
                NULLIF(r.final_body, ''),
                NULLIF(f.summary, '')
            ) AS body,
            COALESCE(
                NULLIF(rs.raw_data->>'url', ''),
                NULLIF(rs.raw_data->>'link', ''),
                NULLIF(rs.raw_data->>'source_url', '')
            ) AS url
        FROM edu_curriculum_evidence e
        LEFT JOIN refined_outputs r ON r.id = e.refined_id
        LEFT JOIN filtered_signals f ON f.id = r.filtered_signal_id
        LEFT JOIN raw_signals rs ON rs.id = f.raw_signal_id
        """,
        fetch=True) or []
