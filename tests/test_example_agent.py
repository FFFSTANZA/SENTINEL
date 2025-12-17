"""Example agent tests to demonstrate coverage tracking"""
import pytest
from senytl import expect, mock
from senytl.models import ToolCall


def simple_agent(prompt: str) -> str:
    """A simple mock agent for testing"""
    return f"Response to: {prompt}"


@pytest.mark.senytl_agent
def test_agent_basic_interaction(senytl_agent):
    """Test basic agent interaction"""
    wrapped = senytl_agent(simple_agent)
    response = wrapped.run("Hello, agent!")
    
    assert response.text is not None
    assert len(response.text) > 0
    expect(response).to_contain("Hello, agent!")


@pytest.mark.senytl_agent
def test_agent_with_multiple_inputs(senytl_agent):
    """Test agent with multiple different inputs"""
    wrapped = senytl_agent(simple_agent)
    
    response1 = wrapped.run("What is AI?")
    response2 = wrapped.run("Tell me about ML")
    response3 = wrapped.run("Explain NLP")
    
    assert all(r.text for r in [response1, response2, response3])


@pytest.mark.senytl_agent  
def test_agent_error_handling(senytl_agent):
    """Test agent handles errors"""
    wrapped = senytl_agent(simple_agent)
    response = wrapped.run("")
    
    assert response.text is not None
    assert len(response.text) > 0
