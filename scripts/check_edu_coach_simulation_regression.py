#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

from edu_coach_corpus_scenario_generator import OUTPUT_CONFIG, collect_corpus_scenarios
from edu_coach_simulation_runner import run_simulation


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MIN_CORPUS_RECORDS = 22862
DEFAULT_MIN_YOUTUBE_RECORDS = 402
DEFAULT_MAX_FAST_RAG_TIMEOUT_MS = 450
DEFAULT_MAX_RAG_PATCH_CALLS = 1
DEFAULT_MAX_STRUCTURED_PACKET_CALLS = 1


def _load_auto_reinforcement_report() -> Any:
    module_name = "edu_safety_coach_auto_reinforcement_report_for_guard"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = ROOT / "scripts" / "report_edu_safety_coach_auto_reinforcement.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    if spec.loader is None:
        raise RuntimeError(f"cannot load auto-reinforcement report: {path}")
    spec.loader.exec_module(module)
    return module


def _load_backend_main() -> Any:
    module_name = "harness_backend_main_for_edu_coach_latency_guard"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = ROOT / "harness-os" / "backend" / "main.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _needs_work(summary: dict[str, Any]) -> int:
    verdict_counts = summary.get("verdict_counts")
    if not isinstance(verdict_counts, dict):
        return 0
    return int(verdict_counts.get("needs_work") or 0)


def _channel_count(summary: dict[str, Any], channel: str) -> int:
    channel_counts = summary.get("channel_counts")
    if not isinstance(channel_counts, dict):
        return 0
    return int(channel_counts.get(channel) or 0)


def _family_count(payload: dict[str, Any], family: str) -> int:
    family_counts = payload.get("source_family_counts")
    if not isinstance(family_counts, dict):
        return 0
    return int(family_counts.get(family) or 0)


def check_freshness(*, config_path: Path = OUTPUT_CONFIG) -> dict[str, Any]:
    committed = json.loads(config_path.read_text(encoding="utf-8"))
    fresh = collect_corpus_scenarios(max_cases=0)
    committed_cases = int(committed.get("case_count") or 0)
    fresh_cases = int(fresh.get("case_count") or 0)
    committed_youtube = _family_count(committed, "youtube")
    fresh_youtube = _family_count(fresh, "youtube")
    failures: list[str] = []
    if str(committed.get("selection_mode") or "") not in {
        "max_quality_corpus_no_family_quota",
        "max_quality_corpus_union_no_family_quota",
        "max_quality_question_corpus_union_no_family_quota",
    }:
        failures.append(f"selection_mode={committed.get('selection_mode')}")
    if int(committed.get("synthetic_used_count") or 0) != 0:
        failures.append(f"synthetic_used_count={committed.get('synthetic_used_count')}")
    if fresh_cases > committed_cases:
        failures.append(f"fresh_cases={fresh_cases}>committed_cases={committed_cases}")
    if fresh_youtube > committed_youtube:
        failures.append(f"fresh_youtube={fresh_youtube}>committed_youtube={committed_youtube}")
    return {
        "ok": not failures,
        "failures": failures,
        "committed_cases": committed_cases,
        "fresh_cases": fresh_cases,
        "committed_youtube": committed_youtube,
        "fresh_youtube": fresh_youtube,
    }


def check_latency_budget(
    *,
    max_fast_rag_timeout_ms: int = DEFAULT_MAX_FAST_RAG_TIMEOUT_MS,
    max_rag_patch_calls: int = DEFAULT_MAX_RAG_PATCH_CALLS,
) -> dict[str, Any]:
    mod = _load_backend_main()
    failures: list[str] = []

    fast_req = mod.EduVpTrainingSafetyCoachRequest(
        case_id=123,
        stage="day0",
        concept_id="safety_concept_ai_llm_words",
        concept_title="먼저 말부터 정리하기: AI와 LLM",
        concept_body="LLM은 다음에 올 법한 말을 이어 붙입니다.",
        question="다음 글에 이어질 최적의 명사는 어떻게 추측해?",
    )

    def slow_evidence(*_args: Any, **_kwargs: Any) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
        time.sleep(0.5)
        return "", [], {"selected_count": 0}

    old_fast_timeout = os.environ.get("EDU_SAFETY_COACH_FAST_RAG_TIMEOUT_SECONDS")
    os.environ["EDU_SAFETY_COACH_FAST_RAG_TIMEOUT_SECONDS"] = "0.01"
    try:
        fast_started = time.monotonic()
        with (
            patch.object(mod, "_edu_vp_safety_coach_evidence", side_effect=slow_evidence),
            patch.object(mod, "_edu_generate_text") as mocked_fast_generate,
        ):
            fast_answer, fast_model, fast_usage, fast_fallback = mod._edu_vp_generate_safety_coach_answer(fast_req)
        fast_elapsed_ms = int(round((time.monotonic() - fast_started) * 1000))
    finally:
        if old_fast_timeout is None:
            os.environ.pop("EDU_SAFETY_COACH_FAST_RAG_TIMEOUT_SECONDS", None)
        else:
            os.environ["EDU_SAFETY_COACH_FAST_RAG_TIMEOUT_SECONDS"] = old_fast_timeout

    fast_meta = fast_usage.get("_safety_coach_evidence_meta") if isinstance(fast_usage, dict) else {}
    if fast_elapsed_ms > max_fast_rag_timeout_ms:
        failures.append(f"fast_rag_timeout_elapsed_ms={fast_elapsed_ms}>max={max_fast_rag_timeout_ms}")
    if str(fast_meta.get("skip_reason") if isinstance(fast_meta, dict) else "") != "retrieve_timeout":
        failures.append(f"fast_rag_skip_reason={fast_meta.get('skip_reason') if isinstance(fast_meta, dict) else None}")
    if getattr(mocked_fast_generate, "call_count", 0) != 0:
        failures.append(f"fast_template_llm_calls={getattr(mocked_fast_generate, 'call_count', 0)}")
    if fast_fallback or "명사는" not in str(fast_answer) or fast_model != "fast-template":
        failures.append(f"fast_template_regressed:model={fast_model}:fallback={fast_fallback}")

    patch_req = mod.EduVpTrainingSafetyCoachRequest(
        case_id=123,
        stage="day0",
        concept_id="safety_concept_attention",
        concept_title="Transformer의 핵심: attention",
        concept_body="attention은 중요한 단어끼리 연결해 문장의 흐름을 잡는 방법입니다.",
        question="attention은 누가 어떻게 설정하는거야?",
    )
    weak_answer = (
        "attention은 사람이 문장마다 직접 정하지 않습니다. 모델이 입력 문장 안에서 단어 사이 관련도를 계산합니다. "
        "예를 들어 이름과 대명사를 함께 보는 식으로 연결을 잡습니다."
    )
    evidence_items = [
        {
            "source": "YouTube family learning digest",
            "cite": "attention 설정을 정답 암기가 아니라 질문 비교 도구로 다룰 때 이해가 오래 남는다고 설명한다.",
        }
    ]
    with (
        patch.object(mod, "_edu_vp_safety_coach_reinforcement_policies", return_value=[]),
        patch.object(mod, "_edu_vp_safety_coach_evidence_with_timeout", return_value=("", evidence_items, {"selected_count": 1, "elapsed_ms": 3, "timeout_ms": 1500})),
        patch.object(mod, "_edu_safety_coach_model_ladder", return_value=["model-a", "model-b"]),
        patch.object(mod, "_edu_generate_text", return_value=(weak_answer, {"prompt_token_count": 10, "candidates_token_count": 8}, "model-a")) as mocked_patch_generate,
        patch.object(mod, "_edu_log_llm_cost"),
    ):
        patch_answer, patch_model, patch_usage, patch_fallback = mod._edu_vp_generate_safety_coach_answer(patch_req)
    patch_calls = int(getattr(mocked_patch_generate, "call_count", 0))
    if patch_calls > max_rag_patch_calls:
        failures.append(f"rag_patch_llm_calls={patch_calls}>max={max_rag_patch_calls}")
    if patch_model != "model-a+rag_patch":
        failures.append(f"rag_patch_model={patch_model}")
    if not bool(patch_usage.get("_safety_coach_rag_patch_applied") if isinstance(patch_usage, dict) else False):
        failures.append("rag_patch_not_applied")
    if not bool(patch_usage.get("_safety_coach_rag_infused") if isinstance(patch_usage, dict) else False):
        failures.append("rag_patch_not_infused")
    if patch_fallback or "질문 비교 도구" not in str(patch_answer):
        failures.append(f"rag_patch_answer_regressed:fallback={patch_fallback}")

    return {
        "ok": not failures,
        "failures": failures,
        "fast_rag_timeout": {
            "elapsed_ms": fast_elapsed_ms,
            "max_ms": max_fast_rag_timeout_ms,
            "model": fast_model,
            "fallback_used": bool(fast_fallback),
            "skip_reason": fast_meta.get("skip_reason") if isinstance(fast_meta, dict) else None,
            "llm_calls": int(getattr(mocked_fast_generate, "call_count", 0)),
        },
        "rag_patch": {
            "model": patch_model,
            "llm_calls": patch_calls,
            "max_llm_calls": max_rag_patch_calls,
            "fallback_used": bool(patch_fallback),
            "patch_applied": bool(patch_usage.get("_safety_coach_rag_patch_applied") if isinstance(patch_usage, dict) else False),
            "rag_infused": bool(patch_usage.get("_safety_coach_rag_infused") if isinstance(patch_usage, dict) else False),
        },
    }


def check_structured_packet_contract(
    *,
    max_structured_packet_calls: int = DEFAULT_MAX_STRUCTURED_PACKET_CALLS,
) -> dict[str, Any]:
    mod = _load_backend_main()
    failures: list[str] = []
    req = mod.EduVpTrainingSafetyCoachRequest(
        case_id=123,
        stage="day0",
        concept_id="safety_concept_attention",
        concept_title="Transformer의 핵심: attention",
        concept_body="attention은 중요한 단어끼리 연결해 문장의 흐름을 잡는 방법입니다.",
        question="attention은 누가 어떻게 설정하는거야?",
    )
    packet = {
        "taxonomy": {"topic_domain": ["ai_principle"], "user_need": ["mechanism_explanation"]},
        "runtime_intent": {"primary": "principle_question", "secondary": [], "latent_need": "attention 설정 주체 설명"},
        "rag_synthesis": {"usable": False, "fresh_angle": "", "reader_relevance": "", "example_seed": "", "evidence_risk": "weak_match"},
        "answer_plan": {
            "opening_move": "direct_answer",
            "core_explanation": ["사람이 문장마다 직접 설정하지 않는다", "모델이 관련도를 계산한다"],
            "fresh_example": "대명사와 이름 연결",
            "boundary": "사람처럼 이해하는 것은 아니다",
            "closing_rule": "계산된 연결 강도",
        },
        "final_answer": (
            "attention은 사람이 문장마다 직접 설정하는 값이 아닙니다. 모델은 학습한 방식에 따라 입력 문장 안에서 "
            "단어 사이 관련도를 계산합니다. 예를 들어 이름과 대명사를 함께 보며 누가 누구인지 연결하는 것처럼 보면 됩니다. "
            "오늘은 attention을 사람이 넣는 표시가 아니라 모델이 계산하는 연결 강도로 기억하면 됩니다."
        ),
    }
    with (
        patch.dict(os.environ, {"EDU_SAFETY_COACH_STRUCTURED_PACKET_ENABLED": "true"}),
        patch.object(mod, "_edu_vp_safety_coach_reinforcement_policies", return_value=[]),
        patch.object(mod, "_edu_vp_safety_coach_evidence_with_timeout", return_value=("", [], {"selected_count": 0, "rejected_count": 0, "rejected": [], "skip_reason": "contract_test"})),
        patch.object(mod, "_edu_safety_coach_model_ladder", return_value=["model-a", "model-b"]),
        patch.object(mod, "_edu_generate_text", return_value=(json.dumps(packet, ensure_ascii=False), {"prompt_token_count": 10, "candidates_token_count": 8}, "model-a")) as mocked_generate,
        patch.object(mod, "_edu_log_llm_cost"),
    ):
        answer, model, usage, fallback = mod._edu_vp_generate_safety_coach_answer(req)
    calls = int(getattr(mocked_generate, "call_count", 0))
    packet_usage = usage.get("_safety_coach_structured_packet") if isinstance(usage, dict) else {}
    if calls > max_structured_packet_calls:
        failures.append(f"structured_packet_llm_calls={calls}>max={max_structured_packet_calls}")
    if model != "model-a+structured_packet":
        failures.append(f"structured_packet_model={model}")
    if fallback:
        failures.append("structured_packet_fallback_used=true")
    if not isinstance(packet_usage, dict) or not packet_usage.get("enabled"):
        failures.append("structured_packet_usage_missing")
    if "attention은" not in str(answer):
        failures.append("structured_packet_answer_regressed")
    return {
        "ok": not failures,
        "failures": failures,
        "model": model,
        "llm_calls": calls,
        "max_llm_calls": max_structured_packet_calls,
        "fallback_used": bool(fallback),
        "schema_keys": packet_usage.get("schema_keys") if isinstance(packet_usage, dict) else [],
    }


def check_auto_reinforcement_health() -> dict[str, Any]:
    report_mod = _load_auto_reinforcement_report()
    report = report_mod.run_report(lookback_days=7, sla_minutes=5, pending_limit=10)
    failures: list[str] = []
    if not bool(report.get("ok")):
        failures.append("auto_reinforcement_report_not_ok")
    stale_pending = int(report.get("stale_pending_count") or 0)
    if stale_pending:
        failures.append(f"auto_reinforcement_stale_pending={stale_pending}")
    pending = int(report.get("pending_count") or 0)
    if pending and float(report.get("review_completion_rate") or 0.0) < 0.99:
        failures.append(f"auto_reinforcement_completion_rate={report.get('review_completion_rate')}")
    return {
        "ok": not failures,
        "failures": failures,
        "report": report,
    }


def check_regression(
    *,
    min_corpus_records: int = DEFAULT_MIN_CORPUS_RECORDS,
    min_youtube_records: int = DEFAULT_MIN_YOUTUBE_RECORDS,
    max_fast_rag_timeout_ms: int = DEFAULT_MAX_FAST_RAG_TIMEOUT_MS,
    max_rag_patch_calls: int = DEFAULT_MAX_RAG_PATCH_CALLS,
    max_structured_packet_calls: int = DEFAULT_MAX_STRUCTURED_PACKET_CALLS,
    report_dir: Path | None = None,
    freshness: bool = True,
    latency: bool = True,
    structured_packet: bool = True,
    auto_reinforcement: bool = True,
) -> dict[str, Any]:
    if report_dir is None:
        temp_context = tempfile.TemporaryDirectory(prefix="edu_coach_regression_")
        work_dir = Path(temp_context.name)
    else:
        temp_context = None
        work_dir = report_dir
        work_dir.mkdir(parents=True, exist_ok=True)
    try:
        adversarial = run_simulation(candidate_source="adversarial-current-fallback", report_dir=work_dir)
        corpus = run_simulation(candidate_source="corpus-current-fallback", report_dir=work_dir)
    finally:
        if temp_context is not None:
            temp_context.cleanup()

    failures: list[str] = []
    adversarial_needs_work = _needs_work(adversarial)
    corpus_needs_work = _needs_work(corpus)
    corpus_records = int(corpus.get("record_count") or 0)
    youtube_records = _channel_count(corpus, "YouTube")

    if adversarial_needs_work != 0:
        failures.append(f"adversarial_needs_work={adversarial_needs_work}")
    if corpus_needs_work != 0:
        failures.append(f"corpus_needs_work={corpus_needs_work}")
    if corpus_records < min_corpus_records:
        failures.append(f"corpus_records={corpus_records}<min={min_corpus_records}")
    if youtube_records < min_youtube_records:
        failures.append(f"youtube_records={youtube_records}<min={min_youtube_records}")
    freshness_summary = check_freshness() if freshness else {"ok": True, "failures": [], "skipped": True}
    failures.extend(f"freshness:{failure}" for failure in freshness_summary.get("failures", []))
    latency_summary = (
        check_latency_budget(
            max_fast_rag_timeout_ms=max_fast_rag_timeout_ms,
            max_rag_patch_calls=max_rag_patch_calls,
        )
        if latency
        else {"ok": True, "failures": [], "skipped": True}
    )
    failures.extend(f"latency:{failure}" for failure in latency_summary.get("failures", []))
    structured_packet_summary = (
        check_structured_packet_contract(max_structured_packet_calls=max_structured_packet_calls)
        if structured_packet
        else {"ok": True, "failures": [], "skipped": True}
    )
    failures.extend(f"structured_packet:{failure}" for failure in structured_packet_summary.get("failures", []))
    auto_reinforcement_summary = (
        check_auto_reinforcement_health()
        if auto_reinforcement
        else {"ok": True, "failures": [], "skipped": True}
    )
    failures.extend(f"auto_reinforcement:{failure}" for failure in auto_reinforcement_summary.get("failures", []))

    return {
        "ok": not failures,
        "failures": failures,
        "freshness": freshness_summary,
        "latency": latency_summary,
        "structured_packet": structured_packet_summary,
        "auto_reinforcement": auto_reinforcement_summary,
        "adversarial": {
            "record_count": int(adversarial.get("record_count") or 0),
            "verdict_counts": adversarial.get("verdict_counts") or {},
            "top_issues": adversarial.get("top_issues") or [],
        },
        "corpus": {
            "record_count": corpus_records,
            "youtube_records": youtube_records,
            "verdict_counts": corpus.get("verdict_counts") or {},
            "top_issues": corpus.get("top_issues") or [],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail if EDU safety-coach max corpus/adversarial regression tests degrade.")
    parser.add_argument("--min-corpus-records", type=int, default=DEFAULT_MIN_CORPUS_RECORDS)
    parser.add_argument("--min-youtube-records", type=int, default=DEFAULT_MIN_YOUTUBE_RECORDS)
    parser.add_argument("--max-fast-rag-timeout-ms", type=int, default=DEFAULT_MAX_FAST_RAG_TIMEOUT_MS)
    parser.add_argument("--max-rag-patch-calls", type=int, default=DEFAULT_MAX_RAG_PATCH_CALLS)
    parser.add_argument("--max-structured-packet-calls", type=int, default=DEFAULT_MAX_STRUCTURED_PACKET_CALLS)
    parser.add_argument("--report-dir", type=Path, default=None, help="optional report directory; default uses a temp dir")
    parser.add_argument("--skip-freshness", action="store_true", help="skip fresh corpus collection vs committed config check")
    parser.add_argument("--skip-latency", action="store_true", help="skip fast RAG timeout and RAG patch call-count checks")
    parser.add_argument("--skip-structured-packet", action="store_true", help="skip structured packet contract check")
    parser.add_argument("--skip-auto-reinforcement", action="store_true", help="skip downvote auto-reinforcement production health check")
    args = parser.parse_args()
    summary = check_regression(
        min_corpus_records=max(1, args.min_corpus_records),
        min_youtube_records=max(1, args.min_youtube_records),
        max_fast_rag_timeout_ms=max(1, args.max_fast_rag_timeout_ms),
        max_rag_patch_calls=max(1, args.max_rag_patch_calls),
        max_structured_packet_calls=max(1, args.max_structured_packet_calls),
        report_dir=args.report_dir,
        freshness=not bool(args.skip_freshness),
        latency=not bool(args.skip_latency),
        structured_packet=not bool(args.skip_structured_packet),
        auto_reinforcement=not bool(args.skip_auto_reinforcement),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
