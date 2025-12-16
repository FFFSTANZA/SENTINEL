# Sentinel Phase 1 Report

## What Phase 1 currently delivers ("Make it work")

### 1) Core Mock Engine
Implemented in `sentinel/mock_engine.py` and exposed via `sentinel.mock(...)`.

**Capabilities implemented**
- Deterministic interception via in-process patching of common SDK entrypoints:
  - OpenAI: `openai.ChatCompletion.create` (legacy) + best-effort support for v1-style resources
  - Anthropic: `anthropic.resources.messages.Messages.create` + best-effort legacy `anthropic.messages.create`
  - Google GenAI: `google.generativeai.GenerativeModel.generate_content`
- Pattern matching:
  - `contains=` (string or list of strings)
  - `regex=` (case-insensitive)
  - `semantic_match=` using deterministic token Jaccard similarity (fast, offline)
- Response templates:
  - `text`, plus tool metadata (`tools` and/or explicit `tool_calls`)
- Stateful mocking (improved):
  - Rules store `state["history"]` across turns
  - **New:** `respond_sequence([...])` returns different responses across calls (multi-turn friendly)
- Fallback handling:
  - `error` (default): raise `NoMockMatchError`
  - `default`: empty response
  - `pass_through`: call the real SDK

### 2) Recording + Replay
Implemented in `sentinel/recording.py` and wired into the patch layer (`sentinel/patching.py`).

**Capabilities implemented**
- `record_session(name)`:
  - switches fallback to `pass_through`
  - records real SDK responses to `.sentinel/sessions/<name>.json`
- `replay_session(name)`:
  - loads the session file
  - matches calls by a stable hash of `{provider, model, request}`
- **Lifecycle improvement:** sessions can be started without a context manager and are automatically finalized when switching modes (`record_session` -> `replay_session`) or on `reset()/uninstall()`.

### 3) pytest Integration Layer
Implemented in `sentinel/pytest_plugin.py`.

**Capabilities implemented**
- Plugin provides fixtures:
  - `sentinel`: preconfigured default instance, auto-installs/uninstalls patches per test
  - `sentinel_agent`: helper for wrapping any agent
- Markers registered:
  - `sentinel_agent`, `sentinel_mock`, `sentinel_adversarial`

### 4) Basic Assertion Library
Implemented in `sentinel/assertions.py`.

**Capabilities implemented**
- `expect(response)` fluent assertions:
  - text assertions: `to_contain`, `to_match`, `to_contain_intent` (deterministic semantic similarity)
  - tool assertions: `to_have_called`, `to_have_called_with`, `not_to_have_called`
  - timing: `to_have_response_time_under`
  - basic safety: `not_to_contain_pii`

### 5) Framework Adapters
Implemented in `sentinel/adapters.py`.

**Capabilities implemented**
- `sentinel.wrap(agent)` supports:
  - raw callables
  - objects with `invoke()` (LangChain-style), `run()`
- Produces a standardized `SentinelResponse`:
  - `.text`, `.raw`, `.duration_seconds`, `.tool_calls`, `.llm_calls`

---

## Small test suite added
A minimal test suite was added in `tests/test_phase1.py` to validate the Phase 1 contract:

- Mock interception for OpenAI-style calls (using a local fake `openai` module)
- Rule precedence (last rule wins)
- **Stateful** sequential responses (`respond_sequence`)
- Record + replay flow **without requiring a context manager**
- Smoke test for pytest fixture wiring

These tests are designed to be:
- deterministic
- offline (no real API calls)
- fast

---

## What was initially implemented “poorly” and what was improved

### 1) Stateful mocking was present but not very usable
**Before:** rules stored history but could not naturally return different answers across turns.

**Improvement implemented:** `respond_sequence([...])` for turn-by-turn scripted responses. This is a practical baseline for multi-turn agent testing without introducing complex templating.

### 2) Recording sessions needed a context manager to safely flush to disk
**Before:** calling `record_session("x")` started recording, but if you didn’t use `with ...:` you could easily forget to stop and never write the file.

**Improvement implemented:**
- `Sentinel` now tracks an active session.
- Switching modes (`record_session` -> `replay_session`) automatically finalizes the active session.
- `reset()` and `uninstall()` also finalize active sessions.
- Added `stop_session()` convenience method.

### 3) Config parsing on Python 3.10 was best-effort only
**Before:** `tomli` was optional but not declared.

**Improvement implemented:** added a conditional dependency:
- `tomli>=2; python_version<'3.11'`

---

## Known limitations / gaps (still Phase 1)

1. **Semantic similarity is simplistic**
   - Jaccard token similarity is fast and deterministic but not a true semantic embedding-based match.
   - Future: pluggable similarity backends (local embeddings, cached remote embeddings).

2. **SDK patching is best-effort**
   - The patch layer targets common entrypoints, but SDKs evolve frequently.
   - Future: patch at the HTTP transport layer (requests/httpx/aiohttp) for broader coverage.

3. **Tool calls are a testing artifact, not real tool execution**
   - Right now, tool calls are recorded as metadata (from mocks / parsed real responses).
   - Future: integrate tool registries and capture actual tool invocations from frameworks.

4. **Request normalization and replay keying is strict**
   - Replay depends on stable serialization of requests.
   - Future: smarter canonicalization (ignore timestamps, random seeds, headers).

---

## Summary
Phase 1 now supports deterministic, fast agent tests with:
- a mock engine capable of keyword/regex/semantic-ish matching
- multi-turn scripted responses
- record-once/replay-forever flows
- pytest-native fixtures
- an assertion DSL focused on agent behaviors

This is a strong foundation for Phase 2+ improvements (smarter semantic matching, broader interception, richer tooling introspection).
