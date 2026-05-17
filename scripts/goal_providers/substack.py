"""Substack goal provider adapter.

Fetches subscriber metrics from Substack and maps them to
goal_progress_snapshot + goal_metric_components.
"""

from __future__ import annotations

from typing import Any

from scripts.goal_providers.base import GoalProviderAdapter


class SubstackAdapter(GoalProviderAdapter):
    @property
    def name(self) -> str:
        return "substack"

    def fetch_metrics(self) -> dict[str, Any]:
        from adapters.content.substack_publisher import fetch_subscriber_metrics
        from core.logger import HarnessLogger
        logger = HarnessLogger(tier=4)
        return fetch_subscriber_metrics(logger)

    def primary_value(self, metrics: dict[str, Any]) -> float:
        val = metrics.get("free_subscribers")
        if val is None:
            raise ValueError("Substack metrics missing 'free_subscribers' — cannot resolve primary value.")
        return float(val)

    def build_components(self, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        _COMPONENT_MAP = [
            ("followers",                  "upstream_audience",  "followers"),
            ("welcome_page_visitors",      "acquisition_input",  "welcome_page_visitors"),
            ("welcome_page_conversion_rate","conversion_rate",   "welcome_page_conversion_rate"),
            ("recommendation_subscribers", "channel_output",     "recommendation_subscribers"),
            ("direct_subscribers",         "channel_output",     "direct_subscribers"),
            ("note_publish_count",         "activity_driver",    "note_publish_count"),
            ("paid_subscribers",           "revenue_signal",     "paid_subscribers"),
            ("post_count",                 "activity_driver",    "post_count"),
        ]
        components = []
        for key, role, src_key in _COMPONENT_MAP:
            if key in metrics and metrics[key] is not None:
                components.append({
                    "component_name": key,
                    "component_role": role,
                    "actual_value": float(metrics[key]),
                    "source_metric_key": src_key,
                })
        return components
