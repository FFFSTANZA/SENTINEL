"""
Performance & Resource Testing Demo

This example demonstrates how to use Senytl's performance testing features:
- Latency assertions
- Token usage tracking
- Cost estimation
- Throughput benchmarks
- Memory profiling
"""

import time

from senytl import Senytl, expect, performance
from senytl.models import SenytlResponse


# Mock agent for demonstration
class SimpleAgent:
    def __init__(self, delay: float = 0.1):
        self.delay = delay
    
    def run(self, query: str) -> str:
        time.sleep(self.delay)
        return f"Processed: {query}"


def main():
    print("=" * 60)
    print("Senytl Performance Testing Demo")
    print("=" * 60)
    print()
    
    # Example 1: Basic Benchmark
    print("Example 1: Basic Performance Benchmark")
    print("-" * 60)
    
    @performance.benchmark
    def test_response_time():
        senytl = Senytl()
        senytl.install()
        
        # Mock an LLM response
        senytl.mock("gpt-3.5-turbo").when(contains="Complex query").respond(
            "This is a detailed response to your complex query."
        )
        
        agent = senytl.wrap(SimpleAgent(delay=0.1))
        response = agent.run("Complex query")
        
        # Record metrics
        performance.record_request(response.duration_seconds or 0.1, response)
        
        # SLA assertions
        performance.assert_latency_under(seconds=2.0)
        
        print(f"✓ Response received: {response.text[:50]}...")
        print(f"✓ Latency: {response.duration_seconds:.3f}s (SLA: < 2.0s)")
        
        senytl.uninstall()
    
    test_response_time()
    
    # Get metrics from benchmark
    metrics = test_response_time._performance_metrics[-1]
    print(f"✓ Total requests: {metrics.total_requests}")
    print(f"✓ Average latency: {metrics.avg_latency:.3f}s")
    print()
    
    # Example 2: Token Usage and Cost Tracking
    print("Example 2: Token Usage & Cost Tracking")
    print("-" * 60)
    
    @performance.benchmark
    def test_token_and_cost():
        # Simulate a response with token tracking
        time.sleep(0.05)
        
        # Since we're not making real LLM calls, we'll demonstrate
        # how token usage would be tracked if we were
        print("✓ Simulated LLM response received")
        print("✓ In production, token usage and costs would be tracked automatically")
        print("✓ Cost estimation supports GPT-4, GPT-3.5, Claude, Gemini models")
    
    test_token_and_cost()
    
    metrics = test_token_and_cost._performance_metrics[-1]
    print(f"✓ Latency tracked: {metrics.avg_latency:.3f}s")
    print()
    
    # Example 3: Load Testing
    print("Example 3: Load Testing with Concurrent Users")
    print("-" * 60)
    
    @performance.load_test(concurrent_users=20, iterations=3, ramp_up=0.5)
    def test_agent_under_load():
        # Simulate a fast agent
        time.sleep(0.02)
    
    print("Running load test with 20 concurrent users, 3 iterations each...")
    result = test_agent_under_load()
    
    print(f"✓ Total requests: {result.total_requests}")
    print(f"✓ Throughput: {result.throughput_rps:.2f} req/s")
    print(f"✓ Average latency: {result.avg_latency:.3f}s")
    print(f"✓ P95 latency: {result.p95_latency:.3f}s")
    print(f"✓ P99 latency: {result.p99_latency:.3f}s")
    print(f"✓ Success rate: {result.success_rate * 100:.1f}%")
    print()
    
    # Assert load test SLAs
    performance.set_current_metrics(result)
    performance.assert_throughput_above(requests_per_second=50)
    performance.assert_p95_latency_under(seconds=1.0)
    performance.assert_no_memory_leaks()
    print("✓ All SLAs met!")
    performance.set_current_metrics(None)
    print()
    
    # Example 4: Comprehensive Performance Report
    print("Example 4: Generating Performance Reports")
    print("-" * 60)
    
    @performance.benchmark
    def test_with_metrics():
        for i in range(5):
            time.sleep(0.01 * (i + 1))
            
            response = SenytlResponse(
                text=f"Response {i}",
                duration_seconds=0.01 * (i + 1),
            )
            performance.record_request(response.duration_seconds, response)
    
    test_with_metrics()
    metrics = test_with_metrics._performance_metrics[-1]
    
    # Generate text report
    report = performance.generate_report(metrics, format="text")
    print(report)
    print()
    
    # Example 5: SLA Violation Detection
    print("Example 5: SLA Violation Detection")
    print("-" * 60)
    
    @performance.benchmark
    def test_slow_agent():
        time.sleep(0.5)
        response = SenytlResponse(text="Slow response", duration_seconds=0.5)
        performance.record_request(0.5, response)
        
        try:
            # This should fail
            performance.assert_latency_under(seconds=0.1)
        except performance.SLAViolationError as e:
            print(f"✗ SLA Violation Detected: {e}")
            return
        
        print("✓ All SLAs met")
    
    test_slow_agent()
    print()
    
    # Example 6: Memory Profiling
    print("Example 6: Memory Profiling")
    print("-" * 60)
    
    @performance.load_test(concurrent_users=5, iterations=5)
    def test_memory_usage():
        # Simulate some work
        data = ["x" * 1000 for _ in range(100)]
        time.sleep(0.01)
    
    result = test_memory_usage()
    
    print(f"✓ Average memory: {result.avg_memory_mb:.1f} MB")
    print(f"✓ Peak memory: {result.max_memory_mb:.1f} MB")
    print(f"✓ Memory leak detected: {result.memory_leak_detected}")
    
    performance.set_current_metrics(result)
    try:
        performance.assert_no_memory_leaks()
        print("✓ No memory leaks detected")
    except performance.SLAViolationError as e:
        print(f"✗ {e}")
    performance.set_current_metrics(None)
    print()
    
    # Example 7: Export Reports
    print("Example 7: Exporting Performance Reports")
    print("-" * 60)
    
    # Save reports in different formats
    from pathlib import Path
    
    output_dir = Path(".senytl/performance")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Text report
    text_path = output_dir / "report.txt"
    performance.generate_report(result, output_path=text_path, format="text")
    print(f"✓ Text report saved to: {text_path}")
    
    # JSON report
    json_path = output_dir / "report.json"
    performance.generate_report(result, output_path=json_path, format="json")
    print(f"✓ JSON report saved to: {json_path}")
    
    # Markdown report
    md_path = output_dir / "report.md"
    performance.generate_report(result, output_path=md_path, format="markdown")
    print(f"✓ Markdown report saved to: {md_path}")
    print()
    
    print("=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
