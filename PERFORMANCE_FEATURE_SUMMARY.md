# Performance & Resource Testing - Implementation Summary

## Overview

Implemented a comprehensive Performance & Resource Testing system for the Senytl framework to enable production-grade SLA testing for LLM agents.

## What Was Implemented

### ✅ Core Module: `senytl/performance.py`

A complete performance testing module with:

1. **Benchmark Decorator** (`@performance.benchmark`)
   - Automatic latency tracking
   - Token usage extraction
   - Cost estimation
   - Memory profiling

2. **Load Test Decorator** (`@performance.load_test`)
   - Concurrent user simulation
   - Duration-based or iteration-based testing
   - Ramp-up support for gradual load increase
   - Thread-safe metric collection
   - Throughput calculation

3. **SLA Assertion Functions**
   - `assert_latency_under(seconds, percentile)` - Latency assertions for avg, p50, p95, p99, max
   - `assert_token_usage_under(tokens, per_request)` - Token usage limits
   - `assert_cost_under(cents, per_request)` - Cost limits
   - `assert_throughput_above(rps)` - Minimum throughput requirements
   - `assert_p95_latency_under(seconds)` - P95 latency shorthand
   - `assert_p99_latency_under(seconds)` - P99 latency shorthand
   - `assert_no_memory_leaks(threshold)` - Memory leak detection

4. **Performance Metrics**
   - `PerformanceMetrics` dataclass with computed properties
   - Latency percentiles (avg, p50, p95, p99, min, max)
   - Token usage statistics
   - Cost estimation for major LLM providers
   - Throughput tracking
   - Memory usage profiling
   - Success rate calculation

5. **Cost Estimation**
   - Built-in pricing for GPT-4, GPT-3.5, Claude 3, Gemini Pro
   - Custom pricing support
   - Per-million-token pricing
   - Separate prompt and completion costs

6. **Report Generation**
   - Text format (human-readable)
   - JSON format (CI/CD integration)
   - Markdown format (documentation)
   - File output support

7. **Memory Profiling**
   - Automatic memory snapshots using `psutil`
   - Memory leak detection (>20% growth threshold)
   - RSS and VMS tracking
   - Memory percentage tracking

### ✅ Tests: `tests/test_performance.py`

Comprehensive test suite with 18 tests covering:
- Token usage extraction
- Cost estimation
- Memory snapshots
- Decorator functionality
- All SLA assertions
- Performance metrics properties
- Report generation (text, JSON, markdown)
- Full benchmark and load test workflows
- Error handling

### ✅ Integration Tests: `tests/test_performance_integration.py`

11 integration tests demonstrating:
- Ticket requirements implementation
- Real-world usage patterns
- SLA violation detection
- Report generation
- Cost estimation
- Memory profiling
- Throughput calculation

### ✅ Documentation: `docs/performance.md`

Comprehensive documentation including:
- Quick start guide
- API reference
- Usage examples
- Best practices
- Troubleshooting guide
- CI/CD integration examples

### ✅ Examples

1. **`examples/performance_demo.py`**
   - 7 complete examples demonstrating all features
   - Basic benchmarking
   - Token usage and cost tracking
   - Load testing
   - Report generation
   - SLA violation detection
   - Memory profiling
   - Report export

2. **`examples/sla_testing_example.py`**
   - Production-ready SLA testing
   - Matches exact ticket requirements
   - Response time SLA testing
   - Load testing with 100 concurrent users
   - Performance report generation

### ✅ README: `PERFORMANCE_TESTING.md`

High-level overview and quick reference:
- Feature highlights
- Quick start examples
- Best practices
- CI/CD integration
- API reference table

## Key Features

### 1. Easy to Use

```python
@performance.benchmark
def test_response_time():
    response = agent.run("Complex query")
    performance.assert_latency_under(seconds=2)
```

### 2. Load Testing

```python
@performance.load_test(concurrent_users=100, duration=60)
def test_agent_under_load():
    agent.run("Simple query")
    performance.assert_throughput_above(requests_per_second=50)
```

### 3. Comprehensive Reports

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

## Technical Implementation Details

### Thread-Safe Metrics Collection

The load test decorator uses threading locks to safely collect metrics across concurrent workers:

```python
metrics_lock = threading.Lock()

def record_request_safe(latency: float, error: Exception | None = None):
    with metrics_lock:
        metrics.total_requests += 1
        metrics.latencies.append(latency)
        # ... more recording
```

### Context Variable Management

Performance metrics are stored in a context variable for thread-safe access:

```python
_perf_context: contextvars.ContextVar[PerformanceMetrics | None] = 
    contextvars.ContextVar("senytl_performance_context", default=None)
```

### Memory Leak Detection

Automatically detects memory leaks by comparing early vs late memory usage:

```python
@property
def memory_leak_detected(self) -> bool:
    split = len(self.memory_snapshots) // 10
    early = statistics.mean(s.rss_mb for s in self.memory_snapshots[:split])
    late = statistics.mean(s.rss_mb for s in self.memory_snapshots[-split:])
    growth = (late - early) / early
    return growth > 0.20
```

### Cost Estimation

Supports major LLM providers with per-million-token pricing:

```python
DEFAULT_PRICING = {
    "gpt-4": {"prompt": 30.0, "completion": 60.0},
    "gpt-3.5-turbo": {"prompt": 0.5, "completion": 1.5},
    "claude-3-opus": {"prompt": 15.0, "completion": 75.0},
    # ... more models
}
```

## Dependencies

Added `psutil>=5.8.0` to `pyproject.toml` for memory profiling.

## Integration with Existing Features

The performance module integrates seamlessly with:
- **Adapters**: Automatic metric collection when using `senytl.wrap()`
- **Models**: Uses `SenytlResponse` for tracking LLM calls
- **Assertions**: Works alongside existing `expect()` assertions

## Test Results

All tests pass:
- ✅ 18 unit tests in `test_performance.py`
- ✅ 11 integration tests in `test_performance_integration.py`
- ✅ All existing tests still pass (203 total)

## File Structure

```
senytl/
├── performance.py                    # Main module (600+ lines)
├── __init__.py                       # Updated exports
tests/
├── test_performance.py               # Unit tests (400+ lines)
├── test_performance_integration.py   # Integration tests (200+ lines)
examples/
├── performance_demo.py               # Comprehensive demo (230+ lines)
├── sla_testing_example.py            # Production SLA testing (150+ lines)
docs/
├── performance.md                    # Full documentation (500+ lines)
PERFORMANCE_TESTING.md                # Quick reference
PERFORMANCE_FEATURE_SUMMARY.md        # This file
```

## Usage Statistics

- **Module Size**: ~650 lines of production code
- **Test Coverage**: 29 tests covering all features
- **Documentation**: 1000+ lines across multiple files
- **Examples**: 2 complete working examples

## Why This Matters

> **Performance issues kill production deployments**

With Senytl's performance testing module, developers can:
1. **Catch issues early** - Test performance before production
2. **Enforce SLAs** - Fail builds if SLAs are violated
3. **Track costs** - Prevent runaway LLM costs
4. **Prevent memory leaks** - Detect leaks in long-running tests
5. **Generate reports** - Professional performance documentation

## Next Steps

The performance module is ready for production use and can be extended with:
- Database-backed performance trend tracking
- Integration with monitoring services (Datadog, New Relic)
- Custom metric collectors
- Performance regression detection
- A/B testing support

## Conclusion

The Performance & Resource Testing feature is fully implemented, tested, and documented, providing production-grade SLA testing for LLM agents as specified in the ticket requirements.
