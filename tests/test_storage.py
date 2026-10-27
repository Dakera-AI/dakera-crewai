"""Tests for DakeraStorage (CrewAI integration)."""

from unittest.mock import MagicMock, create_autospec, patch

import pytest
from dakera import DakeraClient

from crewai_dakera import DakeraStorage


@pytest.fixture
def storage():
    with patch("crewai_dakera.storage.DakeraClient") as MockClient:
        mock_client = create_autospec(DakeraClient, instance=True)
        MockClient.return_value = mock_client
        s = DakeraStorage(
            api_url="http://localhost:3000", api_key="test-key", agent_id="crew-1", search_k=3
        )
        s._client = mock_client
        yield s, mock_client


def test_save_stores_memory(storage):
    s, mock_client = storage
    s.save("Client prefers weekly status reports")
    mock_client.store_memory.assert_called_once_with(
        "crew-1",
        content="Client prefers weekly status reports",
        memory_type="episodic",
        importance=0.7,
    )


def _recall(*memories, **extra):
    from dakera.models import RecallResponse

    return RecallResponse.from_dict({"memories": list(memories), **extra})


def _mem(mid, content, score, **extra):
    return {"id": mid, "content": content, "importance": 0.7, "rank_score": score, **extra}


def test_search_returns_memories(storage):
    s, mock_client = storage
    mock_client.recall.return_value = _recall(
        _mem("m-1", "Client prefers weekly status reports", 0.9)
    )
    results = s.search("What does the client want?")
    assert results == [
        {
            "content": "Client prefers weekly status reports",
            "id": "m-1",
            "score": 0.9,
            "importance": 0.7,
            "metadata": None,
        }
    ]
    mock_client.recall.assert_called_once_with(
        "crew-1", query="What does the client want?", top_k=3, neighborhood_mode="separate"
    )


def test_search_wraps_non_dict_results(storage):
    s, mock_client = storage
    mem = MagicMock(content="plain string memory", id="m-2", score=0.8, metadata=None)
    mock_recall = MagicMock()
    mock_recall.ranked = [mem]
    mock_client.recall.return_value = mock_recall
    results = s.search("test")
    assert results[0]["content"] == "plain string memory"


def test_search_leaves_out_inline_neighborhood_context(storage):
    # A server that appends neighbourhood context inline (v0.12.3 default)
    # must not push the result past the limit.
    s, mock_client = storage
    mock_client.recall.return_value = _recall(
        _mem("m-1", "a", 0.9),
        _mem("m-2", "b", 0.8),
        _mem("n-1", "context", 0.99, retrieval="neighborhood"),
        _mem("m-3", "c", 0.7),
        _mem("m-4", "d", 0.6),
    )
    results = s.search("q")
    assert [r["id"] for r in results] == ["m-1", "m-2", "m-3"]


def test_search_scores_by_rank_score(storage):
    s, mock_client = storage
    mock_client.recall.return_value = _recall(
        {"id": "m-1", "content": "a", "rank_score": 0.42, "smart_score": 0.9, "score": 0.1}
    )
    assert s.search("q")[0]["score"] == 0.42


def test_batch_search_caps_each_result_at_limit(storage):
    s, mock_client = storage
    mock_client.recall.return_value = _recall(
        _mem("m-1", "a", 0.9),
        _mem("n-1", "ctx", 0.5, retrieval="neighborhood"),
        _mem("m-2", "b", 0.8),
    )
    results = s.batch_search(["x", "y"], limit=1)
    assert results == [[{"content": "a", "id": "m-1", "score": 0.9}]] * 2
    mock_client.recall.assert_called_with(
        "crew-1", query="y", top_k=1, neighborhood_mode="separate"
    )


def test_save_forwards_event_time(storage):
    s, mock_client = storage
    s.save("Met Anna in Berlin", event_time="2024-03-01T10:00:00Z")
    mock_client.store_memory.assert_called_once_with(
        "crew-1",
        content="Met Anna in Berlin",
        memory_type="episodic",
        importance=0.7,
        event_time="2024-03-01T10:00:00Z",
    )


def test_consolidate_without_ids(storage):
    s, mock_client = storage
    s.consolidate()
    mock_client.consolidate.assert_called_once_with("crew-1")


def test_consolidate_with_ids(storage):
    s, mock_client = storage
    s.consolidate(["m-1", "m-2"])
    mock_client.consolidate.assert_called_once_with("crew-1", memory_ids=["m-1", "m-2"])


def test_reset_forgets_every_memory_of_the_agent(storage):
    from dakera.models import BatchForgetRequest, BatchMemoryFilter

    s, mock_client = storage
    s.reset()
    mock_client.batch_forget.assert_called_once_with(
        BatchForgetRequest(agent_id="crew-1", filter=BatchMemoryFilter(min_importance=0.0))
    )


def test_reset_of_unknown_agent_on_older_server(storage):
    from dakera import NotFoundError

    s, mock_client = storage
    mock_client.batch_forget.side_effect = NotFoundError("Namespace not found")
    s.reset()


def test_search_takes_crewai_storage_arguments(storage):
    # CrewAI's memories call storage.search(query=, limit=, score_threshold=).
    s, mock_client = storage
    mock_client.recall.return_value = _recall(_mem("m-1", "a", 0.2))
    results = s.search(query="q", limit=2, score_threshold=0.6)
    # The threshold is a cosine cut-off for CrewAI's own stores; not applied.
    assert [r["id"] for r in results] == ["m-1"]
    mock_client.recall.assert_called_once_with(
        "crew-1", query="q", top_k=2, neighborhood_mode="separate"
    )


def test_save_takes_crewai_storage_arguments(storage):
    # CrewAI's memories call storage.save(value, metadata); ExternalMemory attaches
    # the whole agent conversation as metadata["messages"], which is not stored.
    s, mock_client = storage
    s.save(
        "Final Answer: 42",
        {"description": "Answer the question", "messages": [{"role": "user", "content": "?"}]},
    )
    mock_client.store_memory.assert_called_once_with(
        "crew-1",
        content="Final Answer: 42",
        memory_type="episodic",
        importance=0.7,
        metadata={"description": "Answer the question"},
    )


def test_save_stores_non_string_value_as_text(storage):
    s, mock_client = storage
    s.save(42, {})
    mock_client.store_memory.assert_called_once_with(
        "crew-1", content="42", memory_type="episodic", importance=0.7
    )


async def test_async_save_and_search(storage):
    s, mock_client = storage
    mock_client.recall.return_value = _recall(_mem("m-1", "a", 0.9))
    await s.asave("value", {"k": 1})
    assert await s.asearch("q", 1, 0.5) == [
        {"content": "a", "id": "m-1", "score": 0.9, "importance": 0.7, "metadata": None}
    ]
    mock_client.store_memory.assert_called_once_with(
        "crew-1", content="value", memory_type="episodic", importance=0.7, metadata={"k": 1}
    )
    mock_client.recall.assert_called_once_with(
        "crew-1", query="q", top_k=1, neighborhood_mode="separate"
    )


def test_search_forwards_tags(storage):
    # recall() takes tags since dakera 0.13.1 (it raised TypeError before).
    from dakera.models import RecallResponse

    obj, mock_client = storage
    mock_client.recall.return_value = RecallResponse.from_dict({"memories": []})
    assert obj.search("q", tags=["work"]) == []
    _, kwargs = mock_client.recall.call_args
    assert kwargs["tags"] == ["work"]
