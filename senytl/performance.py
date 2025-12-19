from __future__ import annotations

import contextvars
import functools
import gc
import psutil
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, TypeVar

from .models import LLMCallRecord, SenytlResponse

F = TypeVar("F", bound=Callable[..., Any])


class PerformanceError(Exception):
    """Base exception for performance-related errors."""
    pass


class SLAViolationError(PerformanceError):
    """Raised when an SLA assertion fails."""
    pass


@dataclass
class TokenUsage:
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass
class CostEstimate:
    """Cost estimation for LLM calls."""
    prompt_cost: float = 0.0
    completion_cost: float = 0.0
    total_cost: float = 0.0
    currency: str = "USD"
    
    def __add__(self, other: "CostEstimate") -> "CostEstimate":
        return CostEstimate(
            prompt_cost=self.prompt_cost + other.prompt_cost,
            completion_cost=self.completion_cost + other.completion_cost,
            total_cost=self.total_cost + other.total_cost,
            currency=self.currency,
        )


@dataclass
class MemorySnapshot:
    """Memory usage snapshot."""
    rss_mb: float
    vms_mb: float
    percent: float
    timestamp: float


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics for a test run."""
    latencies: list[float] = field(default_factory=list)
    token_usage: list[TokenUsage] = field(default_factory=list)
    costs: list[CostEstimate] = field(default_factory=list)
    memory_snapshots: list[MemorySnapshot] = field(default_factory=list)
    throughput_rps: float | None = None
    total_requests: int = 0
    failed_requests: int = 0
    errors: list[str] = field(default_factory=list)
    
    @property
    def avg_latency(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0.0
    
    @property
    def p50_latency(self) -> float:
        return statistics.median(self.latencies) if self.latencies else 0.0
    
    @property
    def p95_latency(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(0.95 * len(sorted_latencies))
        return sorted_latencies[idx] if idx < len(sorted_latencies) else sorted_latencies[-1]
    
    @property
    def p99_latency(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(0.99 * len(sorted_latencies))
        return sorted_latencies[idx] if idx < len(sorted_latencies) else sorted_latencies[-1]
    
    @property
    def max_latency(self) -> float:
        return max(self.latencies) if self.latencies else 0.0
    
    @property
    def min_latency(self) -> float:
        return min(self.latencies) if self.latencies else 0.0
    
    @property
    def total_tokens(self) -> int:
        return sum(t.total_tokens for t in self.token_usage)
    
    @property
    def avg_tokens_per_request(self) -> float:
        if not self.token_usage:
            return 0.0
        return self.total_tokens / len(self.token_usage)
    
    @property
    def total_cost(self) -> float:
        return sum(c.total_cost for c in self.costs)
    
    @property
    def avg_cost_per_request(self) -> float:
        if not self.costs:
            return 0.0
        return self.total_cost / len(self.costs)
    
    @property
    def avg_memory_mb(self) -> float:
        if not self.memory_snapshots:
            return 0.0
        return statistics.mean(s.rss_mb for s in self.memory_snapshots)
    
    @property
    def max_memory_mb(self) -> float:
        if not self.memory_snapshots:
            return 0.0
        return max(s.rss_mb for s in self.memory_snapshots)
    
    @property
    def memory_leak_detected(self) -> bool:
        """Detect potential memory leaks by comparing early vs late memory usage."""
        if len(self.memory_snapshots) < 10:
            return False
        
        # Compare first 10% vs last 10%
        split = len(self.memory_snapshots) // 10
        if split < 2:
            return False
        
        early = statistics.mean(s.rss_mb for s in self.memory_snapshots[:split])
        late = statistics.mean(s.rss_mb for s in self.memory_snapshots[-split:])
        
        # Flag as leak if memory grows by >20%
        growth = (late - early) / early if early > 0 else 0
        return growth > 0.20
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.total_requests - self.failed_requests) / self.total_requests


# Pricing per 1M tokens (approximate OpenAI pricing as default)
DEFAULT_PRICING = {
    "gpt-4": {"prompt": 30.0, "completion": 60.0},
    "gpt-4-turbo": {"prompt": 10.0, "completion": 30.0},
    "gpt-3.5-turbo": {"prompt": 0.5, "completion": 1.5},
    "claude-3-opus": {"prompt": 15.0, "completion": 75.0},
    "claude-3-sonnet": {"prompt": 3.0, "completion": 15.0},
    "claude-3-haiku": {"prompt": 0.25, "completion": 1.25},
    "gemini-pro": {"prompt": 0.5, "completion": 1.5},
}


def estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars ≈ 1 token)."""
    return len(text) // 4


def extract_token_usage(llm_calls: list[LLMCallRecord]) -> TokenUsage:
    """Extract token usage from LLM call records."""
    total_prompt = 0
    total_completion = 0
    
    for call in llm_calls:
        # Try to extract from request/response metadata
        request = call.request
        response = call.response
        
        # Estimate if not provided
        prompt_text = str(request.get("messages", ""))
        completion_text = response.text or ""
        
        prompt_tokens = estimate_tokens(prompt_text)
        completion_tokens = estimate_tokens(completion_text)
        
        total_prompt += prompt_tokens
        total_completion += completion_tokens
    
    return TokenUsage(
        prompt_tokens=total_prompt,
        completion_tokens=total_completion,
        total_tokens=total_prompt + total_completion,
    )


def estimate_cost(
    token_usage: TokenUsage,
    model: str = "gpt-3.5-turbo",
    custom_pricing: dict[str, dict[str, float]] | None = None,
) -> CostEstimate:
    """Estimate cost based on token usage and model pricing."""
    pricing = custom_pricing or DEFAULT_PRICING
    
    # Find matching pricing
    model_lower = model.lower()
    model_pricing = None
    for key, value in pricing.items():
        if key.lower() in model_lower:
            model_pricing = value
            break
    
    if model_pricing is None:
        # Default to cheapest pricing if unknown
        model_pricing = pricing.get("gpt-3.5-turbo", {"prompt": 0.5, "completion": 1.5})
    
    prompt_cost = (token_usage.prompt_tokens / 1_000_000) * model_pricing["prompt"]
    completion_cost = (token_usage.completion_tokens / 1_000_000) * model_pricing["completion"]
    
    return CostEstimate(
        prompt_cost=prompt_cost,
        completion_cost=completion_cost,
        total_cost=prompt_cost + completion_cost,
    )


def capture_memory_snapshot() -> MemorySnapshot:
    """Capture current memory usage."""
    process = psutil.Process()
    mem = process.memory_info()
    return MemorySnapshot(
        rss_mb=mem.rss / 1024 / 1024,
        vms_mb=mem.vms / 1024 / 1024,
        percent=process.memory_percent(),
        timestamp=time.time(),
    )


# Context variable to store current performance context
_perf_context: contextvars.ContextVar[PerformanceMetrics | None] = contextvars.ContextVar(
    "senytl_performance_context", default=None
)


def get_current_metrics() -> PerformanceMetrics | None:
    """Get current performance metrics context."""
    return _perf_context.get()


def set_current_metrics(metrics: PerformanceMetrics | None) -> None:
    """Set current performance metrics context."""
    _perf_context.set(metrics)


def record_request(
    latency: float,
    response: SenytlResponse | None = None,
    error: Exception | None = None,
) -> None:
    """Record a request's performance metrics."""
    metrics = get_current_metrics()
    if metrics is None:
        return
    
    metrics.total_requests += 1
    metrics.latencies.append(latency)
    
    if error:
        metrics.failed_requests += 1
        metrics.errors.append(str(error))
    
    if response and response.llm_calls:
        token_usage = extract_token_usage(response.llm_calls)
        metrics.token_usage.append(token_usage)
        
        # Estimate cost from first model seen
        model = response.llm_calls[0].model if response.llm_calls else "gpt-3.5-turbo"
        cost = estimate_cost(token_usage, model)
        metrics.costs.append(cost)
    
    # Capture memory snapshot
    metrics.memory_snapshots.append(capture_memory_snapshot())


def benchmark(fn: F) -> F:
    """
    Decorator to benchmark a test function's performance.
    
    Records latency, token usage, cost, and memory metrics.
    
    Example:
        @performance.benchmark
        def test_agent():
            response = agent.run("Hello")
            performance.assert_latency_under(seconds=2)
    """
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        metrics = PerformanceMetrics()
        set_current_metrics(metrics)
        
        try:
            result = fn(*args, **kwargs)
            return result
        finally:
            # Store metrics for reporting
            if not hasattr(wrapper, "_performance_metrics"):
                wrapper._performance_metrics = []  # type: ignore[attr-defined]
            wrapper._performance_metrics.append(metrics)  # type: ignore[attr-defined]
            set_current_metrics(None)
    
    return wrapper  # type: ignore[return-value]


def load_test(
    concurrent_users: int = 10,
    duration: int | None = None,
    iterations: int | None = None,
    ramp_up: float = 0,
) -> Callable[[F], F]:
    """
    Decorator for load testing with concurrent users.
    
    Args:
        concurrent_users: Number of concurrent threads/users
        duration: Test duration in seconds (mutually exclusive with iterations)
        iterations: Number of iterations per user (mutually exclusive with duration)
        ramp_up: Ramp-up time in seconds to gradually start users
        
    Example:
        @performance.load_test(concurrent_users=100, duration=60)
        def test_agent_load():
            response = agent.run("Query")
            performance.assert_throughput_above(requests_per_second=50)
    """
    if duration is None and iterations is None:
        iterations = 1
    
    if duration is not None and iterations is not None:
        raise ValueError("Cannot specify both duration and iterations")
    
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            metrics = PerformanceMetrics()
            metrics_lock = threading.Lock()
            set_current_metrics(metrics)
            
            start_time = time.time()
            stop_flag = threading.Event()
            
            def record_request_safe(latency: float, error: Exception | None = None) -> None:
                """Thread-safe request recording."""
                with metrics_lock:
                    metrics.total_requests += 1
                    metrics.latencies.append(latency)
                    
                    if error:
                        metrics.failed_requests += 1
                        metrics.errors.append(str(error))
                    
                    # Capture memory snapshot
                    metrics.memory_snapshots.append(capture_memory_snapshot())
            
            def run_user(user_id: int) -> None:
                """Run test for a single user."""
                # Ramp-up delay
                if ramp_up > 0:
                    delay = (user_id / concurrent_users) * ramp_up
                    time.sleep(delay)
                
                iter_count = 0
                while True:
                    if stop_flag.is_set():
                        break
                    
                    if duration is None and iterations is not None:
                        if iter_count >= iterations:
                            break
                    elif duration is not None:
                        if time.time() - start_time >= duration:
                            stop_flag.set()
                            break
                    
                    request_start = time.time()
                    try:
                        fn(*args, **kwargs)
                        request_end = time.time()
                        record_request_safe(request_end - request_start)
                    except Exception as e:
                        request_end = time.time()
                        record_request_safe(request_end - request_start, error=e)
                    
                    iter_count += 1
            
            # Run load test with thread pool
            with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = [executor.submit(run_user, i) for i in range(concurrent_users)]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception:
                        pass
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            # Calculate throughput
            if metrics.total_requests > 0:
                metrics.throughput_rps = metrics.total_requests / total_duration
            
            # Store metrics for reporting
            if not hasattr(wrapper, "_performance_metrics"):
                wrapper._performance_metrics = []  # type: ignore[attr-defined]
            wrapper._performance_metrics.append(metrics)  # type: ignore[attr-defined]
            
            set_current_metrics(None)
            return metrics
        
        return wrapper  # type: ignore[return-value]
    
    return decorator


# SLA Assertion Functions

def assert_latency_under(seconds: float, percentile: str = "avg") -> None:
    """
    Assert that latency is under the specified threshold.
    
    Args:
        seconds: Maximum allowed latency in seconds
        percentile: Which percentile to check (avg, p50, p95, p99, max)
    """
    metrics = get_current_metrics()
    if metrics is None:
        raise PerformanceError("No performance context active. Use @performance.benchmark decorator.")
    
    if not metrics.latencies:
        raise PerformanceError("No latency data recorded yet.")
    
    if percentile == "avg":
        actual = metrics.avg_latency
    elif percentile == "p50":
        actual = metrics.p50_latency
    elif percentile == "p95":
        actual = metrics.p95_latency
    elif percentile == "p99":
        actual = metrics.p99_latency
    elif percentile == "max":
        actual = metrics.max_latency
    else:
        raise ValueError(f"Unknown percentile: {percentile}")
    
    if actual > seconds:
        raise SLAViolationError(
            f"Latency {percentile} exceeded: {actual:.3f}s > {seconds}s (SLA: {seconds}s)"
        )


def assert_token_usage_under(tokens: int, per_request: bool = True) -> None:
    """
    Assert that token usage is under the specified threshold.
    
    Args:
        tokens: Maximum allowed tokens
        per_request: If True, check per-request average; if False, check total
    """
    metrics = get_current_metrics()
    if metrics is None:
        raise PerformanceError("No performance context active. Use @performance.benchmark decorator.")
    
    if not metrics.token_usage:
        raise PerformanceError("No token usage data recorded yet.")
    
    if per_request:
        actual = metrics.avg_tokens_per_request
        if actual > tokens:
            raise SLAViolationError(
                f"Token usage per request exceeded: {actual:.0f} > {tokens} (SLA: {tokens} tokens/request)"
            )
    else:
        actual = metrics.total_tokens
        if actual > tokens:
            raise SLAViolationError(
                f"Total token usage exceeded: {actual} > {tokens} (SLA: {tokens} tokens)"
            )


def assert_cost_under(cents: float, per_request: bool = True) -> None:
    """
    Assert that cost is under the specified threshold.
    
    Args:
        cents: Maximum allowed cost in cents (0.01 dollars)
        per_request: If True, check per-request average; if False, check total
    """
    metrics = get_current_metrics()
    if metrics is None:
        raise PerformanceError("No performance context active. Use @performance.benchmark decorator.")
    
    if not metrics.costs:
        raise PerformanceError("No cost data recorded yet.")
    
    dollars = cents / 100.0
    
    if per_request:
        actual = metrics.avg_cost_per_request
        if actual > dollars:
            raise SLAViolationError(
                f"Cost per request exceeded: ${actual:.4f} > ${dollars:.4f} (SLA: {cents}¢/request)"
            )
    else:
        actual = metrics.total_cost
        if actual > dollars:
            raise SLAViolationError(
                f"Total cost exceeded: ${actual:.4f} > ${dollars:.4f} (SLA: {cents}¢)"
            )


def assert_throughput_above(requests_per_second: float) -> None:
    """
    Assert that throughput is above the specified threshold.
    
    Args:
        requests_per_second: Minimum required throughput (RPS)
    """
    metrics = get_current_metrics()
    if metrics is None:
        raise PerformanceError("No performance context active. Use @performance.load_test decorator.")
    
    if metrics.throughput_rps is None:
        raise PerformanceError("No throughput data recorded. Use @performance.load_test decorator.")
    
    if metrics.throughput_rps < requests_per_second:
        raise SLAViolationError(
            f"Throughput below SLA: {metrics.throughput_rps:.2f} req/s < {requests_per_second} req/s"
        )


def assert_p95_latency_under(seconds: float) -> None:
    """Assert that P95 latency is under the specified threshold."""
    assert_latency_under(seconds, percentile="p95")


def assert_p99_latency_under(seconds: float) -> None:
    """Assert that P99 latency is under the specified threshold."""
    assert_latency_under(seconds, percentile="p99")


def assert_no_memory_leaks(threshold: float = 0.20) -> None:
    """
    Assert that no memory leaks are detected.
    
    Args:
        threshold: Maximum allowed memory growth ratio (default 20%)
    """
    metrics = get_current_metrics()
    if metrics is None:
        raise PerformanceError("No performance context active. Use @performance.load_test decorator.")
    
    if metrics.memory_leak_detected:
        raise SLAViolationError(
            f"Memory leak detected: Memory grew by >{threshold*100:.0f}% during test. "
            f"Average memory: {metrics.avg_memory_mb:.1f} MB, Peak: {metrics.max_memory_mb:.1f} MB"
        )


def generate_report(
    metrics: PerformanceMetrics | None = None,
    output_path: Path | str | None = None,
    format: str = "text",
) -> str:
    """
    Generate a performance report.
    
    Args:
        metrics: Performance metrics to report (uses current context if None)
        output_path: Optional path to write report to file
        format: Report format (text, json, markdown)
        
    Returns:
        Report string
    """
    if metrics is None:
        metrics = get_current_metrics()
        if metrics is None:
            raise PerformanceError("No performance metrics available.")
    
    if format == "text":
        report = _generate_text_report(metrics)
    elif format == "json":
        import json
        report = json.dumps({
            "latencies": {
                "avg": metrics.avg_latency,
                "p50": metrics.p50_latency,
                "p95": metrics.p95_latency,
                "p99": metrics.p99_latency,
                "max": metrics.max_latency,
                "min": metrics.min_latency,
            },
            "tokens": {
                "total": metrics.total_tokens,
                "avg_per_request": metrics.avg_tokens_per_request,
            },
            "cost": {
                "total": metrics.total_cost,
                "avg_per_request": metrics.avg_cost_per_request,
            },
            "throughput_rps": metrics.throughput_rps,
            "memory": {
                "avg_mb": metrics.avg_memory_mb,
                "max_mb": metrics.max_memory_mb,
                "leak_detected": metrics.memory_leak_detected,
            },
            "requests": {
                "total": metrics.total_requests,
                "failed": metrics.failed_requests,
                "success_rate": metrics.success_rate,
            },
        }, indent=2)
    elif format == "markdown":
        report = _generate_markdown_report(metrics)
    else:
        raise ValueError(f"Unknown format: {format}")
    
    if output_path:
        Path(output_path).write_text(report)
    
    return report


def _generate_text_report(metrics: PerformanceMetrics) -> str:
    """Generate human-readable text report."""
    lines = [
        "Performance Report",
        "─" * 50,
    ]
    
    # Latency
    lines.append(f"Avg Latency:     {metrics.avg_latency:.3f}s")
    lines.append(f"P50 Latency:     {metrics.p50_latency:.3f}s")
    lines.append(f"P95 Latency:     {metrics.p95_latency:.3f}s")
    lines.append(f"P99 Latency:     {metrics.p99_latency:.3f}s")
    lines.append(f"Max Latency:     {metrics.max_latency:.3f}s")
    lines.append("")
    
    # Tokens
    if metrics.token_usage:
        lines.append(f"Token Usage:     {metrics.avg_tokens_per_request:.0f} tokens/request")
        lines.append(f"Total Tokens:    {metrics.total_tokens}")
        lines.append("")
    
    # Cost
    if metrics.costs:
        lines.append(f"Cost:            ${metrics.avg_cost_per_request:.4f}/request")
        lines.append(f"Total Cost:      ${metrics.total_cost:.4f}")
        lines.append("")
    
    # Throughput
    if metrics.throughput_rps is not None:
        lines.append(f"Throughput:      {metrics.throughput_rps:.2f} req/s")
        lines.append("")
    
    # Memory
    if metrics.memory_snapshots:
        leak_status = "⚠️  LEAK DETECTED" if metrics.memory_leak_detected else "✓ stable"
        lines.append(f"Memory:          {metrics.avg_memory_mb:.1f} MB avg ({leak_status})")
        lines.append(f"Peak Memory:     {metrics.max_memory_mb:.1f} MB")
        lines.append("")
    
    # Success rate
    lines.append(f"Success Rate:    {metrics.success_rate*100:.1f}% ({metrics.total_requests - metrics.failed_requests}/{metrics.total_requests})")
    
    if metrics.errors:
        lines.append("")
        lines.append(f"Errors: {len(metrics.errors)}")
        for i, error in enumerate(metrics.errors[:5], 1):
            lines.append(f"  {i}. {error}")
        if len(metrics.errors) > 5:
            lines.append(f"  ... and {len(metrics.errors) - 5} more")
    
    return "\n".join(lines)


def _generate_markdown_report(metrics: PerformanceMetrics) -> str:
    """Generate Markdown report."""
    lines = [
        "# Performance Report",
        "",
        "## Latency",
        "",
        f"- **Average**: {metrics.avg_latency:.3f}s",
        f"- **P50**: {metrics.p50_latency:.3f}s",
        f"- **P95**: {metrics.p95_latency:.3f}s",
        f"- **P99**: {metrics.p99_latency:.3f}s",
        f"- **Max**: {metrics.max_latency:.3f}s",
        "",
    ]
    
    if metrics.token_usage:
        lines.extend([
            "## Token Usage",
            "",
            f"- **Per Request**: {metrics.avg_tokens_per_request:.0f} tokens",
            f"- **Total**: {metrics.total_tokens} tokens",
            "",
        ])
    
    if metrics.costs:
        lines.extend([
            "## Cost",
            "",
            f"- **Per Request**: ${metrics.avg_cost_per_request:.4f}",
            f"- **Total**: ${metrics.total_cost:.4f}",
            "",
        ])
    
    if metrics.throughput_rps is not None:
        lines.extend([
            "## Throughput",
            "",
            f"- **Requests/sec**: {metrics.throughput_rps:.2f}",
            "",
        ])
    
    if metrics.memory_snapshots:
        leak = "⚠️ Leak Detected" if metrics.memory_leak_detected else "✓ Stable"
        lines.extend([
            "## Memory",
            "",
            f"- **Average**: {metrics.avg_memory_mb:.1f} MB",
            f"- **Peak**: {metrics.max_memory_mb:.1f} MB",
            f"- **Status**: {leak}",
            "",
        ])
    
    lines.extend([
        "## Summary",
        "",
        f"- **Total Requests**: {metrics.total_requests}",
        f"- **Failed**: {metrics.failed_requests}",
        f"- **Success Rate**: {metrics.success_rate*100:.1f}%",
    ])
    
    return "\n".join(lines)


__all__ = [
    "benchmark",
    "load_test",
    "assert_latency_under",
    "assert_token_usage_under",
    "assert_cost_under",
    "assert_throughput_above",
    "assert_p95_latency_under",
    "assert_p99_latency_under",
    "assert_no_memory_leaks",
    "generate_report",
    "record_request",
    "get_current_metrics",
    "PerformanceMetrics",
    "TokenUsage",
    "CostEstimate",
    "MemorySnapshot",
    "PerformanceError",
    "SLAViolationError",
]
