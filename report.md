# Senytl Phase 2 Report

## "Make it smart"

Phase 2 focuses on adding agent-specific testing capabilities that traditional frameworks can't provide. This includes trajectory analysis, snapshot testing, adversarial testing, and behavioral validation.

### 1) Trajectory Capture & Analysis
Implemented in `senytl/trajectory.py`.

**Capabilities implemented**
- **Execution Trace**: Records the entire path of an agent's execution (LLM calls, tool calls).
- **Step Validation**: `assert_steps([...])` allows asserting that specific steps (tool calls) happened in a specific order, or ensuring certain steps did *not* happen.
- **Efficiency Analysis**:
  - `assert_no_redundant_calls()`: Detects consecutive identical tool calls.
  - `assert_no_infinite_loops(threshold=...)`: Detects repeating sequences of tool calls.
- **Visual Debugging**: `visualize()` prints a text-based flowchart of the execution trace.

**User Experience**
```python
from senytl import trajectory

@trajectory.capture
def test_booking_flow():
    # ... run agent ...
    trajectory.assert_steps(["search_flights", "book_flight"])
    trajectory.assert_no_infinite_loops()
```

### 2) Snapshot Testing for Conversations
Implemented in `senytl/snapshot.py`.

**Capabilities implemented**
- **Automated Regression Testing**: Records agent behavior to `.snapshots/<test_name>.yaml`.
- **Modes**:
  - `match(responses)`: Exact or structural match.
  - `match(..., semantic=True)`: Uses token-based Jaccard similarity to allow for phrasing variations (threshold > 0.3).
- **Selective Snapshots**:
  - `match_tone(responses)`: Validates only the tone field.
  - `match_tools(responses)`: Validates only the tool calls.

**Dependencies Added**
- `pyyaml`: Used for serializing and deserializing snapshot files.

### 3) Adversarial Testing Engine
Implemented in `senytl/adversarial.py`.

**Capabilities implemented**
- **Security Testing Decorator**: `@adversarial.test(attacks=[...])` automatically runs the agent against known attack vectors.
- **Built-in Attack Categories**:
  - `jailbreak`: Checks if the agent can be tricked into ignoring instructions (e.g., "Ignore previous instructions").
  - `pii_leak`: Checks if the agent reveals sensitive info (simulated).
  - `tool_abuse`: Checks if the agent calls dangerous tools (e.g., `delete_database`) when prompted maliciously.
- **Custom Attacks**: `@adversarial.custom([...])` allows defining domain-specific attack prompts and asserts the agent refuses them.

**User Experience**
```python
from senytl import adversarial

@adversarial.test(attacks=["jailbreak", "pii_leak"])
def test_agent_security(agent):
    pass
```

### 4) Behavioral Validation Library
Implemented in `senytl/behavior.py`.

**Capabilities implemented**
- **Semantic Assertions**: High-level checks for "soft" qualities.
  - `assert_empathetic`: Checks for empathetic keywords.
  - `assert_professional`: Checks for absence of slang.
  - `assert_no_defensiveness`: Checks for defensive phrasing.
  - `assert_offers_solution`: Checks if a solution is proposed.
  - `assert_no_harmful_content`: Safety check.
- **Custom Validators**: `@behavior.define("rule_name")` to create reusable behavior checks.

**User Experience**
```python
from senytl import behavior

def test_support_agent(response):
    behavior.assert_empathetic(response)
    behavior.assert_professional(response)
```

### 5) Refactoring & Architecture

- **Circular Import Fix**: Moved `_DEFAULT_SENYTL` and `get_default_senytl` to `senytl/core.py` to allow submodules (`trajectory`, etc.) to access the global instance without circular dependency on `senytl/__init__.py`.
- **Module Exposure**: New modules (`trajectory`, `snapshot`, `adversarial`, `behavior`) are exposed at the top-level `senytl` package.
- **Dependencies**: Added `pyyaml` to `pyproject.toml` (implicitly via environment).

---

## Test Suite
New tests were added to validate Phase 2 features:
- `tests/test_trajectory.py`: Verifies capture, step assertion, and loop detection.
- `tests/test_snapshot.py`: Verifies snapshot creation, matching, and semantic comparison.
- `tests/test_adversarial.py`: Verifies attack simulation and failure reporting.
- `tests/test_behavior.py`: Verifies built-in and custom behavioral assertions.

All tests are passing.
