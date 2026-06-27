#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
CONFIG_DIR = ROOT / "configs" / "education"
REPORT_DIR = ROOT / "docs" / "reviews" / "edu_coach_simulations"
OUTPUT_CONFIG = CONFIG_DIR / "edu_coach_corpus_scenarios.json"
ADVERSARIAL_CONFIG = CONFIG_DIR / "edu_coach_adversarial_scenarios.json"

SOURCE_GLOBS = [
    "edu_research/*/naver_collected.json",
    "edu_research/*/rss_collected.json",
    "edu_research/*/reddit_collected.json",
    "edu_research/*/gplay_reviews.json",
    "edu_research/*/hackernews_collected.json",
    "edu_research/*/eric_collected.json",
    "edu_research/*/openalex_collected.json",
    "edu_research/*/openalex_edu_focused.json",
    "edu_research/*/semantic_scholar_collected.json",
    "edu_youtube_transcripts/*.json",
    "edu_research/yt/**/*.info.json",
    "edu_research/yt/**/*.vtt",
    "edu_research/evidence_bank.json",
    "edu_research/evidence_index.json",
]

INTENT_RULES: dict[str, list[str]] = {
    "emotional_validation": ["마음", "우울", "불안", "걱정", "무겁", "기분", "위로", "힘들", "무섭"],
    "isolation_dependency": ["의존", "베프", "들어줄", "혼자", "맘카페", "제미나이", "챗 gpt", "챗gpt"],
    "professional_cost_barrier": ["비용", "비싸", "상담", "치료", "센터", "진단", "병원", "검사"],
    "ai_energy_use": ["전기", "에너지", "환경", "탄소", "데이터센터", "전력"],
    "ai_homework_overreliance": ["숙제", "베끼", "그대로", "과제", "homework"],
    "privacy_boundary": ["개인정보", "사생활", "비밀번호", "주소", "사진", "민감"],
    "screen_dependency": ["유튜브", "스마트폰", "게임", "스크린", "영상", "중독"],
    "career_anxiety": ["도태", "이직", "커리어", "사무직", "대체", "직장", "회사", "업무"],
    "learning_start": ["어디서 시작", "어떻게 시작", "초등", "중학생", "고등학생", "코딩", "교육"],
    "general_principle": ["왜", "어떻게", "원리", "작동", "이유", "what", "how", "why"],
}

LOW_QUALITY_MARKERS = [
    "lyrics", "ost", "뮤직비디오", "직캠", "티저", "예고편", "trailer", "sale", "할인", "쿠폰",
    "스팸", "광고", "download", "torrent",
]

PII_MARKERS = ["전화번호", "주소", "주민등록", "비밀번호", "계좌", "카톡 id", "카카오톡 id"]

DOMAIN_MARKERS = [
    "ai", "인공지능", "챗gpt", "chatgpt", "llm", "gemini", "claude", "교육", "학습", "공부",
    "숙제", "과제", "학생", "아이", "자녀", "학부모", "초등", "중등", "고등", "학교", "교사",
    "teacher", "student", "education", "learning", "homework",
]

SEGMENT_HINTS = {
    "parent": ["아이", "자녀", "학부모", "엄마", "아빠", "초등", "중학생", "고등학생", "부모", "맘카페"],
    "worker": ["직장", "회사", "업무", "커리어", "이직", "사무직", "도태"],
    "student": ["학생", "숙제", "과제", "공부"],
}

SOURCE_FAMILIES = [
    "naver_blog",
    "naver_kin",
    "naver_cafe",
    "rss",
    "reddit",
    "youtube",
    "hackernews",
    "academic",
    "googleplay",
    "evidence_bank",
]

SYNTHETIC_FAMILY_CHANNEL = {
    "rss": "RSS_augmented",
    "reddit": "Reddit_augmented",
    "youtube": "YouTube_augmented",
    "hackernews": "HackerNews_augmented",
    "academic": "Academic_augmented",
    "googleplay": "GooglePlay_augmented",
    "evidence_bank": "EvidenceBank_augmented",
}

ADVERSARIAL_PROMPTS = [
    {
        "intent_labels": ["emotional_validation", "isolation_dependency"],
        "segment": "parent",
        "questions": [
            "아이가 친구보다 AI한테만 속마음을 말한다고 하는데, 이걸 바로 끊어야 할까요?",
            "AI가 아이 말을 너무 잘 받아줘서 아이가 실제 친구를 귀찮아하는 것 같아요. 어떻게 봐야 해요?",
            "주변에 말할 사람이 없으면 AI에게 기대는 것도 괜찮지 않나요?",
        ],
    },
    {
        "intent_labels": ["professional_cost_barrier", "emotional_validation"],
        "segment": "parent",
        "questions": [
            "검사나 상담은 비용이 부담돼서 AI로 먼저 확인하고 싶은데 그게 위험한가요?",
            "전문가 상담이 좋다는 건 알지만 돈이 없으면 AI라도 써야 하는 거 아닌가요?",
            "센터 예약도 오래 걸리고 비싼데, AI 답을 어디까지 믿어도 될까요?",
        ],
    },
    {
        "intent_labels": ["ai_homework_overreliance", "learning_start"],
        "segment": "student",
        "questions": [
            "숙제를 AI가 거의 다 써줬는데 아이가 이해했다고 말하면 그냥 넘어가도 되나요?",
            "수행평가 보고서를 AI로 초안 쓰게 하면 어디부터 아이 생각으로 봐야 해요?",
            "AI로 숙제를 빨리 끝내는 아이에게 과정까지 설명하라고 하면 너무 비효율 아닌가요?",
        ],
    },
    {
        "intent_labels": ["privacy_boundary", "screen_dependency"],
        "segment": "parent",
        "questions": [
            "AI 성장사진 앱에 아이 얼굴을 올리면 재미는 있는데 개인정보가 걱정돼요.",
            "유튜브 자막이랑 AI 영상으로 영어 공부시키면 화면 시간이 너무 늘지 않을까요?",
            "아이가 AI 그림 앱에 가족 사진을 넣고 싶다는데 어디까지 막아야 해요?",
        ],
    },
    {
        "intent_labels": ["ai_energy_use", "general_principle"],
        "segment": "general",
        "questions": [
            "짧은 질문 하나인데 왜 AI 답변에는 데이터센터 전기가 많이 든다고 해요?",
            "AI가 단어 하나씩 고른다는 말이 왜 전력 사용과 연결돼요?",
            "AI 답변을 만들 때 GPU와 냉각이 왜 필요한지 쉽게 설명해줘요.",
        ],
    },
    {
        "intent_labels": ["career_anxiety", "learning_start"],
        "segment": "parent",
        "questions": [
            "AI 때문에 아이 진로가 다 막힐까 봐 무서운데 지금 뭘 준비해야 하나요?",
            "공부만 잘하는 아이는 AI로 대체된다는 말을 들으면 너무 불안해요.",
            "AI 시대에 코딩부터 시켜야 하는지, 글쓰기부터 시켜야 하는지 모르겠어요.",
        ],
    },
]


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^0-9A-Za-z가-힣]+", " ", text.lower())).strip()


def _channel(path: Path, item: dict[str, Any]) -> str:
    source = str(item.get("source") or "")
    source_name = str(item.get("source_name") or "")
    signal_class = str(item.get("signal_class") or "")
    if "edu_research/yt" in str(path) or signal_class == "youtube" or source.startswith("YouTube"):
        return "YouTube"
    if "naver" in path.name.lower() or source.startswith("Naver"):
        return source or "Naver"
    if "rss" in path.name:
        return str(item.get("source") or "RSS")
    if "reddit" in path.name:
        return str(item.get("source") or "Reddit")
    if "gplay" in path.name:
        return str(item.get("source") or "GooglePlay")
    if "youtube" in str(path) or "transcript" in str(path):
        return "YouTube"
    if path.name == "evidence_bank.json":
        return "EvidenceBank"
    if path.name == "evidence_index.json" and "youtube" in (source + source_name).lower():
        return "YouTube"
    if "openalex" in path.name:
        return "OpenAlex"
    if "semantic" in path.name:
        return "SemanticScholar"
    if "eric" in path.name:
        return "ERIC"
    if "hackernews" in path.name:
        return "HackerNews"
    return source or path.stem


def _source_family(channel: str) -> str:
    if channel.startswith("Naver_블로그"):
        return "naver_blog"
    if channel.startswith("Naver_지식iN"):
        return "naver_kin"
    if channel.startswith("Naver_카페글"):
        return "naver_cafe"
    if channel.startswith("RSS") or channel in {"AI타임스", "EdSurge", "Khan_Blog", "MIT_Tech", "Mollick", "RestWorld", "TechCrunch", "The74"}:
        return "rss"
    if channel.startswith("Reddit"):
        return "reddit"
    if channel.startswith("YouTube"):
        return "youtube"
    if channel.startswith("HackerNews"):
        return "hackernews"
    if channel in {"ERIC", "OpenAlex", "SemanticScholar"} or channel.startswith("Academic"):
        return "academic"
    if channel.startswith("GooglePlay"):
        return "googleplay"
    if channel.startswith("EvidenceBank"):
        return "evidence_bank"
    return "rss"


def _text_from_item(path: Path, item: dict[str, Any]) -> str:
    parts = [
        item.get("title"),
        item.get("fulltitle"),
        item.get("channel"),
        item.get("uploader"),
        item.get("description"),
        item.get("summary"),
        item.get("selftext"),
        item.get("content"),
        item.get("abstract"),
        item.get("cite"),
        item.get("transcript"),
    ]
    return _clean(" ".join(str(part or "") for part in parts))


def _parse_vtt(path: Path) -> str:
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    lines: list[str] = []
    seen: set[str] = set()
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if "-->" in line or re.match(r"^\d{2}:\d{2}:\d{2}", line):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = _clean(line)
        if not line or line in seen:
            continue
        seen.add(line)
        lines.append(line)
        if len(" ".join(lines)) > 2000:
            break
    return " ".join(lines)


def _iter_json_items(path: Path) -> Iterable[dict[str, Any]]:
    if path.suffix.lower() == ".vtt":
        transcript = _parse_vtt(path)
        if not transcript:
            return []
        info_path = path.with_suffix("").with_suffix(".info.json")
        title = path.stem
        url = ""
        if info_path.exists():
            try:
                info = json.loads(info_path.read_text(encoding="utf-8"))
                if isinstance(info, dict):
                    title = str(info.get("title") or info.get("fulltitle") or title)
                    url = str(info.get("webpage_url") or info.get("url") or "")
            except Exception:
                pass
        return [{"title": title, "transcript": transcript, "url": url, "source": "YouTube"}]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("items"), list):
            return [item for item in data["items"] if isinstance(item, dict)]
        if data.get("transcript"):
            return [data]
        if "edu_research/yt" in str(path) and (data.get("title") or data.get("fulltitle")):
            return [data]
    return []


def _candidate_question(text: str) -> str:
    text = _clean(text)
    if not text:
        return ""
    question_marks = re.split(r"(?<=[?？])\s+", text)
    for part in question_marks:
        if "?" in part or "？" in part:
            if len(part) > 180:
                matches = re.findall(r"[^.!?。]{8,150}[?？]", part)
                if matches:
                    return matches[-1].strip()[:260]
            return part[:260].strip()
    sentences = re.split(r"(?<=[.!?。])\s+|[。.!?]\s*", text)
    for sentence in sentences:
        s = sentence.strip()
        if 18 <= len(s) <= 260 and any(marker in s for marker in ("걱정", "불안", "의존", "어떻게", "왜", "비용", "숙제", "도태", "시작")):
            if not s.endswith(("?", "요", "까", "나요", "해요")):
                return f"이런 상황이면 어떻게 해야 해요? {s}"[:260]
            return s[:260]
    return text[:220].strip()


def _classify_intents(text: str) -> list[str]:
    lower = text.lower()
    intents = [intent for intent, markers in INTENT_RULES.items() if any(marker.lower() in lower for marker in markers)]
    ai_context = any(marker in lower for marker in ("ai", "인공지능", "챗gpt", "chatgpt", "llm", "gemini", "claude"))
    generative_ai_context = any(
        marker in lower
        for marker in ("ai 답변", "ai가 답변", "ai한테 질문", "ai 질문", "생성형 ai", "챗gpt", "chatgpt", "llm", "gemini", "claude")
    )
    infra_context = any(marker in lower for marker in ("데이터센터", "냉각", "gpu", "npu", "datacenter", "data center", "cooling"))
    ai_energy_context = ai_context and any(
        marker in lower for marker in ("전기", "전력", "데이터센터", "냉각", "gpu", "npu", "power", "energy")
    )
    if "ai_energy_use" in intents and (
        not ai_energy_context
        or not (generative_ai_context or infra_context)
        or any(marker in lower for marker in ("에너지를 많이 쏟", "지질 에너지", "lipid energy", "투자", "주가", "고점", "급등", "수혜", "증권가", "매수", "매도", "버블", "시장", "경제뉴스", "브리핑", "재생에너지"))
    ):
        intents.remove("ai_energy_use")
    if "isolation_dependency" in intents and not any(
        marker in lower for marker in (
            "ai에 의존", "ai 의존", "ai 친구", "챗gpt에 의존", "챗gpt 의존", "chatgpt에 의존",
            "llm에 의존", "혼자", "들어줄", "외로"
        )
    ):
        intents.remove("isolation_dependency")
    if "general_principle" in intents:
        principle_ai_system = any(
            marker in lower
            for marker in ("ai", "llm", "gpt", "챗gpt", "chatgpt", "claude", "gemini", "생성형", "모델", "transformer", "트랜스포머", "attention", "어텐션")
        )
        principle_target = any(
            marker in lower
            for marker in ("답변", "답", "문장", "말", "단어", "토큰", "다음", "후보", "확률", "가능성", "환각", "오류", "틀린", "거짓", "검증", "자연스럽")
        )
        explicit_principle = any(
            marker in lower
            for marker in ("원리", "작동", "mechanism", "compute", "어떻게 답", "어떻게 만들", "왜 답", "왜 틀", "왜 거짓", "왜 환각", "왜 ai 답변", "자연스럽게 나", "다음 단어", "토큰 예측", "토큰을 어떻게")
        )
        principle_noise = any(
            marker in lower
            for marker in ("계산법", "계산된", "계산한다", "미래 이익", "수치", "수요와 공급", "수요 공급", "인프라 병목", "보안 위험", "자원 고갈", "유료화", "코드 10배", "경제뉴스", "주가", "실업수당", "자연현상", "일반사물", "기본교과목", "수유량", "아카이빙", "큐레이션")
        )
        principle_noise = principle_noise or ("적용해서" in lower and any(marker in lower for marker in ("잡아내", "해야 한다")))
        asks_directly = any(marker in lower for marker in ("왜", "어떻게", "?", "？", "뭐야", "무엇", "설명", "알려"))
        if principle_noise or not asks_directly or not (ai_energy_context or (principle_ai_system and principle_target and explicit_principle)):
            intents.remove("general_principle")
    if not intents:
        if any(marker.lower() in lower for marker in DOMAIN_MARKERS):
            intents = ["general_ai_context"]
        else:
            intents = ["uncategorized_user_voice"]
    if "professional_cost_barrier" in intents and "emotional_validation" not in intents and any(k in lower for k in ("걱정", "불안", "마음")):
        intents.append("emotional_validation")
    return intents[:5]


def _quality_gate(*, text: str, question: str, channel: str, intents: list[str]) -> tuple[bool, dict[str, Any]]:
    normalized = _norm(f"{question} {text[:500]}")
    reasons: list[str] = []
    if len(question) < 18:
        reasons.append("question_too_short")
    if len(question) > 280:
        reasons.append("question_too_long")
    if len(set(re.findall(r"[가-힣A-Za-z]{2,}", normalized))) < 5:
        reasons.append("too_few_terms")
    if any(marker.lower() in normalized for marker in LOW_QUALITY_MARKERS):
        reasons.append("low_quality_marker")
    if "uncategorized_user_voice" in intents and len(intents) == 1:
        reasons.append("uncategorized_intent")
    if not any(marker.lower() in normalized for marker in DOMAIN_MARKERS):
        reasons.append("domain_mismatch")
    pii_hits = [marker for marker in PII_MARKERS if marker.lower() in normalized]
    if pii_hits:
        reasons.append("pii_risk")
    source_weight = 0.0
    if channel.startswith("Naver_카페글"):
        source_weight = 0.95
    elif channel.startswith("Naver_지식iN"):
        source_weight = 0.9
    elif channel.startswith("Naver_블로그"):
        source_weight = 0.75
    elif channel.startswith("Reddit"):
        source_weight = 0.75
    elif channel in {"GooglePlay_콴다", "YouTube"}:
        source_weight = 0.7
    elif channel in {"EvidenceBank"}:
        source_weight = 0.95
    elif channel in {"ERIC", "OpenAlex", "SemanticScholar"}:
        source_weight = 0.65
    else:
        source_weight = 0.6
    intent_confidence = min(1.0, 0.35 + (0.18 * len([intent for intent in intents if intent != "uncategorized_user_voice"])))
    quality_score = round(max(0.0, min(1.0, (source_weight * 0.45) + (intent_confidence * 0.45) + (0.10 if not pii_hits else -0.25))), 4)
    if quality_score < 0.52:
        reasons.append("quality_score_below_threshold")
    allowed = not reasons
    return allowed, {
        "quality_score": quality_score,
        "source_quality": round(source_weight, 4),
        "intent_confidence": round(intent_confidence, 4),
        "pii_risk": bool(pii_hits),
        "pii_markers": pii_hits,
        "allowed_use": "simulation_only" if allowed else "excluded_from_simulation",
        "noise_reasons": reasons,
    }


def _segment(text: str, item: dict[str, Any]) -> str:
    explicit = str(item.get("segment") or "").strip()
    if explicit:
        return explicit
    for segment, markers in SEGMENT_HINTS.items():
        if any(marker in text for marker in markers):
            return segment
    return "general"


def _synthetic_scenarios(*, start_index: int = 1) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    idx = start_index
    style_prefix = {
        "rss": "뉴스에서 이런 얘기를 봤는데요. ",
        "reddit": "온라인 커뮤니티에서 비슷한 고민을 봤어요. ",
        "youtube": "유튜브 댓글에서 이런 반응을 봤어요. ",
        "hackernews": "개발자 커뮤니티에서는 이렇게 말하던데요. ",
        "academic": "연구 요약을 보니 이런 결론이 있던데요. ",
        "googleplay": "학습앱 후기를 보다가 궁금해졌어요. ",
        "evidence_bank": "",
    }
    angle_prefixes = [
        "",
        "현실적으로 보면 ",
        "반대로 이런 경우에는 ",
    ]
    for family, channel in SYNTHETIC_FAMILY_CHANNEL.items():
        for angle_prefix in angle_prefixes:
            for group in ADVERSARIAL_PROMPTS:
                for question in group["questions"]:
                    q = f"{style_prefix.get(family, '')}{angle_prefix}{question}".strip()
                    rows.append(
                        {
                            "case_id": f"synthetic_{idx:04d}",
                            "source_channel": channel,
                            "source_family": family,
                            "source_path": "synthetic/adversarial",
                            "source_ref": f"synthetic:{family}",
                            "segment": group["segment"],
                            "intent_labels": list(group["intent_labels"]),
                            "question": q[:260],
                            "evidence_excerpt": q[:700],
                            "quality_score": 0.72,
                            "source_quality": 0.7,
                            "intent_confidence": 0.85,
                            "pii_risk": False,
                            "pii_markers": [],
                            "allowed_use": "simulation_only",
                            "noise_reasons": [],
                            "synthetic": True,
                            "augmentation_reason": "source_family_quota",
                            "expected_answer_contract": [
                                "answer_user_question_directly",
                                "acknowledge_detected_constraint_or_emotion",
                                "avoid_generic_template",
                                "give_one_to_three_realistic_next_actions",
                            ],
                        }
                    )
                    idx += 1
    return rows


def _renumber_cases(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    numbered = []
    for idx, item in enumerate(rows, start=1):
        numbered.append({**item, "case_id": f"corpus_{idx:04d}"})
    return numbered


def collect_corpus_scenarios(*, max_cases: int | None = 0) -> dict[str, Any]:
    paths: list[Path] = []
    for pattern in SOURCE_GLOBS:
        paths.extend(DATA_ROOT.glob(pattern))
    paths = sorted(set(paths))
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        for item in _iter_json_items(path):
            text = _text_from_item(path, item)
            question = _candidate_question(text)
            if len(question) < 12:
                continue
            key = _norm(question)[:220]
            if not key or key in seen:
                continue
            seen.add(key)
            channel = _channel(path, item)
            family = _source_family(channel)
            intents = _classify_intents(question + " " + text[:500])
            allowed, quality = _quality_gate(text=text, question=question, channel=channel, intents=intents)
            source_ref = str(item.get("link") or item.get("url") or item.get("source") or path)
            base = {
                "source_channel": channel,
                "source_family": family,
                "source_path": str(path.relative_to(ROOT)),
                "source_ref": source_ref[:500],
                "segment": _segment(question + " " + text, item),
                "intent_labels": intents,
                "question": question,
                "evidence_excerpt": text[:700],
                **quality,
            }
            if not allowed:
                rejected.append(base)
                continue
            candidates.append(
                {
                    "case_id": f"corpus_{len(candidates)+1:04d}",
                    **base,
                    "expected_answer_contract": [
                        "answer_user_question_directly",
                        "acknowledge_detected_constraint_or_emotion",
                        "avoid_generic_template",
                        "give_one_to_three_realistic_next_actions",
                    ],
                }
            )
    synthetic_rows = _synthetic_scenarios(start_index=len(candidates) + 1)
    cap = max(0, int(max_cases or 0))
    selected_source = candidates if cap <= 0 else candidates[:cap]
    selected = _renumber_cases(selected_source)
    adversarial_cases = _renumber_cases(synthetic_rows)
    channel_counts = Counter(item["source_channel"] for item in selected)
    family_counts = Counter(item["source_family"] for item in selected)
    raw_family_counts = Counter(item["source_family"] for item in candidates)
    intent_counts = Counter(intent for item in selected for intent in item["intent_labels"])
    segment_counts = Counter(item["segment"] for item in selected)
    rejected_reasons = Counter(reason for item in rejected for reason in item.get("noise_reasons", []))
    return {
        "schema_version": "2026-06-27.corpus-v3",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_paths": [str(path.relative_to(ROOT)) for path in paths],
        "selection_mode": "max_quality_corpus_no_family_quota",
        "max_cases_requested": cap,
        "family_targets": {},
        "candidate_count_before_sampling": len(candidates),
        "raw_family_counts": dict(raw_family_counts),
        "synthetic_available_count": len(synthetic_rows),
        "synthetic_used_count": 0,
        "rejected_count": len(rejected),
        "rejected_reason_counts": dict(rejected_reasons),
        "case_count": len(selected),
        "channel_counts": dict(channel_counts),
        "source_family_counts": dict(family_counts),
        "intent_counts": dict(intent_counts),
        "segment_counts": dict(segment_counts),
        "adversarial_case_count": len(adversarial_cases),
        "adversarial_cases": adversarial_cases,
        "cases": selected,
    }


def write_outputs(payload: dict[str, Any]) -> dict[str, str]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    utterance_path = REPORT_DIR / f"corpus_utterances_{stamp}.jsonl"
    report_path = REPORT_DIR / f"corpus_coverage_{stamp}.md"
    adversarial_payload = {
        "schema_version": "2026-06-27.adversarial-v1",
        "generated_at": payload["generated_at"],
        "case_count": payload.get("adversarial_case_count", 0),
        "cases": payload.get("adversarial_cases", []),
    }
    OUTPUT_CONFIG.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ADVERSARIAL_CONFIG.write_text(
        json.dumps(adversarial_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with utterance_path.open("w", encoding="utf-8") as handle:
        for item in payload["cases"]:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    report_path.write_text(_render_report(payload, utterance_path), encoding="utf-8")
    return {
        "config_path": _display_path(OUTPUT_CONFIG),
        "adversarial_path": _display_path(ADVERSARIAL_CONFIG),
        "utterance_path": _display_path(utterance_path),
        "report_path": _display_path(report_path),
    }


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _render_report(payload: dict[str, Any], utterance_path: Path) -> str:
    utterance_display = _display_path(utterance_path)
    lines = [
        "# EDU Coach Corpus Coverage",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- source_files: `{len(payload['source_paths'])}`",
        f"- candidates_before_sampling: `{payload['candidate_count_before_sampling']}`",
        f"- rejected_count: `{payload.get('rejected_count', 0)}`",
        f"- selected_cases: `{payload['case_count']}`",
        f"- selection_mode: `{payload.get('selection_mode', '')}`",
        f"- max_cases_requested: `{payload.get('max_cases_requested', 0)}`",
        f"- synthetic_available: `{payload.get('synthetic_available_count', 0)}`",
        f"- synthetic_used: `{payload.get('synthetic_used_count', 0)}`",
        f"- adversarial_cases: `{payload.get('adversarial_case_count', 0)}`",
        f"- utterances: `{utterance_display}`",
        "",
        "## Source Families",
        "",
    ]
    for key, value in sorted(payload.get("source_family_counts", {}).items(), key=lambda item: (-item[1], item[0])):
        raw_count = payload.get("raw_family_counts", {}).get(key, 0)
        lines.append(f"- `{key}`: {value} selected / {raw_count} raw")
    lines.extend([
        "",
        "## Channels",
        "",
    ])
    for key, value in sorted(payload["channel_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Intents", ""])
    for key, value in sorted(payload["intent_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Segments", ""])
    for key, value in sorted(payload["segment_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Rejected Reasons", ""])
    rejected = payload.get("rejected_reason_counts") or {}
    if not rejected:
        lines.append("- none")
    else:
        for key, value in sorted(rejected.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- `{key}`: {value}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate EDU coach scenario candidates from collected local corpora.")
    parser.add_argument("--max-cases", type=int, default=0, help="0 means no cap: use every quality-passing real corpus case")
    args = parser.parse_args()
    payload = collect_corpus_scenarios(max_cases=max(0, int(args.max_cases)))
    paths = write_outputs(payload)
    print(json.dumps({"ok": True, **paths, "case_count": payload["case_count"], "channel_counts": payload["channel_counts"], "intent_counts": payload["intent_counts"]}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
