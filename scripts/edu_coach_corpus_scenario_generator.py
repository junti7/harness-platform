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
    "edu_research/evidence_bank.json",
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

SEGMENT_HINTS = {
    "parent": ["아이", "자녀", "학부모", "엄마", "아빠", "초등", "중학생", "고등학생", "부모", "맘카페"],
    "worker": ["직장", "회사", "업무", "커리어", "이직", "사무직", "도태"],
    "student": ["학생", "숙제", "과제", "공부"],
}


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^0-9A-Za-z가-힣]+", " ", text.lower())).strip()


def _channel(path: Path, item: dict[str, Any]) -> str:
    source = str(item.get("source") or "")
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
    if "openalex" in path.name:
        return "OpenAlex"
    if "semantic" in path.name:
        return "SemanticScholar"
    if "eric" in path.name:
        return "ERIC"
    if "hackernews" in path.name:
        return "HackerNews"
    return source or path.stem


def _text_from_item(path: Path, item: dict[str, Any]) -> str:
    parts = [
        item.get("title"),
        item.get("description"),
        item.get("summary"),
        item.get("selftext"),
        item.get("content"),
        item.get("abstract"),
        item.get("cite"),
        item.get("transcript"),
    ]
    return _clean(" ".join(str(part or "") for part in parts))


def _iter_json_items(path: Path) -> Iterable[dict[str, Any]]:
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
    return []


def _candidate_question(text: str) -> str:
    text = _clean(text)
    if not text:
        return ""
    question_marks = re.split(r"(?<=[?？])\s+", text)
    for part in question_marks:
        if "?" in part or "？" in part:
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
    if not intents:
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


def collect_corpus_scenarios(*, max_cases: int = 500) -> dict[str, Any]:
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
            intents = _classify_intents(question + " " + text[:500])
            allowed, quality = _quality_gate(text=text, question=question, channel=channel, intents=intents)
            source_ref = str(item.get("link") or item.get("url") or item.get("source") or path)
            base = {
                "source_channel": channel,
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
    # Channel and intent balanced sampling.
    by_bucket: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        primary_intent = item["intent_labels"][0]
        by_bucket[(item["source_channel"], primary_intent)].append(item)
    selected: list[dict[str, Any]] = []
    round_index = 0
    buckets = sorted(by_bucket)
    while len(selected) < max_cases:
        added = False
        for bucket in buckets:
            items = by_bucket[bucket]
            if round_index < len(items):
                selected.append(items[round_index])
                added = True
                if len(selected) >= max_cases:
                    break
        if not added:
            break
        round_index += 1
    channel_counts = Counter(item["source_channel"] for item in selected)
    intent_counts = Counter(intent for item in selected for intent in item["intent_labels"])
    segment_counts = Counter(item["segment"] for item in selected)
    rejected_reasons = Counter(reason for item in rejected for reason in item.get("noise_reasons", []))
    return {
        "schema_version": "2026-06-27.corpus-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_paths": [str(path.relative_to(ROOT)) for path in paths],
        "candidate_count_before_sampling": len(candidates),
        "rejected_count": len(rejected),
        "rejected_reason_counts": dict(rejected_reasons),
        "case_count": len(selected),
        "channel_counts": dict(channel_counts),
        "intent_counts": dict(intent_counts),
        "segment_counts": dict(segment_counts),
        "cases": selected,
    }


def write_outputs(payload: dict[str, Any]) -> dict[str, str]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    utterance_path = REPORT_DIR / f"corpus_utterances_{stamp}.jsonl"
    report_path = REPORT_DIR / f"corpus_coverage_{stamp}.md"
    OUTPUT_CONFIG.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with utterance_path.open("w", encoding="utf-8") as handle:
        for item in payload["cases"]:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    report_path.write_text(_render_report(payload, utterance_path), encoding="utf-8")
    return {
        "config_path": _display_path(OUTPUT_CONFIG),
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
        f"- utterances: `{utterance_display}`",
        "",
        "## Channels",
        "",
    ]
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
    parser.add_argument("--max-cases", type=int, default=500)
    args = parser.parse_args()
    payload = collect_corpus_scenarios(max_cases=max(1, int(args.max_cases)))
    paths = write_outputs(payload)
    print(json.dumps({"ok": True, **paths, "case_count": payload["case_count"], "channel_counts": payload["channel_counts"], "intent_counts": payload["intent_counts"]}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
