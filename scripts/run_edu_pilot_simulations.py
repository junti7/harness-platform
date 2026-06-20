#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

CONFIG_PATH = ROOT / "configs" / "edu_pilot_simulations.json"
REPORT_DIR = ROOT / "docs" / "reviews" / "edu_pilot_simulations"
LATEST_JSON = REPORT_DIR / "latest.json"
LATEST_MD = REPORT_DIR / "latest.md"

DEFAULT_BASE_URL = os.getenv("EDU_PILOT_BASE_URL", "http://100.97.175.44:8000").rstrip("/")
DEFAULT_TIMEOUT = int(os.getenv("EDU_PILOT_SIM_TIMEOUT_SEC", "40"))
DEFAULT_MODE = os.getenv("EDU_PILOT_SIM_MODE", "internal").strip().lower()
HARNESS_OS_SECRET = os.getenv("HARNESS_OS_SECRET_KEY", "").strip()
OPENING_ROLE = "ai"
USER_ROLE = "user"
AI_ROLE = "ai"

ROBOTIC_MARKERS = [
    "이맘때",
    "열에 아홉",
    "원래 이런 경우엔",
    "수많은",
    "연구를 보면",
    "비슷한 사례들을 보면",
    "많이 막히세요",
    "차근히 짚어",
]
PRETENTIOUS_MARKERS = [
    "수많은 사례",
    "P1",
    "데이터셋",
    "관점에서도",
    "워낙 많",
    "세그먼트",
]
GENERIC_MARKERS = [
    "참 다양합니다",
    "충분히 이해",
    "걱정이 많으시죠",
    "많이들 그러세요",
    "일반적으로",
    "보통은",
]
ACTION_MARKERS = ["오늘", "해보", "질문", "관찰", "기록", "정리", "한 문장", "대화", "체크"]
EVIDENCE_MARKERS = ["연구", "자료", "커뮤니티", "맘카페", "지식인", "블로그", "교육부", "학교"]
EMPATHY_MARKERS = ["그 마음", "그 걱정", "답답", "불안", "충분히", "그럴 수", "먼저", "지금 제일"]
JARGON_MARKERS = [
    "self-efficacy",
    "리터러시",
    "프레임워크",
    "워크플로",
    "policy",
    "retrieval",
    "segment",
    "데이터셋",
]
WRONG_GENDER_MAP = {
    "neutral": ["어머님", "아버님", "엄마", "아빠"],
    "father": ["어머님", "어머니", "엄마"],
    "mother": ["아버님", "아버지", "아빠"],
}
ENUM_LEAK_MARKERS = ["ne, father", "네, father", "네, mother", "네, neutral", "네, name", "father.", "mother.", "neutral.", "name."]


@dataclass
class Scenario:
    id: str
    label: str
    segment: str
    profile: dict[str, Any]
    turns: list[str]
    specificity_tokens: list[str]
    min_offer_turn: int = 4


def now_kst_stamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d_%H%M%S_%f")


def load_scenarios(path: Path) -> tuple[dict[str, Any], list[Scenario]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    scenarios = [
        Scenario(
            id=item["id"],
            label=item["label"],
            segment=item["segment"],
            profile=item["profile"],
            turns=item["turns"],
            specificity_tokens=item.get("specificity_tokens", []),
            min_offer_turn=int(item.get("min_offer_turn", 4)),
        )
        for item in payload.get("scenarios", [])
    ]
    return payload, scenarios


def scenario_email(scenario: Scenario, run_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", scenario.id.lower()).strip("-")
    return f"edu-sim-{slug}-{run_id}@example.com"


def post_json(client: httpx.Client, url: str, body: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    response = client.post(url, json=body, headers=headers)
    response.raise_for_status()
    return response.json()


def get_json(client: httpx.Client, url: str, params: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    response = client.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()


def safe_post_json(client: httpx.Client, url: str, body: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        return {"ok": True, "data": post_json(client, url, body, headers=headers)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def safe_get_json(client: httpx.Client, url: str, params: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        return {"ok": True, "data": get_json(client, url, params, headers=headers)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def resolve_api_paths(mode: str) -> dict[str, str]:
    normalized = (mode or "internal").strip().lower()
    if normalized == "public":
        return {
            "bootstrap": "/api/public/edu/bootstrap",
            "diagnose": "/api/public/edu/diagnose",
            "curriculum": "/api/public/edu/curriculum",
            "resume": "/api/public/edu/resume",
        }
    return {
        "bootstrap": "/api/public/edu/bootstrap",
        "diagnose": "/api/edu/diagnose",
        "curriculum": "/api/edu/curriculum",
        "resume": "/api/public/edu/resume",
    }


def auth_headers(mode: str) -> dict[str, str]:
    if (mode or "internal").strip().lower() == "internal" and HARNESS_OS_SECRET:
        return {"x-harness-secret": HARNESS_OS_SECRET}
    return {}


def _count_hits(text: str, terms: list[str]) -> int:
    return sum(text.count(term) for term in terms)


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def evaluate_transcript(scenario: Scenario, transcript: list[dict[str, Any]], show_offer_turn: int | None, curriculum: dict[str, Any] | None) -> dict[str, Any]:
    ai_messages = [m["text"] for m in transcript if m["role"] == AI_ROLE]
    ai_after_opening = ai_messages[1:] if len(ai_messages) > 1 else []
    combined_ai = "\n".join(ai_messages)
    specificity_hits = 0
    specificity_after_turn3 = 0
    ai_turn_count = 0
    repeated_openings: dict[str, int] = {}

    for idx, msg in enumerate(ai_after_opening, start=1):
        ai_turn_count += 1
        if _has_any(msg, scenario.specificity_tokens):
            specificity_hits += 1
            if idx >= 3:
                specificity_after_turn3 += 1
        lead = msg[:18]
        repeated_openings[lead] = repeated_openings.get(lead, 0) + 1

    personalization_ratio = round(specificity_hits / max(1, ai_turn_count), 3)
    robotic_count = _count_hits(combined_ai, ROBOTIC_MARKERS)
    pretentious_count = _count_hits(combined_ai, PRETENTIOUS_MARKERS)
    generic_count = _count_hits(combined_ai, GENERIC_MARKERS)
    evidence_count = _count_hits(combined_ai, EVIDENCE_MARKERS)
    empathy_count = _count_hits(combined_ai, EMPATHY_MARKERS)
    jargon_count = _count_hits(combined_ai.lower(), [m.lower() for m in JARGON_MARKERS])
    action_count = 0
    if ai_messages:
        action_count += _count_hits(ai_messages[-1], ACTION_MARKERS)
    if curriculum:
        action_count += _count_hits(json.dumps(curriculum, ensure_ascii=False), ACTION_MARKERS)

    wrong_salutation_terms = WRONG_GENDER_MAP.get(scenario.profile.get("preferred_salutation", "neutral"), [])
    wrong_salutation = _has_any(combined_ai, wrong_salutation_terms)
    enum_leak = _has_any(combined_ai.lower(), [m.lower() for m in ENUM_LEAK_MARKERS])
    offer_too_early = show_offer_turn is not None and show_offer_turn < scenario.min_offer_turn
    low_specificity = specificity_after_turn3 == 0 and len(scenario.turns) >= 4
    repeated_template = any(count >= 2 for count in repeated_openings.values())
    weak_actionability = action_count == 0
    weak_grounding = evidence_count == 0
    weak_empathy = empathy_count == 0
    jargon_overload = jargon_count >= 1
    showy_authority = pretentious_count >= 1

    naturalness = 40
    naturalness -= min(robotic_count * 3, 12)
    naturalness -= min(pretentious_count * 4, 12)
    naturalness -= min(generic_count * 2, 8)
    naturalness -= 8 if jargon_overload else 0
    naturalness -= 8 if repeated_template else 0
    naturalness -= 10 if wrong_salutation else 0
    naturalness -= 12 if enum_leak else 0
    naturalness = max(0, naturalness)

    personalization = min(25, round(personalization_ratio * 25))
    if low_specificity:
        personalization = max(0, personalization - 8)
    if weak_empathy:
        personalization = max(0, personalization - 6)

    grounding = 20 if evidence_count >= 2 else 12 if evidence_count == 1 else 4
    conversion = 15
    conversion -= 6 if offer_too_early else 0
    conversion -= 5 if weak_actionability else 0
    conversion = max(0, conversion)

    total = naturalness + personalization + grounding + conversion

    complaints: list[str] = []
    if low_specificity:
        complaints.append("내가 말한 구체 상황을 듣고도 3턴 이후 일반론으로만 흐른다.")
    if repeated_template:
        complaints.append("문장 첫머리와 상담 템플릿이 반복돼 챗봇처럼 느껴진다.")
    if robotic_count >= 3:
        complaints.append("‘이맘때’, ‘열에 아홉’ 같은 권위 표현이 과해서 자연스러운 상담처럼 안 들린다.")
    if showy_authority:
        complaints.append("상담보다 지식을 과시하는 말투가 보여서, 내 얘기를 듣는 느낌이 약하다.")
    if offer_too_early:
        complaints.append("신뢰가 쌓이기 전에 다음 단계 제안이 빨리 나온다.")
    if wrong_salutation:
        complaints.append("사용자가 선택하지 않은 성별/호칭을 추정해 부른다.")
    if enum_leak:
        complaints.append("내부 호칭 코드(father/mother/neutral)가 답변 문장에 그대로 새어 나와 매우 부자연스럽다.")
    if weak_grounding:
        complaints.append("연구·커뮤니티·현장 자료가 녹아든 느낌이 약하다.")
    if weak_empathy:
        complaints.append("내 감정을 짧게라도 받아주는 느낌이 부족하다.")
    if jargon_overload:
        complaints.append("영어·전문 용어가 섞여 AI 초보자가 바로 이해하기 어렵다.")
    if weak_actionability:
        complaints.append("마지막으로 뭘 해야 하는지 선명한 한 단계가 없다.")

    return {
        "total_score": total,
        "subscores": {
            "naturalness": naturalness,
            "personalization": personalization,
            "grounding": grounding,
            "conversion_readiness": conversion,
        },
        "metrics": {
            "ai_turn_count": ai_turn_count,
            "specificity_hits": specificity_hits,
            "specificity_after_turn3": specificity_after_turn3,
            "personalization_ratio": personalization_ratio,
            "robotic_marker_count": robotic_count,
            "generic_marker_count": generic_count,
            "evidence_marker_count": evidence_count,
            "pretentious_marker_count": pretentious_count,
            "empathy_marker_count": empathy_count,
            "jargon_marker_count": jargon_count,
            "action_marker_count": action_count,
            "show_offer_turn": show_offer_turn,
        },
        "flags": {
            "low_specificity": low_specificity,
            "repeated_template": repeated_template,
            "offer_too_early": offer_too_early,
            "wrong_salutation": wrong_salutation,
            "enum_leak": enum_leak,
            "weak_grounding": weak_grounding,
            "weak_empathy": weak_empathy,
            "jargon_overload": jargon_overload,
            "showy_authority": showy_authority,
            "weak_actionability": weak_actionability,
        },
        "customer_complaints": complaints,
    }


def run_scenario(client: httpx.Client, base_url: str, scenario: Scenario, run_id: str, mode: str) -> dict[str, Any]:
    email = scenario_email(scenario, run_id)
    paths = resolve_api_paths(mode)
    headers = auth_headers(mode)
    bootstrap = post_json(
        client,
        f"{base_url}{paths['bootstrap']}",
        {
            "segment": scenario.segment,
            "name": scenario.profile.get("name", ""),
            "email": email,
            "preferred_salutation": scenario.profile.get("preferred_salutation", "neutral"),
            "locale": scenario.profile.get("locale", "ko-KR"),
            "force_new": True,
        },
        headers=headers,
    )
    messages = [
        {
            "role": item["role"],
            "text": item["text"],
            "phase": item.get("phase", "opening"),
            "toneLevel": item.get("toneLevel", 0),
        }
        for item in bootstrap.get("messages", [])
    ]
    case_id = bootstrap.get("case", {}).get("id")
    show_offer_turn: int | None = None

    for idx, user_text in enumerate(scenario.turns, start=1):
        messages.append({"role": USER_ROLE, "text": user_text})
        diagnose = post_json(
            client,
            f"{base_url}{paths['diagnose']}",
            {
                "segment": scenario.segment,
                "turn": idx,
                "case_id": case_id,
                "preferred_salutation": scenario.profile.get("preferred_salutation", "neutral"),
                "locale": scenario.profile.get("locale", "ko-KR"),
                "history": [{"role": m["role"], "text": m["text"]} for m in messages],
                "user_text": user_text,
            },
            headers=headers,
        )
        messages.append(
            {
                "role": AI_ROLE,
                "text": diagnose.get("message", ""),
                "phase": diagnose.get("phase", "probing"),
                "toneLevel": diagnose.get("tone_level", 0),
                "showOffer": bool(diagnose.get("show_offer")),
            }
        )
        if diagnose.get("show_offer") and show_offer_turn is None:
            show_offer_turn = idx

    curriculum_payload = {
        "segment": scenario.segment,
        "track": "free_start",
        "turn": len(scenario.turns),
        "case_id": case_id,
        "preferred_salutation": scenario.profile.get("preferred_salutation", "neutral"),
        "locale": scenario.profile.get("locale", "ko-KR"),
        "history": [{"role": m["role"], "text": m["text"]} for m in messages],
    }
    free_start_res = safe_post_json(client, f"{base_url}{paths['curriculum']}", curriculum_payload, headers=headers)
    next_steps_res = safe_post_json(
        client,
        f"{base_url}{paths['curriculum']}",
        {**curriculum_payload, "track": "next_steps"},
        headers=headers,
    )
    resume_res = safe_get_json(client, f"{base_url}{paths['resume']}", {"email": email}, headers=headers)
    evaluation = evaluate_transcript(
        scenario,
        messages,
        show_offer_turn,
        free_start_res.get("data") if free_start_res.get("ok") else None,
    )

    runtime_issues = []
    if not free_start_res.get("ok"):
        runtime_issues.append(f"free_start_timeout_or_error: {free_start_res.get('error')}")
    if not next_steps_res.get("ok"):
        runtime_issues.append(f"next_steps_timeout_or_error: {next_steps_res.get('error')}")
    if not resume_res.get("ok"):
        runtime_issues.append(f"resume_timeout_or_error: {resume_res.get('error')}")
    if runtime_issues:
        evaluation["customer_complaints"].append("일부 단계형 응답이 늦거나 타임아웃돼 실제 고객 입장에선 흐름이 끊길 수 있다.")
        evaluation["runtime_issues"] = runtime_issues

    return {
        "scenario_id": scenario.id,
        "label": scenario.label,
        "segment": scenario.segment,
        "email": email,
        "case_id": case_id,
        "bootstrap": {
            "started_fresh": bootstrap.get("started_fresh"),
            "is_returning": bootstrap.get("is_returning"),
            "has_prior_customer": bootstrap.get("has_prior_customer"),
        },
        "resume_check": {
            "ok": bool(resume_res.get("ok")),
            "message_count": len((resume_res.get("data") or {}).get("messages", [])),
            "is_returning": (resume_res.get("data") or {}).get("is_returning"),
            "case_id": ((resume_res.get("data") or {}).get("case") or {}).get("id"),
            "error": resume_res.get("error", ""),
        },
        "transcript": messages,
        "curriculum": {
            "free_start": free_start_res.get("data"),
            "next_steps": next_steps_res.get("data"),
            "free_start_error": free_start_res.get("error", ""),
            "next_steps_error": next_steps_res.get("error", ""),
        },
        "evaluation": evaluation,
    }


def load_previous_report() -> dict[str, Any] | None:
    if not LATEST_JSON.exists():
        return None
    try:
        return json.loads(LATEST_JSON.read_text(encoding="utf-8"))
    except Exception:
        return None


def compare_with_previous(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    if not previous:
        return {"has_previous": False}
    prev_by_id = {item["scenario_id"]: item for item in previous.get("results", [])}
    deltas = []
    for item in current.get("results", []):
        prev = prev_by_id.get(item["scenario_id"])
        if not prev:
            continue
        delta = item["evaluation"]["total_score"] - prev["evaluation"]["total_score"]
        deltas.append({"scenario_id": item["scenario_id"], "delta": delta})
        item["evaluation"]["delta_vs_previous"] = delta
    avg_delta = round(sum(d["delta"] for d in deltas) / len(deltas), 2) if deltas else None
    return {
        "has_previous": bool(deltas),
        "previous_generated_at": previous.get("generated_at"),
        "average_score_delta": avg_delta,
        "scenario_deltas": deltas,
    }


def build_summary(report: dict[str, Any]) -> dict[str, Any]:
    scores = [item["evaluation"]["total_score"] for item in report["results"]]
    top_complaints: dict[str, int] = {}
    top_flags: dict[str, int] = {}
    for item in report["results"]:
        for complaint in item["evaluation"]["customer_complaints"]:
            top_complaints[complaint] = top_complaints.get(complaint, 0) + 1
        for flag, active in item["evaluation"]["flags"].items():
            if active:
                top_flags[flag] = top_flags.get(flag, 0) + 1
    return {
        "scenario_count": len(report["results"]),
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "min_score": min(scores) if scores else 0,
        "max_score": max(scores) if scores else 0,
        "top_flags": dict(sorted(top_flags.items(), key=lambda x: (-x[1], x[0]))[:8]),
        "top_complaints": dict(sorted(top_complaints.items(), key=lambda x: (-x[1], x[0]))[:8]),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Edu Pilot Simulation Report — {report['generated_at']}",
        "",
        f"- base_url: `{report['base_url']}`",
        f"- config_version: `{report['config_version']}`",
        f"- average_score: `{report['summary']['average_score']}`",
        f"- min_score: `{report['summary']['min_score']}`",
        f"- max_score: `{report['summary']['max_score']}`",
    ]
    comparison = report.get("comparison") or {}
    if comparison.get("has_previous"):
        lines.append(f"- average_score_delta_vs_previous: `{comparison.get('average_score_delta')}`")
    lines.extend([
        "",
        "## Common Flags",
        "",
    ])
    for flag, count in (report["summary"].get("top_flags") or {}).items():
        lines.append(f"- `{flag}`: {count}")
    lines.extend([
        "",
        "## Common Customer Complaints",
        "",
    ])
    for complaint, count in (report["summary"].get("top_complaints") or {}).items():
        lines.append(f"- {complaint} ({count})")
    lines.extend(["", "## Scenario Results", ""])
    for item in report["results"]:
        ev = item["evaluation"]
        lines.extend(
            [
                f"### {item['label']}",
                "",
                f"- scenario_id: `{item['scenario_id']}`",
                f"- score: `{ev['total_score']}`",
                f"- segment: `{item['segment']}`",
                f"- case_id: `{item['case_id']}`",
                f"- show_offer_turn: `{ev['metrics']['show_offer_turn']}`",
                f"- personalization_ratio: `{ev['metrics']['personalization_ratio']}`",
                f"- evidence_marker_count: `{ev['metrics']['evidence_marker_count']}`",
                f"- resume_message_count: `{item['resume_check']['message_count']}`",
            ]
        )
        if "delta_vs_previous" in ev:
            lines.append(f"- delta_vs_previous: `{ev['delta_vs_previous']}`")
        if ev["customer_complaints"]:
            lines.append("- customer complaints:")
            for complaint in ev["customer_complaints"]:
                lines.append(f"  - {complaint}")
        lines.append("- last_ai_message:")
        last_ai = next((m["text"] for m in reversed(item["transcript"]) if m["role"] == AI_ROLE), "")
        lines.append(f"  - {last_ai[:280]}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live customer simulations against the Edu Pilot public API.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--scenario", action="append", default=[], help="Run only matching scenario id(s).")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--mode", choices=["public", "internal"], default=DEFAULT_MODE)
    args = parser.parse_args()

    config_meta, scenarios = load_scenarios(Path(args.config))
    selected = [s for s in scenarios if not args.scenario or s.id in set(args.scenario)]
    if not selected:
        raise SystemExit("No scenarios selected.")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    results = []
    with httpx.Client(timeout=args.timeout, headers={"User-Agent": "harness-edu-sim/1.0"}) as client:
        for scenario in selected:
            try:
                results.append(run_scenario(client, args.base_url.rstrip("/"), scenario, run_id, args.mode))
            except Exception as exc:  # noqa: BLE001
                results.append(
                    {
                        "scenario_id": scenario.id,
                        "label": scenario.label,
                        "segment": scenario.segment,
                        "email": scenario_email(scenario, run_id),
                        "case_id": None,
                        "bootstrap": {"started_fresh": False, "is_returning": False, "has_prior_customer": False},
                        "resume_check": {"ok": False, "message_count": 0, "is_returning": False, "case_id": None, "error": ""},
                        "transcript": [],
                        "curriculum": {"free_start": None, "next_steps": None, "free_start_error": "", "next_steps_error": ""},
                        "evaluation": {
                            "total_score": 0,
                            "subscores": {"naturalness": 0, "personalization": 0, "grounding": 0, "conversion_readiness": 0},
                            "metrics": {"ai_turn_count": 0, "specificity_hits": 0, "specificity_after_turn3": 0, "personalization_ratio": 0, "robotic_marker_count": 0, "generic_marker_count": 0, "evidence_marker_count": 0, "action_marker_count": 0, "show_offer_turn": None},
                            "flags": {"low_specificity": True, "repeated_template": False, "offer_too_early": False, "wrong_salutation": False, "weak_grounding": True, "weak_actionability": True},
                            "customer_complaints": [f"시나리오 자체가 실패했다: {type(exc).__name__}: {exc}"],
                            "runtime_issues": [f"scenario_failure: {type(exc).__name__}: {exc}"],
                        },
                    }
                )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run_id,
        "base_url": args.base_url.rstrip("/"),
        "mode": args.mode,
        "config_version": config_meta.get("version", "unknown"),
        "results": results,
    }
    previous = load_previous_report()
    report["comparison"] = compare_with_previous(report, previous)
    report["summary"] = build_summary(report)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = f"{datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d')}_{run_id}"
    json_path = REPORT_DIR / f"edu_pilot_simulations_{stamp}.json"
    md_path = REPORT_DIR / f"edu_pilot_simulations_{stamp}.md"
    json_text = json.dumps(report, ensure_ascii=False, indent=2)
    md_text = render_markdown(report)
    json_path.write_text(json_text, encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    LATEST_JSON.write_text(json_text, encoding="utf-8")
    LATEST_MD.write_text(md_text, encoding="utf-8")
    print(json.dumps({"ok": True, "json_report": str(json_path), "md_report": str(md_path), "average_score": report["summary"]["average_score"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
