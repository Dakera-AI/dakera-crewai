# Changelog

## [0.4.0] - 2026-10-27

Dakera server **v0.12.3** support and a `DakeraStorage` that really plugs into a crew.
Requires the `dakera` Python SDK **>= 0.14.1**; tested against Dakera server v0.12.3 and still
works with v0.12.0 – v0.12.2 (the new arguments below need the server version named next to
them). The `crewai` extra targets CrewAI 0.193 – 1.9 (tested with 0.193.0, 1.6.1 and 1.9.3).

### Changed
- Requires `dakera>=0.14.1` (was `>=0.13.1`).
- **`DakeraStorage.reset()` deletes every memory of the agent** on the server (it was a no-op).
  CrewAI calls it from `crew.reset_memories(...)` / `crewai reset-memories`, which now really
  resets a crew's Dakera memory; it cannot be undone.
- The `crewai` extra requires `crewai>=0.193.0,<1.10` (was `>=0.30.0`): CrewAI 1.10 replaced
  `ExternalMemory` / `ShortTermMemory` / `EntityMemory` with a unified `Memory` whose storage
  backends receive client-side embeddings, which `DakeraStorage` does not implement. The
  package without the extra works with any CrewAI version.
- `DakeraStorage.search()` and `DakeraStorage.batch_search()` return at most `limit` ranked
  memories. A v0.12.3 server appends neighbourhood context to a recall by default, which
  could push the result past `limit` and mix in items whose scores are not comparable with
  the ranked ones; the context is now requested separately (`neighborhood_mode="separate"`)
  and left out.
- Result `score` is the server's `rank_score` (v0.12.3), the field recall ranks by; older
  servers keep the previous score.
- `DakeraStorage.search()` results carry the memory's `importance` and `metadata`.
- `DakeraNamespaceManager.create(metadata=...)` is deprecated and not sent
  (`DeprecationWarning`).

### Added
- **CrewAI storage interface** on `DakeraStorage`: `save(value, metadata)` takes any value (a
  non-string is stored as its `str()`), `search(query, limit, score_threshold)` takes CrewAI's
  arguments (`score_threshold` is a cut-off for CrewAI's own cosine similarity and is not
  applied), and `asave()` / `asearch()` serve CrewAI's async paths. `DakeraStorage` backs
  `ExternalMemory(storage=...)`, `ShortTermMemory(storage=...)` and `EntityMemory(storage=...)`.
- `DakeraStorage.save(..., event_time=)`: when the memory's event happened (Unix seconds, an
  RFC 3339 string or a timezone-aware `datetime`) for history written after the fact. Server
  v0.12.3 reads it for recency and `since` / `until`; `created_at` stays the ingest time.
- `DakeraStorage.consolidate(memory_ids=None)`: merge exactly the given memories (at least two).
- `DakeraSessionManager.start(metadata=None, *, idle_timeout_secs=None)` and
  `DakeraSessionManager.touch()`: from v0.12.2 the server ends a session after 4 h without
  activity by default; set the session's own timeout (`0` = never) or keep it open.
  `DakeraSessionManager.get()` returns `ended_reason` (`"client"`, `"idle"`, ...) and
  `last_activity_at`; `DakeraSessionManager.list()` returns `ended_reason`.
- `DakeraSessionManager.memories(session_id, *, include_derived=False)`.
- `DakeraKnowledgeGraph.deduplicate(*, threshold=None, dry_run=False)`.
- `examples/crew_memory.py`: a crew with `ExternalMemory(storage=DakeraStorage(...))` that
  recalls its first run in the second; it uses OpenAI when `OPENAI_API_KEY` is set and a
  scripted stand-in LLM otherwise.
- `LICENSE` (MIT, as declared in `pyproject.toml`).

### Fixed
- The README's headline example passed `DakeraStorage` to `LongTermMemory(storage=...)`, whose
  storage interface (`save(task_description, ...)`, `load(...)`) `DakeraStorage` does not
  implement, so the crew failed when it saved or recalled long-term memory. The README now
  uses `ExternalMemory`, documents which CrewAI memories take the storage, and every README
  snippet is run against a live server.
- A crew's `ExternalMemory` passes the agent's whole conversation as `metadata["messages"]`;
  stored as metadata it could exceed the server's metadata limit and fail the save. It is
  left out (the value already holds the agent's answer).
- `DakeraNamespaceManager.create(..., metadata=...)` failed with `422` on a v0.12.3 server,
  which refuses fields its create route does not know.
- `DakeraSessionManager.memories()` returned the sentence sub-memories the server derives from
  a session's memories (tagged `dakera-curated`) alongside them; they are left out unless
  `include_derived=True`.
- README: the `docker run` quick start published port 3300 while the server listens on 3000;
  the Docker Compose URL pointed at a file that does not exist and set `DAKERA_API_KEY`
  instead of the required `DAKERA_ROOT_API_KEY`; the configuration table named a `top_k`
  constructor argument (it is `search_k`).
- `DakeraKnowledgeGraph.deduplicate()` was documented as deduplicating graph entities; it
  merges the agent's near-duplicate memories.
- The `advanced_memory.py` example printed `importance`, which `search()` did not return; it
  now queries something the stored memories answer and shows `event_time`.

### Docs / examples
- README rewritten around `ExternalMemory(storage=DakeraStorage(...))`, with sections for the
  storage interface, the direct API, sessions, the knowledge graph, entities and namespaces,
  and an examples table. CONTRIBUTING describes the current commands and how to run the live
  tests (`DAKERA_API_URL`). Public classes and methods document their arguments and results.
- Examples default to `http://localhost:3000` (the server's default port), forget what they
  store so reruns start clean, and cover tag filters, consolidation, links and paths,
  `touch()` and the session context manager.

### Tests / CI
- `tests/test_integration.py`: live tests of every class against a real server, including a
  crew whose second run recalls the first through `ExternalMemory`; skipped unless
  `DAKERA_API_URL` is set (the CI integration job sets it).
- Integration tests and examples run against `ghcr.io/dakera-ai/dakera:0.12.3` with the
  `crewai` extra installed. That image ships no `curl`, so the service container has no
  in-container health check; the job polls `/health` from the runner instead.
- CI checks formatting (`ruff format --check`, the whole tree is formatted), and a failing
  example now fails the examples job.

## [0.3.0] - 2026-10-01

Dakera server **v0.12.0** support. Requires the `dakera` Python SDK **>= 0.13.1**; compatible
with Dakera server v0.12.0 and v0.11.108.

### Changed
- Requires `dakera>=0.13.1` (was `>=0.9.0`).
- `DakeraEntityExtractor.configure(entity_types=None, *, extract_entities=True)` configures the
  agent's memory namespace (`_dakera_agent_{agent_id}`), the namespace whose settings apply when
  memories are stored. It previously targeted a namespace named after the agent id (a 404 on the
  server) and could not succeed because the required `extract_entities` argument was never sent.
- `DakeraNamespaceManager.configure(name, *, dimension, distance=None)`: `dimension` is required
  by the server and is now an explicit argument (the old `**kwargs` pass-through could not work
  without it).
- `DakeraKnowledgeGraph.link(source_id, target_id, *, label=None)` sends the agent id the server
  requires (every link was a 422 before) and returns the server's `{from_id, to_id, edge_type}`.
  The `edge_type` argument is gone: the server records every explicit link as `linked_by`.
- `DakeraKnowledgeGraph.summarize(memory_ids, *, target_type=None)` needs at least two ids and has
  no `dry_run`: the server has no dry run and always stores the summary (dakera 0.13.1 raises on
  `dry_run=True` rather than silently writing).
- `DakeraKnowledgeGraph.build(memory_id, depth=None)`: the seed `memory_id` is required by the server.
- `DakeraStorage.search(tags=...)` works: dakera 0.13.1 `recall()` accepts `tags` (it raised
  `TypeError` before).

### Fixed
- `DakeraSessionManager.list()` reads the server's `{"sessions": [...]}` answer (it iterated over
  the object's keys and failed).
- `DakeraNamespaceManager.stats()` works: dakera 0.13.0 reads `GET /v1/namespaces/{ns}`
  (older SDKs called a route the server does not serve).
- The `knowledge_graph.py` example stores two memories and summarizes them.

### Tests / CI
- Unit tests mock the client with `create_autospec(DakeraClient)`, so a call that does not match
  the SDK's signature fails the test.
- Integration tests and examples run against `ghcr.io/dakera-ai/dakera:0.12.0` instead of `latest`.

## [0.1.1] - 2026-05-13

### Added
- **`__repr__` for `DakeraStorage`**: meaningful string representation for easier debugging in CrewAI pipelines
- Community health files: `CONTRIBUTING.md`, `SECURITY.md`, issue templates, PR template

### Changed
- Bumped GitHub Actions: `actions/checkout` v4 → v6, `actions/setup-python` v5 → v6

## [0.1.0] - 2026-05-13

### Added
- Initial release — CrewAI integration for Dakera AI memory platform
- `DakeraStorage` class implementing CrewAI's `Storage` interface for persistent agent memory
- PyPI publish via OIDC Trusted Publisher
