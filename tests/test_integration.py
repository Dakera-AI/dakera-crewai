"""Live tests against a real Dakera server.

Skipped unless ``DAKERA_API_URL`` is set (the CI integration job runs them
against the pinned ``ghcr.io/dakera-ai/dakera`` image). Each run uses fresh
agent ids, so the tests do not depend on what the server already holds.
"""

from __future__ import annotations

import os
import uuid

import pytest

from crewai_dakera import (
    DakeraEntityExtractor,
    DakeraKnowledgeGraph,
    DakeraNamespaceManager,
    DakeraSessionManager,
    DakeraStorage,
)

API_URL = os.environ.get("DAKERA_API_URL", "")
API_KEY = os.environ.get("DAKERA_API_KEY", "")

pytestmark = pytest.mark.skipif(not API_URL, reason="DAKERA_API_URL not set")


@pytest.fixture
def agent_id() -> str:
    return f"crewai-it-{uuid.uuid4().hex[:12]}"


def test_storage_round_trip(agent_id: str) -> None:
    storage = DakeraStorage(API_URL, agent_id, api_key=API_KEY, search_k=2)
    # An agent that has stored nothing recalls nothing (no 404 from v0.12.3).
    assert storage.search("anything") == []

    stored = [
        storage.save("Project Falcon ships on April 15", tags=["project"]),
        storage.save("Project Falcon is written in Rust", tags=["project"]),
        storage.save("Anna prefers tea over coffee", event_time="2024-03-01T10:00:00Z"),
    ]
    ids = [m["id"] for m in stored]
    assert stored[2]["metadata"]["_dakera_event_time"] == 1709287200

    results = storage.search("When does Project Falcon ship?")
    assert 1 <= len(results) <= 2
    assert results[0]["id"] == ids[0]
    assert set(results[0]) == {"content", "id", "score", "importance", "metadata"}
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)

    assert {r["id"] for r in storage.search("Falcon", tags=["project"], limit=5)} <= set(ids[:2])
    assert all(len(batch) <= 1 for batch in storage.batch_search(["Falcon", "tea"], limit=1))
    assert storage.hybrid_search("Falcon Rust", limit=2)

    storage.update_importance(ids[2], 0.95)
    assert storage.search("tea", min_importance=0.9)[0]["id"] == ids[2]
    assert storage.stats()["total_memories"] == 3

    merged = storage.consolidate(ids[:2])
    assert sorted(merged["source_memory_ids"]) == sorted(ids[:2])
    storage.forget(ids[2])
    storage.batch_forget([merged["consolidated_memory"]["id"]])


def test_sessions(agent_id: str) -> None:
    sessions = DakeraSessionManager(API_URL, agent_id, api_key=API_KEY)
    storage = DakeraStorage(API_URL, agent_id, api_key=API_KEY)

    with sessions:
        sid = sessions.active_session_id
        assert sid is not None
        assert sessions.touch()["session_state"] == "active"
        stored = storage.save(
            "User asked about password reset. The reset link had expired, so we sent a new one.",
            session_id=sid,
        )
        assert stored["session_state"] == "active"
        # The server also lists the sentences it derives; memories() leaves them out.
        assert [m["id"] for m in sessions.memories(sid)] == [stored["id"]]
        assert sid in [s["id"] for s in sessions.list(active_only=True)]
    assert sessions.active_session_id is None
    assert sessions.get(sid)["ended_reason"] == "client"

    sid = sessions.start(idle_timeout_secs=0)
    sessions.end()
    assert sessions.get(sid)["ended_at"] is not None


def test_knowledge_graph(agent_id: str) -> None:
    storage = DakeraStorage(API_URL, agent_id, api_key=API_KEY)
    kg = DakeraKnowledgeGraph(API_URL, agent_id, api_key=API_KEY)
    a = storage.save("Anna leads the platform team in Berlin")["id"]
    b = storage.save("The platform team ships the Berlin release every Friday")["id"]

    link = kg.link(a, b, label="team")
    assert (link["from_id"], link["to_id"]) == (a, b)
    assert kg.query(root_id=a)["edge_count"] >= 1
    assert kg.find_path(a, b)["hop_count"] >= 1
    assert kg.export()["edge_count"] >= 1
    assert isinstance(kg.build(a, depth=1), dict)
    assert kg.summarize([a, b])["source_count"] == 2
    assert isinstance(kg.deduplicate(), dict)


def test_entities(agent_id: str) -> None:
    storage = DakeraStorage(API_URL, agent_id, api_key=API_KEY)
    entities = DakeraEntityExtractor(API_URL, agent_id, api_key=API_KEY)
    storage.save("first memory creates the agent namespace")
    entities.configure(["person", "location"])
    assert isinstance(entities.extract("Anna lives in Berlin"), list)
    mid = storage.save("Anna moved to Berlin in 2021")["id"]
    assert isinstance(entities.memory_entities(mid), list)


def test_namespaces() -> None:
    namespaces = DakeraNamespaceManager(API_URL, api_key=API_KEY)
    name = f"crewai-it-ns-{uuid.uuid4().hex[:12]}"
    created = namespaces.create(name, dimensions=8)
    assert created["name"] == name
    try:
        assert namespaces.get(name)["dimensions"] == 8
        assert name in [ns["name"] for ns in namespaces.list()]
        namespaces.configure(name, dimension=8, distance="cosine")
        assert namespaces.stats(name)["dimensions"] == 8
    finally:
        namespaces.delete(name)


def test_crewai_memories_use_the_storage(agent_id: str) -> None:
    """CrewAI's ExternalMemory / ShortTermMemory call the storage interface (CrewAI < 1.10)."""
    external = pytest.importorskip("crewai.memory.external.external_memory")
    short_term = pytest.importorskip("crewai.memory.short_term.short_term_memory")

    storage = DakeraStorage(API_URL, agent_id, api_key=API_KEY)
    memory = external.ExternalMemory(storage=storage)
    memory.save(
        "The client wants weekly status reports",
        {"description": "Collect requirements", "messages": [{"role": "user", "content": "x"}]},
    )
    short_term.ShortTermMemory(storage=storage).save("The launch is on May 3")

    results = memory.search("How often does the client want reports?", limit=1)
    assert [r["content"] for r in results] == ["The client wants weekly status reports"]
    assert results[0]["metadata"] == {"description": "Collect requirements"}

    storage.reset()
    assert storage.search("reports") == []


def test_crew_recalls_external_memory(agent_id: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """A crew stores its answer in Dakera and recalls it in the next run (CrewAI < 1.10)."""
    external = pytest.importorskip("crewai.memory.external.external_memory")
    from crewai import Agent, Crew, Task
    from crewai.llms.base_llm import BaseLLM

    monkeypatch.setenv("CREWAI_TRACING_ENABLED", "false")
    monkeypatch.setenv("CREWAI_DISABLE_TELEMETRY", "true")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")

    class ScriptedLLM(BaseLLM):
        def __init__(self, answers: list[str]) -> None:
            super().__init__(model="scripted")
            self.answers = answers
            self.prompts: list[str] = []

        def call(self, messages, *args, **kwargs):  # type: ignore[no-untyped-def]
            self.prompts.append(str(messages))
            return f"Thought: I know the answer.\nFinal Answer: {self.answers.pop(0)}"

        def supports_function_calling(self) -> bool:
            return False

        def supports_stop_words(self) -> bool:
            return False

        def get_context_window_size(self) -> int:
            return 8192

    llm = ScriptedLLM(["Dakera keeps agent memory server-side.", "As found before."])
    storage = DakeraStorage(API_URL, agent_id, api_key=API_KEY)
    agent = Agent(role="Researcher", goal="Research {topic}", backstory="An expert.", llm=llm)
    task = Task(description="Research {topic}", expected_output="One sentence", agent=agent)
    for _ in range(2):
        crew = Crew(
            agents=[agent], tasks=[task], external_memory=external.ExternalMemory(storage=storage)
        )
        crew.kickoff(inputs={"topic": "AI memory"})

    # The second run's prompt carries what the first run stored.
    assert "Dakera keeps agent memory server-side." in llm.prompts[-1]
    storage.reset()
