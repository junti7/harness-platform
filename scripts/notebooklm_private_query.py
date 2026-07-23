#!/usr/bin/env python3
"""Query NotebookLM with sensitive text supplied over stdin, not argv."""

from __future__ import annotations

import json
import sys

from notebooklm_tools.cli.utils import get_client
from notebooklm_tools.services import chat as chat_service


def main() -> int:
    request = json.load(sys.stdin)
    with get_client(request.get("profile")) as client:
        result = chat_service.query(
            client,
            str(request["notebook_id"]),
            str(request["question"]),
            timeout=float(request.get("timeout", 120)),
        )
    result.pop("question", None)
    json.dump(result, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
