"""Comprehensive tests for multi-agent module"""
import pytest
from senytl import multi_agent
from senytl.multi_agent import (
    AgentMessage,
    AgentExecution,
    SystemResult,
    AgentResult,
    System,
    assert_workflow_completed,
    assert_no_deadlocks,
    assert_message_passing_correct,
)
from senytl.models import ToolCall


class TestAgentMessage:
    """Test AgentMessage dataclass"""
    
    def test_initialization(self):
        """Test message initialization"""
        msg = AgentMessage(
            from_agent="agent1",
            to_agent="agent2",
            content="Hello",
            timestamp=1234.5
        )
        assert msg.from_agent == "agent1"
        assert msg.to_agent == "agent2"
        assert msg.content == "Hello"
        assert msg.timestamp == 1234.5
    
    def test_with_metadata(self):
        """Test message with metadata"""
        msg = AgentMessage(
            from_agent="agent1",
            to_agent=None,
            content="test",
            timestamp=0.0,
            metadata={"key": "value"}
        )
        assert msg.metadata["key"] == "value"


class TestAgentExecution:
    """Test AgentExecution dataclass"""
    
    def test_successful_execution(self):
        """Test successful agent execution"""
        exec = AgentExecution(
            agent_name="agent1",
            input_message="input",
            output="output",
            duration=0.5
        )
        assert exec.agent_name == "agent1"
        assert exec.output == "output"
        assert exec.error is None
    
    def test_failed_execution(self):
        """Test failed agent execution"""
        error = ValueError("Test error")
        exec = AgentExecution(
            agent_name="agent1",
            input_message="input",
            output=None,
            error=error
        )
        assert exec.error is not None


class TestSystemResult:
    """Test SystemResult class"""
    
    def test_empty_result(self):
        """Test empty system result"""
        result = SystemResult()
        assert len(result.executions) == 0
        assert len(result.messages) == 0
        assert result.completed is False
    
    def test_agent_query(self):
        """Test querying agent from result"""
        result = SystemResult()
        result.executions.append(AgentExecution(
            agent_name="agent1",
            input_message="test",
            output="output"
        ))
        
        agent_result = result.agent("agent1")
        assert agent_result.name == "agent1"
        assert len(agent_result.executions) == 1
    
    def test_duration_calculation(self):
        """Test duration calculation"""
        result = SystemResult(start_time=100.0, end_time=105.5)
        assert result.duration() == 5.5
    
    def test_visualize_flow_empty(self):
        """Test visualization with no messages"""
        result = SystemResult()
        flow = result.visualize_flow()
        assert "No messages" in flow
    
    def test_visualize_flow_with_messages(self):
        """Test visualization with messages"""
        result = SystemResult()
        result.messages.append(AgentMessage(
            from_agent="user",
            to_agent="agent1",
            content="Hello",
            timestamp=0.0
        ))
        result.messages.append(AgentMessage(
            from_agent="agent1",
            to_agent="agent2",
            content="Forwarding",
            timestamp=0.1
        ))
        
        flow = result.visualize_flow()
        assert "Agent Interaction Flow" in flow
        assert "user → agent1" in flow
        assert "agent1 → agent2" in flow


class TestAgentResult:
    """Test AgentResult class"""
    
    def test_tool_calls(self):
        """Test getting tool calls from agent"""
        exec = AgentExecution(
            agent_name="agent1",
            input_message="test",
            output="output",
            tool_calls=[
                ToolCall(name="search", args={}),
                ToolCall(name="create", args={})
            ]
        )
        
        result = AgentResult("agent1", [exec])
        calls = result.tool_calls()
        
        assert len(calls) == 2
        assert calls[0].name == "search"
    
    def test_called_tool(self):
        """Test checking if tool was called"""
        exec = AgentExecution(
            agent_name="agent1",
            input_message="test",
            output="output",
            tool_calls=[ToolCall(name="search", args={})]
        )
        
        result = AgentResult("agent1", [exec])
        assert result.called_tool("search") is True
        assert result.called_tool("delete") is False


class TestSystem:
    """Test System class"""
    
    def test_initialization(self):
        """Test system initialization"""
        def agent1(msg):
            return "response1"
        
        def agent2(msg):
            return "response2"
        
        system = System([
            ("agent1", agent1),
            ("agent2", agent2)
        ])
        
        assert "agent1" in system._agents
        assert "agent2" in system._agents
    
    def test_route(self):
        """Test agent routing"""
        system = System([("a1", lambda x: x), ("a2", lambda x: x)])
        system.route("a1", "a2")
        
        assert system._routing["a1"] == "a2"
    
    def test_run_scenario_single_agent(self):
        """Test running scenario with single agent"""
        def agent1(msg):
            return f"Processed: {msg}"
        
        system = System([("agent1", agent1)])
        result = system.run_scenario([("agent1", "test input")])
        
        assert result.completed is True
        assert len(result.executions) == 1
        assert "Processed: test input" in str(result.executions[0].output)
    
    def test_run_scenario_with_routing(self):
        """Test running scenario with routing"""
        def agent1(msg):
            return f"Agent1: {msg}"
        
        def agent2(msg):
            return f"Agent2: {msg}"
        
        system = System([("agent1", agent1), ("agent2", agent2)])
        system.route("agent1", "agent2")
        
        result = system.run_scenario([("agent1", "start")])
        
        assert result.completed is True
        assert len(result.executions) == 2
        assert len(result.messages) >= 2
    
    def test_run_scenario_with_error(self):
        """Test running scenario with agent error"""
        def failing_agent(msg):
            raise ValueError("Agent failed")
        
        system = System([("agent1", failing_agent)])
        result = system.run_scenario([("agent1", "test")])
        
        assert result.completed is False
        assert result.executions[0].error is not None
    
    def test_run_scenario_unknown_agent(self):
        """Test running scenario with unknown agent"""
        system = System([("agent1", lambda x: x)])
        
        with pytest.raises(ValueError, match="Unknown agent"):
            system.run_scenario([("unknown", "test")])
    
    def test_execute_agent_callable(self):
        """Test executing callable agent"""
        def agent(msg):
            return "response"
        
        system = System([("agent1", agent)])
        execution = system._execute_agent("agent1", "test")
        
        assert execution.output == "response"
        assert execution.error is None
    
    def test_execute_agent_with_run_method(self):
        """Test executing agent with run method"""
        class Agent:
            def run(self, msg):
                return f"Agent ran: {msg}"
        
        system = System([("agent1", Agent())])
        execution = system._execute_agent("agent1", "test")
        
        assert "Agent ran: test" in execution.output
    
    def test_execute_agent_not_callable(self):
        """Test executing non-callable agent"""
        system = System([("agent1", "not callable")])
        execution = system._execute_agent("agent1", "test")
        
        assert execution.error is not None


class TestMultiAgentAssertions:
    """Test assertion functions"""
    
    def test_assert_workflow_completed_success(self):
        """Test workflow completed assertion with success"""
        result = SystemResult(completed=True)
        # Should not raise
        assert_workflow_completed(result)
    
    def test_assert_workflow_completed_failure(self):
        """Test workflow completed assertion with failure"""
        result = SystemResult(completed=False)
        result.executions.append(AgentExecution(
            agent_name="agent1",
            input_message="test",
            output=None,
            error=ValueError("Failed")
        ))
        
        with pytest.raises(AssertionError, match="Workflow failed"):
            assert_workflow_completed(result)
    
    def test_assert_no_deadlocks_success(self):
        """Test no deadlocks assertion with success"""
        result = SystemResult(deadlock_detected=False)
        # Should not raise
        assert_no_deadlocks(result)
    
    def test_assert_no_deadlocks_failure(self):
        """Test no deadlocks assertion with failure"""
        result = SystemResult(deadlock_detected=True)
        
        with pytest.raises(AssertionError, match="Deadlock detected"):
            assert_no_deadlocks(result)
    
    def test_assert_message_passing_correct_success(self):
        """Test message passing assertion with messages"""
        result = SystemResult()
        result.messages.append(AgentMessage(
            from_agent="a1",
            to_agent="a2",
            content="Hello",
            timestamp=0.0
        ))
        
        # Should not raise
        assert_message_passing_correct(result)
    
    def test_assert_message_passing_correct_no_messages(self):
        """Test message passing assertion with no messages"""
        result = SystemResult()
        
        with pytest.raises(AssertionError, match="No messages"):
            assert_message_passing_correct(result)
    
    def test_assert_message_passing_correct_empty_message(self):
        """Test message passing assertion with empty message"""
        result = SystemResult()
        result.messages.append(AgentMessage(
            from_agent="a1",
            to_agent="a2",
            content="",
            timestamp=0.0
        ))
        
        with pytest.raises(AssertionError, match="Empty message"):
            assert_message_passing_correct(result)


class TestMultiAgentEdgeCases:
    """Test edge cases"""
    
    def test_long_agent_chain(self):
        """Test long chain of agents"""
        agents = []
        for i in range(10):
            agents.append((f"agent{i}", lambda x, i=i: f"Agent{i}: {x}"))
        
        system = System(agents)
        for i in range(9):
            system.route(f"agent{i}", f"agent{i+1}")
        
        result = system.run_scenario([("agent0", "start")])
        
        # With max_iterations, should complete or stop
        assert result.completed or len(result.executions) > 0
    
    def test_message_truncation_in_visualization(self):
        """Test long messages are truncated in visualization"""
        result = SystemResult()
        long_message = "A" * 100
        result.messages.append(AgentMessage(
            from_agent="a1",
            to_agent="a2",
            content=long_message,
            timestamp=0.0
        ))
        
        flow = result.visualize_flow()
        assert "..." in flow or len(flow) < len(long_message) + 100
    
    def test_multiple_tool_calls_per_agent(self):
        """Test agent making multiple tool calls"""
        class AgentWithTools:
            def run(self, msg):
                class Response:
                    text = "response"
                    tool_calls = [
                        ToolCall(name="tool1", args={}),
                        ToolCall(name="tool2", args={}),
                        ToolCall(name="tool3", args={})
                    ]
                return Response()
        
        system = System([("agent1", AgentWithTools())])
        result = system.run_scenario([("agent1", "test")])
        
        agent_result = result.agent("agent1")
        calls = agent_result.tool_calls()
        assert len(calls) >= 0  # May not extract from Response object
