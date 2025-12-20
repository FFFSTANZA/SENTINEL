# Phase 3: Scale & Production-Ready Features

This document describes the Phase 3 features that make Senytl production-ready for teams using it in CI/CD, across multiple agents, at scale.

## Features Overview

### 3.1 Coverage & Quality Metrics

Track agent-specific code coverage metrics showing what behaviors are tested vs. untested.

**Usage:**
```bash
# Run tests with coverage
pytest --senytl-coverage
```

**Example Output:**
```
Senytl Coverage Report
─────────────────────────────────────
Tool Coverage:        12/15 tools (80%)
Conversation Paths:   45 paths tested
Decision Branches:    89 branches tested
Input Diversity:      ⭐⭐⭐⭐☆ (Good)
Overall Quality:      A- (87/100)

⚠️  GAPS DETECTED:

Untested Tools:
  • delete_account (HIGH RISK)
  • export_data (MEDIUM RISK)

Recommendations:
  1. Add adversarial tests for delete_account
  2. Test error recovery paths (7 missing)

Run: senytl suggest-tests
To auto-generate missing test cases
```

**Key Capabilities:**
- **Tool coverage**: Which tools are tested, which aren't
- **Conversation coverage**: Which conversation paths are tested
- **Decision coverage**: Which decision branches are tested
- **Input diversity**: How varied are your test inputs
- **Quality score**: Overall test suite quality rating (A+ to D)
- **Gap analysis**: Automated recommendations for missing tests

### 3.2 CI/CD Integration

Make Senytl work seamlessly in continuous integration pipelines.

**Quick Start:**
```bash
# Initialize GitHub Actions workflow
senytl init-ci --github

# Run tests in CI mode
pytest --ci
```

**Example Workflow:**
```yaml
name: Senytl Agent Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -e .[pytest]
      - name: Run Senytl tests
        run: |
          pytest --senytl-coverage --ci
      - name: Upload coverage report
        uses: actions/upload-artifact@v3
        with:
          name: senytl-coverage
          path: .senytl/coverage.json
```

**Key Capabilities:**
- Pre-built GitHub Actions workflow templates
- Parallel test execution support
- CI-specific reporting
- PR comment integration
- Performance benchmarks

**CI Report Format:**
```
✅ Senytl Test Results

✅ 47/50 tests passed (94%)
❌ 3 tests failed
⚠️  2 vulnerabilities detected

Failed Tests:
  • test_refund_handling: Agent didn't call create_ticket
  • test_conversation_flow: Snapshot mismatch

Coverage: 87%
Duration: 12.5s
```

### 3.3 Test Generation Assistant

Auto-generate test cases based on agent code using AI analysis.

**Usage:**
```bash
# Analyze agent and suggest tests
senytl generate tests --agent customer_support.py

# Specify output file
senytl generate tests --agent agent.py --output tests/test_generated.py

# Interactive mode
senytl generate --interactive
```

**Example Output:**
```
🛡️ Analyzing agent: CustomerSupportAgent

Found 8 tools: create_ticket, search_orders, cancel_order...
Found 3 conversation patterns: greeting, problem_solving, escalation
Detected 5 safety-critical operations

Generating test suite...

✅ Generated 24 test cases:
   • 8 tool-specific tests
   • 6 conversation flow tests
   • 5 adversarial tests
   • 5 edge case tests

Review and customize: tests/test_customer_support_generated.py
Run: pytest tests/test_customer_support_generated.py
```

**Key Capabilities:**
- **Code analysis**: Reads agent implementation, suggests tests
- **Conversation simulation**: Generates realistic test scenarios
- **Edge case discovery**: Finds boundary conditions to test
- **Adversarial generation**: Creates attack vectors for safety-critical operations
- **Interactive mode**: CLI tool that guides you through test creation

### 3.4 Multi-Agent Testing

Test systems where multiple agents interact with each other.

**Usage:**
```python
from senytl import multi_agent, expect

def test_order_processing_workflow():
    # Define agent system
    system = multi_agent.System([
        ("customer_agent", customer_agent),
        ("payment_agent", payment_agent),
        ("inventory_agent", inventory_agent),
        ("shipping_agent", shipping_agent)
    ])
    
    # Set up routing
    system.route("customer_agent", "payment_agent")
    system.route("payment_agent", "inventory_agent")
    system.route("inventory_agent", "shipping_agent")
    
    # Test end-to-end workflow
    result = system.run_scenario([
        ("customer_agent", "I want to buy product X"),
    ])
    
    # System-wide assertions
    multi_agent.assert_workflow_completed(result)
    multi_agent.assert_no_deadlocks(result)
    multi_agent.assert_message_passing_correct(result)
    
    # Per-agent assertions
    expect(result.agent("payment_agent").executions[0].output).to_not_be_empty()
    assert result.agent("payment_agent").called_tool("charge_card")
    
    # Visualize agent interactions
    print(result.visualize_flow())
```

**Example Visualization:**
```
Agent Interaction Flow
══════════════════════════════════════════════════

1. user → customer_agent
   I want to buy product X

2. customer_agent → payment_agent
   Processing order for product X, amount: $99.99

3. payment_agent → inventory_agent
   Payment confirmed, reserve item X

4. inventory_agent → shipping_agent
   Item reserved, create shipment
```

**Key Capabilities:**
- **Agent choreography**: Test sequences of agent interactions
- **Message passing validation**: Ensure agents communicate correctly
- **Distributed assertions**: Assert conditions across multiple agents
- **Race condition detection**: Find timing-related bugs
- **System-level scenarios**: Test end-to-end workflows
- **Flow visualization**: Visual representation of agent interactions

## CLI Commands

### Coverage & Suggestions
```bash
# Show coverage gaps and recommendations
senytl suggest-tests
```

### Test Generation
```bash
# Generate tests from agent code
senytl generate tests --agent <file> [--output <file>]

# Interactive test generation
senytl generate --interactive
```

### CI/CD Setup
```bash
# Initialize GitHub Actions workflow
senytl init-ci --github
```

### Version Info
```bash
senytl version
```

## API Reference

### Coverage Module
```python
from senytl.coverage import get_coverage_tracker

tracker = get_coverage_tracker()
tracker.register_available_tools(["tool1", "tool2"])
tracker.record_tool_call(tool_call)
tracker.record_input(user_input)
report = tracker.generate_report()
```

### Multi-Agent Module
```python
from senytl import multi_agent

# Create system
system = multi_agent.System([
    ("agent1", agent1_function),
    ("agent2", agent2_function),
])

# Route messages
system.route("agent1", "agent2")

# Run scenario
result = system.run_scenario([
    ("agent1", "input message"),
])

# Assertions
multi_agent.assert_workflow_completed(result)
multi_agent.assert_no_deadlocks(result)
multi_agent.assert_message_passing_correct(result)
```

### Generation Module
```python
from senytl.generation import generate_tests, generate_summary

# Generate tests
tests = generate_tests("agent.py", "tests/test_agent.py")

# Get summary
summary = generate_summary("agent.py")
print(summary)
```

### CI Module
```python
from senytl.ci import CIReport, TestResult

# Create report
report = CIReport(
    total_tests=10,
    passed_tests=8,
    failed_tests=2,
)

# Add test results
report.test_results.append(TestResult(
    name="test_example",
    passed=False,
    duration=0.5,
    error="AssertionError"
))

# Generate summary
print(report.generate_summary())

# Save to file
report.save_json(Path(".senytl/ci-report.json"))
```

## Configuration

Phase 3 features work with existing Senytl configuration in `pyproject.toml`:

```toml
[tool.senytl]
fallback = "error"  # error | default | pass_through
```

## Output Files

Phase 3 features create the following files:

- `.senytl/coverage.json` - Coverage metrics
- `.senytl/ci-report.json` - CI test report
- `.senytl/ci-report.txt` - Human-readable CI summary
- `.senytl/pr-comment.txt` - PR comment content
- `.github/workflows/senytl.yml` - GitHub Actions workflow (if initialized)

All `.senytl/` outputs are automatically gitignored.

## Best Practices

1. **Run coverage regularly**: Use `--senytl-coverage` during development to track test completeness
2. **Set up CI early**: Initialize CI with `senytl init-ci --github` before first commit
3. **Generate tests first**: Use `senytl generate` to bootstrap test suites for new agents
4. **Test multi-agent flows**: Use `multi_agent.System` for integration tests
5. **Review generated tests**: Always review and customize auto-generated tests
6. **Track quality score**: Aim for A- or better (85+) on the quality score
7. **Address gaps**: Prioritize HIGH RISK untested tools

## Examples

See `tests/test_phase3_features.py` for comprehensive examples of all Phase 3 features.

See `tests/test_example_agent.py` for real-world agent testing examples with coverage tracking.
