import pytest
from sentinel import trajectory, Sentinel
from sentinel.models import ToolCall

def test_trajectory_capture_and_assert():
    sentinel = Sentinel()
    
    # Mocking the global sentinel for the test
    import sentinel.core as core_module
    original_get = core_module.get_default_sentinel
    core_module.get_default_sentinel = lambda: sentinel
    
    try:
        @trajectory.capture
        def run_agent():
            # Simulate agent execution by manually adding to context
            # In a real scenario, the agent would trigger LLM calls which Sentinel intercepts
            # Here we manually invoke the mechanism or rely on Sentinel.mock
            
            # Let's use the mock engine to simulate calls
            sentinel.mock("gpt-4").when(contains="step 1").respond(tools=["tool_a"], tool_calls=[{"name": "tool_a", "args": {}}])
            sentinel.mock("gpt-4").when(contains="step 2").respond(tools=["tool_b"], tool_calls=[{"name": "tool_b", "args": {}}])
            
            # Simulate calls
            # We need to manually trigger the handle_call or use a wrapped agent.
            # Let's just manually append to the context for this unit test if possible,
            # but the context is hidden.
            # So we should use the engine.
            
            sentinel._handle_call(provider="openai", model="gpt-4", request={"messages": [{"role": "user", "content": "step 1"}]})
            sentinel._handle_call(provider="openai", model="gpt-4", request={"messages": [{"role": "user", "content": "step 2"}]})
            
            trajectory.assert_steps(["tool_a", "tool_b"])
            trajectory.assert_steps(["tool_a", ("tool_c", False)])
            
            with pytest.raises(trajectory.TrajectoryError):
                trajectory.assert_steps(["tool_b", "tool_a"]) # Wrong order
            
        run_agent()
    finally:
        core_module.get_default_sentinel = original_get

def test_redundant_calls():
    sentinel = Sentinel()
    import sentinel.core as core_module
    original_get = core_module.get_default_sentinel
    core_module.get_default_sentinel = lambda: sentinel
    
    try:
        @trajectory.capture
        def run_redundant():
            sentinel.mock("gpt-4").when(contains="repeat").respond(tool_calls=[{"name": "tool_a", "args": {"x": 1}}])
            
            sentinel._handle_call(provider="openai", model="gpt-4", request={"messages": [{"role": "user", "content": "repeat"}]})
            sentinel._handle_call(provider="openai", model="gpt-4", request={"messages": [{"role": "user", "content": "repeat"}]})
            
            with pytest.raises(trajectory.TrajectoryError, match="Redundant tool call"):
                trajectory.assert_no_redundant_calls()
                
        run_redundant()
    finally:
        core_module.get_default_sentinel = original_get

def test_infinite_loop():
    sentinel = Sentinel()
    import sentinel.core as core_module
    original_get = core_module.get_default_sentinel
    core_module.get_default_sentinel = lambda: sentinel
    
    try:
        @trajectory.capture
        def run_loop():
            sentinel.mock("gpt-4").when(contains="A").respond(tool_calls=[{"name": "A", "args": {}}])
            sentinel.mock("gpt-4").when(contains="B").respond(tool_calls=[{"name": "B", "args": {}}])

            # A, B, A, B, A, B
            for _ in range(3):
                sentinel._handle_call(provider="openai", model="gpt-4", request={"messages": [{"role": "user", "content": "A"}]})
                sentinel._handle_call(provider="openai", model="gpt-4", request={"messages": [{"role": "user", "content": "B"}]})
                
            with pytest.raises(trajectory.TrajectoryError, match="infinite loop"):
                trajectory.assert_no_infinite_loops(threshold=3)
                
        run_loop()
    finally:
        core_module.get_default_sentinel = original_get
