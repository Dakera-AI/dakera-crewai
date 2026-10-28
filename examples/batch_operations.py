"""Batch operations with CrewAI and Dakera.

Stores several memories, searches for several queries at once and forgets them
in one call.

Usage:
    export DAKERA_API_URL="http://localhost:3000"
    python batch_operations.py
"""

import os

from crewai_dakera import DakeraStorage

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3000")
api_key = os.environ.get("DAKERA_API_KEY", "")

memory = DakeraStorage(
    api_url=api_url,
    api_key=api_key,
    agent_id="crewai-batch-demo",
)

print("Storing batch of memories...")
items = [
    "30-day return policy for unopened items.",
    "International shipping to 40+ countries.",
    "Accepts Visa, Mastercard, and PayPal.",
    "Loyalty program: 1 point per dollar.",
    "Gift cards: $25, $50, $100 denominations.",
]
ids = [memory.save(item, importance=0.7)["id"] for item in items]
print(f"Stored {len(ids)} memories.")

print("\n--- Batch recall ---")
queries = ["shipping", "payment", "returns"]
results = memory.batch_search(queries, limit=2)
for query, matches in zip(queries, results):
    print(f"\n  Query: '{query}'")
    for m in matches:
        print(f"    [{m['score']:.3f}] {m['content'][:50]}")

print("\n--- Batch forget ---")
memory.batch_forget(ids)
print(f"Forgot {len(ids)} memories.")
