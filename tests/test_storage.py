"""Tests for DakeraStorage (CrewAI integration)."""

from unittest.mock import MagicMock, patch

import pytest

from crewai_dakera import DakeraStorage


@pytest.fixture
def storage():
    with patch("crewai_dakera.storage.DakeraClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        s = DakeraStorage(api_url="http://localhost:3000", api_key="test-key",
                          agent_id="crew-1", search_k=3)
        s._client = mock_client
        yield s, mock_client


def test_save_stores_memory(storage):
    s, mock_client = storage
    s.save("Client prefers weekly status reports")
    mock_client.store_memory.assert_called_once_with(
        "crew-1", content="Client prefers weekly status reports",
        memory_type="episodic", importance=0.7)


def test_search_returns_memories(storage):
    s, mock_client = storage
    mem = MagicMock(content="Client prefers weekly status reports", id="m-1", score=0.9,
                    metadata=None)
    mock_recall = MagicMock()
    mock_recall.memories = [mem]
    mock_client.recall.return_value = mock_recall
    results = s.search("What does the client want?")
    assert len(results) == 1
    assert results[0]["content"] == "Client prefers weekly status reports"
    mock_client.recall.assert_called_once_with(
        "crew-1", query="What does the client want?", top_k=3)


def test_search_wraps_non_dict_results(storage):
    s, mock_client = storage
    mem = MagicMock(content="plain string memory", id="m-2", score=0.8, metadata=None)
    mock_recall = MagicMock()
    mock_recall.memories = [mem]
    mock_client.recall.return_value = mock_recall
    results = s.search("test")
    assert results[0]["content"] == "plain string memory"


def test_reset_is_noop(storage):
    s, mock_client = storage
    s.reset()
    mock_client.forget.assert_not_called()
