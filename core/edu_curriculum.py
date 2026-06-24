"""edu 입문 커리큘럼 개인화 — 공유 로직.

CLI(scripts/build_edu_curriculum.py)와 백엔드(harness-os/backend/main.py)가 함께 쓴다.
요청 시점에 '미리 적재된 evidence 풀'을 사용자 속성으로 재가중·재정렬하는 순수 함수가 핵심.
파이프라인을 재실행하지 않으므로 밀리초 단위로 즉시 재편된다.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
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


def personalize(
    rows: list[dict[str, Any]],
    *,
    llm: str = "",
    level: str = "",
    motivation: str = "",
    env: str = "",
    job: str = "",
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

    return {
        "attrs": {"llm": llm, "level": level, "motivation": motivation, "env": env, "job": job},
        "segment": seg,
        "base_pool": (f"segment:{seg}:{len(seg_rows)}" if use_seg
                      else f"global:{len(ever)}") + ("" if (use_seg or not seg) else " (fallback)"),
        "order": order,
        "overlay": overlay,
    }


def load_evidence_rows() -> list[dict[str, Any]]:
    """edu_curriculum_evidence 전체를 개인화에 필요한 컬럼만 읽어온다."""
    from core.database import execute_query
    return execute_query(
        "SELECT klass, buckets, model_tags, item_created_at, segment FROM edu_curriculum_evidence",
        fetch=True) or []
