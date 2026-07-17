"""Cost ledger for visual artifacts and production steps outside api_cost_log."""
from __future__ import annotations

import json
import os
from typing import Any

from core.database import execute_query


def log_artifact_cost(
    *,
    job_id: str,
    artifact_type: str,
    provider: str,
    model: str | None = None,
    units: float = 1,
    unit_name: str = "call",
    unit_price_usd: float | None = None,
    actual_cost_usd: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Write a reproducible estimate; actual provider receipts may be added later."""
    estimated = float(units) * float(unit_price_usd or 0)
    execute_query(
        """INSERT INTO artifact_cost_log
        (job_id, artifact_type, provider, model, units, unit_name,
         unit_price_usd, estimated_cost_usd, actual_cost_usd, metadata)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
        (job_id, artifact_type, provider, model, units, unit_name,
         unit_price_usd, estimated, actual_cost_usd,
         json.dumps(metadata or {}, ensure_ascii=False)),
    )


def configured_image_unit_price() -> float:
    """Provider price is explicit config, never silently invented in the ledger."""
    return float(os.getenv("IMAGE_GENERATION_UNIT_PRICE_USD", "0"))
