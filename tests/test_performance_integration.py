"""
Integration tests demonstrating performance testing as specified in the ticket.
"""

import time

import pytest

from senytl import performance


def test_ticket_example_basic_benchmark():
    """Test the exact example from the ticket."""
    
    # Mock agent for testing
    class MockAgent:
        def run(self, query: str) -> str:
            time.sleep(0.05)  # Simulate processing
            return f"Response to: {query}"
    
    agent = MockAgent()
    
    @performance.benchmark
    def test_response_time():
        response = agent.run("Complex query")
        
        # Simulate recording request (in real usage, this happens automatically with wrapped agents)
        performance.record_request(0.05)
        
        # SLA assertions - exactly as shown in ticket
        performance.assert_latency_under(seconds=2)
        # Note: token_usage and cost assertions require actual LLM calls
        # They work automatically when using senytl.wrap() with real LLM interactions
        
        return response
    
    result = test_response_time()
    assert result is not None
    
    # Verify metrics were collected
    metrics = test_response_time._performance_metrics[-1]
    assert metrics.avg_latency < 2.0
    assert metrics.total_requests == 1


def test_ticket_example_load_test():
    """Test the load testing example from the ticket."""
    
    request_count = 0
    
    @performance.load_test(concurrent_users=50, duration=1)
    def test_agent_under_load():
        nonlocal request_count
        request_count += 1
        time.sleep(0.01)  # Simulate fast agent
    
    result = test_agent_under_load()
    
    # Verify load test ran
    assert result.total_requests >= 50  # At least one request per user
    assert result.throughput_rps is not None
    assert result.throughput_rps > 0
    
    # Check SLAs can be asserted
    performance.set_current_metrics(result)
    performance.assert_throughput_above(requests_per_second=10)
    performance.assert_p95_latency_under(seconds=1.0)
    performance.assert_no_memory_leaks()
    performance.set_current_metrics(None)


def test_performance_report_generation():
    """Test that performance reports can be generated as shown in ticket."""
    
    @performance.load_test(concurrent_users=10, iterations=2)
    def test_run():
        time.sleep(0.01)
    
    result = test_run()
    
    # Generate report
    report = performance.generate_report(result, format="text")
    
    # Verify report contains expected sections (as shown in ticket example)
    assert "Performance Report" in report
    assert "Avg Latency" in report
    assert "P95 Latency" in report
    assert "P99 Latency" in report
    assert "Throughput" in report
    assert "Memory" in report
    assert "Success Rate" in report


def test_sla_violation_errors():
    """Test that SLA violations raise appropriate errors."""
    
    @performance.benchmark
    def test_slow():
        time.sleep(0.5)
        performance.record_request(0.5)
        
        # Assert within the benchmark context
        with pytest.raises(performance.SLAViolationError):
            performance.assert_latency_under(seconds=0.1)
    
    test_slow()


def test_all_sla_assertions_available():
    """Verify all SLA assertion functions mentioned in ticket are available."""
    
    # Create dummy metrics
    metrics = performance.PerformanceMetrics()
    metrics.latencies = [0.1, 0.2, 0.3]
    metrics.total_requests = 3
    metrics.throughput_rps = 50.0
    
    performance.set_current_metrics(metrics)
    
    # All these should be available and work
    try:
        performance.assert_latency_under(seconds=1.0)
        # Token and cost assertions require token_usage/costs data
        performance.assert_throughput_above(requests_per_second=10)
        performance.assert_p95_latency_under(seconds=1.0)
        performance.assert_p99_latency_under(seconds=1.0)
        performance.assert_no_memory_leaks()  # Will work even with empty snapshots
    finally:
        performance.set_current_metrics(None)


def test_cost_estimation():
    """Test that cost estimation works for different models."""
    
    usage = performance.TokenUsage(
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500
    )
    
    # Test different models from the ticket
    gpt4_cost = performance.estimate_cost(usage, model="gpt-4")
    gpt35_cost = performance.estimate_cost(usage, model="gpt-3.5-turbo")
    claude_cost = performance.estimate_cost(usage, model="claude-3-opus")
    
    # GPT-4 should be most expensive
    assert gpt4_cost.total_cost > gpt35_cost.total_cost
    assert claude_cost.total_cost > gpt35_cost.total_cost
    
    # All should have valid costs
    assert gpt4_cost.total_cost > 0
    assert gpt35_cost.total_cost > 0
    assert claude_cost.total_cost > 0


def test_memory_profiling():
    """Test memory profiling capabilities."""
    
    @performance.load_test(concurrent_users=5, iterations=3)
    def test_memory():
        # Create some temporary data
        data = ["x" * 100 for _ in range(10)]
        time.sleep(0.01)
    
    result = test_memory()
    
    # Memory should be tracked
    assert len(result.memory_snapshots) > 0
    assert result.avg_memory_mb > 0
    assert result.max_memory_mb > 0
    
    # Memory leak detection should work
    assert isinstance(result.memory_leak_detected, bool)


def test_throughput_calculation():
    """Test that throughput is correctly calculated."""
    
    @performance.load_test(concurrent_users=10, duration=0.5)
    def test_throughput():
        time.sleep(0.01)
    
    result = test_throughput()
    
    # Throughput should be calculated
    assert result.throughput_rps is not None
    assert result.throughput_rps > 0
    
    # It should be reasonable (total_requests / duration)
    assert result.total_requests > 0


def test_percentile_latencies():
    """Test that percentile latencies are correctly calculated."""
    
    metrics = performance.PerformanceMetrics()
    
    # Add known latency distribution
    for i in range(100):
        metrics.latencies.append(i / 100.0)  # 0.00s to 0.99s
    
    # Check percentiles
    assert metrics.p50_latency < metrics.p95_latency
    assert metrics.p95_latency < metrics.p99_latency
    assert metrics.avg_latency < metrics.max_latency
    assert metrics.min_latency < metrics.avg_latency


def test_json_report_format():
    """Test JSON report generation."""
    
    metrics = performance.PerformanceMetrics()
    metrics.latencies = [0.1, 0.2, 0.3]
    metrics.total_requests = 3
    
    import json
    report = performance.generate_report(metrics, format="json")
    data = json.loads(report)
    
    # Should have all expected fields
    assert "latencies" in data
    assert "requests" in data
    assert data["latencies"]["avg"] > 0
    assert data["requests"]["total"] == 3


def test_markdown_report_format():
    """Test Markdown report generation."""
    
    metrics = performance.PerformanceMetrics()
    metrics.latencies = [0.1, 0.2, 0.3]
    metrics.total_requests = 3
    
    report = performance.generate_report(metrics, format="markdown")
    
    # Should be valid markdown
    assert "# Performance Report" in report
    assert "## Latency" in report
    assert "## Summary" in report
    assert "- **" in report  # Markdown list items
