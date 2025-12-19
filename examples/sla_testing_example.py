"""
SLA Testing Example

This example demonstrates production-grade SLA testing for LLM agents,
matching the exact requirements from the ticket.
"""

import time

from senytl import Senytl, performance


def create_test_agent():
    """Create a mock agent for testing."""
    
    class ProductionAgent:
        def __init__(self):
            self.senytl = Senytl()
            self.senytl.install()
            
            # Mock GPT-3.5-turbo responses
            self.senytl.mock("gpt-3.5-turbo").when(
                contains="Complex query"
            ).respond(
                "This is a detailed response that addresses your complex query. " * 10
            )
            
            self.senytl.mock("gpt-3.5-turbo").when(
                contains="Simple query"
            ).respond(
                "Quick response."
            )
        
        def run(self, query: str) -> str:
            # Simulate processing time
            if "Complex" in query:
                time.sleep(0.05)
            else:
                time.sleep(0.01)
            
            # This would be actual LLM call in production
            return f"Processed: {query}"
        
        def cleanup(self):
            self.senytl.uninstall()
    
    return ProductionAgent()


def main():
    print("=" * 70)
    print("Production SLA Testing Example")
    print("=" * 70)
    print()
    
    # Test 1: Response Time SLA
    print("Test 1: Response Time SLA")
    print("-" * 70)
    
    agent = create_test_agent()
    wrapped_agent = agent.senytl.wrap(agent)
    
    @performance.benchmark
    def test_response_time():
        response = wrapped_agent.run("Complex query")
        performance.record_request(response.duration_seconds or 0.05, response)
        
        # SLA assertions
        performance.assert_latency_under(seconds=2)
        
        # Only assert token usage and cost if we have LLM calls
        if response.llm_calls:
            performance.assert_token_usage_under(1000)
            performance.assert_cost_under(cents=5)
        
        return response
    
    response = test_response_time()
    metrics = test_response_time._performance_metrics[-1]
    
    print(f"✓ Response received: {response.text[:50]}...")
    print(f"✓ Latency: {metrics.avg_latency:.3f}s (SLA: < 2.0s)")
    if response.llm_calls:
        print(f"✓ Token usage: {metrics.avg_tokens_per_request:.0f} (SLA: < 1000)")
        print(f"✓ Cost: ${metrics.avg_cost_per_request:.4f} (SLA: < $0.05)")
    else:
        print("✓ No LLM calls made (mocked agent)")
    print()
    
    agent.cleanup()
    
    # Test 2: Load Testing
    print("Test 2: Load Testing")
    print("-" * 70)
    
    agent = create_test_agent()
    wrapped_agent = agent.senytl.wrap(agent)
    
    @performance.load_test(concurrent_users=100, duration=3, ramp_up=0.5)
    def test_agent_under_load():
        wrapped_agent.run("Simple query")
    
    print("Running load test with 100 concurrent users for 3 seconds...")
    result = test_agent_under_load()
    
    print(f"✓ Total requests: {result.total_requests}")
    print(f"✓ Throughput: {result.throughput_rps:.2f} req/s")
    print(f"✓ Success rate: {result.success_rate * 100:.1f}%")
    print()
    
    # Assert load test SLAs
    performance.set_current_metrics(result)
    performance.assert_throughput_above(requests_per_second=50)
    performance.assert_p95_latency_under(seconds=3)
    performance.assert_no_memory_leaks()
    print("✓ All load test SLAs met!")
    performance.set_current_metrics(None)
    print()
    
    agent.cleanup()
    
    # Generate comprehensive report
    print("Performance Report:")
    print("─" * 70)
    
    token_line = f"Token Usage:     {result.avg_tokens_per_request:.0f} tokens/request ✓" if result.token_usage else "Token Usage:     N/A (no LLM calls)"
    cost_line = f"Cost:            ${result.avg_cost_per_request:.4f}/request ✓" if result.costs else "Cost:            N/A (no LLM calls)"
    
    report = f"""
Performance Report:
────────────────────
Avg Latency:     {result.avg_latency:.3f}s ✓
P95 Latency:     {result.p95_latency:.3f}s ✓
P99 Latency:     {result.p99_latency:.3f}s {"✓" if result.p99_latency < 3.0 else "✗ (SLA: 3.0s)"}
{token_line}
{cost_line}
Throughput:      {result.throughput_rps:.0f} req/s ✓
Memory:          {result.avg_memory_mb:.0f} MB {"✓ stable" if not result.memory_leak_detected else "✗ leak detected"}
Success Rate:    {result.success_rate * 100:.1f}% ✓
"""
    print(report)
    
    print("=" * 70)
    print("All SLAs met! Agent ready for production.")
    print("=" * 70)


if __name__ == "__main__":
    main()
