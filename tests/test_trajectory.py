import pytest
from senytl import trajectory, Senytl
from senytl.models import ToolCall

def test_trajectory_capture_and_assert():
    senytl = Senytl()
    
    # Mocking the global senytl for the test
    import senytl.core as core_module
    original_get = core_module.get_default_senytl
    core_module.get_default_senytl = lambda: senytl
    
    try:
        @trajectory.capture
        def run_agent():
            # Simulate agent execution by manually adding to context
            # In a real scenario, the agent would trigger LLM calls which Senytl intercepts
            # Here we manually invoke the mechanism or rely on Senytl.mock
            
            # Let's use the mock engine to simulate calls
            senytl.mock("gpt-4").when(contains="step 1").respond(tools=["tool_a"], tool_calls=[{"name": "tool_a", "args": {}}])
            senytl.mock("gpt-4").when(contains="step 2").respond(tools=["tool_b"], tool_calls=[{"name": "tool_b", "args": {}}])
            
            # Simulate calls
            # We need to manually trigger the handle_call or use a wrapped agent.
            # Let's just manually append to the context for this unit test if possible,
            # but the context is hidden.
            # So we should use the engine.
            
            senytl._handle_call(provider="openai", model="gpt-4", request={"messages": [{"role": "user", "content": "step 1"}]})
            senytl._handle_call(provider="openai", model="gpt-4", request={"messages": [{"role": "user", "content": "step 2"}]})
            
            trajectory.assert_steps(["tool_a", "tool_b"])
            trajectory.assert_steps(["tool_a", ("tool_c", False)])
            
            with pytest.raises(trajectory.TrajectoryError):
                trajectory.assert_steps(["tool_b", "tool_a"]) # Wrong order
            
        run_agent()
    finally:
        core_module.get_default_senytl = original_get

def test_redundant_calls():
    senytl = Senytl()
    import senytl.core as core_module
    original_get = core_module.get_default_senytl
    core_module.get_default_senytl = lambda: senytl
    
    try:
        @trajectory.capture
        def run_redundant():
            senytl.mock("gpt-4").when(contains="repeat").respond(tool_calls=[{"name": "tool_a", "args": {"x": 1}}])
            
            senytl._handle_call(provider="openai", model="gpt-4", request={"messages": [{"role": "user", "content": "repeat"}]})
            senytl._handle_call(provider="openai", model="gpt-4", request={"messages": [{"role": "user", "content": "repeat"}]})
            
            with pytest.raises(trajectory.TrajectoryError, match="Redundant tool call"):
                trajectory.assert_no_redundant_calls()
                
        run_redundant()
    finally:
        core_module.get_default_senytl = original_get

def test_infinite_loop():
    senytl = Senytl()
    import senytl.core as core_module
    original_get = core_module.get_default_senytl
    core_module.get_default_senytl = lambda: senytl
    
    try:
        @trajectory.capture
        def run_loop():
            senytl.mock("gpt-4").when(contains="A").respond(tool_calls=[{"name": "A", "args": {}}])
            senytl.mock("gpt-4").when(contains="B").respond(tool_calls=[{"name": "B", "args": {}}])

            # A, B, A, B, A, B
            for _ in range(3):
                senytl._handle_call(provider="openai", model="gpt-4", request={"messages": [{"role": "user", "content": "A"}]})
                senytl._handle_call(provider="openai", model="gpt-4", request={"messages": [{"role": "user", "content": "B"}]})
                
            with pytest.raises(trajectory.TrajectoryError, match="infinite loop"):
                trajectory.assert_no_infinite_loops(threshold=3)
                
        run_loop()
    finally:
        core_module.get_default_senytl = original_get
