#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_BANK_PATH = ROOT / "data" / "edu_research" / "evidence_bank.json"
OBSERVATIONS_PATH = ROOT / "data" / "edu_research" / "manual_observations.jsonl"
RUNTIME_EVENTS_PATH = ROOT / "runtime" / "edu_pilot_runtime_events.jsonl"
OUTPUT_PATH = ROOT / "runtime" / "edu_pattern_intelligence.json"
HISTORY_PATH = ROOT / "runtime" / "edu_pattern_history.jsonl"
RED_TEAM_REVIEW_GLOB = "edu_pattern_intelligence_red_team_*.md"

WEIGHTS = {
    "frequency": 0.35,
    "urgency": 0.20,
    "frustration_intensity": 0.20,
    "execution_block": 0.10,
    "cross_source_support": 0.15,
}

PARENT_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern_id": "parent-ai-dependency-fear",
        "segment": "parent",
        "label": "아이의 AI 의존 심화 불안",
        "pain_category": "dependency_fear",
        "desire_category": "realistic_rule",
        "keywords": ["의존", "의지", "대신", "스스로", "혼자", "shortcut", "shortcutting", "편하게", "생각 안", "반복해야"],
        "urgency_keywords": ["지금", "이미", "빨리", "급", "위험", "무너", "1년"],
        "execution_keywords": ["어떻게", "기준", "규칙", "룰", "잡아", "막막", "모르"],
        "failure_modes": ["도구 금지만 강조하는 답변", "아이의 실제 사용 맥락 없이 일반론으로 끝나는 답변"],
        "safe_prompt_hints": ["사용자가 말한 자녀 학년과 현재 사용 습관부터 확인한다.", "금지보다 사용 규칙 설계를 먼저 제안한다."],
        "avoid_response_patterns": ["'무조건 막으세요' 같은 단정", "도덕 공포만 반복하는 문장"],
    },
    {
        "pattern_id": "parent-academic-integrity-fear",
        "segment": "parent",
        "label": "숙제·읽기·사고력 붕괴 우려",
        "pain_category": "academic_integrity_fear",
        "desire_category": "conversation_script",
        "keywords": ["숙제", "과제", "논문", "책", "읽지", "읽기", "사고력", "표절", "써주", "cheat", "essay"],
        "urgency_keywords": ["당장", "학교", "무너", "걱정", "심각"],
        "execution_keywords": ["대화", "말해", "지도", "기준", "어떻게"],
        "failure_modes": ["학습 윤리만 말하고 부모가 오늘 밤 할 행동을 주지 않는 답변"],
        "safe_prompt_hints": ["불안의 대상이 숙제인지 독서인지 먼저 분리한다.", "부모가 바로 쓸 수 있는 질문 문장을 준다."],
        "avoid_response_patterns": ["'AI 쓰면 다 망합니다' 식 과장", "근거 없는 학교 제재 공포 조장"],
    },
    {
        "pattern_id": "parent-ai-literacy-gap",
        "segment": "parent",
        "label": "부모 본인의 AI 이해 부족 불안",
        "pain_category": "ai_literacy_gap",
        "desire_category": "step_by_step_start",
        "keywords": ["부모", "보호자", "내가 먼저", "모르", "기초", "사용법", "시작", "뭘", "어디서", "tool"],
        "urgency_keywords": ["지금", "뒤처", "빨리", "먼저"],
        "execution_keywords": ["처음", "기초", "오늘", "시작", "1단계", "step"],
        "failure_modes": ["부모를 초보자로 인정하지 않고 어려운 툴 나열로 끝나는 답변"],
        "safe_prompt_hints": ["부모가 이해해야 할 최소 개념부터 제시한다.", "도구보다 사용 원칙을 먼저 정리한다."],
        "avoid_response_patterns": ["툴 목록만 나열", "전문가 용어를 설명 없이 사용하는 답변"],
    },
    {
        "pattern_id": "parent-parenting-conflict",
        "segment": "parent",
        "label": "가정 내 AI 사용 규칙 갈등",
        "pain_category": "parenting_conflict",
        "desire_category": "conversation_script",
        "keywords": ["갈등", "싸움", "남편", "아내", "가족", "규칙", "허용", "통제", "반대", "충돌"],
        "urgency_keywords": ["매일", "계속", "심해", "버거"],
        "execution_keywords": ["합의", "대화", "문장", "기준", "원칙"],
        "failure_modes": ["아이 문제로만 축소하고 보호자 간 충돌을 무시하는 답변"],
        "safe_prompt_hints": ["부모 간 원칙 합의가 필요한지 먼저 확인한다.", "대화 스크립트를 준다."],
        "avoid_response_patterns": ["한쪽 보호자만 탓하는 문장", "즉시 통제 강화만 제안"],
    },
]

WORKER_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern_id": "worker-career-replacement-fear",
        "segment": "worker",
        "label": "일자리 대체·뒤처짐 불안",
        "pain_category": "career_replacement_fear",
        "desire_category": "future_roadmap",
        "keywords": ["뒤처", "대체", "일자리", "해고", "커리어", "경쟁력", "끝이다", "못 따라가"],
        "urgency_keywords": ["당장", "지금", "곧", "빠르게", "급"],
        "execution_keywords": ["어떻게", "준비", "뭘", "무엇부터", "roadmap", "순서"],
        "failure_modes": ["공포만 키우고 현실적인 2주 행동 계획이 없는 답변"],
        "safe_prompt_hints": ["직무와 현재 AI 사용 정도를 먼저 묻는다.", "불안을 행동 단위로 쪼갠다."],
        "avoid_response_patterns": ["'당장 갈아타세요' 같은 과격한 단정", "직무 맥락 없는 업계 전망 반복"],
    },
    {
        "pattern_id": "worker-tool-choice-overload",
        "segment": "worker",
        "label": "도구 과잉·모델 선택 혼란",
        "pain_category": "tool_choice_overload",
        "desire_category": "comparative_benchmark",
        "keywords": ["툴", "tool", "모델", "뭘 써", "어떤", "너무 많", "헷갈", "비교"],
        "urgency_keywords": ["매일", "자꾸", "시간 낭비"],
        "execution_keywords": ["비교", "선택", "기준", "한 개", "먼저"],
        "failure_modes": ["모든 툴을 다 써보라고 하는 답변"],
        "safe_prompt_hints": ["현재 업무 1개를 기준으로 도구를 줄인다.", "선택 기준 2~3개만 준다."],
        "avoid_response_patterns": ["긴 툴 리스트", "업무와 무관한 추천"],
    },
    {
        "pattern_id": "worker-decision-paralysis",
        "segment": "worker",
        "label": "무엇부터 해야 할지 모르는 정지 상태",
        "pain_category": "decision_paralysis",
        "desire_category": "step_by_step_start",
        "keywords": ["무엇부터", "뭘 해야", "막막", "모르겠", "start", "처음", "정리 안", "결정 못"],
        "urgency_keywords": ["계속", "답답", "정체", "시간만"],
        "execution_keywords": ["오늘", "한 개", "첫 단계", "바로", "실행"],
        "failure_modes": ["막막함을 공감만 하고 출발 과제를 안 주는 답변"],
        "safe_prompt_hints": ["첫 실행 과제 1개를 가장 먼저 준다.", "성과 측정 기준을 붙인다."],
        "avoid_response_patterns": ["비전 이야기만 길게 하는 답변", "실행 과제 없는 격려"],
    },
    {
        "pattern_id": "worker-trust-gap",
        "segment": "worker",
        "label": "AI 답변 신뢰 부족",
        "pain_category": "trust_in_answer_gap",
        "desire_category": "realistic_rule",
        "keywords": ["믿", "신뢰", "틀리", "hallucination", "환각", "검증", "사실", "엉터리"],
        "urgency_keywords": ["회사", "업무", "실수", "리스크"],
        "execution_keywords": ["검증", "체크", "근거", "사실확인", "rule"],
        "failure_modes": ["신뢰 문제를 '익숙해지세요'로 덮는 답변"],
        "safe_prompt_hints": ["답변 검증 루프를 명시한다.", "근거 확인 단계를 제시한다."],
        "avoid_response_patterns": ["모델 맹신 유도", "근거 없이 확신하는 문장"],
    },
]

COMPLAINT_RULES: list[dict[str, Any]] = [
    {
        "complaint_type": "generic_answer_complaint",
        "keywords": ["뻔", "일반론", "generic", "template", "복붙", "뜬구름", "알맹이 없"],
        "label": "일반론·템플릿 답변 불만",
    },
    {
        "complaint_type": "realism_gap_complaint",
        "keywords": ["현실감", "현장감", "사례 부족", "실제", "community", "맘카페", "blind", "구체적이지"],
        "label": "현실성·현장감 부족 불만",
    },
    {
        "complaint_type": "overgeneralization_complaint",
        "keywords": ["단정", "일반화", "stereotype", "고정관념", "너무 쉽게", "모두 그렇"],
        "label": "과잉 일반화 불만",
    },
]

NEGATIVE_WORDS = ["걱정", "불안", "막막", "답답", "위험", "무섭", "심각", "부담", "갈등", "혼란", "confused", "anxious"]
EXECUTION_BLOCK_WORDS = ["어떻게", "뭘", "무엇부터", "모르", "막혀", "막히", "시작", "기준", "정리", "step", "first"]


@dataclass
class SourceFact:
    source_type: str
    segment: str
    text: str
    observed_at: str | None
    source_label: str
    provenance: dict[str, Any]
    matched_keywords: list[str]
    urgency_hits: int
    execution_hits: int
    negative_hits: int
    complaint_signal: bool
    complaint_type: str | None
    complaint_severity: int


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            if isinstance(raw, dict):
                rows.append(raw)
    except Exception:
        return rows
    return rows


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _count_hits(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    normalized = _normalize(text)
    matches = [kw for kw in keywords if kw.lower() in normalized]
    return len(matches), matches


def _detect_complaint(text: str) -> tuple[bool, str | None, int, list[str]]:
    normalized = _normalize(text)
    best_type = None
    best_hits = 0
    best_words: list[str] = []
    for rule in COMPLAINT_RULES:
        hits = [kw for kw in rule["keywords"] if kw.lower() in normalized]
        if len(hits) > best_hits:
            best_hits = len(hits)
            best_type = rule["complaint_type"]
            best_words = hits
    severity = min(10, best_hits * 3) if best_hits else 0
    return best_hits > 0, best_type, severity, best_words


def _safe_excerpt(text: str, cap: int = 220) -> str:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    return clean[:cap] + ("…" if len(clean) > cap else "")


def _excluded_sample(
    reason: str,
    excerpt: str,
    meta: dict[str, Any] | None = None,
    source_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "reason": reason,
        "excerpt": _safe_excerpt(excerpt),
        "meta": meta or {},
        "source_ref": source_ref or {},
    }


def _source_ref_from_fact(fact: SourceFact) -> dict[str, Any]:
    ref = {
        "type": fact.source_type,
        "label": fact.source_label,
        "observed_at": fact.observed_at,
    }
    if fact.source_type in {"research_policy", "community_voice", "general_reference", "unknown"}:
        ref.update({
            "resolver": "evidence_bank",
            "id": fact.provenance.get("id"),
            "path": fact.provenance.get("path"),
        })
    elif fact.source_type == "runtime_event":
        ref.update({
            "resolver": "runtime_event",
            "event_type": (fact.provenance.get("row") or {}).get("event_type"),
            "ts": (fact.provenance.get("row") or {}).get("ts"),
        })
    elif fact.source_type == "operator_note":
        ref.update({
            "resolver": "manual_observation",
            "id": fact.provenance.get("id"),
            "url": fact.provenance.get("url"),
        })
    elif fact.source_type == "transcript":
        ref.update({
            "resolver": "transcript_turn",
            "case_id": fact.provenance.get("case_id"),
            "turn_no": fact.provenance.get("turn_no"),
        })
    else:
        ref.update({"resolver": "unknown"})
    return ref


def _load_db_turns() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    details = {
        "available": False,
        "query_ok": False,
        "case_count": 0,
        "turn_count": 0,
        "error": None,
    }
    try:
        from core.database import execute_query
    except Exception as exc:
        details["error"] = f"database_import_failed:{type(exc).__name__}"
        return [], details

    if not os.getenv("DATABASE_URL"):
        details["error"] = "DATABASE_URL missing"
        return [], details

    try:
        table_rows = execute_query(
            "SELECT count(*) AS c FROM information_schema.tables WHERE table_name='edu_case_turns'",
            fetch=True,
        ) or []
        if not table_rows or int(table_rows[0]["c"] or 0) == 0:
            details["error"] = "edu_case_turns table missing"
            return [], details
        rows = execute_query(
            """
            SELECT
              t.case_id,
              t.turn_no,
              t.role,
              t.text,
              t.phase,
              t.created_at,
              c.status,
              cu.segment,
              cu.preferred_salutation
            FROM edu_case_turns t
            JOIN edu_cases c ON c.id = t.case_id
            JOIN edu_customers cu ON cu.id = c.customer_id
            ORDER BY t.created_at DESC
            LIMIT 500
            """,
            fetch=True,
        ) or []
        details["available"] = True
        details["query_ok"] = True
        details["turn_count"] = len(rows)
        details["case_count"] = len({int(row["case_id"]) for row in rows if row.get("case_id") is not None})
        return rows, details
    except Exception as exc:
        details["error"] = f"{type(exc).__name__}:{str(exc)[:180]}"
        return [], details


def _extract_facts_from_evidence(items: list[dict[str, Any]], pattern_defs: list[dict[str, Any]]) -> dict[str, list[SourceFact]]:
    facts: dict[str, list[SourceFact]] = defaultdict(list)
    for item in items:
        text = " ".join(
            str(item.get(key) or "")
            for key in ("cite", "source", "type", "title", "summary", "note")
        )
        segment = item.get("segment") or "parent"
        source_kind = item.get("source_kind") or "unknown"
        source_label = item.get("source") or item.get("type") or "evidence_bank"
        for pattern in pattern_defs:
            if pattern["segment"] != segment:
                continue
            hit_count, matched = _count_hits(text, pattern["keywords"])
            if hit_count == 0:
                continue
            urgency_hits, _ = _count_hits(text, pattern["urgency_keywords"])
            execution_hits, _ = _count_hits(text, pattern["execution_keywords"])
            negative_hits, _ = _count_hits(text, NEGATIVE_WORDS)
            complaint_signal, complaint_type, complaint_severity, complaint_words = _detect_complaint(text)
            facts[pattern["pattern_id"]].append(
                SourceFact(
                    source_type=source_kind,
                    segment=segment,
                    text=_safe_excerpt(text),
                    observed_at=None,
                    source_label=str(source_label),
                    provenance={
                        "path": str(EVIDENCE_BANK_PATH.relative_to(ROOT)),
                        "id": item.get("id"),
                        "evergreen": bool(item.get("evergreen")),
                        "provenance": item.get("provenance"),
                    },
                    matched_keywords=sorted(set(matched + complaint_words)),
                    urgency_hits=urgency_hits,
                    execution_hits=execution_hits,
                    negative_hits=negative_hits,
                    complaint_signal=complaint_signal,
                    complaint_type=complaint_type,
                    complaint_severity=complaint_severity,
                )
            )
    return facts


def _funnel_for_evidence(items: list[dict[str, Any]], pattern_defs: list[dict[str, Any]]) -> dict[str, Any]:
    total_rows = len(items)
    rows_with_match = 0
    included_facts = 0
    excluded_samples: list[dict[str, Any]] = []
    segment_counts = Counter(str(item.get("segment") or "parent") for item in items)
    source_kind_counts = Counter(str(item.get("source_kind") or "unknown") for item in items)
    for item in items:
        text = " ".join(str(item.get(key) or "") for key in ("cite", "source", "type", "title", "summary", "note"))
        segment = item.get("segment") or "parent"
        source_kind = str(item.get("source_kind") or "unknown")
        source_label = str(item.get("source") or item.get("type") or "evidence_bank")
        row_hits = 0
        for pattern in pattern_defs:
            if pattern["segment"] != segment:
                continue
            hit_count, _ = _count_hits(text, pattern["keywords"])
            if hit_count > 0:
                row_hits += 1
        if row_hits > 0:
            rows_with_match += 1
            included_facts += row_hits
        elif len(excluded_samples) < 3:
            excluded_samples.append(_excluded_sample(
                "no_pattern_keyword_match",
                text,
                {
                    "id": item.get("id"),
                    "segment": segment,
                    "source_kind": source_kind,
                    "source": source_label,
                },
                {
                    "resolver": "evidence_bank",
                    "id": item.get("id"),
                },
            ))
    return {
        "source_key": "evidence_bank",
        "label": "Evidence bank",
        "total_rows": total_rows,
        "scanned_rows": total_rows,
        "eligible_rows": total_rows,
        "rows_with_match": rows_with_match,
        "unique_rows_linked": rows_with_match,
        "included_fact_count": included_facts,
        "excluded_rows": max(0, total_rows - rows_with_match),
        "excluded_reason_counts": {
            "no_pattern_keyword_match": max(0, total_rows - rows_with_match),
        },
        "excluded_samples": excluded_samples,
        "notes": [
            "evidence_bank는 segment가 맞는 pattern keyword 1개 이상 hit해야 fact로 연결된다.",
            "complaint rule만으로는 evidence_bank fact를 만들지 않는다.",
        ],
        "segment_counts": dict(segment_counts),
        "source_kind_counts": dict(source_kind_counts),
    }


def _extract_facts_from_turns(rows: list[dict[str, Any]], pattern_defs: list[dict[str, Any]]) -> dict[str, list[SourceFact]]:
    facts: dict[str, list[SourceFact]] = defaultdict(list)
    for row in rows:
        if str(row.get("role") or "").lower() != "user":
            continue
        text = str(row.get("text") or "")
        segment = row.get("segment") or "parent"
        complaint_signal, complaint_type, complaint_severity, complaint_words = _detect_complaint(text)
        for pattern in pattern_defs:
            if pattern["segment"] != segment:
                continue
            hit_count, matched = _count_hits(text, pattern["keywords"])
            if hit_count == 0 and not complaint_signal:
                continue
            urgency_hits, _ = _count_hits(text, pattern["urgency_keywords"])
            execution_hits, _ = _count_hits(text, pattern["execution_keywords"])
            negative_hits, _ = _count_hits(text, NEGATIVE_WORDS)
            facts[pattern["pattern_id"]].append(
                SourceFact(
                    source_type="transcript",
                    segment=segment,
                    text=_safe_excerpt(text),
                    observed_at=row.get("created_at").isoformat() if hasattr(row.get("created_at"), "isoformat") else str(row.get("created_at") or ""),
                    source_label=f"case:{row.get('case_id')} turn:{row.get('turn_no')}",
                    provenance={
                        "case_id": row.get("case_id"),
                        "turn_no": row.get("turn_no"),
                        "phase": row.get("phase"),
                        "status": row.get("status"),
                    },
                    matched_keywords=sorted(set(matched + complaint_words)),
                    urgency_hits=urgency_hits,
                    execution_hits=execution_hits,
                    negative_hits=negative_hits,
                    complaint_signal=complaint_signal,
                    complaint_type=complaint_type,
                    complaint_severity=complaint_severity,
                )
            )
    return facts


def _funnel_for_turns(rows: list[dict[str, Any]], pattern_defs: list[dict[str, Any]]) -> dict[str, Any]:
    total_rows = len(rows)
    scanned_rows = 0
    rows_with_match = 0
    complaint_only_rows = 0
    included_facts = 0
    excluded_non_user = 0
    excluded_no_match = 0
    excluded_samples: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("role") or "").lower() != "user":
            excluded_non_user += 1
            if len(excluded_samples) < 3:
                excluded_samples.append(_excluded_sample(
                    "assistant_or_system_turn",
                    str(row.get("text") or ""),
                    {
                        "case_id": row.get("case_id"),
                        "turn_no": row.get("turn_no"),
                        "role": row.get("role"),
                        "segment": row.get("segment"),
                    },
                    {
                        "resolver": "transcript_turn",
                        "case_id": row.get("case_id"),
                        "turn_no": row.get("turn_no"),
                    },
                ))
            continue
        scanned_rows += 1
        text = str(row.get("text") or "")
        segment = row.get("segment") or "parent"
        complaint_signal, _, _, _ = _detect_complaint(text)
        row_hits = 0
        matched_pattern = False
        for pattern in pattern_defs:
            if pattern["segment"] != segment:
                continue
            hit_count, _ = _count_hits(text, pattern["keywords"])
            if hit_count > 0:
                matched_pattern = True
                row_hits += 1
            elif complaint_signal:
                row_hits += 1
        if row_hits == 0:
            excluded_no_match += 1
            if len(excluded_samples) < 3:
                excluded_samples.append(_excluded_sample(
                    "no_pattern_keyword_or_complaint_match",
                    text,
                    {
                        "case_id": row.get("case_id"),
                        "turn_no": row.get("turn_no"),
                        "role": row.get("role"),
                        "segment": segment,
                    },
                    {
                        "resolver": "transcript_turn",
                        "case_id": row.get("case_id"),
                        "turn_no": row.get("turn_no"),
                    },
                ))
            continue
        rows_with_match += 1
        included_facts += row_hits
        if complaint_signal and not matched_pattern:
            complaint_only_rows += 1
    return {
        "source_key": "transcript_db",
        "label": "Transcript DB",
        "total_rows": total_rows,
        "scanned_rows": scanned_rows,
        "eligible_rows": scanned_rows,
        "rows_with_match": rows_with_match,
        "unique_rows_linked": rows_with_match,
        "included_fact_count": included_facts,
        "excluded_rows": excluded_non_user + excluded_no_match,
        "excluded_reason_counts": {
            "assistant_or_system_turn": excluded_non_user,
            "no_pattern_keyword_or_complaint_match": excluded_no_match,
        },
        "excluded_samples": excluded_samples,
        "complaint_only_rows": complaint_only_rows,
        "notes": [
            "transcript는 user role turn만 스캔한다.",
            "pattern keyword hit가 없더라도 complaint rule hit면 같은 segment pattern 후보들에 연결될 수 있다.",
        ],
    }


def _extract_facts_from_runtime(rows: list[dict[str, Any]], pattern_defs: list[dict[str, Any]]) -> dict[str, list[SourceFact]]:
    facts: dict[str, list[SourceFact]] = defaultdict(list)
    for row in rows:
        text = " ".join(str(row.get(key) or "") for key in ("event_type", "error", "reason", "segment", "track"))
        segment = row.get("segment") or "parent"
        complaint_signal, complaint_type, complaint_severity, complaint_words = _detect_complaint(text)
        for pattern in pattern_defs:
            if pattern["segment"] != segment:
                continue
            hit_count, matched = _count_hits(text, pattern["keywords"])
            if hit_count == 0 and not complaint_signal:
                continue
            urgency_hits, _ = _count_hits(text, pattern["urgency_keywords"])
            execution_hits, _ = _count_hits(text, pattern["execution_keywords"])
            negative_hits, _ = _count_hits(text, NEGATIVE_WORDS)
            facts[pattern["pattern_id"]].append(
                SourceFact(
                    source_type="runtime_event",
                    segment=segment,
                    text=_safe_excerpt(text),
                    observed_at=str(row.get("ts") or ""),
                    source_label=str(row.get("event_type") or "runtime"),
                    provenance={"row": row},
                    matched_keywords=sorted(set(matched + complaint_words)),
                    urgency_hits=urgency_hits,
                    execution_hits=execution_hits,
                    negative_hits=negative_hits,
                    complaint_signal=complaint_signal,
                    complaint_type=complaint_type,
                    complaint_severity=complaint_severity,
                )
            )
    return facts


def _funnel_for_runtime(rows: list[dict[str, Any]], pattern_defs: list[dict[str, Any]]) -> dict[str, Any]:
    total_rows = len(rows)
    rows_with_match = 0
    complaint_only_rows = 0
    included_facts = 0
    excluded_no_match = 0
    excluded_samples: list[dict[str, Any]] = []
    for row in rows:
        text = " ".join(str(row.get(key) or "") for key in ("event_type", "error", "reason", "segment", "track"))
        segment = row.get("segment") or "parent"
        complaint_signal, _, _, _ = _detect_complaint(text)
        row_hits = 0
        matched_pattern = False
        for pattern in pattern_defs:
            if pattern["segment"] != segment:
                continue
            hit_count, _ = _count_hits(text, pattern["keywords"])
            if hit_count > 0:
                matched_pattern = True
                row_hits += 1
            elif complaint_signal:
                row_hits += 1
        if row_hits == 0:
            excluded_no_match += 1
            if len(excluded_samples) < 3:
                excluded_samples.append(_excluded_sample(
                    "no_pattern_keyword_or_complaint_match",
                    text,
                    {
                        "event_type": row.get("event_type"),
                        "segment": segment,
                        "ts": row.get("ts"),
                    },
                    {
                        "resolver": "runtime_event",
                        "event_type": row.get("event_type"),
                        "ts": row.get("ts"),
                    },
                ))
            continue
        rows_with_match += 1
        included_facts += row_hits
        if complaint_signal and not matched_pattern:
            complaint_only_rows += 1
    return {
        "source_key": "runtime_events",
        "label": "Runtime events",
        "total_rows": total_rows,
        "scanned_rows": total_rows,
        "eligible_rows": total_rows,
        "rows_with_match": rows_with_match,
        "unique_rows_linked": rows_with_match,
        "included_fact_count": included_facts,
        "excluded_rows": excluded_no_match,
        "excluded_reason_counts": {
            "no_pattern_keyword_or_complaint_match": excluded_no_match,
        },
        "excluded_samples": excluded_samples,
        "complaint_only_rows": complaint_only_rows,
        "notes": [
            "runtime event는 event_type/error/reason/segment/track 문자열만 fact 추출에 사용한다.",
            "패턴 keyword hit 또는 complaint hit가 있어야 fact로 연결된다.",
        ],
        "event_type_counts": dict(Counter(str(row.get("event_type") or "unknown") for row in rows)),
    }


def _extract_facts_from_observations(rows: list[dict[str, Any]], pattern_defs: list[dict[str, Any]]) -> dict[str, list[SourceFact]]:
    facts: dict[str, list[SourceFact]] = defaultdict(list)
    for row in rows:
        text = " ".join(str(row.get(key) or "") for key in ("quote", "note", "source"))
        segment = row.get("segment") or "worker"
        complaint_signal, complaint_type, complaint_severity, complaint_words = _detect_complaint(text)
        for pattern in pattern_defs:
            if pattern["segment"] != segment:
                continue
            hit_count, matched = _count_hits(text, pattern["keywords"])
            if hit_count == 0 and not complaint_signal:
                continue
            urgency_hits, _ = _count_hits(text, pattern["urgency_keywords"])
            execution_hits, _ = _count_hits(text, pattern["execution_keywords"])
            negative_hits, _ = _count_hits(text, NEGATIVE_WORDS)
            facts[pattern["pattern_id"]].append(
                SourceFact(
                    source_type="operator_note",
                    segment=segment,
                    text=_safe_excerpt(text),
                    observed_at=str(row.get("ts") or ""),
                    source_label=str(row.get("source") or "manual_observation"),
                    provenance={"id": row.get("id"), "url": row.get("url") or ""},
                    matched_keywords=sorted(set(matched + complaint_words)),
                    urgency_hits=urgency_hits,
                    execution_hits=execution_hits,
                    negative_hits=negative_hits,
                    complaint_signal=complaint_signal,
                    complaint_type=complaint_type,
                    complaint_severity=complaint_severity,
                )
            )
    return facts


def _funnel_for_observations(rows: list[dict[str, Any]], pattern_defs: list[dict[str, Any]]) -> dict[str, Any]:
    total_rows = len(rows)
    rows_with_match = 0
    complaint_only_rows = 0
    included_facts = 0
    excluded_no_match = 0
    excluded_samples: list[dict[str, Any]] = []
    for row in rows:
        text = " ".join(str(row.get(key) or "") for key in ("quote", "note", "source"))
        segment = row.get("segment") or "worker"
        complaint_signal, _, _, _ = _detect_complaint(text)
        row_hits = 0
        matched_pattern = False
        for pattern in pattern_defs:
            if pattern["segment"] != segment:
                continue
            hit_count, _ = _count_hits(text, pattern["keywords"])
            if hit_count > 0:
                matched_pattern = True
                row_hits += 1
            elif complaint_signal:
                row_hits += 1
        if row_hits == 0:
            excluded_no_match += 1
            if len(excluded_samples) < 3:
                excluded_samples.append(_excluded_sample(
                    "no_pattern_keyword_or_complaint_match",
                    text,
                    {
                        "id": row.get("id"),
                        "segment": segment,
                        "source": row.get("source"),
                        "ts": row.get("ts"),
                    },
                    {
                        "resolver": "manual_observation",
                        "id": row.get("id"),
                    },
                ))
            continue
        rows_with_match += 1
        included_facts += row_hits
        if complaint_signal and not matched_pattern:
            complaint_only_rows += 1
    return {
        "source_key": "manual_observations",
        "label": "Manual observations",
        "total_rows": total_rows,
        "scanned_rows": total_rows,
        "eligible_rows": total_rows,
        "rows_with_match": rows_with_match,
        "unique_rows_linked": rows_with_match,
        "included_fact_count": included_facts,
        "excluded_rows": excluded_no_match,
        "excluded_reason_counts": {
            "no_pattern_keyword_or_complaint_match": excluded_no_match,
        },
        "excluded_samples": excluded_samples,
        "complaint_only_rows": complaint_only_rows,
        "notes": [
            "manual observation은 quote/note/source 문자열에서만 fact를 뽑는다.",
            "패턴 keyword hit 또는 complaint hit가 있어야 fact로 연결된다.",
        ],
    }


def _merge_fact_maps(*fact_maps: dict[str, list[SourceFact]]) -> dict[str, list[SourceFact]]:
    merged: dict[str, list[SourceFact]] = defaultdict(list)
    for fact_map in fact_maps:
        for key, values in fact_map.items():
            merged[key].extend(values)
    return merged


def _score_pattern(pattern: dict[str, Any], facts: list[SourceFact]) -> dict[str, Any]:
    if not facts:
        return {}
    fact_count = len(facts)
    distinct_source_types = sorted({fact.source_type for fact in facts})
    complaints = [fact for fact in facts if fact.complaint_signal]
    frequency = min(10.0, fact_count * 1.8)
    urgency = min(10.0, (sum(f.urgency_hits for f in facts) / fact_count) * 3.2)
    frustration = min(10.0, ((sum(f.negative_hits for f in facts) + sum(f.complaint_severity for f in complaints)) / max(1, fact_count)) * 1.2)
    execution = min(10.0, (sum(f.execution_hits for f in facts) / fact_count) * 2.7)
    cross_source = min(10.0, len(distinct_source_types) * 3.4)
    pattern_score = round(
        frequency * WEIGHTS["frequency"]
        + urgency * WEIGHTS["urgency"]
        + frustration * WEIGHTS["frustration_intensity"]
        + execution * WEIGHTS["execution_block"]
        + cross_source * WEIGHTS["cross_source_support"],
        2,
    )
    complaint_risk = round(min(10.0, sum(f.complaint_severity for f in complaints) / max(1, len(complaints)) if complaints else 0.0), 2)
    source_counter = Counter(f.source_type for f in facts)
    complaint_counter = Counter(f.complaint_type for f in complaints if f.complaint_type)
    top_samples = sorted(
        facts,
        key=lambda item: (
            item.complaint_severity,
            item.urgency_hits,
            item.execution_hits,
            item.negative_hits,
        ),
        reverse=True,
    )[:5]
    return {
        "pattern_id": pattern["pattern_id"],
        "segment": pattern["segment"],
        "label": pattern["label"],
        "pain_category": pattern["pain_category"],
        "desire_category": pattern["desire_category"],
        "status": "candidate",
        "pattern_score": pattern_score,
        "complaint_risk_score": complaint_risk,
        "distinct_source_types": len(distinct_source_types),
        "source_types": distinct_source_types,
        "source_counts": dict(source_counter),
        "supporting_evidence_count": fact_count,
        "complaint_count": len(complaints),
        "complaint_types": dict(complaint_counter),
        "factor_breakdown": {
            "frequency": round(frequency, 2),
            "urgency": round(urgency, 2),
            "frustration_intensity": round(frustration, 2),
            "execution_block": round(execution, 2),
            "cross_source_support": round(cross_source, 2),
        },
        "scoring_formula": "pattern_score = frequency*0.35 + urgency*0.20 + frustration_intensity*0.20 + execution_block*0.10 + cross_source_support*0.15",
        "known_failure_modes": pattern["failure_modes"],
        "safe_prompt_hints": pattern["safe_prompt_hints"],
        "avoid_response_patterns": pattern["avoid_response_patterns"],
        "why_it_ranked": [
            f"지원 fact {fact_count}건",
            f"서로 다른 source_type {len(distinct_source_types)}개",
            f"complaint signal {len(complaints)}건",
        ],
        "evidence_samples": [
            {
                "source_type": sample.source_type,
                "source_label": sample.source_label,
                "observed_at": sample.observed_at,
                "excerpt": sample.text,
                "matched_keywords": sample.matched_keywords,
                "complaint_signal": sample.complaint_signal,
                "complaint_type": sample.complaint_type,
                "complaint_severity": sample.complaint_severity,
                "provenance": sample.provenance,
                "source_ref": _source_ref_from_fact(sample),
            }
            for sample in top_samples
        ],
    }


def _latest_red_team_review() -> dict[str, Any]:
    review_dir = ROOT / "docs" / "reviews"
    files = sorted(review_dir.glob(RED_TEAM_REVIEW_GLOB))
    if not files:
        return {
            "available": False,
            "verdict": "missing",
            "summary": "패턴 인텔리전스 전용 Red Team artifact가 없습니다.",
            "path": None,
        }
    target = files[-1]
    text = target.read_text(encoding="utf-8")
    verdict_match = re.search(r"`(red_team_[a-z_]+)`", text)
    summary_match = re.search(r"Interpretation:\s*(?:\n|\r\n?)([\s\S]+)$", text)
    return {
        "available": True,
        "path": str(target.relative_to(ROOT)),
        "verdict": verdict_match.group(1) if verdict_match else "unknown",
        "summary": _safe_excerpt(summary_match.group(1) if summary_match else text, cap=420),
    }


def build_payload() -> dict[str, Any]:
    evidence_bank = _load_json(EVIDENCE_BANK_PATH, {"items": []})
    evidence_items = evidence_bank.get("items") if isinstance(evidence_bank, dict) else []
    evidence_items = evidence_items if isinstance(evidence_items, list) else []
    runtime_rows = _load_jsonl(RUNTIME_EVENTS_PATH)
    observation_rows = _load_jsonl(OBSERVATIONS_PATH)
    turn_rows, db_meta = _load_db_turns()

    pattern_defs = PARENT_PATTERNS + WORKER_PATTERNS
    evidence_funnel = _funnel_for_evidence(evidence_items, pattern_defs)
    runtime_funnel = _funnel_for_runtime(runtime_rows, pattern_defs)
    observation_funnel = _funnel_for_observations(observation_rows, pattern_defs)
    transcript_funnel = _funnel_for_turns(turn_rows, pattern_defs)
    merged_facts = _merge_fact_maps(
        _extract_facts_from_evidence(evidence_items, pattern_defs),
        _extract_facts_from_runtime(runtime_rows, pattern_defs),
        _extract_facts_from_observations(observation_rows, pattern_defs),
        _extract_facts_from_turns(turn_rows, pattern_defs),
    )

    patterns = []
    for pattern in pattern_defs:
        scored = _score_pattern(pattern, merged_facts.get(pattern["pattern_id"], []))
        if scored:
            patterns.append(scored)
    patterns.sort(key=lambda item: (item["pattern_score"], item["complaint_risk_score"]), reverse=True)

    total_facts = sum(len(v) for v in merged_facts.values())
    complaint_facts = sum(sum(1 for fact in v if fact.complaint_signal) for v in merged_facts.values())
    funnel_rows = [evidence_funnel, runtime_funnel, observation_funnel, transcript_funnel]
    total_raw_rows = sum(int(row.get("total_rows") or 0) for row in funnel_rows)
    total_scanned_rows = sum(int(row.get("scanned_rows") or 0) for row in funnel_rows)
    total_unique_rows_linked = sum(int(row.get("unique_rows_linked") or 0) for row in funnel_rows)
    output = {
        "generated_at": _now_iso(),
        "artifact_version": "v1",
        "purpose": "잠재 고객의 반복 고민과 답변 실패 신호를 미리 파악해 더 빠르고 현실적인 대응 체계를 준비하되, 고정관념 엔진이 되지 않도록 투명하게 관리한다.",
        "status": "ok",
        "source_inputs": {
            "evidence_bank": {
                "path": str(EVIDENCE_BANK_PATH.relative_to(ROOT)),
                "available": EVIDENCE_BANK_PATH.exists(),
                "item_count": len(evidence_items),
                "source_kind_counts": dict(Counter(item.get("source_kind") or "unknown" for item in evidence_items)),
            },
            "runtime_events": {
                "path": str(RUNTIME_EVENTS_PATH.relative_to(ROOT)),
                "available": RUNTIME_EVENTS_PATH.exists(),
                "event_count": len(runtime_rows),
                "event_type_counts": dict(Counter(row.get("event_type") or "unknown" for row in runtime_rows)),
            },
            "manual_observations": {
                "path": str(OBSERVATIONS_PATH.relative_to(ROOT)),
                "available": OBSERVATIONS_PATH.exists(),
                "item_count": len(observation_rows),
            },
            "transcript_db": db_meta,
        },
        "transparency": {
            "non_negotiables": [
                "이 시스템의 목적은 고객 대응 정밀도 향상이지 demographic shortcut으로 사람을 미리 규정하는 것이 아니다.",
                "inferred demographic 값은 runtime answer biasing에 사용하지 않는다.",
                "complaint signal은 일반 feedback보다 높은 우선순위로 개선 큐에 들어간다.",
                "live runtime shaping은 Fact Check + Red Team + QA + Legal + CEO/VP sign-off 전에는 주입하지 않는다.",
            ],
            "scoring_formula": "pattern_score = frequency*0.35 + urgency*0.20 + frustration_intensity*0.20 + execution_block*0.10 + cross_source_support*0.15",
            "weights": WEIGHTS,
            "normalization_rules": {
                "frequency": "지원 fact 수를 1.8배로 스케일 후 10 cap",
                "urgency": "pattern urgency keyword 평균 hit 수를 3.2배 후 10 cap",
                "frustration_intensity": "negative word + complaint severity 평균을 1.2배 후 10 cap",
                "execution_block": "실행 막힘 keyword 평균 hit 수를 2.7배 후 10 cap",
                "cross_source_support": "distinct source_type 수를 3.4배 후 10 cap",
                "complaint_risk_score": "complaint severity 평균, 별도 quality field",
            },
            "complaint_policy": [
                "generic/template 불만은 다음 유사 응답에서 avoid_response_patterns로 반영한다.",
                "reality gap 불만은 retrieval gap 보완 우선순위를 올린다.",
                "complaint recurrence는 fact check 단계에서 별도 점검한다.",
            ],
            "fact_selection_definition": {
                "raw_input_row": "evidence item 1개, runtime event 1개, manual observation 1개, transcript turn 1개를 뜻한다.",
                "unique_linked_row": "raw row 중 pattern keyword 또는 complaint rule에 걸려 적어도 1개 pattern에 연결된 row다.",
                "extracted_fact": "pattern별로 연결된 row 1건이다. 같은 raw row가 여러 pattern에 매칭되면 fact는 2건 이상으로 늘어난다.",
                "not_every_document_becomes_fact": "저장된 자료 전체를 다 fact로 세지 않는다. pattern과 무관한 일반 자료는 raw input으로만 집계되고 fact에서는 제외된다.",
            },
            "fact_selection_rules": [
                "evidence_bank는 segment가 맞는 pattern keyword 1개 이상 hit해야 fact가 된다.",
                "runtime_events / manual_observations / transcript user turn은 pattern keyword hit 또는 complaint rule hit가 있어야 fact가 된다.",
                "transcript는 user role turn만 스캔하고 assistant/system turn은 fact 추출 대상에서 제외된다.",
                "complaint rule만 hit하고 pattern keyword가 없는 row는 같은 segment의 여러 pattern 후보에 동시에 연결될 수 있다.",
            ],
            "fact_selection_why_low": [
                "원자료가 많아도 pattern과 직접 연결되지 않으면 fact에 포함되지 않는다.",
                "현재 pattern catalog가 parent/worker 핵심 고민만 정의하므로 범용 자료는 많이 제외될 수 있다.",
                "검토된 fact 수는 '모든 문서 수'가 아니라 '패턴과 연결된 신호 수'다.",
            ],
            "pattern_catalog": [
                {
                    "pattern_id": pattern["pattern_id"],
                    "segment": pattern["segment"],
                    "label": pattern["label"],
                    "pain_category": pattern["pain_category"],
                    "keywords": pattern["keywords"],
                    "urgency_keywords": pattern["urgency_keywords"],
                    "execution_keywords": pattern["execution_keywords"],
                }
                for pattern in pattern_defs
            ],
        },
        "summary": {
            "total_raw_input_rows": total_raw_rows,
            "total_scanned_rows": total_scanned_rows,
            "total_unique_rows_linked": total_unique_rows_linked,
            "total_extracted_facts": total_facts,
            "pattern_count": len(patterns),
            "complaint_fact_count": complaint_facts,
            "top_segments": dict(Counter(pattern["segment"] for pattern in patterns)),
            "top_patterns": [
                {
                    "pattern_id": pattern["pattern_id"],
                    "label": pattern["label"],
                    "score": pattern["pattern_score"],
                    "segment": pattern["segment"],
                }
                for pattern in patterns[:5]
            ],
        },
        "extraction_funnel": {
            "raw_input_rows": total_raw_rows,
            "scanned_rows": total_scanned_rows,
            "unique_rows_linked": total_unique_rows_linked,
            "extracted_facts": total_facts,
            "source_breakdown": funnel_rows,
        },
        "patterns": patterns,
        "artifact_paths": {
            "pattern_monitor_json": str(OUTPUT_PATH.relative_to(ROOT)),
            "pattern_history_jsonl": str(HISTORY_PATH.relative_to(ROOT)),
            "fact_check_json": "runtime/edu_pattern_fact_check.json",
            "red_team_review": _latest_red_team_review(),
        },
    }
    return output


def _append_history(payload: dict[str, Any]) -> None:
    summary = payload.get("summary") or {}
    top_patterns = payload.get("patterns") or []
    row = {
        "generated_at": payload.get("generated_at"),
        "total_extracted_facts": summary.get("total_extracted_facts", 0),
        "pattern_count": summary.get("pattern_count", 0),
        "complaint_fact_count": summary.get("complaint_fact_count", 0),
        "top_patterns": [
            {
                "pattern_id": p.get("pattern_id"),
                "label": p.get("label"),
                "segment": p.get("segment"),
                "pattern_score": p.get("pattern_score"),
                "complaint_risk_score": p.get("complaint_risk_score"),
                "supporting_evidence_count": p.get("supporting_evidence_count"),
            }
            for p in top_patterns[:8]
        ],
    }
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_jsonl(HISTORY_PATH)
    if existing:
        latest = existing[-1]
        if latest.get("generated_at") == row["generated_at"]:
            return
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build transparent Edu pattern intelligence artifact.")
    parser.add_argument("--stdout", action="store_true", help="Print JSON to stdout.")
    parser.add_argument("--write", action="store_true", help="Write runtime artifact.")
    args = parser.parse_args()

    payload = build_payload()
    if args.write or not args.stdout:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        _append_history(payload)
    if args.stdout:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
