"""Advanced memory features with CrewAI and Dakera.

Demonstrates importance levels, tags and event time.

Usage:
    export DAKERA_API_URL="http://localhost:3300"
    python advanced_memory.py
"""

import os

from crewai_dakera import DakeraStorage

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3300")
api_key = os.environ.get("DAKERA_API_KEY", "")

memory = DakeraStorage(
    api_url=api_url,
    api_key=api_key,
    agent_id="crewai-advanced-demo",
)

print("--- Different importance levels ---")
memory.save("casual greeting", importance=0.3)
memory.save("user is allergic to peanuts", importance=0.95)
memory.save("birthday is March 15", importance=0.8, tags=["personal"])

print("--- High-importance recall ---")
results = memory.search("user allergy and birthday", min_importance=0.7)
for r in results:
    print(f"  [{r['importance']:.1f}] {r['content']}")

print("--- Event time (server v0.12.3+) ---")
# A memory written after the fact keeps when its event happened; recency and
# since/until read it, while created_at stays the ingest time.
stored = memory.save("user moved to Berlin", event_time="2021-06-01T00:00:00Z")
print(f"  event time: {stored['metadata']['_dakera_event_time']}")
