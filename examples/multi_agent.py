"""Multi-agent shared memory with CrewAI and Dakera.

Demonstrates how multiple CrewAI agents can share context through
Dakera's memory platform using separate agent IDs and cross-agent recall.

Usage:
    export DAKERA_API_URL="http://localhost:3300"
    export DAKERA_API_KEY="dk-..."          # optional
    pip install crewai-dakera
    python multi_agent.py
"""

import os

from crewai_dakera import DakeraStorage

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3300")
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
researcher.save("Python is the most popular language for AI/ML development.")
researcher.save("TypeScript adoption in AI tooling grew 60% in 2025.")

print("Writer stores drafts...")
writer.save("Blog outline: 'Top Languages for AI Development in 2026'")
writer.save("Key angle: polyglot approach — Python for ML, TypeScript for tooling.")

print("\nResearcher recalls their findings about 'AI languages':")
for r in researcher.search("AI languages"):
    print(f"  [{r['score']:.3f}] {r['content']}")

print("\nWriter recalls their drafts about 'blog content':")
for r in writer.search("blog content"):
    print(f"  [{r['score']:.3f}] {r['content']}")
