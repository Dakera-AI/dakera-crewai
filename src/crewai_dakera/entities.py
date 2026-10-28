"""DakeraEntityExtractor — named entity extraction for CrewAI agents."""

from __future__ import annotations

from typing import Any

from dakera import DakeraClient


class DakeraEntityExtractor:
    """Named-entity extraction with the Dakera server's model.

    Args:
        api_url: Dakera server URL.
        agent_id: The agent whose memory namespace :meth:`configure` sets up.
        api_key: Dakera API key.
    """

    def __init__(self, api_url: str, agent_id: str, api_key: str = "") -> None:
        self._client = DakeraClient(api_url, api_key=api_key)
        self._agent_id = agent_id

    def extract(self, text: str, entity_types: list[str] | None = None) -> list[dict[str, Any]]:
        """Extract entities from ``text``: dicts with ``type``, ``value`` and ``score``."""
        result = self._client.extract_entities(text, entity_types=entity_types)
        return [
            {"type": e.entity_type, "value": e.value, "score": e.score} for e in result.entities
        ]

    def memory_entities(self, memory_id: str) -> list[dict[str, Any]]:
        """Get the entities extracted from a stored memory, in the shape of :meth:`extract`."""
        result = self._client.memory_entities(memory_id)
        return [
            {"type": e.entity_type, "value": e.value, "score": e.score} for e in result.entities
        ]

    def configure(
        self, entity_types: list[str] | None = None, *, extract_entities: bool = True
    ) -> None:
        """Configure entity extraction on this agent's memory namespace.

        The agent's memories live in ``_dakera_agent_{agent_id}``; that is the
        namespace whose extraction settings apply when memories are stored.
        ``entity_types=None`` keeps the configured types.
        """
        self._client.configure_namespace_ner(
            f"_dakera_agent_{self._agent_id}",
            extract_entities=extract_entities,
            entity_types=entity_types,
        )
