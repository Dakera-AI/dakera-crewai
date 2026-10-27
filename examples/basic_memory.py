"""Basic agent memory with CrewAI and Dakera.

DakeraStorage is a direct API to an agent's memories (and the storage of a
crew's memory, see crew_memory.py); memories survive across processes and runs.

Usage:
    export DAKERA_API_URL="http://localhost:3000"
    export DAKERA_API_KEY="dk-..."          # optional
    pip install crewai-dakera
    python basic_memory.py
"""

import os

from crewai_dakera import DakeraStorage

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3000")
api_key = os.environ.get("DAKERA_API_KEY", "")

storage = DakeraStorage(
    api_url=api_url,
    agent_id="crewai-researcher",
    api_key=api_key,
    search_k=3,
    importance=0.8,
)

ids = [
    storage.save("Completed market analysis: AI memory market growing 40% YoY.")["id"],
    storage.save("Key competitor identified: Mem0 — open-source, Python-first.")["id"],
    storage.save("Client prefers executive summary format with bullet points.")["id"],
]

print("Searching for 'market research findings':")
results = storage.search("market research findings")
for r in results:
    print(f"  [{r['score']:.3f}] {r['content']}")

print("\nSearching for 'client preferences':")
results = storage.search("client preferences")
for r in results:
    print(f"  [{r['score']:.3f}] {r['content']}")

# Forget what this demo stored, so a rerun starts from scratch.
storage.batch_forget(ids)
