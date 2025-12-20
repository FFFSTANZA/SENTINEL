# Performance & Resource Testing

> **Production agents must meet SLAs** – Senytl helps you enforce latency, cost, throughput, and memory requirements

## Why Performance Testing Matters

Performance issues kill production deployments. With Senytl's performance testing module, you can:

- ✅ **Enforce SLAs** – Assert latency, token usage, and cost limits
- ✅ **Load Test** – Test with 100+ concurrent users
- ✅ **Track Costs** – Estimate costs across GPT-4, Claude, Gemini
- ✅ **Detect Memory Leaks** – Automatic memory profiling
- ✅ **Generate Reports** – Professional performance reports

## Quick Start

```python
from senytl import performance

@performance.benchmark
def test_response_time():
    response = agent.run("Complex query")
    
    # SLA assertions
    performance.assert_latency_under(seconds=2)
    performance.assert_token_usage_under(1000)
    performance.assert_cost_under(cents=5)
```

## Load Testing

Test your agent under realistic production load:

```python
@performance.load_test(concurrent_users=100, duration=60)
def test_agent_under_load():
    response = agent.run("Simple query")
    
    performance.assert_throughput_above(requests_per_second=50)
    performance.assert_p95_latency_under(seconds=3)
    performance.assert_no_memory_leaks()
```

## Performance Reports

Automatically generate comprehensive reports:

```
Performance Report:
────────────────────
Avg Latency:     1.2s ✓
P95 Latency:     2.1s ✓
P99 Latency:     3.8s ✗ (SLA: 3.0s)
Token Usage:     450 tokens/request ✓
Cost:           $0.03/request ✓
Throughput:      67 req/s ✓
Memory:          125 MB (stable) ✓
```

## Features

### 🚀 Latency Assertions

```python
performance.assert_latency_under(seconds=2.0)
performance.assert_p95_latency_under(seconds=3.0)
performance.assert_p99_latency_under(seconds=5.0)
```

### 💰 Cost Tracking

Automatic cost estimation for major LLM providers:

```python
performance.assert_cost_under(cents=5.0, per_request=True)
```

Supports:
- GPT-4, GPT-4 Turbo, GPT-3.5 Turbo
- Claude 3 (Opus, Sonnet, Haiku)
- Gemini Pro

### 📊 Token Usage

```python
performance.assert_token_usage_under(1000, per_request=True)
```

### ⚡ Throughput Testing

```python
@performance.load_test(concurrent_users=100, duration=60)
def test_load():
    agent.run("Query")
    
performance.assert_throughput_above(requests_per_second=50)
```

### 🧠 Memory Profiling

Automatic memory leak detection:

```python
performance.assert_no_memory_leaks()
```

## Complete Example

```python
from senytl import Senytl, performance

# Setup
senytl = Senytl()
senytl.mock("gpt-3.5-turbo").when(contains="hello").respond("Hi there!")
agent = senytl.wrap(my_agent)

# Benchmark test
@performance.benchmark
def test_performance():
    response = agent.run("hello")
    
    performance.assert_latency_under(seconds=2.0)
    performance.assert_token_usage_under(500)
    performance.assert_cost_under(cents=1.0)

test_performance()

# Load test
@performance.load_test(concurrent_users=100, duration=60)
def test_load():
    agent.run("hello")

result = test_load()

# Check SLAs
performance.set_current_metrics(result)
performance.assert_throughput_above(requests_per_second=50)
performance.assert_p95_latency_under(seconds=3.0)
performance.assert_no_memory_leaks()
performance.set_current_metrics(None)

# Generate report
report = performance.generate_report(result, format="text")
print(report)
```

## Report Formats

Generate reports in multiple formats:

```python
# Text report
performance.generate_report(metrics, format="text")

# JSON for CI/CD integration
performance.generate_report(metrics, format="json")

# Markdown for documentation
performance.generate_report(metrics, format="markdown")

# Save to file
performance.generate_report(
    metrics,
    output_path="performance_report.json",
    format="json"
)
```

## Best Practices

### 1. Define SLAs Upfront

```python
# SLA constants
MAX_LATENCY_P95 = 2.0
MAX_TOKENS = 1000
MAX_COST_CENTS = 5

@performance.benchmark
def test_slas():
    response = agent.run("Query")
    performance.record_request(response.duration_seconds, response)
    
    performance.assert_p95_latency_under(seconds=MAX_LATENCY_P95)
    performance.assert_token_usage_under(MAX_TOKENS)
    performance.assert_cost_under(cents=MAX_COST_CENTS)
```

### 2. Test Under Load

```python
@performance.load_test(
    concurrent_users=100,
    duration=300,  # 5 minutes
    ramp_up=30     # 30 second ramp-up
)
def test_production_load():
    agent.run(generate_realistic_query())
```

### 3. Monitor Memory

```python
@performance.load_test(concurrent_users=50, duration=600)
def test_long_running():
    agent.run("Query")

result = test_long_running()
performance.set_current_metrics(result)
performance.assert_no_memory_leaks(threshold=0.10)  # Max 10% growth
```

### 4. Track Trends

```python
# Run regularly and save reports
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
performance.generate_report(
    metrics,
    output_path=f".senytl/performance/report_{timestamp}.json",
    format="json"
)
```

## SLA Assertion Reference

| Function | Purpose |
|----------|---------|
| `assert_latency_under(seconds, percentile)` | Assert latency threshold |
| `assert_p95_latency_under(seconds)` | Assert P95 latency |
| `assert_p99_latency_under(seconds)` | Assert P99 latency |
| `assert_token_usage_under(tokens)` | Assert token usage limit |
| `assert_cost_under(cents)` | Assert cost limit |
| `assert_throughput_above(rps)` | Assert minimum throughput |
| `assert_no_memory_leaks(threshold)` | Assert no memory leaks |

## Cost Estimation

Default pricing per 1M tokens:

| Model | Prompt | Completion |
|-------|--------|------------|
| GPT-4 | $30.00 | $60.00 |
| GPT-4 Turbo | $10.00 | $30.00 |
| GPT-3.5 Turbo | $0.50 | $1.50 |
| Claude 3 Opus | $15.00 | $75.00 |
| Claude 3 Sonnet | $3.00 | $15.00 |
| Claude 3 Haiku | $0.25 | $1.25 |
| Gemini Pro | $0.50 | $1.50 |

Custom pricing:

```python
custom_pricing = {
    "my-model": {"prompt": 5.0, "completion": 10.0}
}

cost = performance.estimate_cost(usage, model="my-model", custom_pricing=custom_pricing)
```

## CI/CD Integration

Fail builds on SLA violations:

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e .
      - run: pytest tests/performance/ --verbose
```

## Examples

- 📁 [examples/performance_demo.py](examples/performance_demo.py) - Comprehensive demo
- 📁 [examples/sla_testing_example.py](examples/sla_testing_example.py) - Production SLA testing
- 📁 [tests/test_performance_integration.py](tests/test_performance_integration.py) - Integration tests

## Documentation

Full documentation: [docs/performance.md](docs/performance.md)

## More Features

Combine with other Senytl features:

```python
@performance.benchmark
def test_comprehensive():
    # Snapshot testing
    with snapshot.snapshot_mode("update"):
        response = agent.run("Query")
    
    # Performance SLAs
    performance.assert_latency_under(seconds=2.0)
    
    # Semantic validation
    expect(response).semantically_similar_to("expected meaning")
    
    # Coverage tracking
    expect(response).to_have_called("tool_name")
```

---

**Why This Matters**: Performance issues are the #1 reason agents fail in production. With Senytl's performance testing, you can ship with confidence.
