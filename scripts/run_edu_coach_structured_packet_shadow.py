#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs" / "education"
REPORT_DIR = ROOT / "docs" / "reviews" / "edu_coach_simulations"
CORPUS_SCENARIO_PATH = CONFIG_DIR / "edu_coach_corpus_scenarios.json"
ADVERSARIAL_SCENARIO_PATH = CONFIG_DIR / "edu_coach_adversarial_scenarios.json"


def _load_backend_main() -> Any:
    module_name = "harness_backend_main_for_edu_coach_structured_packet_shadow"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = ROOT / "harness-os" / "backend" / "main.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    if spec.loader is None:
        raise RuntimeError(f"cannot load backend module: {path}")
    spec.loader.exec_module(module)
    return module


def _read_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = [item for item in payload.get("cases", []) if isinstance(item, dict)]
    if not rows:
        raise ValueError(f"no cases: {path}")
    return rows


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _mock_packet_for(question: str) -> dict[str, Any]:
    return {
        "taxonomy": {"topic_domain": ["ai_principle"], "user_need": ["explanation"]},
        "runtime_intent": {"primary": "principle_question", "secondary": [], "latent_need": "shadow evaluation"},
        "rag_synthesis": {"usable": False, "fresh_angle": "", "reader_relevance": "", "example_seed": "", "evidence_risk": "weak_match"},
        "answer_plan": {
            "opening_move": "direct_answer",
            "core_explanation": ["질문에 바로 답한다", "중요한 결정은 확인한다"],
            "fresh_example": "생활 예시",
            "boundary": "AI 답은 확인이 필요하다",
            "closing_rule": "초안으로 받고 확인한다",
        },
        "final_answer": (
            f"{question[:24]} 질문은 먼저 핵심부터 답하는 것이 좋습니다. "
            "AI 답은 가능성이 높은 말을 계산해 만든 초안이라서 도움이 되지만, 중요한 내용은 사람이 다시 확인해야 합니다. "
            "오늘은 AI 답을 바로 실행할 정답이 아니라 확인할 초안으로 기억하면 됩니다."
        ),
    }


def run_shadow(
    *,
    source: str = "adversarial",
    limit: int = 10,
    report_dir: Path = REPORT_DIR,
    mock: bool = False,
) -> dict[str, Any]:
    backend = _load_backend_main()
    cases_path = ADVERSARIAL_SCENARIO_PATH if source == "adversarial" else CORPUS_SCENARIO_PATH
    cases = _read_cases(cases_path)[: max(1, int(limit or 10))]
    report_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = report_dir / f"structured_packet_shadow_{run_id}_{source}.jsonl"

    old_flag = os.environ.get("EDU_SAFETY_COACH_STRUCTURED_PACKET_ENABLED")
    os.environ["EDU_SAFETY_COACH_STRUCTURED_PACKET_ENABLED"] = "true"
    records: list[dict[str, Any]] = []
    try:
        for idx, item in enumerate(cases, start=1):
            question = str(item.get("question") or "")
            req = backend.EduVpTrainingSafetyCoachRequest(
                case_id=idx,
                stage="day0",
                concept_id=str(item.get("case_id") or "")[:120],
                concept_title="수집 corpus 기반 사용자 질문",
                concept_body=str(item.get("evidence_excerpt") or ""),
                question=question,
            )
            patches = [
                patch.object(backend, "_edu_vp_safety_coach_reinforcement_policies", return_value=[]),
                patch.object(backend, "_edu_vp_safety_coach_evidence_with_timeout", return_value=("", [], {"selected_count": 0, "rejected_count": 0, "rejected": [], "skip_reason": "shadow"})),
            ]
            if mock:
                patches.append(
                    patch.object(
                        backend,
                        "_edu_generate_text",
                        return_value=(json.dumps(_mock_packet_for(question), ensure_ascii=False), {"prompt_token_count": 10, "candidates_token_count": 8}, "mock-model"),
                    )
                )
            with patches[0], patches[1]:
                if mock:
                    with patches[2]:
                        answer, model, usage, fallback_used = backend._edu_vp_generate_safety_coach_answer(req)
                else:
                    answer, model, usage, fallback_used = backend._edu_vp_generate_safety_coach_answer(req)
            packet_usage = usage.get("_safety_coach_structured_packet") if isinstance(usage, dict) else {}
            records.append(
                {
                    "case_id": str(item.get("case_id") or ""),
                    "source": source,
                    "question": question,
                    "model": model,
                    "fallback_used": bool(fallback_used),
                    "structured_packet_used": isinstance(packet_usage, dict) and bool(packet_usage.get("enabled")),
                    "rag_infused": bool(usage.get("_safety_coach_rag_infused") if isinstance(usage, dict) else False),
                    "answer": str(answer)[:1200],
                }
            )
    finally:
        if old_flag is None:
            os.environ.pop("EDU_SAFETY_COACH_STRUCTURED_PACKET_ENABLED", None)
        else:
            os.environ["EDU_SAFETY_COACH_STRUCTURED_PACKET_ENABLED"] = old_flag

    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    structured_count = sum(1 for item in records if item["structured_packet_used"])
    fallback_count = sum(1 for item in records if item["fallback_used"])
    return {
        "ok": True,
        "run_id": run_id,
        "source": source,
        "mock": bool(mock),
        "record_count": len(records),
        "structured_packet_used": structured_count,
        "fallback_used": fallback_count,
        "output_path": _display_path(output_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow-run EDU coach structured packet path without changing production flag.")
    parser.add_argument("--source", choices=["adversarial", "corpus"], default="adversarial")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--mock", action="store_true", help="mock LLM response for deterministic contract smoke test")
    args = parser.parse_args()
    summary = run_shadow(source=args.source, limit=args.limit, report_dir=args.report_dir, mock=bool(args.mock))
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
