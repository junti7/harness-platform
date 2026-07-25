"""OpenClaw command surface for smartfarm operations.

Two kinds of commands live here:
  - market research (plan/validate/search/open/extract): read-only, no cart/
    order/payment/GPIO/actuator command.
  - ops (alerts/report/threshold-propose/threshold-decide/threshold-apply):
    read sensor/pump history from the pi_hub SQLite db and propose config.yaml
    threshold changes. threshold-apply is the only command with a side effect
    (patching config.yaml), and it refuses to run unless threshold-decide
    already recorded an 'approved' decision for that proposal_id. Nothing in
    this file ever issues an MQTT command or touches an actuator directly —
    that stays exclusively in hardware/smartfarm/pi_hub/hub.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.smartfarm_market_research import (
    DEFAULT_CATALOG,
    build_research_plan,
    load_catalog,
    validate_report,
)
from scripts import smartfarm_ops as ops


def _emit(payload: Any, output: str | None = None) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


def command_plan(args: argparse.Namespace) -> int:
    _emit(build_research_plan(load_catalog(Path(args.catalog))), args.output)
    return 0


def command_validate(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    result = validate_report(report, load_catalog(Path(args.catalog)))
    _emit(result, args.output)
    return 0 if result["ok"] else 2


def command_search(args: argparse.Namespace) -> int:
    from adapters.content.tools import structured_web_search

    payload = structured_web_search(args.query, count=args.limit)
    _emit(payload, args.output)
    return 0 if payload["ok"] else 2


def command_open(args: argparse.Namespace) -> int:
    from scripts.browser_control import browser_open

    _emit(browser_open(args.url, extract_text=True), args.output)
    return 0


def command_extract(args: argparse.Namespace) -> int:
    from scripts.browser_control import browser_extract

    _emit(browser_extract(args.url, args.selector), args.output)
    return 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _deliver_to_slack(route: str, text: str) -> dict[str, Any]:
    """Best-effort Slack delivery. Never raises past this call: a broken/
    unconfigured Slack route must not turn a working alert/report command into
    a hard failure — it degrades to 'delivered: false' with the reason."""
    from adapters.content.slack_router import send_slack_route

    try:
        send_slack_route(route, {"text": text})
        return {"delivered": True, "route": route}
    except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring
        return {"delivered": False, "route": route, "error": f"{type(exc).__name__}: {exc}"}


def _alerts_to_slack_text(alerts: list[dict[str, Any]]) -> str:
    if not alerts:
        return "🌱 스마트팜: 이상 없음"
    lines = [f"🌱 스마트팜 알림 ({len(alerts)}건)"]
    for a in alerts:
        metric = f"/{a['metric']}" if a.get("metric") else ""
        lines.append(f"• [{a['severity']}] {a['zone_id']}{metric} — {a['type']}: {a['detail']}")
    return "\n".join(lines)


def command_alerts(args: argparse.Namespace) -> int:
    alerts = ops.detect_alerts(
        db_path=Path(args.db), config_path=Path(args.config), lookback_hours=args.lookback_hours
    )
    payload: dict[str, Any] = {"generated_at": _now_iso(), "alerts": alerts}
    if args.deliver and alerts:
        payload["slack"] = _deliver_to_slack(args.deliver, _alerts_to_slack_text(alerts))
    _emit(payload, args.output)
    return 0


def _report_to_slack_text(report: dict[str, Any]) -> str:
    lines = [f"🌱 스마트팜 리포트 (최근 {report['period_hours']:.0f}시간)"]
    for zone_id, zone in report["zones"].items():
        soil = zone.get("soil_pct", {})
        soil_summary = (
            f"{soil['min']}~{soil['max']}% (avg {soil['avg']})" if soil.get("count") else "데이터 없음"
        )
        lines.append(f"• {zone_id}: 토양수분 {soil_summary}, 펌프 {zone['pump']['on_count']}회 작동")
    return "\n".join(lines)


def command_report(args: argparse.Namespace) -> int:
    report = ops.build_status_report(
        db_path=Path(args.db), config_path=Path(args.config), period_hours=args.period_hours
    )
    if args.deliver:
        report["slack"] = _deliver_to_slack(args.deliver, _report_to_slack_text(report))
    _emit(report, args.output)
    return 0


def command_threshold_propose(args: argparse.Namespace) -> int:
    proposals = ops.propose_threshold_adjustments(
        db_path=Path(args.db), config_path=Path(args.config), lookback_hours=args.lookback_hours
    )
    _emit(
        {
            "generated_at": _now_iso(),
            "note": (
                "Data-driven heuristic suggestions only, not agronomic advice. "
                "Nothing is applied until threshold-decide (approved) + threshold-apply are run."
            ),
            "proposals": proposals,
        },
        args.output,
    )
    return 0


def command_threshold_decide(args: argparse.Namespace) -> int:
    proposals = ops.propose_threshold_adjustments(
        db_path=Path(args.db), config_path=Path(args.config), lookback_hours=args.lookback_hours
    )
    proposal = next((p for p in proposals if p["proposal_id"] == args.proposal_id), None)
    if proposal is None:
        _emit(
            {
                "ok": False,
                "error": (
                    f"proposal_id={args.proposal_id} does not match any currently live "
                    "proposal. Re-run threshold-propose to get current proposal_ids."
                ),
            },
            args.output,
        )
        return 2
    record = ops.record_threshold_decision(
        proposal,
        decision=args.decision,
        decided_by=args.decided_by,
        note=args.note or "",
        log_path=Path(args.log),
    )
    _emit({"ok": True, "recorded": record}, args.output)
    return 0


def command_threshold_apply(args: argparse.Namespace) -> int:
    try:
        result = ops.apply_threshold_decision(
            args.proposal_id, config_path=Path(args.config), log_path=Path(args.log)
        )
    except (PermissionError, ValueError, FileNotFoundError) as exc:
        _emit({"ok": False, "error": str(exc)}, args.output)
        return 2
    _emit({"ok": True, "applied": result}, args.output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "OpenClaw smartfarm command surface. Market research commands "
            "(plan/validate/search/open/extract) are read-only with no cart/order/"
            "payment/GPIO/actuator command. Ops commands (alerts/report/threshold-*) "
            "read the pi_hub SQLite db; only threshold-apply writes to config.yaml, "
            "and only after threshold-decide recorded an 'approved' decision. No "
            "command here ever issues an MQTT command or touches an actuator — that "
            "stays exclusively in hardware/smartfarm/pi_hub/hub.py."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan")
    plan.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    plan.add_argument("--output")
    plan.set_defaults(func=command_plan)

    validate = subparsers.add_parser("validate")
    validate.add_argument("report")
    validate.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    validate.add_argument("--output")
    validate.set_defaults(func=command_validate)

    search = subparsers.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--output")
    search.set_defaults(func=command_search)

    open_page = subparsers.add_parser("open")
    open_page.add_argument("url")
    open_page.add_argument("--output")
    open_page.set_defaults(func=command_open)

    extract = subparsers.add_parser("extract")
    extract.add_argument("url")
    extract.add_argument("selector")
    extract.add_argument("--output")
    extract.set_defaults(func=command_extract)

    alerts = subparsers.add_parser("alerts", help="Scan sensor/pump history for anomalies.")
    alerts.add_argument("--db", default=str(ops.DEFAULT_DB_PATH))
    alerts.add_argument("--config", default=str(ops.DEFAULT_CONFIG_PATH))
    alerts.add_argument("--lookback-hours", type=float, default=24.0)
    alerts.add_argument(
        "--deliver",
        metavar="ROUTE",
        help=(
            "Slack route name to push a summary to when alerts are found "
            "(e.g. ops_incidents). Omit to only print JSON (default). Reusing an "
            "existing company route mixes smartfarm alerts into that real channel."
        ),
    )
    alerts.add_argument("--output")
    alerts.set_defaults(func=command_alerts)

    report = subparsers.add_parser("report", help="Per-zone status summary for a period.")
    report.add_argument("--db", default=str(ops.DEFAULT_DB_PATH))
    report.add_argument("--config", default=str(ops.DEFAULT_CONFIG_PATH))
    report.add_argument("--period-hours", type=float, default=24.0)
    report.add_argument(
        "--deliver",
        metavar="ROUTE",
        help="Slack route name to push this report to (e.g. exec_daily_brief). Omit to only print JSON.",
    )
    report.add_argument("--output")
    report.set_defaults(func=command_report)

    threshold_propose = subparsers.add_parser(
        "threshold-propose", help="Data-driven threshold adjustment suggestions (proposal only)."
    )
    threshold_propose.add_argument("--db", default=str(ops.DEFAULT_DB_PATH))
    threshold_propose.add_argument("--config", default=str(ops.DEFAULT_CONFIG_PATH))
    threshold_propose.add_argument("--lookback-hours", type=float, default=168.0)
    threshold_propose.add_argument("--output")
    threshold_propose.set_defaults(func=command_threshold_propose)

    threshold_decide = subparsers.add_parser(
        "threshold-decide", help="Record CEO approve/reject for a proposal_id."
    )
    threshold_decide.add_argument("proposal_id")
    threshold_decide.add_argument("decision", choices=["approved", "rejected"])
    threshold_decide.add_argument("--decided-by", default="CEO")
    threshold_decide.add_argument("--note", default="")
    threshold_decide.add_argument("--db", default=str(ops.DEFAULT_DB_PATH))
    threshold_decide.add_argument("--config", default=str(ops.DEFAULT_CONFIG_PATH))
    threshold_decide.add_argument("--lookback-hours", type=float, default=168.0)
    threshold_decide.add_argument("--log", default=str(ops.DEFAULT_DECISION_LOG_PATH))
    threshold_decide.add_argument("--output")
    threshold_decide.set_defaults(func=command_threshold_decide)

    threshold_apply = subparsers.add_parser(
        "threshold-apply",
        help="Patch config.yaml for a proposal_id. Refuses unless already 'approved'.",
    )
    threshold_apply.add_argument("proposal_id")
    threshold_apply.add_argument("--config", default=str(ops.DEFAULT_CONFIG_PATH))
    threshold_apply.add_argument("--log", default=str(ops.DEFAULT_DECISION_LOG_PATH))
    threshold_apply.add_argument("--output")
    threshold_apply.set_defaults(func=command_threshold_apply)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
