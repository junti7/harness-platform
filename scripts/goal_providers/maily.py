"""Maily goal provider adapter."""

from __future__ import annotations

from typing import Any

from scripts.goal_providers.base import GoalProviderAdapter


class MailyAdapter(GoalProviderAdapter):
    @property
    def name(self) -> str:
        return "maily"

    def fetch_metrics(self) -> dict[str, Any]:
        from adapters.content.maily_adapter import fetch_subscriber_metrics
        from core.logger import HarnessLogger

        logger = HarnessLogger(tier=4)
        return fetch_subscriber_metrics(logger)

    def primary_value(self, metrics: dict[str, Any]) -> float:
        return float(metrics.get("free_subscribers") or 0)

    def build_components(self, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        component_map = [
            ("free_subscribers", "channel_output"),
            ("paid_subscribers", "revenue_signal"),
            ("paid_revenue_krw", "revenue_signal"),
            ("opens", "engagement_signal"),
            ("clicks", "engagement_signal"),
            ("replies", "engagement_signal"),
            ("shares", "engagement_signal"),
            ("unsubscribe_count", "risk_signal"),
            ("post_count", "activity_driver"),
            ("draft_count", "activity_driver"),
        ]
        components: list[dict[str, Any]] = []
        for key, role in component_map:
            value = metrics.get(key)
            if value is None:
                continue
            components.append(
                {
                    "component_name": key,
                    "component_role": role,
                    "actual_value": float(value),
                    "source_metric_key": key,
                }
            )
        return components
