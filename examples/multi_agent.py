"""Multi-agent shared memory with CrewAI and Dakera.

Each Dakera agent id is its own memory: here a researcher and a writer keep
separate memories on the same server. Give two crews the same agent id to let
them share one memory.

Usage:
    export DAKERA_API_URL="http://localhost:3000"
    export DAKERA_API_KEY="dk-..."          # optional
    pip install crewai-dakera
    python multi_agent.py
"""

import os

from crewai_dakera import DakeraStorage

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3000")
api_key = os.environ.get("DAKERA_API_KEY", "")

researcher = DakeraStorage(
    api_url=api_url,
    agent_id="crewai-researcher",
    api_key=api_key,
    importance=0.8,
)

writer = DakeraStorage(
    api_url=api_url,
    agent_id="crewai-writer",
    api_key=api_key,
    importance=0.8,
)

print("Researcher stores findings...")
research_ids = [
    researcher.save("Python is the most popular language for AI/ML development.")["id"],
    researcher.save("TypeScript adoption in AI tooling grew 60% in 2025.")["id"],
]

print("Writer stores drafts...")
draft_ids = [
    writer.save("Blog outline: 'Top Languages for AI Development in 2026'")["id"],
    writer.save("Key angle: polyglot approach — Python for ML, TypeScript for tooling.")["id"],
]

print("\nResearcher recalls their findings about 'AI languages':")
for r in researcher.search("AI languages"):
    print(f"  [{r['score']:.3f}] {r['content']}")

print("\nWriter recalls their drafts about 'blog content':")
for r in writer.search("blog content"):
    print(f"  [{r['score']:.3f}] {r['content']}")

# Forget what this demo stored, so a rerun starts from scratch.
researcher.batch_forget(research_ids)
writer.batch_forget(draft_ids)
