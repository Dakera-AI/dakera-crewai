# crewai-dakera

[![CI](https://github.com/Dakera-AI/dakera-crewai/actions/workflows/ci.yml/badge.svg)](https://github.com/Dakera-AI/dakera-crewai/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/crewai-dakera)](https://pypi.org/project/crewai-dakera/)
[![Downloads](https://img.shields.io/pypi/dm/crewai-dakera)](https://pypi.org/project/crewai-dakera/)
[![Python](https://img.shields.io/pypi/pyversions/crewai-dakera)](https://pypi.org/project/crewai-dakera/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![dakera.ai](https://img.shields.io/badge/dakera.ai-website-22c55e?style=flat-square)](https://dakera.ai)
[![Docs](https://img.shields.io/badge/docs-dakera.ai%2Fdocs-3b82f6?style=flat-square)](https://dakera.ai/docs)

**Persistent, semantically recalled memory for [CrewAI](https://crewai.com) crews, powered by [Dakera](https://dakera.ai).**

Your crews remember across runs, processes and restarts. Dakera embeds, stores and ranks
memories server-side, so no embedding model or vector database runs in your process.

---

## Quick Start

### Step 1 — Run Dakera

Dakera is a self-hosted memory server. Start it with Docker:

```bash
docker run -d \
  --name dakera \
  -p 3000:3000 \
  -e DAKERA_ROOT_API_KEY=dk-mykey \
  ghcr.io/dakera-ai/dakera:0.12.3

curl http://localhost:3000/health
```

For persistent storage, use the Docker Compose setup:

```bash
curl -sSfL https://raw.githubusercontent.com/Dakera-AI/dakera-deploy/main/docker/docker-compose.yml \
  -o docker-compose.yml
DAKERA_ROOT_API_KEY=dk-mykey docker compose up -d
```

> Full deployment guide (Docker Compose, Kubernetes, Helm): [github.com/Dakera-AI/dakera-deploy](https://github.com/Dakera-AI/dakera-deploy)

### Step 2 — Install the integration

```bash
pip install "crewai-dakera[crewai]"
```

### Step 3 — Give your crew a memory

`DakeraStorage` implements CrewAI's memory storage interface. Pass it to CrewAI's
`ExternalMemory`: after each task the crew stores the agent's answer in Dakera, and
before each task it recalls the memories relevant to the task into the agent's prompt.

```python
from crewai import Agent, Crew, Task
from crewai.memory.external.external_memory import ExternalMemory

from crewai_dakera import DakeraStorage

storage = DakeraStorage(
    api_url="http://localhost:3000",
    api_key="dk-mykey",
    agent_id="research-crew",
)

researcher = Agent(
    role="Senior Researcher",
    goal="Uncover insights about {topic}",
    backstory="An expert researcher who builds on earlier findings.",
)
task = Task(
    description="Research {topic} and state the key finding in one sentence.",
    expected_output="One sentence",
    agent=researcher,
)

crew = Crew(
    agents=[researcher],
    tasks=[task],
    external_memory=ExternalMemory(storage=storage),
)

crew.kickoff(inputs={"topic": "AI agent memory"})  # stores the finding
crew.kickoff(inputs={"topic": "long-term memory for AI agents"})  # recalls it
```

A new crew, process or machine that uses the same `agent_id` recalls the same memories.
[`examples/crew_memory.py`](examples/crew_memory.py) runs this crew, with or without a
model API key.

---

## Installation

```bash
# DakeraStorage as the memory of a crew, plus the helpers
pip install "crewai-dakera[crewai]"

# Only the direct API (DakeraStorage, sessions, knowledge graph, ...), with any CrewAI
pip install crewai-dakera
```

**Requirements:** Python ≥ 3.10, a running Dakera server (see Step 1).

**Compatibility:**

- Dakera: tested against server v0.12.3; works with v0.12.0 – v0.12.2 (dakera Python
  SDK ≥ 0.14.1). `event_time` needs server v0.12.3; `DakeraSessionManager.touch()` and
  `idle_timeout_secs` need v0.12.2.
- CrewAI: the `crewai` extra installs CrewAI 0.193 – 1.9, whose `ExternalMemory`,
  `ShortTermMemory` and `EntityMemory` take a `storage`. CrewAI 1.10 replaced them with a
  unified `Memory` whose storage backends receive client-side embeddings; `DakeraStorage`
  does not plug into it, though its direct API works with any CrewAI version.

---

## What's in the package

| Class | Use it for |
|-------|-----------|
| `DakeraStorage` | The memory of a crew (`ExternalMemory(storage=...)`) and a direct API to an agent's memories |
| `DakeraSessionManager` | Group memories into conversation sessions |
| `DakeraKnowledgeGraph` | Link memories, query the graph, find paths, summarize, deduplicate |
| `DakeraEntityExtractor` | Named-entity extraction and its per-agent configuration |
| `DakeraNamespaceManager` | Create and configure Dakera namespaces |

---

## `DakeraStorage`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_url` | `str` | — | Dakera server URL, e.g. `http://localhost:3000` |
| `agent_id` | `str` | — | The Dakera agent whose memories are read and written |
| `api_key` | `str` | `""` | API key (the server's `DAKERA_ROOT_API_KEY` or a key created from it) |
| `search_k` | `int` | `5` | Memories returned by `search()` when CrewAI or you pass no `limit` |
| `min_importance` | `float` | `0.0` | Only recall memories at least this important (`0.0` = no filter) |
| `importance` | `float` | `0.7` | Importance of saved memories |

Read the URL and key from the environment rather than hard-coding them:

```python
import os

from crewai_dakera import DakeraStorage

storage = DakeraStorage(
    api_url=os.environ.get("DAKERA_API_URL", "http://localhost:3000"),
    api_key=os.environ.get("DAKERA_API_KEY", ""),
    agent_id="research-crew",
)
```

### As CrewAI storage

CrewAI calls these methods; you rarely call them yourself:

- **`save(value, metadata)`** / **`asave(...)`** stores `value` (as `str()` if it is not a
  string) with `metadata`. The conversation that `ExternalMemory` attaches as
  `metadata["messages"]` is left out: the value already holds the answer, and a long
  conversation would exceed the server's metadata limit.
- **`search(query, limit, score_threshold)`** / **`asearch(...)`** returns at most `limit`
  memories, most relevant first, as dicts with `content`, `id`, `score` (the server's
  ranking score), `importance` and `metadata`. `score_threshold` is a cut-off for the cosine
  similarity of CrewAI's own stores; Dakera's ranking score is on another scale, so it is
  not applied (use `min_importance`).
- **`reset()`** deletes **every memory of the agent** on the server. CrewAI calls it from
  `crew.reset_memories(...)` and `crewai reset-memories`; it cannot be undone.

The same storage also backs `ShortTermMemory(storage=...)` and `EntityMemory(storage=...)`.
`LongTermMemory` uses a different storage interface (`save(task_description, ...)` /
`load(...)`) and is not supported.

### Direct API

```python
from crewai_dakera import DakeraStorage

storage = DakeraStorage(api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-crew")

stored = storage.save(
    "The client moved the launch to May 3",
    {"project": "apollo"},
    memory_type="semantic",  # episodic (default), semantic, procedural or working
    importance=0.9,
    tags=["launch"],
    event_time="2026-03-01T09:00:00Z",  # when it happened (server v0.12.3+)
)
for r in storage.search("When is the launch?", tags=["launch"], min_importance=0.5):
    print(f"[{r['score']:.3f}] {r['content']}")  # score: the server's ranking score

storage.hybrid_search("launch May", limit=3)  # vector + BM25
storage.batch_search(["launch", "budget"], limit=2)
storage.update_importance(stored["id"], 0.95)

a = storage.save("Likes tea")["id"]
b = storage.save("Drinks green tea every morning")["id"]
merged = storage.consolidate([a, b])  # merge into one memory
storage.forget(stored["id"])
storage.batch_forget([merged["consolidated_memory"]["id"]])
print(storage.stats()["total_memories"])
```

`save()` also takes `ttl_seconds` (the memory expires) and `session_id` (see below).
`search()` takes `limit`, `tags` (memories carrying at least one of them), `memory_type`
and `min_importance`; it and `batch_search()` return at most `limit` ranked memories.

## Sessions

```python
from crewai_dakera import DakeraSessionManager, DakeraStorage

storage = DakeraStorage(api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-crew")
sessions = DakeraSessionManager(
    api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-crew"
)

with sessions:  # starts a session, ends it on exit
    storage.save("User asked about password reset", session_id=sessions.active_session_id)
    sessions.touch()  # record activity on a long-running session
    print(sessions.memories(sessions.active_session_id))
```

The server ends a session after 4 h without activity by default (server v0.12.2+;
`get()` then reports `ended_reason: "idle"`). `start(idle_timeout_secs=...)` sets a session's
own timeout (`0` = never) and `touch()` keeps it open. `memories()` leaves out the sentence
sub-memories the server derives from each memory (`include_derived=True` keeps them).

## Knowledge graph, entities, namespaces

```python
from crewai_dakera import (
    DakeraEntityExtractor,
    DakeraKnowledgeGraph,
    DakeraNamespaceManager,
    DakeraStorage,
)

storage = DakeraStorage(api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-crew")
kg = DakeraKnowledgeGraph(api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-crew")

a = storage.save("Anna leads the platform team in Berlin")["id"]
b = storage.save("The platform team ships every Friday")["id"]
kg.link(a, b, label="team")
print(kg.find_path(a, b)["hop_count"])
print(kg.summarize([a, b])["summary_memory"]["content"])  # stores a summary memory
print(kg.deduplicate(dry_run=True))  # report near-duplicate memories

entities = DakeraEntityExtractor(
    api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-crew"
)
entities.configure(["person", "location"])  # extraction for this agent's memories
print(entities.extract("Anna lives in Berlin"))

namespaces = DakeraNamespaceManager(api_url="http://localhost:3000", api_key="dk-mykey")
namespaces.create("product-docs", dimensions=384)
print(namespaces.get("product-docs"))
namespaces.delete("product-docs")
```

---

## Examples

| Script | Shows |
|--------|-------|
| [`crew_memory.py`](examples/crew_memory.py) | A crew with `ExternalMemory(storage=DakeraStorage(...))` (runs without a model key) |
| [`basic_memory.py`](examples/basic_memory.py) | Save and search with `DakeraStorage` |
| [`advanced_memory.py`](examples/advanced_memory.py) | Importance, filtered recall, event time, consolidation |
| [`batch_operations.py`](examples/batch_operations.py) | Batch search and forget |
| [`hybrid_search.py`](examples/hybrid_search.py) | Semantic recall vs. vector + BM25 search |
| [`knowledge_graph.py`](examples/knowledge_graph.py) | Links, graph queries, paths, summaries |
| [`multi_agent.py`](examples/multi_agent.py) | Separate and shared memories of several agents |
| [`sessions.py`](examples/sessions.py) | Sessions, idle timeout and `touch()` |

```bash
export DAKERA_API_URL=http://localhost:3000
export DAKERA_API_KEY=dk-mykey
pip install "crewai-dakera[crewai]"
python examples/crew_memory.py
```

---

## Related packages

| Package | Framework | Language |
|---------|-----------|----------|
| [`autogen-dakera`](https://github.com/Dakera-AI/dakera-autogen) | AutoGen | Python |
| [`langchain-dakera`](https://github.com/Dakera-AI/dakera-langchain) | LangChain | Python |
| [`llamaindex-dakera`](https://github.com/Dakera-AI/dakera-llamaindex) | LlamaIndex | Python |
| [`strands-dakera`](https://github.com/Dakera-AI/strands-dakera) | Strands Agents | Python |
| [`@dakera-ai/langchain`](https://github.com/Dakera-AI/dakera-langchain-js) | LangChain.js | TypeScript |
| [`@dakera-ai/ai-sdk`](https://github.com/Dakera-AI/dakera-ai-sdk) | Vercel AI SDK | TypeScript |

---

## Links

- [Dakera deployment](https://github.com/Dakera-AI/dakera-deploy) — self-hosting the memory server
- [Dakera Python SDK](https://github.com/Dakera-AI/dakera-py) — the API client this package uses
- [Integration guide](https://dakera.ai/integrations/crewai.html) — full setup walkthrough
- [All integrations](https://dakera.ai/integrations/)
- [Changelog](CHANGELOG.md)

---

## License

MIT © [Dakera AI](https://dakera.ai)

---

<div align="center">

**[dakera.ai](https://dakera.ai)** · [Documentation](https://dakera.ai/docs) · [Request Early Access](https://dakera.ai#cta)

</div>
