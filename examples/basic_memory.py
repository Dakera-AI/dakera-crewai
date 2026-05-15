"""Basic agent memory with CrewAI and Dakera.

Shows how to use DakeraStorage for persistent semantic memory
that survives across CrewAI agent runs.

Usage:
    export DAKERA_API_URL="http://localhost:3300"
    export DAKERA_API_KEY="dk-..."          # optional
    pip install crewai-dakera
    python basic_memory.py
"""

import os

from crewai_dakera import DakeraStorage

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3300")
api_key = os.environ.get("DAKERA_API_KEY", "")

storage = DakeraStorage(
    api_url=api_url,
    agent_id="crewai-researcher",
    api_key=api_key,
    search_k=3,
    importance=0.8,
)

storage.save("Completed market analysis: AI memory market growing 40% YoY.")
storage.save("Key competitor identified: Mem0 — open-source, Python-first.")
storage.save("Client prefers executive summary format with bullet points.")

print("Searching for 'market research findings':")
results = storage.search("market research findings")
for r in results:
    print(f"  [{r['score']:.3f}] {r['content']}")

print("\nSearching for 'client preferences':")
results = storage.search("client preferences")
for r in results:
    print(f"  [{r['score']:.3f}] {r['content']}")
