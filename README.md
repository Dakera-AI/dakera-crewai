# crewai-dakera

**Persistent, decay-weighted memory for [CrewAI](https://crewai.com) crews, powered by a self-hosted [Dakera](https://dakera.ai) server.**

[![CI](https://github.com/Dakera-AI/dakera-crewai/actions/workflows/ci.yml/badge.svg)](https://github.com/Dakera-AI/dakera-crewai/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/crewai-dakera)](https://pypi.org/project/crewai-dakera/)
[![Downloads](https://img.shields.io/pypi/dm/crewai-dakera)](https://pypi.org/project/crewai-dakera/)
[![Python](https://img.shields.io/pypi/pyversions/crewai-dakera)](https://pypi.org/project/crewai-dakera/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/Dakera-AI/dakera-crewai/blob/main/LICENSE)
[![Dakera server](https://img.shields.io/badge/Dakera%20server-v0.12.3-D4A843)](https://dakera.ai)
[![LoCoMo](https://img.shields.io/badge/LoCoMo-88.2%25%20Recall%4020-brightgreen)](https://dakera.ai/benchmark)

Give a crew a memory that outlives the process: `DakeraStorage` implements CrewAI's memory
storage interface, so after each task the crew stores what it learned in Dakera, and before
each task it recalls what is relevant into the agent's prompt. Dakera embeds, stores and ranks
the memories on the server — no embedding API key, no vector database in your process — and
ranks them by relevance, importance and recency.

## Why Dakera

- **Plugs into CrewAI's memory** — `ExternalMemory(storage=DakeraStorage(...))`, and the same
  storage backs `ShortTermMemory` and `EntityMemory`.
- **Memory that survives restarts** — a new crew, process or machine with the same `agent_id`
  builds on what earlier runs learned; several crews can share one memory.
- **Decay-weighted recall** — results are ranked by semantic relevance, importance and recency,
  not by vector distance alone; filter by importance, memory type and tags.
- **No embedding model to run or pay for** — the Dakera server embeds text itself, so the crew
  needs no embedder configuration.
- **Self-hosted, one container** — your crews' memories stay on your infrastructure.
- **Measured** — 88.2% Recall@20 on the [LoCoMo long-conversation memory benchmark](https://dakera.ai/benchmark).

## Contents

- [Quick start](#quick-start)
- [Compatibility](#compatibility)
- [What's new in 0.4.0](#whats-new-in-040)
- [`DakeraStorage`](#dakerastorage)
- [`DakeraSessionManager`](#dakerasessionmanager)
- [`DakeraKnowledgeGraph`](#dakeraknowledgegraph)
- [`DakeraEntityExtractor`](#dakeraentityextractor)
- [`DakeraNamespaceManager`](#dakeranamespacemanager)
- [Configuration](#configuration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Related packages](#related-packages)
- [Links](#links)
- [License](#license)

## Quick start

**1. Run Dakera**

```bash
docker run -d --name dakera -p 3000:3000 -v dakera-data:/data \
  -e DAKERA_ROOT_API_KEY=dk-mykey \
  ghcr.io/dakera-ai/dakera:0.12.3

curl http://localhost:3000/health   # {"service":"dakera","status":"healthy",...}
```

The image ships its embedding model, so the server is ready in seconds. Docker Compose,
Kubernetes and Helm setups are in [dakera-deploy](https://github.com/Dakera-AI/dakera-deploy).

**2. Install**

```bash
pip install "crewai-dakera[crewai]"
```

**3. Give your crew a memory**

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
)  # uses CrewAI's default LLM (OpenAI: needs OPENAI_API_KEY)
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

crew.kickoff(inputs={"topic": "AI agent memory"})  # stores the finding in Dakera
crew.kickoff(inputs={"topic": "long-term memory for AI agents"})  # recalls it into the prompt
```

Run it again — in a new process, on another machine — and the crew still builds on its
earlier findings. No OpenAI key?
[`examples/crew_memory.py`](https://github.com/Dakera-AI/dakera-crewai/blob/main/examples/crew_memory.py)
runs the same crew with a scripted stand-in LLM and prints what the second run recalled.

## Compatibility

| crewai-dakera | Dakera server | `dakera` SDK | CrewAI (`crewai` extra) | Python |
|---|---|---|---|---|
| **0.4.x** | v0.12.0 – **v0.12.3** | ≥ 0.14.1 | ≥ 0.193, < 1.10 (tested 0.193.0, 1.6.1, 1.9.3) | ≥ 3.10 |
| 0.3.x | v0.12.0 | ≥ 0.13.1 | ≥ 0.30 | ≥ 3.10 |

`event_time` needs server v0.12.3; sessions' `idle_timeout_secs` and `touch()` need v0.12.2.
Older v0.12 servers ignore the new fields.

CrewAI 1.10 replaced `ExternalMemory`, `ShortTermMemory` and `EntityMemory` with a unified
`Memory` whose storage backends receive client-side embeddings; `DakeraStorage` does not plug
into it. Without the extra (`pip install crewai-dakera`), the direct API works with any CrewAI
version.

## What's new in 0.4.0

- **`DakeraStorage` plugs into a crew** — `ExternalMemory(storage=...)`, `ShortTermMemory` and
  `EntityMemory` (the README's previous example used `LongTermMemory`, whose interface it does
  not implement), with CrewAI's async `asave()` / `asearch()`.
- **`reset()` deletes the agent's memories**, so `crew.reset_memories()` resets the crew's
  Dakera memory (it was a no-op).
- Dakera server **v0.12.3** support with `dakera>=0.14.1`; search returns at most `limit`
  ranked memories and `score` is the server's ranking score.
- `event_time` — when the remembered event happened, for history written after the fact.
- `consolidate(memory_ids)` merges exactly the memories you name.
- Sessions: `idle_timeout_secs`, `touch()` and `ended_reason` (the server ends idle sessions).
- `DakeraKnowledgeGraph.deduplicate(threshold=, dry_run=)`.

Full list: [CHANGELOG](https://github.com/Dakera-AI/dakera-crewai/blob/main/CHANGELOG.md).

## `DakeraStorage`

The memory storage of a crew, and a direct API to an agent's memories.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `api_url` | `str` | — | Dakera server URL, e.g. `http://localhost:3000` |
| `agent_id` | `str` | — | The Dakera agent whose memories are read and written |
| `api_key` | `str` | `""` | API key (the server's `DAKERA_ROOT_API_KEY` or a key created with it) |
| `search_k` | `int` | `5` | Memories returned by `search()` when CrewAI or you pass no `limit` |
| `min_importance` | `float` | `0.0` | Only recall memories at least this important (`0.0` = no filter) |
| `importance` | `float` | `0.7` | Importance (0.0–1.0) of saved memories |

### As CrewAI storage

CrewAI calls these methods; you rarely call them yourself:

- **`save(value, metadata)`** / **`asave(...)`** stores `value` (as `str()` if it is not a
  string) with `metadata`. The conversation that `ExternalMemory` attaches as
  `metadata["messages"]` is left out: the value already holds the answer, and a long
  conversation would exceed the server's metadata limit.
- **`search(query, limit, score_threshold)`** / **`asearch(...)`** returns at most `limit`
  memories, most relevant first, as dicts with `content`, `id`, `score` (the server's ranking
  score), `importance` and `metadata`. `score_threshold` is a cut-off for the cosine
  similarity of CrewAI's own stores; Dakera's ranking score is on another scale, so it is not
  applied (use `min_importance`).
- **`reset()`** deletes **every memory of the agent** on the server. CrewAI calls it from
  `crew.reset_memories(...)` and `crewai reset-memories`. It cannot be undone.

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

- `save(value, metadata=None, *, memory_type="episodic", importance=None, tags=None, ttl_seconds=None, session_id=None, event_time=None)`
  — `ttl_seconds` makes the memory expire; `session_id` attaches it to a session.
- `search(query, limit=None, score_threshold=None, *, tags=None, memory_type=None, min_importance=None)`
  and `batch_search(queries, limit=None)` return at most `limit` ranked memories; `tags`
  matches memories carrying at least one of them.
- `consolidate(memory_ids)` merges at least two memories into one.

## `DakeraSessionManager`

Groups an agent's memories into conversation sessions. Use it as a context manager to start a
session and end it on exit.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `api_url` | `str` | — | Dakera server URL |
| `agent_id` | `str` | — | The agent the sessions belong to |
| `api_key` | `str` | `""` | API key |

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

The server ends a session after 4 h without activity by default (server v0.12.2+; `get()` then
reports `ended_reason: "idle"`). `start(metadata=None, *, idle_timeout_secs=None)` sets a
session's own timeout (`0` = never) and `touch()` keeps it open. `memories()` leaves out the
sentence sub-memories the server derives from each memory (`include_derived=True` keeps them).
`get()`, `list(active_only=False)` and `end()` complete the API.

## `DakeraKnowledgeGraph`

Links an agent's memories and queries the resulting graph: paths, neighbourhoods, summaries
and deduplication. Constructor: `api_url`, `agent_id`, `api_key`.

```python
from crewai_dakera import DakeraKnowledgeGraph, DakeraStorage

storage = DakeraStorage(api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-crew")
kg = DakeraKnowledgeGraph(api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-crew")

a = storage.save("Anna leads the platform team in Berlin")["id"]
b = storage.save("The platform team ships every Friday")["id"]
kg.link(a, b, label="team")
print(kg.find_path(a, b)["hop_count"])
print(kg.query(root_id=a, max_depth=2)["edge_count"])
print(kg.summarize([a, b])["summary_memory"]["content"])  # stores a summary memory
print(kg.deduplicate(dry_run=True))  # report near-duplicate memories
```

`build(memory_id, depth=None)` expands the graph around a memory and `export()` returns the
whole graph.

## `DakeraEntityExtractor`

Named-entity extraction, and the extraction settings applied to the agent's memories as they
are stored. Constructor: `api_url`, `agent_id`, `api_key`.

```python
from crewai_dakera import DakeraEntityExtractor

entities = DakeraEntityExtractor(
    api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-crew"
)
entities.configure(["person", "location"])  # extraction for this agent's memories
print(entities.extract("Anna lives in Berlin"))
```

`memory_entities(memory_id)` returns the entities found in a stored memory.

## `DakeraNamespaceManager`

Creates and configures Dakera namespaces (vector collections) for your own data. An agent's
memories live in the namespace `_dakera_agent_{agent_id}`, which the server creates on the
first stored memory. Constructor: `api_url`, `api_key`.

```python
from crewai_dakera import DakeraNamespaceManager

namespaces = DakeraNamespaceManager(api_url="http://localhost:3000", api_key="dk-mykey")
namespaces.create("product-docs", dimensions=384)  # dimensions is required
print(namespaces.get("product-docs"))
namespaces.delete("product-docs")
```

`list()`, `stats(name)` and `configure(name, dimension=, distance=None)` complete the API.

## Configuration

Every class takes `api_url` and `api_key` explicitly. Read them from the environment rather
than hard-coding them — the examples use these variables:

| Variable | Used by | Description |
|---|---|---|
| `DAKERA_API_URL` | the examples | Dakera server URL (default `http://localhost:3000`) |
| `DAKERA_API_KEY` | the examples | API key |
| `OPENAI_API_KEY` | CrewAI's default LLM, `crew_memory.py` | Optional for `crew_memory.py` (scripted LLM without one) |

```python
import os

from crewai_dakera import DakeraStorage

storage = DakeraStorage(
    api_url=os.environ.get("DAKERA_API_URL", "http://localhost:3000"),
    api_key=os.environ.get("DAKERA_API_KEY", ""),
    agent_id="research-crew",
)
```

The server's root key is set with `DAKERA_ROOT_API_KEY` when it starts; keys scoped to
namespaces can be created with it (see the [Dakera docs](https://dakera.ai/docs)).

## Examples

| Script | Shows | LLM key? |
|---|---|---|
| [`crew_memory.py`](https://github.com/Dakera-AI/dakera-crewai/blob/main/examples/crew_memory.py) | A crew with `ExternalMemory(storage=DakeraStorage(...))` | Optional (scripted LLM without one) |
| [`basic_memory.py`](https://github.com/Dakera-AI/dakera-crewai/blob/main/examples/basic_memory.py) | Save and search with `DakeraStorage` | No |
| [`advanced_memory.py`](https://github.com/Dakera-AI/dakera-crewai/blob/main/examples/advanced_memory.py) | Importance, filtered recall, event time, consolidation | No |
| [`batch_operations.py`](https://github.com/Dakera-AI/dakera-crewai/blob/main/examples/batch_operations.py) | Batch search and forget | No |
| [`hybrid_search.py`](https://github.com/Dakera-AI/dakera-crewai/blob/main/examples/hybrid_search.py) | Semantic recall vs. vector + BM25 search | No |
| [`knowledge_graph.py`](https://github.com/Dakera-AI/dakera-crewai/blob/main/examples/knowledge_graph.py) | Links, graph queries, paths, summaries | No |
| [`multi_agent.py`](https://github.com/Dakera-AI/dakera-crewai/blob/main/examples/multi_agent.py) | Separate and shared memories of several agents | No |
| [`sessions.py`](https://github.com/Dakera-AI/dakera-crewai/blob/main/examples/sessions.py) | Sessions, idle timeout and `touch()` | No |

```bash
export DAKERA_API_URL=http://localhost:3000
export DAKERA_API_KEY=dk-mykey
python examples/crew_memory.py
```

## Troubleshooting

- **`dakera.ConnectionError` / connection refused** — the server is not running or not on that
  port. The docs use port 3000 (`-p 3000:3000`); this repository's CI publishes it on 3300.
  Check with `curl http://localhost:3000/health`.
- **`dakera.AuthenticationError` (401)** — the key does not match the server's
  `DAKERA_ROOT_API_KEY` (or a key created with it).
- **The crew fails when it saves or recalls long-term memory** — `DakeraStorage` was passed to
  `LongTermMemory`, which needs another storage interface. Use
  `ExternalMemory(storage=...)` (or `ShortTermMemory` / `EntityMemory`).
- **CrewAI 1.10 or later** — CrewAI 1.10 replaced these memories with a unified `Memory` that
  `DakeraStorage` does not plug into; use CrewAI < 1.10 (the `crewai` extra pins it).
- **Nothing recalled for a new agent** — an agent that has stored nothing recalls nothing. A
  server before v0.12.3 answers such a recall with 404 `NAMESPACE_NOT_FOUND` for some queries
  (v0.12.3 answers an empty list); `DakeraStorage` (`search()`, `batch_search()`,
  `hybrid_search()`, and so a crew's first run) treats it as no memories, so a new agent starts
  the same way on every v0.12 server. Other 404s are raised.
- **Fewer results than expected** — search returns at most `limit` ranked memories. A v0.12.3
  server can add a session's neighbouring memories after the ranked results; this package
  requests them separately and leaves them out. `score_threshold` from CrewAI is not applied.
- **`event_time` / `idle_timeout_secs` seem to have no effect** — they need server v0.12.3 /
  v0.12.2; older servers ignore them. `GET /health` reports the server version.

## Development

```bash
pip install -e ".[dev,crewai]"
pytest tests/ -v                             # unit tests; live tests need DAKERA_API_URL
ruff check . && ruff format --check . && mypy src/
```

See [CONTRIBUTING.md](https://github.com/Dakera-AI/dakera-crewai/blob/main/CONTRIBUTING.md)
for the live tests against a local server and the pull request process.

## Related packages

| Package | What it is |
|---|---|
| [`dakera`](https://pypi.org/project/dakera/) · [`@dakera-ai/dakera`](https://www.npmjs.com/package/@dakera-ai/dakera) · [`dakera-client`](https://crates.io/crates/dakera-client) · [`dakera-go`](https://github.com/Dakera-AI/dakera-go) | Python, TypeScript, Rust and Go SDKs |
| [`langchain-dakera`](https://pypi.org/project/langchain-dakera/) | LangChain (Python): memory, vector store, sessions, knowledge graph |
| [`@dakera-ai/langchain`](https://www.npmjs.com/package/@dakera-ai/langchain) | LangChain.js: memory, vector store, sessions, knowledge graph |
| [`llamaindex-dakera`](https://pypi.org/project/llamaindex-dakera/) | LlamaIndex: memory block, vector store, memory store |
| [`autogen-dakera`](https://pypi.org/project/autogen-dakera/) | AutoGen: `Memory` for `AssistantAgent`, sessions, knowledge graph |
| **[`crewai-dakera`](https://pypi.org/project/crewai-dakera/)** | **CrewAI: storage for a crew's memories** |
| [`strands-dakera`](https://pypi.org/project/strands-dakera/) | Strands Agents: memory tool and `MemoryStore` |
| [`@dakera-ai/ai-sdk`](https://www.npmjs.com/package/@dakera-ai/ai-sdk) | Vercel AI SDK: memory middleware and tools |

## Links

- [dakera.ai](https://dakera.ai) · [Documentation](https://dakera.ai/docs) · [LoCoMo benchmark](https://dakera.ai/benchmark) · [CrewAI integration guide](https://dakera.ai/integrations/crewai.html)
- Self-hosting: [dakera-deploy](https://github.com/Dakera-AI/dakera-deploy) (Docker Compose, Kubernetes) · [dakera-helm](https://github.com/Dakera-AI/dakera-helm) · server image `ghcr.io/dakera-ai/dakera`
- Tools: [dakera-mcp](https://github.com/Dakera-AI/dakera-mcp) (MCP server) · [dakera-cli](https://github.com/Dakera-AI/dakera-cli) (`dk` command line)
- [Issues](https://github.com/Dakera-AI/dakera-crewai/issues) · [Changelog](https://github.com/Dakera-AI/dakera-crewai/blob/main/CHANGELOG.md)

## License

[MIT](https://github.com/Dakera-AI/dakera-crewai/blob/main/LICENSE) © [Dakera AI](https://dakera.ai)
