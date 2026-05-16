"""DakeraStorage — CrewAI storage backed by the Dakera AI memory platform."""

from __future__ import annotations

from typing import Any

from dakera import DakeraClient


class DakeraStorage:
    """Persistent semantic storage for CrewAI agents backed by Dakera AI.

    Supports memory types, tags, TTL, batch operations, hybrid search,
    sessions, knowledge graph, and entity extraction.
    """

    def __init__(
        self,
        api_url: str,
        agent_id: str,
        api_key: str = "",
        search_k: int = 5,
        min_importance: float = 0.0,
        importance: float = 0.7,
    ) -> None:
        self._client = DakeraClient(api_url, api_key=api_key)
        self._agent_id = agent_id
        self._search_k = search_k
        self._min_importance = min_importance
        self._importance = importance

    def save(
        self,
        value: str,
        metadata: dict[str, Any] | None = None,
        *,
        memory_type: str = "episodic",
        importance: float | None = None,
        tags: list[str] | None = None,
        ttl_seconds: int | None = None,
        session_id: str | None = None,
    ) -> Any:
        """Store a memory with full parameter control."""
        kwargs: dict[str, Any] = {
            "memory_type": memory_type,
            "importance": importance if importance is not None else self._importance,
        }
        if metadata:
            kwargs["metadata"] = metadata
        if tags:
            kwargs["tags"] = tags
        if ttl_seconds is not None:
            kwargs["ttl_seconds"] = ttl_seconds
        if session_id:
            kwargs["session_id"] = session_id
        return self._client.store_memory(self._agent_id, content=value, **kwargs)

    def search(
        self,
        query: str,
        limit: int | None = None,
        *,
        tags: list[str] | None = None,
        memory_type: str | None = None,
        min_importance: float | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search with optional tag and type filtering."""
        k = limit if limit is not None else self._search_k
        min_imp = (
            min_importance
            if min_importance is not None
            else (self._min_importance if self._min_importance > 0.0 else None)
        )
        kwargs: dict[str, Any] = {"top_k": k}
        if min_imp:
            kwargs["min_importance"] = min_imp
        if tags:
            kwargs["tags"] = tags
        if memory_type:
            kwargs["memory_type"] = memory_type
        memories = self._client.recall(self._agent_id, query=query, **kwargs)
        return [
            {"content": m.content, "id": m.id, "score": m.score, "tags": m.tags}
            for m in memories.memories
        ]

    def hybrid_search(
        self,
        query: str,
        limit: int | None = None,
        *,
        alpha: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Combined vector + BM25 search."""
        k = limit if limit is not None else self._search_k
        result = self._client.search_memories(self._agent_id, query=query, top_k=k, alpha=alpha)
        return [{"content": m.content, "id": m.id, "score": m.score} for m in result.memories]

    def batch_search(
        self, queries: list[str], limit: int | None = None
    ) -> list[list[dict[str, Any]]]:
        """Run multiple searches in batch."""
        k = limit if limit is not None else self._search_k
        results = []
        for q in queries:
            memories = self._client.recall(self._agent_id, query=q, top_k=k)
            results.append(
                [{"content": m.content, "id": m.id, "score": m.score} for m in memories.memories]
            )
        return results

    def forget(self, memory_id: str) -> None:
        """Delete a specific memory."""
        self._client.forget(self._agent_id, memory_id=memory_id)

    def batch_forget(self, memory_ids: list[str]) -> None:
        """Delete multiple memories."""
        self._client.batch_forget(self._agent_id, memory_ids=memory_ids)

    def update_importance(self, memory_id: str, importance: float) -> None:
        """Update the importance score of a memory."""
        self._client.update_importance(self._agent_id, memory_id=memory_id, importance=importance)

    def consolidate(self) -> Any:
        """Deduplicate and consolidate memories."""
        return self._client.consolidate(self._agent_id)

    def stats(self) -> dict[str, Any]:
        """Get agent memory statistics."""
        return self._client.agent_stats(self._agent_id)

    def reset(self) -> None:
        """No-op: Dakera memories are persistent by design."""

    def __repr__(self) -> str:
        return (
            f"DakeraStorage(agent_id={self._agent_id!r}, "
            f"search_k={self._search_k}, min_importance={self._min_importance})"
        )
