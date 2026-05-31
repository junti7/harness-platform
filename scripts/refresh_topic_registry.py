from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.database import execute_query
from core.topic_registry import refresh_topic_registry


def main() -> int:
    rows = execute_query(
        "SELECT source, status, ingested_at, raw_data->>'title' as title "
        "FROM raw_signals "
        "WHERE coalesce(raw_data->>'domain', 'physical_ai') = 'physical_ai' "
        "ORDER BY ingested_at DESC LIMIT 120",
        fetch=True,
    )
    payload = refresh_topic_registry("physical_ai", rows)
    print(json.dumps({
        "domain": payload.get("domain"),
        "generated_at": payload.get("generated_at"),
        "auto_topics": len(payload.get("auto_topics", [])),
        "query_sources": len(payload.get("query_sources", [])),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
