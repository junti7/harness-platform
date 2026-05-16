import argparse
from pathlib import Path

from scripts.dispatch_llm_task_packet import dispatch_packet


def build_packet(args: argparse.Namespace) -> dict:
    input_artifacts = [str(args.brief)]
    if args.memory_doc:
        input_artifacts.append(str(args.memory_doc))

    notes = [
        f"customer_external_ref={args.external_ref}",
        "This packet starts after customer-memory draft generation.",
        "Use the brief as the customer-specific framing anchor, not as final evidence.",
    ]
    checks = [
        "Return customer-specific findings, not generic domain commentary.",
        "Separate validated evidence from assumptions.",
        "Recommend a next research plan that resolves the open questions in the brief.",
        "Preserve the customer's preferred delivery style when proposing the next artifact.",
    ]

    return {
        "generated_at": None,
        "owner": "Codex Chief of Staff",
        "task_kind": "customer_research_packet",
        "title": args.title,
        "objective": args.objective,
        "input_artifacts": input_artifacts,
        "output_artifacts": [str(args.output_dir)],
        "checks": checks,
        "notes": notes,
        "callback_route": args.callback_route,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch a customer-specific research packet to external LLM CLIs.")
    parser.add_argument("external_ref")
    parser.add_argument("brief", type=Path)
    parser.add_argument("--memory-doc", type=Path, default=Path("docs/CUSTOMER_MEMORY_SCHEMA_V1.md"))
    parser.add_argument("--title", required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--provider", action="append", choices=["claude", "gemini", "copilot"], dest="providers")
    parser.add_argument("--callback-route", default="agent_openclaw_routing")
    parser.add_argument("--notify-route", default="agent_openclaw_routing")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/reports/llm_outputs"))
    args = parser.parse_args()

    packet = build_packet(args)
    providers = args.providers or ["claude", "gemini", "copilot"]
    result = dispatch_packet(packet, providers, args.output_dir, args.notify_route)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
