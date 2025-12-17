# Senytl

Senytl provides deterministic, fast testing primitives for LLM agents, designed for production use at scale.

## Features

### Phase 1: Core Testing
- Mock engine for common LLM providers (OpenAI, Anthropic, Google)
- Pytest integration (plugin + fixtures + markers)
- Agent-centric assertion library
- Framework adapters (LangChain-style `invoke` plus raw Python agents)
- Session recording and replay
- Snapshot testing
- Trajectory analysis
- Adversarial testing
- Behavioral validation

### Phase 3: Production-Ready Scale
- **Coverage & Quality Metrics**: Track tool coverage, conversation paths, input diversity
- **CI/CD Integration**: Seamless GitHub Actions integration with automated reporting
- **Test Generation Assistant**: Auto-generate test cases from agent code
- **Multi-Agent Testing**: Test systems where multiple agents interact

## Quick Start

### Installation

```bash
pip install -e .
```

### Basic Usage

```python
import pytest
from senytl import expect

@pytest.mark.senytl_agent
def test_my_agent(senytl_agent):
    wrapped = senytl_agent(my_agent)
    response = wrapped.run("Hello!")
    
    expect(response).to_contain("greeting")
    expect(response).to_be_polite()
```

### Coverage Tracking

```bash
# Run tests with coverage
pytest --senytl-coverage

# Get recommendations
senytl suggest-tests
```

### Test Generation

```bash
# Generate tests from agent code
senytl generate tests --agent my_agent.py

# Interactive mode
senytl generate --interactive
```

### CI/CD Setup

```bash
# Initialize GitHub Actions workflow
senytl init-ci --github

# Run in CI mode
pytest --ci
```

### Multi-Agent Testing

```python
from senytl import multi_agent

system = multi_agent.System([
    ("agent1", agent1_function),
    ("agent2", agent2_function),
])

system.route("agent1", "agent2")
result = system.run_scenario([("agent1", "test input")])

multi_agent.assert_workflow_completed(result)
```

## Documentation

- [Phase 3 Features Guide](PHASE3_FEATURES.md) - Comprehensive guide to coverage, CI/CD, test generation, and multi-agent testing
- [Tests](tests/) - Example tests demonstrating all features

## CLI Commands

```bash
senytl suggest-tests              # Analyze coverage gaps
senytl generate tests --agent <f> # Generate test cases
senytl generate --interactive     # Interactive test generation
senytl init-ci --github          # Initialize CI/CD
senytl version                   # Show version
```

## Configuration

Create a `pyproject.toml` with:

```toml
[tool.senytl]
fallback = "error"  # error | default | pass_through
```

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --senytl-coverage

# Run in CI mode
pytest tests/ --ci
```

## License

MIT
