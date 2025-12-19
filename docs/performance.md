# Performance & Resource Testing

Production agents must meet SLAs (Service Level Agreements) around latency, cost, throughput, and resource usage. Senytl's performance testing module provides comprehensive tools to benchmark, monitor, and enforce these requirements.

## Overview

The `senytl.performance` module provides:

- **Latency Assertions**: Ensure response times meet SLAs
- **Token Usage Tracking**: Monitor and control token consumption
- **Cost Estimation**: Track and limit operational costs
- **Throughput Benchmarks**: Test performance under load
- **Memory Profiling**: Detect memory leaks and resource issues

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

## Benchmarking

### Basic Benchmark

Use the `@performance.benchmark` decorator to track performance metrics:

```python
@performance.benchmark
def test_agent_performance():
    response = agent.run("Test query")
    
    # Metrics are automatically recorded
    performance.assert_latency_under(seconds=2.0)
    performance.assert_token_usage_under(1000)
```

The decorator automatically:
- Records latency for each request
- Tracks token usage from LLM calls
- Estimates costs based on model pricing
- Monitors memory usage

### Recording Metrics Manually

For more control, manually record metrics:

```python
@performance.benchmark
def test_custom():
    start = time.time()
    response = agent.run("Query")
    latency = time.time() - start
    
    # Manually record
    performance.record_request(latency, response)
    
    # Then assert
    performance.assert_latency_under(seconds=1.0)
```

## Load Testing

Test your agent under realistic load with concurrent users:

```python
@performance.load_test(concurrent_users=100, duration=60)
def test_agent_under_load():
    response = agent.run("Simple query")
    
    # Assert throughput SLAs
    performance.assert_throughput_above(requests_per_second=50)
    performance.assert_p95_latency_under(seconds=3)
    performance.assert_no_memory_leaks()
```

### Load Test Parameters

- `concurrent_users`: Number of simulated concurrent users
- `duration`: Test duration in seconds (alternative to iterations)
- `iterations`: Number of iterations per user (alternative to duration)
- `ramp_up`: Ramp-up time in seconds to gradually start users

```python
# Duration-based
@performance.load_test(concurrent_users=50, duration=120, ramp_up=10)
def test_sustained_load():
    agent.run("Query")

# Iteration-based
@performance.load_test(concurrent_users=20, iterations=10)
def test_fixed_iterations():
    agent.run("Query")
```

## SLA Assertions

### Latency Assertions

```python
# Average latency
performance.assert_latency_under(seconds=2.0)

# Percentile latencies
performance.assert_latency_under(seconds=1.0, percentile="avg")
performance.assert_latency_under(seconds=2.0, percentile="p95")
performance.assert_latency_under(seconds=3.0, percentile="p99")
performance.assert_latency_under(seconds=5.0, percentile="max")

# Convenience methods
performance.assert_p95_latency_under(seconds=2.0)
performance.assert_p99_latency_under(seconds=3.0)
```

### Token Usage Assertions

```python
# Per-request average
performance.assert_token_usage_under(1000, per_request=True)

# Total tokens across all requests
performance.assert_token_usage_under(10000, per_request=False)
```

### Cost Assertions

```python
# Per-request cost in cents
performance.assert_cost_under(cents=5.0, per_request=True)

# Total cost across all requests
performance.assert_cost_under(cents=100.0, per_request=False)
```

### Throughput Assertions

```python
# Minimum requests per second
performance.assert_throughput_above(requests_per_second=50)
```

### Memory Assertions

```python
# Detect memory leaks (default threshold: 20% growth)
performance.assert_no_memory_leaks()

# Custom threshold
performance.assert_no_memory_leaks(threshold=0.15)  # 15% growth
```

## Performance Reports

Generate detailed performance reports in multiple formats:

```python
@performance.benchmark
def test_agent():
    response = agent.run("Query")
    performance.record_request(response.duration_seconds, response)

# Get metrics
metrics = test_agent._performance_metrics[-1]

# Generate reports
text_report = performance.generate_report(metrics, format="text")
json_report = performance.generate_report(metrics, format="json")
md_report = performance.generate_report(metrics, format="markdown")

# Save to file
performance.generate_report(
    metrics,
    output_path="performance_report.txt",
    format="text"
)
```

### Report Example

```
Performance Report
──────────────────────────────────────────────────
Avg Latency:     1.234s
P50 Latency:     1.200s
P95 Latency:     2.100s
P99 Latency:     2.500s
Max Latency:     2.800s

Token Usage:     450 tokens/request
Total Tokens:    4500

Cost:            $0.0225/request
Total Cost:      $0.2250

Throughput:      67.50 req/s

Memory:          125.3 MB avg (✓ stable)
Peak Memory:     138.7 MB

Success Rate:    98.0% (98/100)
```

## Cost Estimation

Senytl estimates costs based on standard model pricing:

### Default Pricing (per 1M tokens)

| Model | Prompt | Completion |
|-------|--------|------------|
| GPT-4 | $30.00 | $60.00 |
| GPT-4 Turbo | $10.00 | $30.00 |
| GPT-3.5 Turbo | $0.50 | $1.50 |
| Claude 3 Opus | $15.00 | $75.00 |
| Claude 3 Sonnet | $3.00 | $15.00 |
| Claude 3 Haiku | $0.25 | $1.25 |
| Gemini Pro | $0.50 | $1.50 |

### Custom Pricing

Override pricing for your specific models:

```python
custom_pricing = {
    "my-model": {"prompt": 5.0, "completion": 10.0},
}

cost = performance.estimate_cost(
    token_usage,
    model="my-model",
    custom_pricing=custom_pricing
)
```

## Token Usage Tracking

Token usage is automatically extracted from LLM call records:

```python
from senytl.models import LLMCallRecord, MockResponse

llm_calls = [
    LLMCallRecord(
        provider="openai",
        model="gpt-4",
        request={"messages": "Your prompt here"},
        response=MockResponse(text="Response text")
    )
]

usage = performance.extract_token_usage(llm_calls)
print(f"Tokens: {usage.total_tokens}")
print(f"Prompt: {usage.prompt_tokens}")
print(f"Completion: {usage.completion_tokens}")
```

## Memory Profiling

Monitor memory usage during tests:

```python
@performance.load_test(concurrent_users=50, duration=60)
def test_memory_profile():
    agent.run("Query")

result = test_memory_profile()

print(f"Average memory: {result.avg_memory_mb:.1f} MB")
print(f"Peak memory: {result.max_memory_mb:.1f} MB")
print(f"Memory leak: {result.memory_leak_detected}")

# Assert no leaks
performance.set_current_metrics(result)
performance.assert_no_memory_leaks()
performance.set_current_metrics(None)
```

### Memory Snapshot

Capture memory usage at any point:

```python
snapshot = performance.capture_memory_snapshot()
print(f"RSS: {snapshot.rss_mb:.1f} MB")
print(f"VMS: {snapshot.vms_mb:.1f} MB")
print(f"Percent: {snapshot.percent:.1f}%")
```

## Performance Metrics

Access detailed metrics programmatically:

```python
@performance.benchmark
def test_agent():
    # ... test code ...
    pass

# Get metrics
metrics = test_agent._performance_metrics[-1]

# Latency
print(f"Average: {metrics.avg_latency:.3f}s")
print(f"P50: {metrics.p50_latency:.3f}s")
print(f"P95: {metrics.p95_latency:.3f}s")
print(f"P99: {metrics.p99_latency:.3f}s")
print(f"Min: {metrics.min_latency:.3f}s")
print(f"Max: {metrics.max_latency:.3f}s")

# Tokens
print(f"Total tokens: {metrics.total_tokens}")
print(f"Avg per request: {metrics.avg_tokens_per_request:.0f}")

# Cost
print(f"Total cost: ${metrics.total_cost:.4f}")
print(f"Avg per request: ${metrics.avg_cost_per_request:.4f}")

# Throughput
print(f"Throughput: {metrics.throughput_rps:.2f} req/s")

# Memory
print(f"Avg memory: {metrics.avg_memory_mb:.1f} MB")
print(f"Max memory: {metrics.max_memory_mb:.1f} MB")
print(f"Memory leak: {metrics.memory_leak_detected}")

# Reliability
print(f"Total requests: {metrics.total_requests}")
print(f"Failed requests: {metrics.failed_requests}")
print(f"Success rate: {metrics.success_rate * 100:.1f}%")
```

## Complete Example

```python
from senytl import Senytl, performance

# Create and wrap agent
senytl = Senytl()
senytl.install()

senytl.mock("gpt-3.5-turbo").when(contains="hello").respond(
    "Hello! How can I help you?"
)

agent = senytl.wrap(my_agent)

# Benchmark test
@performance.benchmark
def test_basic_performance():
    response = agent.run("hello")
    performance.record_request(response.duration_seconds, response)
    
    # Assert SLAs
    performance.assert_latency_under(seconds=2.0)
    performance.assert_token_usage_under(500)
    performance.assert_cost_under(cents=1.0)

test_basic_performance()

# Load test
@performance.load_test(concurrent_users=100, duration=60)
def test_load():
    agent.run("hello")

result = test_load()

# Check load test SLAs
performance.set_current_metrics(result)
performance.assert_throughput_above(requests_per_second=50)
performance.assert_p95_latency_under(seconds=3.0)
performance.assert_no_memory_leaks()
performance.set_current_metrics(None)

# Generate report
report = performance.generate_report(result, format="text")
print(report)

# Save report
performance.generate_report(
    result,
    output_path=".senytl/performance/load_test_report.json",
    format="json"
)

senytl.uninstall()
```

## Best Practices

### 1. Define SLAs Early

Define performance SLAs before implementation:

```python
# SLA requirements
MAX_LATENCY_P95 = 2.0  # seconds
MAX_TOKENS_PER_REQUEST = 1000
MAX_COST_PER_REQUEST = 0.05  # dollars
MIN_THROUGHPUT = 50  # req/s

@performance.benchmark
def test_sla_compliance():
    response = agent.run("Query")
    performance.record_request(response.duration_seconds, response)
    
    performance.assert_p95_latency_under(seconds=MAX_LATENCY_P95)
    performance.assert_token_usage_under(MAX_TOKENS_PER_REQUEST)
    performance.assert_cost_under(cents=MAX_COST_PER_REQUEST * 100)
```

### 2. Test Under Realistic Load

Simulate production conditions:

```python
@performance.load_test(
    concurrent_users=100,  # Expected concurrent users
    duration=300,          # 5 minutes sustained load
    ramp_up=30             # 30 second ramp-up
)
def test_production_load():
    agent.run(generate_realistic_query())
```

### 3. Monitor Trends

Track performance over time:

```python
# Run tests regularly and save reports
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path = f".senytl/performance/report_{timestamp}.json"

performance.generate_report(metrics, output_path=output_path, format="json")
```

### 4. Profile Memory for Long-Running Tests

Always check for memory leaks in sustained load tests:

```python
@performance.load_test(concurrent_users=50, duration=600)  # 10 minutes
def test_long_running():
    agent.run("Query")

result = test_long_running()

performance.set_current_metrics(result)
performance.assert_no_memory_leaks(threshold=0.10)  # Strict 10% threshold
performance.set_current_metrics(None)
```

### 5. Combine with Other Testing Features

Integrate performance testing with other Senytl features:

```python
@performance.benchmark
def test_comprehensive():
    # Snapshot for regression testing
    with snapshot.snapshot_mode("update"):
        response = agent.run("Query")
    
    # Performance SLAs
    performance.record_request(response.duration_seconds, response)
    performance.assert_latency_under(seconds=2.0)
    
    # Behavioral assertions
    expect(response).to_contain("expected text")
    expect(response).to_have_called("tool_name")
```

## Troubleshooting

### High Latency

```python
# Check percentile breakdown
metrics = get_current_metrics()
print(f"P50: {metrics.p50_latency:.3f}s")
print(f"P95: {metrics.p95_latency:.3f}s")
print(f"P99: {metrics.p99_latency:.3f}s")

# If P99 >> P95, investigate tail latency
```

### High Token Usage

```python
# Analyze token distribution
for i, usage in enumerate(metrics.token_usage):
    print(f"Request {i}: {usage.total_tokens} tokens")
    print(f"  Prompt: {usage.prompt_tokens}")
    print(f"  Completion: {usage.completion_tokens}")
```

### Memory Leaks

```python
# Examine memory growth
for i, snapshot in enumerate(metrics.memory_snapshots):
    print(f"Sample {i}: {snapshot.rss_mb:.1f} MB")

# Check if memory continuously grows
```

## API Reference

See the full API documentation in the module source or use:

```python
help(performance.benchmark)
help(performance.load_test)
help(performance.assert_latency_under)
# ... etc
```

## Integration with CI/CD

Fail builds on SLA violations:

```yaml
# .github/workflows/performance.yml
- name: Run Performance Tests
  run: |
    pytest tests/performance/ --verbose
    
    # Exit with error on SLA violations
    if grep -q "SLAViolationError" test_output.log; then
      exit 1
    fi
```

## Next Steps

- Review [examples/performance_demo.py](../examples/performance_demo.py) for working examples
- Check [tests/test_performance.py](../tests/test_performance.py) for test patterns
- Combine with [Coverage Testing](./coverage.md) for comprehensive quality assurance
