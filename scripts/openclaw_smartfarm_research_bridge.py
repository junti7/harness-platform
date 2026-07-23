"""Read-only OpenClaw command surface for smartfarm market research."""

from __future__ import annotations

import argparse
import json
import sys
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only smartfarm research bridge. This command surface intentionally "
            "has no form-fill, cart, order, payment, GPIO, or actuator command."
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
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
