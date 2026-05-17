"""Abstract base class for Goal provider adapters.

A provider adapter knows how to:
1. Fetch raw metrics from an external platform (Substack, payment CRM, etc.)
2. Identify the primary goal value from those metrics
3. Decompose metrics into goal_metric_components for diagnostic drill-down
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class GoalProviderAdapter(ABC):
    """One registered provider = one platform that can feed goal snapshots."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Canonical provider name used in the registry (e.g. 'substack')."""

    @abstractmethod
    def fetch_metrics(self) -> dict[str, Any]:
        """Fetch raw metrics from the platform.

        Returns a flat dict of metric_key → value. Keys are provider-specific
        but should be stable (used as source_metric_key in components).
        """

    @abstractmethod
    def primary_value(self, metrics: dict[str, Any]) -> float:
        """Extract the single numeric value that maps to the goal's target_metric."""

    @abstractmethod
    def build_components(self, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        """Decompose metrics into goal_metric_component rows.

        Each row must include:
          component_name, component_role, actual_value, source_metric_key
        """
