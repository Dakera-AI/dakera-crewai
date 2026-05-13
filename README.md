# crewai-dakera

[![PyPI](https://img.shields.io/pypi/v/crewai-dakera)](https://pypi.org/project/crewai-dakera/)
[![Python](https://img.shields.io/pypi/pyversions/crewai-dakera)](https://pypi.org/project/crewai-dakera/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**CrewAI integration for the [Dakera AI](https://dakera.ai) memory platform.**

Give your CrewAI agents persistent, semantically-recalled memory backed by Dakera.

## Installation

```bash
pip install crewai-dakera
```

## Quick Start

```python
from crewai import Crew
from crewai.memory import LongTermMemory
from crewai_dakera import DakeraStorage

storage = DakeraStorage(
    api_url="https://your-dakera-instance.com",
    api_key="dk-...",
    agent_id="my-crew",
)
crew = Crew(
    agents=[...], tasks=[...],
    memory=True,
    long_term_memory=LongTermMemory(storage=storage),
)
```

## Links

- [Dakera Documentation](https://docs.dakera.ai/integrations/crewai)
- [Dakera AI](https://dakera.ai)
