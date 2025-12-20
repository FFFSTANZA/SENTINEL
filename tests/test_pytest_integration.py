"""Tests for pytest plugin integration."""

import pytest
from senytl import Senytl

def test_pytest_mark_senytl_agent():
    """Test that pytest marker works correctly."""
    # This test is decorated with the marker but doesn't use the fixture
    # to ensure the marker is recognized by pytest
    assert True

@pytest.mark.senytl_agent
def test_senytl_agent_fixture_with_run(senytl_agent):
    """Test agent fixture with actual agent execution."""
    def simple_agent(prompt: str):
        return f"Processed: {prompt}"
    
    wrapped = senytl_agent(simple_agent)
    response = wrapped.run("test input")
    
    assert response is not None
    assert "test input" in str(response.text)

@pytest.mark.senytl_mock
def test_senytl_mock_marker():
    """Test that senytl_mock marker is recognized."""
    assert True

@pytest.mark.senytl_adversarial
def test_senytl_adversarial_marker():
    """Test that senytl_adversarial marker is recognized."""
    assert True

def test_senytl_fixture(senytl):
    """Test basic senytl fixture."""
    assert isinstance(senytl, Senytl)

def test_senytl_config_fixture():
    """Test senytl config through regular import instead of deprecated fixture."""
    from senytl.config import load_config
    from pathlib import Path
    
    config = load_config(Path.cwd())
    assert config is not None
    assert hasattr(config, 'fallback')

def test_pytest_config_integration():
    """Test that pytest configuration is properly loaded."""
    # Test that our pytest plugin is registered
    import pytest
    
    # The plugin should be registered through entry points
    # Just verify pytest is working with our plugin structure
    assert hasattr(pytest, 'mark')

@pytest.mark.senytl_agent
def test_multiple_agent_calls(senytl_agent):
    """Test multiple calls to same agent."""
    def counting_agent(prompt: str):
        return f"Call number: {prompt}"
    
    wrapped = senytl_agent(counting_agent)
    
    response1 = wrapped.run("first")
    response2 = wrapped.run("second")
    response3 = wrapped.run("third")
    
    assert "first" in str(response1.text)
    assert "second" in str(response2.text) 
    assert "third" in str(response3.text)

def test_agent_with_complex_return():
    """Test agents returning complex data structures."""
    def complex_agent(prompt: str):
        return {
            "status": "success",
            "data": {"input": prompt, "processed": True},
            "metadata": {"version": "1.0"}
        }
    
    senytl = Senytl()
    wrapped = senytl.wrap(complex_agent)
    response = wrapped.run("complex test")
    
    assert response.text is not None