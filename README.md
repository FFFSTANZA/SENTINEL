# Senytl

> **Deterministic, fast testing utilities for LLM agents**

Senytl provides deterministic, fast testing primitives for LLM agents, designed to run reliably in local development and CI environments. Built with Python 3.10+, it offers comprehensive testing capabilities specifically designed for agent-based systems.

[![PyPI version](https://badge.fury.io/py/senytl.svg)](https://badge.fury.io/py/senytl)
[![Python Support](https://img.shields.io/pypi/pyversions/senytl.svg)](https://pypi.org/project/senytl/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📦 Installation

```bash
pip install senytl
```

### Optional Extras

```bash
# Pytest integration (recommended)
pip install "senytl[pytest]"

# Semantic similarity testing using embeddings
pip install "senytl[semantic]"

# Full installation with all features
pip install "senytl[pytest,semantic]"
```

## ✨ Features

- **pytest Integration** - Seamless integration with pytest fixtures and markers
- **Coverage & Quality Metrics** - Track tool coverage, conversation paths, and quality scores
- **State Persistence & Replay** - Test stateful agents by saving and restoring checkpoints
- **Performance & SLA Testing** - Benchmark latency, throughput, cost, and resource usage
- **CI/CD Integration** - Automated reporting and assertions for continuous integration
- **Multi-Agent Testing** - Orchestrate and test multi-agent systems
- **Snapshot Testing** - Capture and assert on agent outputs
- **Adversarial Testing** - Robustness testing against edge cases and attacks
- **Semantic Validation** - Validate agent outputs using embeddings and similarity
- **Test Generation** - Automatically generate test cases from agent code

## 🚀 Quick Start

### Basic Usage

```python
from senytl import Senytl, expect

# Create a Senytl instance
senytl = Senytl()

# Define your agent
def my_agent(prompt: str) -> str:
    return f"Hello! You said: {prompt}"

# Wrap your agent for testing
wrapped = senytl(my_agent)

# Run and test your agent
response = wrapped.run("Hello!")
expect(response).to_contain("Hello")
```

### pytest Integration

```python
import pytest
from senytl import expect

@pytest.mark.senytl_agent
def test_my_agent(senytl_agent):
    def my_agent(prompt: str) -> str:
        return f"Response: {prompt}"
    
    wrapped = senytl_agent(my_agent)
    response = wrapped.run("Test")
    
    expect(response).to_contain("Test")
```

## 📊 Coverage & Quality

Track your agent testing coverage and quality metrics:

```bash
# Run with coverage reporting
pytest --senytl-coverage

# CI mode with detailed reporting
pytest --senytl-coverage --ci

# Generate coverage report programmatically
from senytl.coverage import get_coverage_tracker

tracker = get_coverage_tracker()
report = tracker.generate_report()
```

Coverage tracks:
- Tool Coverage: Which tools your agent uses
- Conversation Paths: Scenarios tested
- Decision Branches: Logic paths exercised
- Input Diversity: Variety of test inputs

## 🔄 State Persistence & Replay

Test stateful agents by persisting and restoring state:

```python
from senytl import state

# Save a checkpoint
checkpoint = state.save_checkpoint("my-agent-state")

# Restore from checkpoint
def test_with_state():
    restored_agent = state.from_checkpoint(checkpoint)
    response = restored_agent.run("Continue conversation")
    expect(response).to_contain("expected output")
```

## ⚡ Performance & SLA Testing

Benchmark your agent's performance and test SLA compliance:

```python
from senytl import performance
from senytl import expect_performance

@performance.benchmark
def my_llm_agent(prompt: str):
    # Your agent code here
    return f"Processed: {prompt}"

@performance.load_test(concurrent_users=10, duration=60)
def test_concurrent_load():
    # Performance testing under load
    pass

def test_sla_compliance():
    response = my_llm_agent("test")
    response.assert_latency_under(2.0)  # seconds
    response.assert_throughput_above(10)  # req/s
    response.assert_cost_under(0.01)  # $ per request
```

## 🏢 CI/CD Integration

Automated testing in your CI pipeline:

```bash
# Initialize GitHub Actions workflow
senytl init-ci --github

# Run tests in CI mode
pytest --ci

# Generate CI report
from senytl import ci
ci.generate_report()
```

## 🤖 Multi-Agent Testing

Test systems with multiple interacting agents:

```python
from senytl import multi_agent

system = multi_agent.System()
system.add_agent("planner", planning_agent)
system.add_agent("executor", execution_agent)

@multi_agent.test
def test_collaboration():
    result = system.orchestrate("Complete a complex task")
    expect(result.success).to_be_true()
```

## 📸 Snapshot Testing

Capture and assert on agent outputs across test runs:

```python
from senytl import snapshot

@snapshot.test
def test_consistent_output():
    response = my_agent("standard prompt")
    snapshot.assert_match(response.output)
```

## 🎯 Adversarial Testing

Test your agent's robustness:

```python
from senytl import adversarial

@adversarial.test
def test_robustness():
    # Tests with malformed inputs, edge cases, and attacks
    results = adversarial.run_suite(my_agent)
    expect(results.success_rate).to_be_greater_than(0.95)
```

## 🧠 Semantic Validation

Validate agent outputs using embeddings and similarity:

```python
from senytl import semantic

def test_semantic_similarity():
    response = my_agent("question about Python")
    expect(response).to_be_semantically_similar_to("python programming response")
```

## 📝 Test Generation

Automatically generate test cases:

```bash
# Generate tests from agent code
senytl generate tests --agent path/to/agent.py

# Interactive test generation
senytl generate --interactive

# Suggest missing tests based on coverage
senytl suggest-tests
```

## 🛠️ CLI Commands

```bash
# Display version
senytl version

# Suggest test improvements
senytl suggest-tests

# Generate tests
senytl generate tests --agent <file>

# Initialize CI workflow
senytl init-ci --github

# Show help
senytl --help
```

## 📈 pytest Plugin Features

- Custom markers: `@pytest.mark.senytl_agent`, `@pytest.mark.senytl_mock`, `@pytest.mark.senytl_adversarial`
- Fixtures: `senytl`, `senytl_agent`, `senytl_mock`, `senytl_config`
- Coverage tracking automatically enabled with CLI flags
- Integration with pytest-xdist for parallel testing

## 🗂️ Directory Structure

```
.senytl/
├── sessions/           # Session recordings
├── checkpoints/        # State checkpoints
├── coverage.json       # Coverage metrics
├── ci-report.json      # CI reports
└── performance/        # Performance reports

.snapshots/             # Snapshot files for testing
```

## 🎓 Advanced Examples

### Performance Testing Production Agents

```python
def test_llm_cost_efficiency():
    prompt = "Write a detailed explanation of machine learning"
    response = my_llm_agent(prompt)
    
    # Assert SLA compliance
    response.assert_p95_latency_under(5.0)
    response.assert_token_usage_under(2000, per_request=True)
    response.assert_cost_under(0.05, per_request=True)
    response.assert_no_memory_leaks(threshold=0.10)
```

### Stateful Agent Testing

```python
@state.persist_test
def test_conversation_flow():
    # First interaction
    agent = create_agent()
    response1 = agent.run("initialize")
    checkpoint = state.save_checkpoint()
    
    # Second interaction with restored state
    restored = state.from_checkpoint(checkpoint)
    response2 = restored.run("continue")
    expect(response2).to_contain("Continuing from previous state")
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT (see [LICENSE](LICENSE))

---

**[View on PyPI](https://pypi.org/project/senytl/) • [Report Issues](https://github.com/senytl/senytl/issues) • [View Source](https://github.com/senytl/senytl)**