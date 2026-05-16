import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from scripts.openclaw_codex_bridge import status_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist OpenClaw bridge heartbeat for 24/7 hosts.")
    parser.add_argument(
        "--output",
        default="runtime/openclaw_status.json",
        help="Path to write the latest bridge status JSON.",
    )
    args = parser.parse_args()

    payload = status_snapshot()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(str(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
