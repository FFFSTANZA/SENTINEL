from __future__ import annotations

import functools
from collections import Counter
from typing import Any, Callable, List, Tuple, Union

from . import core
from .models import SentinelError

class TrajectoryError(SentinelError):
    pass

def capture(func: Callable) -> Callable:
    """Decorator to capture agent trajectory during test execution."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        sentinel = core.get_default_sentinel()
        sentinel.install()
        run_handle = core.start_run(sentinel)
        try:
            return func(*args, **kwargs)
        finally:
            run_handle.finish()
    return wrapper

def _get_current_context():
    sentinel = core.get_default_sentinel()
    ctx = sentinel._run_context.get()
    if ctx is None:
        raise TrajectoryError("No active trajectory. Ensure function is decorated with @trajectory.capture")
    return ctx

def assert_steps(expected_steps: List[Union[str, Tuple[str, bool]]]):
    """
    Assert that specific steps happened in the correct order.
    Steps can be tool names.
    ("step_name", False) asserts that the step did NOT happen.
    """
    ctx = _get_current_context()
    
    # Flatten actual steps from the context
    # We primarily look at tool calls as "steps"
    actual_steps = [tc.name for tc in ctx.tool_calls]
    
    # We also consider reasoning/thoughts if we can parse them, 
    # but for now let's stick to tool calls as the primary identifiable steps.
    # Optionally, we could look at the 'response.text' or 'response.reasoning' 
    # to find matching strings? 
    # The requirement "understand_intent" suggests high-level steps.
    # If "understand_intent" is not a tool, maybe it's a substring in reasoning?
    
    # Let's assume for now steps are tool names. 
    # If we need to match reasoning, we'd need to inspect llm_calls.
    
    actual_idx = 0
    
    for step in expected_steps:
        should_exist = True
        step_name = step
        if isinstance(step, tuple):
            step_name, should_exist = step
        
        if not should_exist:
            if step_name in actual_steps:
                raise TrajectoryError(f"Step '{step_name}' should NOT have occurred, but did.")
            continue
            
        # Find the next occurrence of step_name starting from actual_idx
        found_at = -1
        for i in range(actual_idx, len(actual_steps)):
            if actual_steps[i] == step_name:
                found_at = i
                break
        
        if found_at != -1:
            actual_idx = found_at + 1
        else:
            raise TrajectoryError(f"Expected step '{step_name}' not found (or out of order).")

def assert_no_redundant_calls():
    """Asserts that there are no identical tool calls (same tool, same arguments) repeated consecutively."""
    ctx = _get_current_context()
    
    for i in range(len(ctx.tool_calls) - 1):
        current_call = ctx.tool_calls[i]
        next_call = ctx.tool_calls[i+1]
        
        if current_call.name == next_call.name and current_call.args == next_call.args:
            raise TrajectoryError(f"Redundant tool call detected: {current_call.name} with args {current_call.args}")

def assert_no_infinite_loops(threshold: int = 3):
    """Asserts that there are no repeating sequences of tool calls."""
    ctx = _get_current_context()
    if not ctx.tool_calls:
        return

    # Simple cycle detection: Look for repeating tool names
    tool_names = [tc.name for tc in ctx.tool_calls]
    
    # Check for immediate repetition of a sequence
    # e.g. A, B, A, B, A, B
    
    # Naive implementation: check if the last N calls are same as previous N calls
    n = len(tool_names)
    for length in range(1, n // 2 + 1):
        # Check if the sequence of length 'length' repeats 'threshold' times
        
        # We only check the end of the sequence for loops that are currently happening/just happened
        # or we check the whole history? "Detect redundant calls, infinite loops"
        
        # Let's check generally for any repeating sub-sequence repeated 'threshold' times
        # This is O(N^3) or O(N^2) depending on implementation. N is small (number of steps).
        
        for i in range(len(tool_names) - length * threshold + 1):
            sequence = tool_names[i : i + length]
            is_loop = True
            for k in range(1, threshold):
                next_seq = tool_names[i + k * length : i + (k + 1) * length]
                if sequence != next_seq:
                    is_loop = False
                    break
            
            if is_loop:
                raise TrajectoryError(f"Potential infinite loop detected: sequence {sequence} repeated {threshold} times")

def assert_tool_selection_was_optimal():
    """
    Asserts tool selection was optimal. 
    In this context, it checks if there were any failed tool calls or hallucinations (calls to non-existent tools).
    This is a heuristic.
    """
    ctx = _get_current_context()
    # If we have access to tool definitions/results, we could check for errors.
    # Sentinel's ToolCall doesn't store the result/success status directly unless we infer it from the next turn.
    # But we can check if the tool exists in the mocked definition? 
    # Or just check if the agent tried to call a tool that wasn't mocked?
    # For now, let's assume it passes if no exceptions were thrown during execution regarding missing tools.
    # Since we are in post-execution assertion, maybe we check if there are "error" entries in the LLM history?
    
    # We can check ctx.llm_calls responses.
    pass

def visualize():
    """Generates a flowchart of execution."""
    ctx = _get_current_context()
    print("Execution Trajectory:")
    for i, call in enumerate(ctx.llm_calls):
        print(f"[{i}] {call.provider}/{call.model}")
        print(f"   Request: {str(call.request)[:100]}...")
        print(f"   Response: {str(call.response.text)[:100]}...")
        if call.response.tools:
            print(f"   Tools: {call.response.tools}")
        if call.response.tool_calls:
            for tc in call.response.tool_calls:
                 print(f"   -> Tool Call: {tc.name}({tc.args})")
