#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "reviews" / "edu_pilot_simulations" / "edu_data_analysis_agent_customer_simulations_2026-06-15.md"

CASE_SPLIT_RE = re.compile(r"^## (Case \d+\..+)$", re.MULTILINE)
EVIDENCE_LINE_RE = re.compile(r"^\s*-\s+\[(?P<source>[^\]]+)\]\s+`(?P<kind>[^`]+)`\s+\|\s+(?P<rest>.+)$")
TURN_LINE_RE = re.compile(r"^\d+\.\s+\*\*(?P<speaker>[^*]+)\*\*:\s+(?P<text>.+)$")
TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]{2,}")

STOPWORDS = {
    "이번", "기준", "지금", "정말", "그냥", "조금", "아주", "같이", "먼저", "이유", "내용", "자료",
    "연구", "기사", "서비스", "고객", "오늘", "내일", "정리", "설명", "사용", "대한", "에서", "으로",
    "하는", "하고", "하면", "같은", "있는", "있는지", "입니다", "있습니다", "합니다", "하세요",
    "하세요", "있어요", "하는지", "because", "with", "that", "from", "into", "your", "have", "will",
}
ACTION_MARKERS = ("오늘", "이번 주", "3일", "4주", "질문", "기록", "정리", "합의", "관찰", "체크", "시도")


@dataclass
class EvidenceItem:
    source_label: str
    kind: str
    title: str
    excerpt: str
    locator: str


@dataclass
class SimulationTurn:
    speaker: str
    text: str


@dataclass
class SimulationCase:
    title: str
    evidence_items: list[EvidenceItem]
    turns: list[SimulationTurn]


def _keywords(text: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_RE.findall(text or "")
        if token.lower() not in STOPWORDS
    }


def _split_sections(markdown: str) -> list[tuple[str, str]]:
    matches = list(CASE_SPLIT_RE.finditer(markdown))
    sections: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        sections.append((match.group(1).strip(), markdown[start:end]))
    return sections


def _parse_evidence_items(section: str) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    in_bundle = False
    for line in section.splitlines():
        stripped = line.rstrip()
        if stripped.startswith("- Retrieved evidence bundle:"):
            in_bundle = True
            continue
        if in_bundle and stripped.startswith("### 12-turn Simulation"):
            break
        if not in_bundle:
            continue
        match = EVIDENCE_LINE_RE.match(stripped)
        if not match:
            continue
        parts = match.group("rest").split(" | ", 2)
        if len(parts) != 3:
            continue
        items.append(
            EvidenceItem(
                source_label=match.group("source").strip(),
                kind=match.group("kind").strip(),
                title=parts[0].strip(),
                excerpt=parts[1].strip(),
                locator=parts[2].strip(),
            )
        )
    return items


def _parse_turns(section: str) -> list[SimulationTurn]:
    turns: list[SimulationTurn] = []
    in_sim = False
    for line in section.splitlines():
        stripped = line.strip()
        if stripped == "### 12-turn Simulation":
            in_sim = True
            continue
        if in_sim and stripped.startswith("### What This Shows About P1"):
            break
        if not in_sim:
            continue
        match = TURN_LINE_RE.match(stripped)
        if match:
            turns.append(SimulationTurn(speaker=match.group("speaker").strip(), text=match.group("text").strip()))
    return turns


def parse_simulation_markdown(markdown: str) -> list[SimulationCase]:
    cases: list[SimulationCase] = []
    for title, section in _split_sections(markdown):
        evidence_items = _parse_evidence_items(section)
        turns = _parse_turns(section)
        if evidence_items and turns:
            cases.append(SimulationCase(title=title, evidence_items=evidence_items, turns=turns))
    return cases


def _score_case(case: SimulationCase) -> dict[str, Any]:
    service_turns = [turn for turn in case.turns if turn.speaker == "서비스"]
    evidence_keywords = [_keywords(f"{item.title} {item.excerpt}") for item in case.evidence_items]
    evidence_sources = [item.source_label for item in case.evidence_items]
    supported_turns = 0
    used_items: set[int] = set()
    per_turn: list[dict[str, Any]] = []

    for turn in service_turns:
        turn_keywords = _keywords(turn.text)
        best_overlap = 0
        best_item = -1
        for idx, item_keywords in enumerate(evidence_keywords):
            overlap = len(turn_keywords & item_keywords)
            if overlap > best_overlap:
                best_overlap = overlap
                best_item = idx
        supported = best_overlap >= 1
        if supported:
            supported_turns += 1
            used_items.add(best_item)
        per_turn.append(
            {
                "text": turn.text,
                "supported": supported,
                "overlap_count": best_overlap,
                "matched_evidence_index": best_item if supported else None,
                "matched_source": evidence_sources[best_item] if supported else None,
            }
        )

    grounded_turn_ratio = supported_turns / max(1, len(service_turns))
    evidence_item_coverage = len(used_items) / max(1, len(case.evidence_items))
    source_diversity = len({evidence_sources[idx] for idx in used_items}) / max(1, min(2, len(case.evidence_items)))
    actionability = 1.0 if service_turns and any(marker in service_turns[-1].text for marker in ACTION_MARKERS) else 0.0

    total_score = round(
        grounded_turn_ratio * 50
        + evidence_item_coverage * 25
        + min(source_diversity, 1.0) * 15
        + actionability * 10,
        2,
    )
    verdict = "clear" if total_score >= 70 else "needs_work" if total_score >= 50 else "weak"
    uncovered = [
        {"index": idx, "source_label": item.source_label, "title": item.title}
        for idx, item in enumerate(case.evidence_items)
        if idx not in used_items
    ]
    return {
        "title": case.title,
        "total_score": total_score,
        "verdict": verdict,
        "metrics": {
            "service_turns": len(service_turns),
            "supported_turns": supported_turns,
            "grounded_turn_ratio": round(grounded_turn_ratio, 3),
            "evidence_item_count": len(case.evidence_items),
            "used_evidence_items": len(used_items),
            "evidence_item_coverage": round(evidence_item_coverage, 3),
            "source_diversity_score": round(min(source_diversity, 1.0), 3),
            "actionability_score": actionability,
        },
        "unused_evidence_items": uncovered,
        "turns": per_turn,
    }


def score_cases(cases: list[SimulationCase]) -> dict[str, Any]:
    results = [_score_case(case) for case in cases]
    scores = [item["total_score"] for item in results]
    return {
        "summary": {
            "case_count": len(results),
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
            "min_score": min(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
            "clear_count": sum(1 for item in results if item["verdict"] == "clear"),
            "needs_work_count": sum(1 for item in results if item["verdict"] == "needs_work"),
            "weak_count": sum(1 for item in results if item["verdict"] == "weak"),
        },
        "results": results,
    }


def render_markdown(report: dict[str, Any], source_path: Path) -> str:
    summary = report["summary"]
    lines = [
        "# Edu Grounded Simulation Score Report",
        "",
        f"- source: `{source_path}`",
        f"- case_count: `{summary['case_count']}`",
        f"- average_score: `{summary['average_score']}`",
        f"- min_score: `{summary['min_score']}`",
        f"- max_score: `{summary['max_score']}`",
        f"- clear_count: `{summary['clear_count']}`",
        f"- needs_work_count: `{summary['needs_work_count']}`",
        f"- weak_count: `{summary['weak_count']}`",
        "",
    ]
    for item in report["results"]:
        metrics = item["metrics"]
        lines.extend(
            [
                f"## {item['title']}",
                "",
                f"- score: `{item['total_score']}`",
                f"- verdict: `{item['verdict']}`",
                f"- grounded_turn_ratio: `{metrics['grounded_turn_ratio']}`",
                f"- evidence_item_coverage: `{metrics['evidence_item_coverage']}`",
                f"- source_diversity_score: `{metrics['source_diversity_score']}`",
                f"- actionability_score: `{metrics['actionability_score']}`",
            ]
        )
        if item["unused_evidence_items"]:
            lines.append("- unused_evidence_items:")
            for unused in item["unused_evidence_items"]:
                lines.append(f"  - [{unused['source_label']}] {unused['title']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Score groundedness of edu customer simulation packs.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    args = parser.parse_args()

    markdown = args.input.read_text(encoding="utf-8")
    cases = parse_simulation_markdown(markdown)
    report = score_cases(cases)

    if args.json_out:
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.write_text(render_markdown(report, args.input), encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
