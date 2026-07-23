"""Plan and verify grounded notebook queries that may require derived facts.

NotebookLM is a source-grounded interpreter, not a calculator.  This module keeps
that boundary explicit: deterministic enrichers produce facts, NotebookLM
interprets them, and a route-independent delivery check rejects non-answers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class SupplementalFacts:
    provider: str
    facts: tuple[str, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class NotebookQueryPlan:
    original_question: str
    grounded_question: str
    requirements: tuple[str, ...]
    supplemental_facts: tuple[SupplementalFacts, ...]


Enricher = Callable[[str], SupplementalFacts | None]

_NON_ANSWER_MARKERS = (
    "바로 산출한 답은 나오지",
    "구체적인 일진 결과가 기록",
    "임의로 계산하거나",
    "답변해 드리지 못",
    "정보가 부족",
    "확인할 수 없",
    "답변 불가",
    "제공할 수 없",
    "cannot answer",
    "unable to answer",
    "insufficient information",
    "not enough information",
)


def infer_requirements(question: str) -> tuple[str, ...]:
    """Infer user-visible sections without binding logic to one notebook."""
    mappings = (
        ("운세", ("운세",)),
        ("일진", ("일진",)),
        ("전체운", ("전체운", "종합운")),
        ("재물운", ("재물운", "금전운")),
        ("건강운", ("건강운",)),
        ("대인운", ("대인운", "인간관계")),
        ("주의사항", ("주의사항", "주의할")),
        ("근거", ("근거", "출처", "이유", "해석")),
    )
    return tuple(label for label, needles in mappings if any(n in question for n in needles))


def build_query_plan(question: str, enrichers: Iterable[Enricher] = ()) -> NotebookQueryPlan:
    supplements = tuple(item for fn in enrichers if (item := fn(question)) is not None)
    requirements = infer_requirements(question)
    if not supplements:
        return NotebookQueryPlan(question, question, requirements, ())

    fact_lines = [
        f"- [{supplement.provider}] {fact}"
        for supplement in supplements
        for fact in supplement.facts
    ]
    warning_lines = [
        f"- [{supplement.provider}] 주의: {warning}"
        for supplement in supplements
        for warning in supplement.warnings
    ]
    required = ", ".join(requirements) if requirements else "사용자가 요청한 모든 항목"
    grounded = "\n".join(
        [
            "이 요청은 이전 대화와 독립적이다.",
            "아래 보강 사실은 허용된 결정론 도구가 산출했다. 이를 재계산하지 말고, "
            "노트북 자료가 실제로 뒷받침하는 이론과 인용을 적용해 해석하라. "
            "동일 인물의 사례가 소스에 없는 것은 결격이 아니다. 사례의 계산 입력은 "
            "보강 사실이 담당하고, 노트북은 일반 해석 이론의 근거를 담당한다. "
            "보강 사실과 노트북 근거를 구분하고, 근거가 닿지 않는 "
            "부분은 추정이라고 명시하라.",
            "",
            "[사용자 원문]",
            question,
            "",
            "[보강 사실]",
            *fact_lines,
            *warning_lines,
            "",
            f"[답변 계약] {required}을 직접 답하라. 계산 입력을 되묻거나 외부 검색을 "
            "제안하는 것으로 끝내지 말라. 인용 근거와 한계를 함께 밝혀라.",
        ]
    )
    return NotebookQueryPlan(question, grounded, requirements, supplements)


def assess_notebook_answer(plan: NotebookQueryPlan, answer: str) -> tuple[bool, tuple[str, ...]]:
    text = answer.strip()
    reasons: list[str] = []
    if not text:
        reasons.append("empty_answer")
    lowered = text.lower()
    if any(marker.lower() in lowered for marker in _NON_ANSWER_MARKERS):
        reasons.append("non_answer_or_refusal")
    refusal_patterns = (
        r"(?:출처|자료|소스|근거|항목).{0,30}(?:없|않|못|불가|어렵|제시할\s*수\s*없)",
        r"(?:답변|응답|설명).{0,20}(?:없|않|못|불가|어렵)",
        r"(?:나와|기록되어|포함되어)\s*있지\s*않",
    )
    if len(text) < 300 and any(re.search(pattern, lowered) for pattern in refusal_patterns):
        reasons.append("semantic_non_answer")
    for requirement in plan.requirements:
        if requirement == "근거":
            if not any(marker in text for marker in ("[1", "근거", "출처", "십신", "합", "충", "형")):
                reasons.append("missing:근거")
        elif requirement not in text:
            reasons.append(f"missing:{requirement}")
    return not reasons, tuple(reasons)
