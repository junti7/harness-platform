#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT / "harness-os" / "backend" / "main.py"

DEFAULT_QUESTION = "그렇지만 전문가에게 상담을 받을 경우 비용이 많이 들잖아요."
DEFAULT_BAD_ANSWER = (
    "AI의 사용은 민감한 일일 뿐 아니라 개인의 건강과 법률에 영향을 미칠 수 있습니다. "
    "전문가와 상담을 통해 필요한 정보를 얻는 것이 가장 안전하고 효과적인 방법입니다. "
    "비용이 많이 들지 않는다는 점도 고려해야 합니다. 가족이나 친구에게 먼저 이야기해보세요."
)


def _load_backend() -> Any:
    module_name = "harness_backend_main_for_edu_downvote_auto_action_sim"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, BACKEND_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load backend module: {BACKEND_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _mock_llm_for_review(*_: Any, **__: Any) -> tuple[str, dict[str, int], str]:
    return (
        json.dumps(
            {
                "verdict": "user_mistake",
                "issues": [],
                "improvement_note": "",
                "confidence": 0.2,
            },
            ensure_ascii=False,
        ),
        {"prompt_token_count": 8, "candidates_token_count": 5},
        "mock-review-model",
    )


def _improved_answer() -> str:
    return (
        "맞아요. 비용 부담은 실제 장벽입니다. 그래서 답은 '무조건 전문가'가 아니라, 위험도에 따라 길을 나누는 것입니다. "
        "급한 건강·법률·안전 문제는 무료 또는 저비용 공공 창구, 보건소, 학교·회사 상담 창구, 법률구조공단 같은 곳을 먼저 찾아볼 수 있습니다. "
        "AI는 그 전에 상황을 정리하고 물어볼 질문을 만드는 데 쓰면 좋습니다."
    )


def run_simulation(
    *,
    question: str = DEFAULT_QUESTION,
    bad_answer: str = DEFAULT_BAD_ANSWER,
    mock: bool = True,
) -> dict[str, Any]:
    backend = _load_backend()
    payload = {
        "stage": "day0",
        "concept_id": "understand_boundaries",
        "concept_title": "개인정보와 고위험 판단 경계 확인",
        "concept_body": "건강·법률·돈·아이 안전 문제는 AI 답을 초안으로 보고 사람 확인을 거친다.",
        "question": question,
        "answer": bad_answer,
        "answer_version": backend._edu_vp_safety_coach_answer_version(""),
        "rating": "down",
        "model": "simulated-bad-answer",
        "fallback_used": False,
        "evidence_used": False,
        "feedback_saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    review_patch = patch.object(backend, "_edu_generate_text", side_effect=_mock_llm_for_review) if mock else patch.object(backend, "_edu_log_llm_cost")
    with review_patch:
        review = backend._edu_vp_safety_coach_feedback_review(
            question=question,
            answer=bad_answer,
            concept_title=payload["concept_title"],
            concept_body=payload["concept_body"],
        )

    candidate = backend._edu_vp_safety_coach_policy_candidate_from_downvote(
        case_id=999001,
        email="simulation@example.com",
        payload=payload,
        review=review,
    )

    fake_rows = [{"event_payload": {**payload, "auto_reinforcement": review}, "created_at": datetime.now(timezone.utc)}]

    def fake_execute(query: str, params: tuple[Any, ...] | None = None, *, fetch: bool = False, **kwargs: Any) -> list[dict[str, Any]]:
        if "answer_auto_reinforcement_reviewed" in query and fetch:
            return fake_rows
        return []

    with patch.object(backend, "_edu_execute", side_effect=fake_execute):
        policies = backend._edu_vp_safety_coach_reinforcement_policies(
            question=question,
            concept_title=payload["concept_title"],
            answer_version=payload["answer_version"],
        )

    def mock_answer_llm(prompt: str, *_: Any, **__: Any) -> tuple[str, dict[str, int], str]:
        if "이전 질문" not in prompt or "싫어요" not in prompt:
            raise AssertionError("reinforcement policy was not injected into answer prompt")
        return (_improved_answer(), {"prompt_token_count": 100, "candidates_token_count": 60}, "mock-answer-model")

    req = backend.EduVpTrainingSafetyCoachRequest(
        case_id=999001,
        stage="day0",
        concept_id=payload["concept_id"],
        concept_title=payload["concept_title"],
        concept_body=payload["concept_body"],
        question=question,
        answer_version=payload["answer_version"],
    )
    with (
        patch.object(backend, "_edu_vp_safety_coach_reinforcement_policies", return_value=policies),
        patch.object(backend, "_edu_vp_safety_coach_evidence_with_timeout", return_value=("", [], {"selected_count": 0, "rejected_count": 0, "rejected": [], "skip_reason": "simulation"})),
        patch.object(backend, "_edu_generate_text", side_effect=mock_answer_llm),
        patch.object(backend, "_edu_log_llm_cost"),
    ):
        next_answer, model, usage, fallback_used = backend._edu_vp_generate_safety_coach_answer(req)

    low_cost_terms = ("무료", "저비용", "공공", "보건소", "학교", "회사", "법률구조")
    summary = {
        "ok": bool(
            review.get("verdict") == "needs_improvement"
            and candidate
            and policies
            and not fallback_used
            and any(term in next_answer for term in low_cost_terms)
        ),
        "review_verdict": review.get("verdict"),
        "review_issues": review.get("issues") or [],
        "review_source": review.get("review_source"),
        "candidate_created": bool(candidate),
        "candidate_id": candidate.get("candidate_id") if isinstance(candidate, dict) else "",
        "policy_hit": bool(policies),
        "policy_count": len(policies),
        "next_model": model,
        "next_fallback_used": bool(fallback_used),
        "next_answer_has_low_cost_options": any(term in next_answer for term in low_cost_terms),
        "auto_reinforcement_applied": usage.get("_safety_coach_reinforcement_policies") if isinstance(usage, dict) else [],
        "next_answer": next_answer,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate EDU safety-coach downvote -> auto-action -> improved next answer.")
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--bad-answer", default=DEFAULT_BAD_ANSWER)
    parser.add_argument("--real-review", action="store_true", help="call configured LLM for review instead of deterministic mock")
    args = parser.parse_args()
    summary = run_simulation(question=args.question, bad_answer=args.bad_answer, mock=not bool(args.real_review))
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
