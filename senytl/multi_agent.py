from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple

from .assertions import expect
from .models import ToolCall


class Agent:
    """Represents an individual agent in a multi-agent system."""
    
    def __init__(self, name: str, implementation: Any):
        """Initialize an agent.
        
        Args:
            name: Unique identifier for the agent
            implementation: Callable or object that implements the agent logic
        """
        self.name = name
        self.implementation = implementation
    
    def __call__(self, input_msg: str) -> Any:
        """Make the agent callable."""
        if callable(self.implementation):
            return self.implementation(input_msg)
        elif hasattr(self.implementation, "run"):
            return self.implementation.run(input_msg)
        else:
            raise ValueError(f"Agent {self.name} implementation is not callable")
    
    def run(self, input_msg: str) -> Any:
        """Run the agent with given input."""
        return self(input_msg)


@dataclass
class AgentMessage:
    from_agent: str
    to_agent: str | None
    content: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentExecution:
    agent_name: str
    input_message: str
    output: Any
    tool_calls: List[ToolCall] = field(default_factory=list)
    duration: float = 0.0
    error: Exception | None = None


@dataclass
class SystemResult:
    executions: List[AgentExecution] = field(default_factory=list)
    messages: List[AgentMessage] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    completed: bool = False
    deadlock_detected: bool = False
    
    def agent(self, name: str) -> AgentResult:
        agent_execs = [e for e in self.executions if e.agent_name == name]
        return AgentResult(name, agent_execs)
    
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    def visualize_flow(self) -> str:
        if not self.messages:
            return "No messages exchanged"
        
        lines = [
            "",
            "Agent Interaction Flow",
            "═" * 50,
            ""
        ]
        
        for i, msg in enumerate(self.messages, 1):
            to_agent = msg.to_agent or "output"
            lines.append(f"{i}. {msg.from_agent} → {to_agent}")
            lines.append(f"   {msg.content[:60]}{'...' if len(msg.content) > 60 else ''}")
            lines.append("")
        
        return "\n".join(lines)


@dataclass
class AgentResult:
    name: str
    executions: List[AgentExecution]
    
    def tool_calls(self) -> List[ToolCall]:
        calls = []
        for exec in self.executions:
            calls.extend(exec.tool_calls)
        return calls
    
    def called_tool(self, tool_name: str) -> bool:
        return any(tc.name == tool_name for tc in self.tool_calls())


class System:
    def __init__(self, agents: List[Tuple[str, Any]]):
        self._agents: Dict[str, Any] = dict(agents)
        self._routing: Dict[str, str] = {}
        self._message_queue: List[AgentMessage] = []
        self._executions: List[AgentExecution] = []
        self._max_iterations = 20
    
    def route(self, from_agent: str, to_agent: str) -> None:
        self._routing[from_agent] = to_agent
    
    def run_scenario(
        self,
        steps: List[Tuple[str, str]],
        *,
        max_iterations: int = 20
    ) -> SystemResult:
        self._max_iterations = max_iterations
        result = SystemResult(start_time=time.time())
        
        for agent_name, input_msg in steps:
            if agent_name not in self._agents:
                raise ValueError(f"Unknown agent: {agent_name}")
            
            result.messages.append(AgentMessage(
                from_agent="user",
                to_agent=agent_name,
                content=input_msg,
                timestamp=time.time()
            ))
            
            execution = self._execute_agent(agent_name, input_msg)
            result.executions.append(execution)
            
            if execution.error is None and agent_name in self._routing:
                next_agent = self._routing[agent_name]
                output_str = str(execution.output)
                result.messages.append(AgentMessage(
                    from_agent=agent_name,
                    to_agent=next_agent,
                    content=output_str,
                    timestamp=time.time()
                ))
                
                next_execution = self._execute_agent(next_agent, output_str)
                result.executions.append(next_execution)
        
        result.end_time = time.time()
        result.completed = all(e.error is None for e in result.executions)
        
        return result
    
    def _execute_agent(self, agent_name: str, input_msg: str) -> AgentExecution:
        agent = self._agents[agent_name]
        start = time.time()
        
        try:
            if callable(agent):
                output = agent(input_msg)
            elif hasattr(agent, "run"):
                output = agent.run(input_msg)
            elif hasattr(agent, "__call__"):
                output = agent(input_msg)
            else:
                raise ValueError(f"Agent {agent_name} is not callable")
            
            tool_calls = []
            if hasattr(output, "tool_calls"):
                tool_calls = output.tool_calls
            
            return AgentExecution(
                agent_name=agent_name,
                input_message=input_msg,
                output=output,
                tool_calls=tool_calls,
                duration=time.time() - start,
                error=None
            )
        except Exception as e:
            return AgentExecution(
                agent_name=agent_name,
                input_message=input_msg,
                output=None,
                duration=time.time() - start,
                error=e
            )


def assert_workflow_completed(result: SystemResult) -> None:
    if not result.completed:
        failed = [e.agent_name for e in result.executions if e.error is not None]
        raise AssertionError(f"Workflow failed. Agents with errors: {failed}")


def assert_no_deadlocks(result: SystemResult) -> None:
    if result.deadlock_detected:
        raise AssertionError("Deadlock detected in agent system")


def assert_message_passing_correct(result: SystemResult) -> None:
    if len(result.messages) == 0:
        raise AssertionError("No messages were passed between agents")
    
    for msg in result.messages:
        if not msg.content or msg.content.strip() == "":
            raise AssertionError(f"Empty message from {msg.from_agent} to {msg.to_agent}")
