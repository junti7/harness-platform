"""Goal provider adapter registry.

Usage:
    from scripts.goal_providers import registry

    adapter = registry.get("substack")
    metrics = adapter.fetch_metrics()
    value   = adapter.primary_value(metrics)

To add a new provider:
    from scripts.goal_providers import registry
    from scripts.goal_providers.my_provider import MyAdapter
    registry.register(MyAdapter())
"""

from __future__ import annotations

from scripts.goal_providers.base import GoalProviderAdapter
from scripts.goal_providers.maily import MailyAdapter
from scripts.goal_providers.substack import SubstackAdapter


class _ProviderRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, GoalProviderAdapter] = {}

    def register(self, adapter: GoalProviderAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> GoalProviderAdapter:
        adapter = self._adapters.get(name.lower())
        if adapter is None:
            available = sorted(self._adapters)
            raise ValueError(
                f"Unknown provider '{name}'. "
                f"Registered providers: {available}. "
                f"Add a new adapter in scripts/goal_providers/ and register it here."
            )
        return adapter

    def list_providers(self) -> list[str]:
        return sorted(self._adapters)


registry = _ProviderRegistry()
registry.register(MailyAdapter())
registry.register(SubstackAdapter())
