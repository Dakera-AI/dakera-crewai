# crewai-dakera

[![CI](https://github.com/Dakera-AI/dakera-crewai/actions/workflows/ci.yml/badge.svg)](https://github.com/Dakera-AI/dakera-crewai/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/crewai-dakera)](https://pypi.org/project/crewai-dakera/)
[![Python](https://img.shields.io/pypi/pyversions/crewai-dakera)](https://pypi.org/project/crewai-dakera/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Persistent, semantically-recalled memory for [CrewAI](https://crewai.com) agents, powered by [Dakera](https://github.com/Dakera-AI/dakera-deploy).**

Your CrewAI crews remember everything — across sessions, across restarts. Dakera handles embedding, storage, and retrieval server-side with no local model required.

---

## Quick Start

### Step 1 — Run Dakera

Dakera is a self-hosted memory server. Spin it up with Docker:

```bash
docker run -d \
  --name dakera \
  -p 3300:3300 \
  -e DAKERA_ROOT_API_KEY=dk-mykey \
  ghcr.io/dakera-ai/dakera:latest
```

For a production setup with persistent storage, use Docker Compose:

```bash
# Download and start
curl -sSfL https://raw.githubusercontent.com/Dakera-AI/dakera-deploy/main/docker-compose.yml \
  -o docker-compose.yml
DAKERA_API_KEY=dk-mykey docker compose up -d

# Verify it's running
curl http://localhost:3300/health
```

> Full deployment guide: [github.com/Dakera-AI/dakera-deploy](https://github.com/Dakera-AI/dakera-deploy)

### Step 2 — Install the integration

```bash
pip install crewai-dakera
```

### Step 3 — Add memory to your crew

```python
from crewai import Crew, Agent, Task
from crewai.memory import LongTermMemory
from crewai_dakera import DakeraStorage

storage = DakeraStorage(
    api_url="http://localhost:3300",
    api_key="dk-mykey",
    agent_id="my-crew",
)

crew = Crew(
    agents=[...],
    tasks=[...],
    memory=True,
    long_term_memory=LongTermMemory(storage=storage),
)

result = crew.kickoff(inputs={"topic": "AI trends"})
```

Your crew now persists everything it learns across runs.

---

## Installation

```bash
# Core + integration
pip install crewai-dakera

# With CrewAI (if not already installed)
pip install "crewai-dakera[crewai]"
```

**Requirements:** Python ≥ 3.10, a running Dakera server (see Step 1 above)

---

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_url` | `str` | — | Dakera server URL (e.g. `http://localhost:3300`) |
| `api_key` | `str` | `""` | API key set via `DAKERA_ROOT_API_KEY` |
| `agent_id` | `str` | — | Logical identifier for this crew's memory |
| `min_importance` | `float` | `0.0` | Minimum importance score for recalled memories |
| `top_k` | `int` | `5` | Number of memories to surface per turn |

Use environment variables to avoid hardcoding credentials:

```python
import os
from crewai_dakera import DakeraStorage

storage = DakeraStorage(
    api_url=os.environ["DAKERA_URL"],
    api_key=os.environ["DAKERA_API_KEY"],
    agent_id="research-crew",
)
```

---

## Examples

### Research crew with persistent memory

```python
from crewai import Agent, Task, Crew, Process
from crewai.memory import LongTermMemory, ShortTermMemory, EntityMemory
from crewai_dakera import DakeraStorage

dakera = DakeraStorage(
    api_url="http://localhost:3300",
    api_key="dk-mykey",
    agent_id="research-crew",
)

researcher = Agent(
    role="Senior Researcher",
    goal="Uncover groundbreaking insights in {topic}",
    backstory="An expert researcher with decades of experience.",
    verbose=True,
)

writer = Agent(
    role="Content Writer",
    goal="Craft compelling reports based on research findings",
    backstory="A skilled writer who turns complex ideas into clear prose.",
    verbose=True,
)

research_task = Task(
    description="Research the latest developments in {topic}",
    expected_output="A detailed research report",
    agent=researcher,
)

write_task = Task(
    description="Write a blog post based on the research",
    expected_output="A polished 500-word article",
    agent=writer,
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    process=Process.sequential,
    memory=True,
    long_term_memory=LongTermMemory(storage=dakera),
    verbose=True,
)

# First run — learns and stores findings
result = crew.kickoff(inputs={"topic": "quantum computing"})
print(result.raw)

# Second run — recalls prior research automatically
result = crew.kickoff(inputs={"topic": "quantum computing advances"})
print(result.raw)
```

### Custom importance scoring

```python
storage = DakeraStorage(
    api_url="http://localhost:3300",
    api_key="dk-mykey",
    agent_id="my-crew",
    min_importance=0.6,  # only surface high-quality memories
    top_k=10,
)
```

---

## How it works

1. After each task, CrewAI calls `DakeraStorage.save()` with the result
2. Dakera embeds the content server-side (no local model needed) and stores it with a semantic vector
3. Before the next task, CrewAI calls `DakeraStorage.search()` — Dakera performs hybrid search (vector + BM25) and returns the most relevant past memories
4. Memories decay gracefully over time based on access patterns — frequently-accessed memories stay prominent

---

## Related packages

| Package | Framework | Language |
|---------|-----------|----------|
| `langchain-dakera` | LangChain | Python |
| `llamaindex-dakera` | LlamaIndex | Python |
| `autogen-dakera` | AutoGen | Python |
| `@dakera-ai/langchain` | LangChain.js | TypeScript |

---

## Links

- [Dakera Server](https://github.com/Dakera-AI/dakera-deploy) — self-hosted memory server
- [Dakera Python SDK](https://github.com/Dakera-AI/dakera-py) — low-level API client
- [Documentation](https://docs.dakera.ai/integrations/crewai)
- [All integrations](https://github.com/Dakera-AI/dakera-integrations)

---

## License

MIT © [Dakera AI](https://dakera.ai)
