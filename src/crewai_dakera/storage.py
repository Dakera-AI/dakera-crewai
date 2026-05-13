"""DakeraStorage — CrewAI storage backed by the Dakera AI memory platform."""

from __future__ import annotations

from typing import Any

from dakera import DakeraClient


class DakeraStorage:
    """Persistent semantic storage for CrewAI agents backed by Dakera AI."""

    def __init__(self, api_url: str, agent_id: str, api_key: str = "",
                 search_k: int = 5, min_importance: float = 0.0, importance: float = 0.7) -> None:
        self._client = DakeraClient(api_url, api_key=api_key)
        self._agent_id = agent_id
        self._search_k = search_k
        self._min_importance = min_importance
        self._importance = importance

    def save(self, value: str, metadata: dict[str, Any] | None = None) -> None:
        self._client.store_memory(self._agent_id, content=value, memory_type="episodic",
                                  importance=self._importance, metadata=metadata or {})

    def search(self, query: str, limit: int | None = None) -> list[dict[str, Any]]:
        k = limit if limit is not None else self._search_k
        min_imp = self._min_importance if self._min_importance > 0.0 else None
        memories = self._client.recall(self._agent_id, query=query, top_k=k, min_importance=min_imp)
        return [m if isinstance(m, dict) else {"content": str(m)} for m in memories]

    def reset(self) -> None:
        """No-op: Dakera memories are persistent by design."""
