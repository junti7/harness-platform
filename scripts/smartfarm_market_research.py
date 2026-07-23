"""Build and validate OpenClaw smartfarm procurement research artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = REPO_ROOT / "configs/smartfarm/procurement_items_v1.json"
MIN_CANDIDATES = 3
VERIFIED_CHECK_VALUES = {True, "verified", "pass", "yes"}
SEARCH_RESULT_HOSTS = {
    "www.google.com",
    "google.com",
    "search.naver.com",
    "www.bing.com",
    "bing.com",
    "duckduckgo.com",
    "www.duckduckgo.com",
}


def _now() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")


def load_catalog(path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("items"), list) or not payload["items"]:
        raise ValueError("procurement catalog must contain a non-empty items list")
    return payload


def build_research_plan(catalog: dict[str, Any]) -> dict[str, Any]:
    items = []
    for item in catalog["items"]:
        items.append(
            {
                "id": item["id"],
                "name_ko": item["name_ko"],
                "phase": item.get("phase", "now"),
                "search_queries": item["search_queries"],
                "minimum_candidates": MIN_CANDIDATES,
                "required_checks": item["required_checks"],
            }
        )
    return {
        "schema_version": "1.0",
        "generated_at": _now(),
        "owner": "OpenClaw Smartfarm Market Research",
        "objective": (
            "Compare purchasable Korean-market candidates for the home smartfarm pilot "
            "using current, source-backed price, delivery, safety, and compatibility evidence."
        ),
        "market": catalog.get("market", "KR"),
        "currency": catalog.get("currency", "KRW"),
        "controller_architecture": {
            "edge_node": "ESP32 programmed with the Arduino framework",
            "gateway": "Raspberry Pi",
            "rule": (
                "Prefer ESP32 over Arduino Uno for sensor and actuator nodes. "
                "Use ESP32 ADC1 pins for analog soil sensing while Wi-Fi is active."
            ),
        },
        "items": items,
        "candidate_contract": {
            "required_fields": [
                "item_id",
                "product_name",
                "vendor",
                "product_url",
                "observed_at",
                "price",
                "currency",
                "shipping_cost",
                "delivery_estimate",
                "availability",
                "evidence_urls",
                "required_check_results",
                "risks",
                "recommendation",
            ],
            "recommendation_values": ["recommended", "alternate", "reject"],
            "rules": [
                "Use a direct product or manufacturer URL, never a search-result URL.",
                "Record unknown values as unknown; never infer a safety mark or specification.",
                "Preserve at least two evidence URLs for the recommended candidate when possible.",
                (
                    "For every required check on a recommended or alternate candidate, record "
                    "{status, evidence_url, note}; status must be verified and evidence_url direct."
                ),
                "Treat seller claims as claims and distinguish them from manufacturer specifications.",
                "Do not add to cart, place an order, or spend money.",
                "Any electrical or pump candidate with unresolved safety or compatibility checks must be rejected.",
            ],
        },
        "deliverables": {
            "json_report": "runtime/smartfarm_market_research/latest.json",
            "human_summary": "runtime/smartfarm_market_research/latest.md",
            "decision": "shortlist_only_no_purchase",
        },
    }


def _is_direct_http_url(value: Any) -> bool:
    try:
        parsed = urlparse(str(value))
    except ValueError:
        return False
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
        and parsed.netloc.lower() not in SEARCH_RESULT_HOSTS
    )


def _check_status_and_evidence(value: Any) -> tuple[Any, str]:
    if not isinstance(value, dict):
        return value, ""
    return value.get("status"), str(value.get("evidence_url", ""))


def validate_report(report: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    expected = {item["id"]: item for item in catalog["items"]}
    candidates = report.get("candidates")
    if not isinstance(candidates, list):
        return {"ok": False, "findings": ["candidates must be a list"], "counts": {}}

    counts = {item_id: 0 for item_id in expected}
    recommended_counts = {item_id: 0 for item_id in expected}
    required_fields = build_research_plan(catalog)["candidate_contract"]["required_fields"]

    for index, candidate in enumerate(candidates):
        label = f"candidate[{index}]"
        if not isinstance(candidate, dict):
            findings.append(f"{label} must be an object")
            continue
        missing = [field for field in required_fields if field not in candidate]
        if missing:
            findings.append(f"{label} missing fields: {', '.join(missing)}")
        item_id = candidate.get("item_id")
        if item_id not in expected:
            findings.append(f"{label} has unknown item_id: {item_id}")
            continue
        counts[item_id] += 1
        if candidate.get("recommendation") == "recommended":
            recommended_counts[item_id] += 1

        if not _is_direct_http_url(candidate.get("product_url")):
            findings.append(f"{label} product_url must be a direct http(s) product URL")
        evidence_urls = candidate.get("evidence_urls")
        if not isinstance(evidence_urls, list) or not evidence_urls:
            findings.append(f"{label} requires at least one evidence URL")
        elif any(not _is_direct_http_url(url) for url in evidence_urls):
            findings.append(f"{label} evidence_urls must contain direct http(s) URLs")
        if (
            candidate.get("recommendation") == "recommended"
            and isinstance(evidence_urls, list)
            and len(set(evidence_urls)) < 2
        ):
            findings.append(f"{label} recommended candidate requires two evidence URLs")

        try:
            observed_at = datetime.fromisoformat(str(candidate.get("observed_at", "")))
            if observed_at.tzinfo is None:
                raise ValueError
            now = datetime.now(ZoneInfo("Asia/Seoul"))
            if observed_at < now - timedelta(days=14) or observed_at > now + timedelta(days=1):
                findings.append(f"{label} observed_at must be within the last 14 days")
        except ValueError:
            findings.append(f"{label} observed_at must be timezone-aware ISO8601")

        checks = candidate.get("required_check_results")
        if not isinstance(checks, dict):
            findings.append(f"{label} required_check_results must be an object")
        else:
            missing_checks = [
                check for check in expected[item_id]["required_checks"] if check not in checks
            ]
            if missing_checks:
                findings.append(
                    f"{label} missing required checks: {', '.join(missing_checks)}"
                )
            if candidate.get("recommendation") in {"recommended", "alternate"}:
                unresolved = [
                    check
                    for check in expected[item_id]["required_checks"]
                    if _check_status_and_evidence(checks.get(check))[0]
                    not in VERIFIED_CHECK_VALUES
                ]
                if unresolved:
                    findings.append(
                        f"{label} shortlisted candidate has unresolved checks: "
                        f"{', '.join(unresolved)}"
                    )
                missing_evidence = [
                    check
                    for check in expected[item_id]["required_checks"]
                    if not _is_direct_http_url(
                        _check_status_and_evidence(checks.get(check))[1]
                    )
                ]
                if missing_evidence:
                    findings.append(
                        f"{label} shortlisted candidate lacks direct check evidence: "
                        f"{', '.join(missing_evidence)}"
                    )
        if candidate.get("recommendation") not in {"recommended", "alternate", "reject"}:
            findings.append(f"{label} has invalid recommendation value")

    for item_id in expected:
        if counts[item_id] < MIN_CANDIDATES:
            findings.append(
                f"{item_id} has {counts[item_id]} candidates; minimum is {MIN_CANDIDATES}"
            )
        if recommended_counts[item_id] != 1:
            findings.append(
                f"{item_id} must have exactly one recommended candidate; "
                f"found {recommended_counts[item_id]}"
            )

    return {"ok": not findings, "findings": findings, "counts": counts}


def command_plan(args: argparse.Namespace) -> int:
    plan = build_research_plan(load_catalog(Path(args.catalog)))
    rendered = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


def command_validate(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    result = validate_report(report, load_catalog(Path(args.catalog)))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Build the OpenClaw research contract.")
    plan.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    plan.add_argument("--output")
    plan.set_defaults(func=command_plan)

    validate = subparsers.add_parser("validate", help="Validate a completed market report.")
    validate.add_argument("report")
    validate.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    validate.set_defaults(func=command_validate)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
