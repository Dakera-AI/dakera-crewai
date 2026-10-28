"""DakeraStorage — CrewAI storage backed by the Dakera AI memory platform."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from dakera import DakeraClient, ErrorCode, NotFoundError, RecalledMemory
from dakera.models import BatchForgetRequest, BatchMemoryFilter


class DakeraStorage:
    """Persistent semantic storage for CrewAI crews backed by a Dakera agent.

    Implements CrewAI's memory storage interface (``save``, ``search``, ``reset`` and
    their async forms ``asave`` / ``asearch``), so it can back the memories that take
    a ``storage``: ``ExternalMemory(storage=...)``, ``ShortTermMemory(storage=...)``
    and ``EntityMemory(storage=...)`` (CrewAI 0.193 – 1.9; CrewAI 1.10 replaced them
    with a unified ``Memory``). Dakera embeds and ranks memories server-side, so no
    embedding model runs in the crew's process.

    It is also a direct API to the agent's memories: memory types, tags, TTL,
    sessions and event time on :meth:`save`; filtered recall, hybrid search,
    consolidation and forgetting.

    Args:
        api_url: Dakera server URL.
        agent_id: The Dakera agent whose memories are read and written.
        api_key: Dakera API key.
        search_k: Memories returned by :meth:`search` when no ``limit`` is given.
        min_importance: Default minimum importance of searched memories.
        importance: Importance of memories saved by :meth:`save` by default.
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
        value: Any,
        metadata: dict[str, Any] | None = None,
        *,
        memory_type: str = "episodic",
        importance: float | None = None,
        tags: list[str] | None = None,
        ttl_seconds: int | None = None,
        session_id: str | None = None,
        event_time: int | float | str | datetime | None = None,
    ) -> Any:
        """Store ``value`` as a memory of the agent and return the stored memory.

        CrewAI calls ``save(value, metadata)``; a value that is not a string is
        stored as its ``str()``. The agent conversation that CrewAI's ``ExternalMemory``
        attaches as ``metadata["messages"]`` is not stored: the value already holds
        the agent's answer, and a long conversation would exceed the server's
        metadata size limit. ``event_time`` is when the memory's event happened
        (Unix seconds, an RFC 3339 string or a timezone-aware ``datetime``), for
        history written after the fact. Server v0.12.3+ reads it for recency and
        ``since`` / ``until``; ``created_at`` stays the ingest time.
        """
        kwargs: dict[str, Any] = {
            "memory_type": memory_type,
            "importance": importance if importance is not None else self._importance,
        }
        if metadata and isinstance(metadata.get("messages"), list):
            metadata = {k: v for k, v in metadata.items() if k != "messages"}
        if metadata:
            kwargs["metadata"] = metadata
        if tags:
            kwargs["tags"] = tags
        if ttl_seconds is not None:
            kwargs["ttl_seconds"] = ttl_seconds
        if session_id:
            kwargs["session_id"] = session_id
        if event_time is not None:
            kwargs["event_time"] = event_time
        content = value if isinstance(value, str) else str(value)
        return self._client.store_memory(self._agent_id, content=content, **kwargs)

    def search(
        self,
        query: str,
        limit: int | None = None,
        score_threshold: float | None = None,
        *,
        tags: list[str] | None = None,
        memory_type: str | None = None,
        min_importance: float | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic recall with optional tag, type and importance filters.

        Returns at most ``limit`` ranked memories, most relevant first, as dicts with
        ``content``, ``id``, ``score`` (the server's ranking score), ``importance``
        and ``metadata``. The server's neighbourhood context is requested separately
        and left out. ``tags`` matches memories carrying at least one of the tags.

        ``score_threshold`` is accepted for CrewAI's storage interface and not
        applied: CrewAI passes a cut-off for the cosine similarity of its own
        stores, while Dakera's ranking score is on a different scale. Filter with
        ``min_importance`` instead.
        """
        del score_threshold
        k = limit if limit is not None else self._search_k
        min_imp = (
            min_importance
            if min_importance is not None
            else (self._min_importance if self._min_importance > 0.0 else None)
        )
        kwargs: dict[str, Any] = {"top_k": k, "neighborhood_mode": "separate"}
        if min_imp:
            kwargs["min_importance"] = min_imp
        if tags:
            kwargs["tags"] = tags
        if memory_type:
            kwargs["memory_type"] = memory_type
        return [
            {
                "content": m.content,
                "id": m.id,
                "score": m.score,
                "importance": m.importance,
                "metadata": m.metadata,
            }
            for m in self._recall_ranked(query, k, **kwargs)
        ]

    def _recall_ranked(self, query: str, k: int, **kwargs: Any) -> list[RecalledMemory]:
        """At most ``k`` ranked memories for ``query``; none if the agent has stored nothing.

        A server before v0.12.3 answers a recall of an agent that has no memories with
        ``404 NAMESPACE_NOT_FOUND`` for some queries (the agent's namespace is created by
        its first stored memory); v0.12.3 returns no memories.
        """
        try:
            response = self._client.recall(self._agent_id, query=query, **kwargs)
        except NotFoundError as err:
            if err.code != ErrorCode.NAMESPACE_NOT_FOUND:
                raise
            return []
        return response.ranked[:k]

    def hybrid_search(
        self,
        query: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Combined vector + BM25 search; dicts with ``content``, ``id`` and ``score``."""
        k = limit if limit is not None else self._search_k
        try:
            results = self._client.search_memories(self._agent_id, query=query, top_k=k)
        except NotFoundError as err:
            # An agent that has stored nothing, on a server before v0.12.3.
            if err.code != ErrorCode.NAMESPACE_NOT_FOUND:
                raise
            return []
        return [
            {"content": m.get("content", ""), "id": m.get("id", ""), "score": m.get("score", 0.0)}
            for m in results
        ]

    def batch_search(
        self, queries: list[str], limit: int | None = None
    ) -> list[list[dict[str, Any]]]:
        """Run multiple searches in batch (at most ``limit`` ranked memories each)."""
        k = limit if limit is not None else self._search_k
        results = []
        for q in queries:
            memories = self._recall_ranked(q, k, top_k=k, neighborhood_mode="separate")
            results.append([{"content": m.content, "id": m.id, "score": m.score} for m in memories])
        return results

    def forget(self, memory_id: str) -> None:
        """Delete one memory of the agent."""
        self._client.forget(self._agent_id, memory_id)

    def batch_forget(self, memory_ids: list[str]) -> None:
        """Delete several memories of the agent, one request each."""
        for mid in memory_ids:
            self._client.forget(self._agent_id, mid)

    def update_importance(self, memory_id: str, importance: float) -> None:
        """Set a memory's importance (0.0 – 1.0)."""
        self._client.update_importance(self._agent_id, [memory_id], importance)

    def consolidate(self, memory_ids: list[str] | None = None) -> Any:
        """Merge memories into one.

        ``memory_ids`` (at least two) picks the memories; without it the server
        picks up to five of the agent's most common memory type.
        """
        if memory_ids is None:
            return self._client.consolidate(self._agent_id)
        return self._client.consolidate(self._agent_id, memory_ids=memory_ids)

    def stats(self) -> dict[str, Any]:
        """Get the agent's memory statistics (``total_memories``, ...)."""
        return self._client.agent_stats(self._agent_id)

    def reset(self) -> None:
        """Delete every memory of the agent on the Dakera server. This cannot be undone.

        CrewAI calls it from ``crew.reset_memories(...)`` / ``crewai reset-memories``.
        """
        try:
            self._client.batch_forget(
                BatchForgetRequest(
                    agent_id=self._agent_id,
                    # The server refuses a filter without predicates; this one matches
                    # every memory.
                    filter=BatchMemoryFilter(min_importance=0.0),
                )
            )
        except NotFoundError:
            # Servers before v0.12.3 answer 404 for an agent that has stored nothing.
            pass

    async def asave(self, value: Any, metadata: dict[str, Any] | None = None) -> Any:
        """Async :meth:`save` (CrewAI's async kickoff calls it); runs in a worker thread."""
        return await asyncio.to_thread(self.save, value, metadata)

    async def asearch(
        self,
        query: str,
        limit: int | None = None,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Async :meth:`search` (CrewAI's async kickoff calls it); runs in a worker thread."""
        return await asyncio.to_thread(self.search, query, limit, score_threshold)

    def __repr__(self) -> str:
        return (
            f"DakeraStorage(agent_id={self._agent_id!r}, "
            f"search_k={self._search_k}, min_importance={self._min_importance})"
        )
