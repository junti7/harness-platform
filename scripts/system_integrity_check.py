import argparse
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import execute_query


REQUIRED_TABLE_COLUMNS: dict[str, list[str]] = {
    "raw_signals": ["id", "source", "raw_data", "status"],
    "filtered_signals": ["id", "title", "summary", "score", "content_hash"],
    "refined_outputs": ["id", "filtered_signal_id", "final_title", "final_body", "published"],
    "pipeline_runs": ["id", "correlation_id", "status", "started_at", "finished_at"],
    "ceo_decisions": ["id", "target_type", "target_id", "approval_type", "decision"],
    "source_catalog": ["id", "source_name", "base_url", "enabled"],
}

REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "OLLAMA_HOST",
    "OLLAMA_MODEL",
    "DAILY_COST_LIMIT_USD",
]


def _table_exists(table_name: str) -> bool:
    rows = execute_query(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        ) AS exists
        """,
        (table_name,),
        fetch=True,
    )
    return bool(rows and rows[0]["exists"])


def _columns_for(table_name: str) -> set[str]:
    rows = execute_query(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table_name,),
        fetch=True,
    )
    return {row["column_name"] for row in rows or []}


def _check_schema() -> list[str]:
    findings: list[str] = []
    for table_name, required_columns in REQUIRED_TABLE_COLUMNS.items():
        if not _table_exists(table_name):
            findings.append(f"missing_table:{table_name}")
            continue
        present = _columns_for(table_name)
        for column in required_columns:
            if column not in present:
                findings.append(f"missing_column:{table_name}.{column}")
    return findings


def _check_env() -> list[str]:
    findings: list[str] = []
    for key in REQUIRED_ENV_VARS:
        if not os.getenv(key):
            findings.append(f"missing_env:{key}")
    return findings


def _check_model_identity() -> list[str]:
    findings: list[str] = []
    tier2_model = os.getenv("OLLAMA_MODEL", "").strip()
    if not tier2_model:
        findings.append("missing_model_identity:OLLAMA_MODEL")

    cost_limit = os.getenv("DAILY_COST_LIMIT_USD", "").strip()
    try:
        float(cost_limit)
    except ValueError:
        findings.append("invalid_cost_limit:DAILY_COST_LIMIT_USD")

    return findings


def run_check() -> dict[str, Any]:
    schema_findings = _check_schema()
    env_findings = _check_env()
    model_findings = _check_model_identity()
    findings = schema_findings + env_findings + model_findings
    return {
        "ok": not findings,
        "schema_findings": schema_findings,
        "env_findings": env_findings,
        "model_findings": model_findings,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Harness system integrity preflight check.")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    result = run_check()
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["ok"]:
            print("OK: schema/env/model integrity preflight passed")
        else:
            print("FAILED: schema/env/model integrity preflight")
            for finding in result["findings"]:
                print(f"- {finding}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
