from __future__ import annotations

import time
from unittest.mock import Mock

import pytest

from senytl import performance
from senytl.models import LLMCallRecord, MockResponse, SenytlResponse, ToolCall


def test_token_usage_extraction():
    """Test extracting token usage from LLM calls."""
    llm_calls = [
        LLMCallRecord(
            provider="openai",
            model="gpt-3.5-turbo",
            request={"messages": "Hello, how are you?" * 50},
            response=MockResponse(text="I'm doing well, thank you!" * 20),
        ),
    ]
    
    usage = performance.extract_token_usage(llm_calls)
    assert usage.total_tokens > 0
    assert usage.prompt_tokens > 0
    assert usage.completion_tokens > 0
    assert usage.total_tokens == usage.prompt_tokens + usage.completion_tokens


def test_cost_estimation():
    """Test cost estimation for different models."""
    usage = performance.TokenUsage(
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
    )
    
    # Test GPT-3.5-turbo pricing
    cost = performance.estimate_cost(usage, model="gpt-3.5-turbo")
    assert cost.total_cost > 0
    assert cost.prompt_cost > 0
    assert cost.completion_cost > 0
    assert cost.total_cost == cost.prompt_cost + cost.completion_cost
    
    # Test GPT-4 pricing (should be more expensive)
    cost_gpt4 = performance.estimate_cost(usage, model="gpt-4")
    assert cost_gpt4.total_cost > cost.total_cost


def test_memory_snapshot():
    """Test memory snapshot capture."""
    snapshot = performance.capture_memory_snapshot()
    assert snapshot.rss_mb > 0
    assert snapshot.vms_mb > 0
    assert snapshot.percent >= 0
    assert snapshot.timestamp > 0


def test_benchmark_decorator():
    """Test the @benchmark decorator."""
    
    @performance.benchmark
    def test_function():
        time.sleep(0.01)
        response = SenytlResponse(
            text="Hello world",
            duration_seconds=0.1,
            llm_calls=[
                LLMCallRecord(
                    provider="openai",
                    model="gpt-3.5-turbo",
                    request={"messages": "test"},
                    response=MockResponse(text="response"),
                )
            ],
        )
        performance.record_request(0.1, response)
    
    test_function()
    
    # Check that metrics were stored
    assert hasattr(test_function, "_performance_metrics")
    metrics = test_function._performance_metrics[0]
    assert metrics.total_requests > 0
    assert len(metrics.latencies) > 0
    assert len(metrics.token_usage) > 0


def test_assert_latency_under():
    """Test latency assertions."""
    metrics = performance.PerformanceMetrics()
    metrics.latencies = [0.5, 0.6, 0.7, 0.8, 0.9]
    performance.set_current_metrics(metrics)
    
    # Should pass
    performance.assert_latency_under(1.0, percentile="avg")
    performance.assert_latency_under(1.0, percentile="p95")
    
    # Should fail
    with pytest.raises(performance.SLAViolationError):
        performance.assert_latency_under(0.5, percentile="avg")
    
    performance.set_current_metrics(None)


def test_assert_token_usage_under():
    """Test token usage assertions."""
    metrics = performance.PerformanceMetrics()
    metrics.token_usage = [
        performance.TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        performance.TokenUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300),
    ]
    performance.set_current_metrics(metrics)
    
    # Should pass
    performance.assert_token_usage_under(300, per_request=True)
    
    # Should fail
    with pytest.raises(performance.SLAViolationError):
        performance.assert_token_usage_under(100, per_request=True)
    
    performance.set_current_metrics(None)


def test_assert_cost_under():
    """Test cost assertions."""
    metrics = performance.PerformanceMetrics()
    metrics.costs = [
        performance.CostEstimate(prompt_cost=0.001, completion_cost=0.002, total_cost=0.003),
        performance.CostEstimate(prompt_cost=0.001, completion_cost=0.002, total_cost=0.003),
    ]
    performance.set_current_metrics(metrics)
    
    # Should pass (0.003 dollars = 0.3 cents)
    performance.assert_cost_under(1.0, per_request=True)
    
    # Should fail
    with pytest.raises(performance.SLAViolationError):
        performance.assert_cost_under(0.1, per_request=True)
    
    performance.set_current_metrics(None)


def test_assert_throughput_above():
    """Test throughput assertions."""
    metrics = performance.PerformanceMetrics()
    metrics.throughput_rps = 100.0
    performance.set_current_metrics(metrics)
    
    # Should pass
    performance.assert_throughput_above(50.0)
    
    # Should fail
    with pytest.raises(performance.SLAViolationError):
        performance.assert_throughput_above(200.0)
    
    performance.set_current_metrics(None)


def test_assert_no_memory_leaks():
    """Test memory leak detection."""
    metrics = performance.PerformanceMetrics()
    
    # Simulate stable memory (no leak)
    for i in range(20):
        metrics.memory_snapshots.append(
            performance.MemorySnapshot(
                rss_mb=100.0 + i * 0.1,  # Small growth
                vms_mb=200.0,
                percent=5.0,
                timestamp=time.time(),
            )
        )
    
    performance.set_current_metrics(metrics)
    performance.assert_no_memory_leaks()  # Should pass
    
    # Simulate memory leak
    metrics2 = performance.PerformanceMetrics()
    for i in range(20):
        metrics2.memory_snapshots.append(
            performance.MemorySnapshot(
                rss_mb=100.0 + i * 5.0,  # Large growth
                vms_mb=200.0,
                percent=5.0,
                timestamp=time.time(),
            )
        )
    
    performance.set_current_metrics(metrics2)
    with pytest.raises(performance.SLAViolationError):
        performance.assert_no_memory_leaks()
    
    performance.set_current_metrics(None)


def test_performance_metrics_properties():
    """Test PerformanceMetrics computed properties."""
    metrics = performance.PerformanceMetrics()
    
    # Add latency data
    metrics.latencies = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    
    assert metrics.avg_latency == 0.55
    assert metrics.p50_latency == 0.55
    assert metrics.min_latency == 0.1
    assert metrics.max_latency == 1.0
    assert 0.9 <= metrics.p95_latency <= 1.0
    assert 0.9 <= metrics.p99_latency <= 1.0
    
    # Add token usage
    metrics.token_usage = [
        performance.TokenUsage(100, 50, 150),
        performance.TokenUsage(200, 100, 300),
    ]
    
    assert metrics.total_tokens == 450
    assert metrics.avg_tokens_per_request == 225.0
    
    # Add costs
    metrics.costs = [
        performance.CostEstimate(0.001, 0.002, 0.003),
        performance.CostEstimate(0.002, 0.003, 0.005),
    ]
    
    assert metrics.total_cost == 0.008
    assert metrics.avg_cost_per_request == 0.004
    
    # Test success rate
    metrics.total_requests = 100
    metrics.failed_requests = 5
    assert metrics.success_rate == 0.95


def test_load_test_decorator_with_iterations():
    """Test load_test decorator with iterations."""
    call_count = 0
    
    @performance.load_test(concurrent_users=5, iterations=2)
    def test_load():
        nonlocal call_count
        call_count += 1
        time.sleep(0.01)
    
    result = test_load()
    
    # Should have called function 5 users * 2 iterations = 10 times
    assert call_count == 10
    assert isinstance(result, performance.PerformanceMetrics)
    assert result.total_requests == 10
    assert result.throughput_rps is not None
    assert result.throughput_rps > 0


def test_load_test_decorator_with_duration():
    """Test load_test decorator with duration."""
    call_count = 0
    
    @performance.load_test(concurrent_users=3, duration=0.2)
    def test_load():
        nonlocal call_count
        call_count += 1
        time.sleep(0.05)
    
    result = test_load()
    
    # Should have called function multiple times across 3 users in 0.2 seconds
    assert call_count >= 3  # At least one per user
    assert isinstance(result, performance.PerformanceMetrics)
    assert result.throughput_rps is not None


def test_generate_report_text():
    """Test generating text performance report."""
    metrics = performance.PerformanceMetrics()
    metrics.latencies = [0.1, 0.2, 0.3]
    metrics.total_requests = 3
    metrics.failed_requests = 0
    metrics.token_usage = [performance.TokenUsage(100, 50, 150)]
    metrics.costs = [performance.CostEstimate(0.001, 0.002, 0.003)]
    metrics.memory_snapshots = [performance.MemorySnapshot(100.0, 200.0, 5.0, time.time())]
    
    report = performance.generate_report(metrics, format="text")
    
    assert "Performance Report" in report
    assert "Avg Latency" in report
    assert "P95 Latency" in report
    assert "Token Usage" in report
    assert "Cost" in report
    assert "Memory" in report
    assert "Success Rate" in report


def test_generate_report_json():
    """Test generating JSON performance report."""
    metrics = performance.PerformanceMetrics()
    metrics.latencies = [0.1, 0.2, 0.3]
    metrics.total_requests = 3
    metrics.failed_requests = 0
    
    report = performance.generate_report(metrics, format="json")
    
    import json
    data = json.loads(report)
    
    assert "latencies" in data
    assert "avg" in data["latencies"]
    assert "p95" in data["latencies"]
    assert "requests" in data


def test_generate_report_markdown():
    """Test generating Markdown performance report."""
    metrics = performance.PerformanceMetrics()
    metrics.latencies = [0.1, 0.2, 0.3]
    metrics.total_requests = 3
    
    report = performance.generate_report(metrics, format="markdown")
    
    assert "# Performance Report" in report
    assert "## Latency" in report
    assert "## Summary" in report


def test_full_benchmark_workflow():
    """Test complete benchmark workflow with real scenario."""
    
    @performance.benchmark
    def test_agent_performance():
        # Simulate agent execution
        time.sleep(0.05)
        
        response = SenytlResponse(
            text="Test response",
            duration_seconds=0.05,
            llm_calls=[
                LLMCallRecord(
                    provider="openai",
                    model="gpt-3.5-turbo",
                    request={"messages": "test query " * 100},
                    response=MockResponse(text="test response " * 50),
                )
            ],
        )
        
        performance.record_request(0.05, response)
        
        # Assert SLAs
        performance.assert_latency_under(seconds=1.0)
        performance.assert_token_usage_under(2000)
        performance.assert_cost_under(cents=10.0)
    
    # Run test
    test_agent_performance()
    
    # Get metrics
    metrics = test_agent_performance._performance_metrics[0]
    assert metrics.total_requests == 1
    assert len(metrics.latencies) == 1
    assert len(metrics.token_usage) == 1
    assert len(metrics.costs) == 1


def test_full_load_test_workflow():
    """Test complete load test workflow."""
    
    @performance.load_test(concurrent_users=10, iterations=2)
    def test_agent_under_load():
        # Simulate fast agent
        time.sleep(0.01)
        
        # No SLA assertions here as they're global across all requests
    
    result = test_agent_under_load()
    
    assert result.total_requests == 20  # 10 users * 2 iterations
    assert result.throughput_rps > 0
    assert result.avg_latency > 0
    
    # Can still check SLAs after the fact
    performance.set_current_metrics(result)
    performance.assert_latency_under(seconds=1.0)
    performance.assert_throughput_above(requests_per_second=10)
    performance.set_current_metrics(None)


def test_error_handling():
    """Test error handling when no context is active."""
    
    with pytest.raises(performance.PerformanceError):
        performance.assert_latency_under(1.0)
    
    with pytest.raises(performance.PerformanceError):
        performance.assert_token_usage_under(1000)
    
    with pytest.raises(performance.PerformanceError):
        performance.assert_cost_under(1.0)
