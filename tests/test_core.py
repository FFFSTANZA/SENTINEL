"""Tests for core Senytl functionality."""

import pytest
from senytl import Senytl
from senytl.mock_engine import MockEngine

def test_senytl_instantiation():
    """Test that Senytl can be instantiated."""
    senytl = Senytl()
    assert isinstance(senytl, Senytl)

def test_senytl_wrap_method():
    """Test that wrap method works correctly."""
    senytl = Senytl()
    
    def simple_agent(prompt: str) -> str:
        return f"Response: {prompt}"
    
    # Test wrap method (not __call__)
    wrapped = senytl.wrap(simple_agent)
    assert wrapped is not None


@pytest.mark.senytl_agent
def test_senytl_agent_fixture(senytl_agent):
    """Test Senytl agent fixture integration."""
    
    def my_agent(prompt: str) -> str:
        return f"Response: {prompt}"
    
    wrapped = senytl_agent(my_agent)
    response = wrapped.run("Test")
    
    assert response is not None
    assert "Test" in str(response)


def test_mock_engine_creation():
    """Test that MockEngine can be created."""
    engine = MockEngine()
    assert isinstance(engine, MockEngine)


@pytest.mark.senytl_mock
def test_mock_integration():
    """Test basic mock integration."""
    senytl = Senytl()
    
    # Test that we can set up mocks
    with senytl.mock("gpt-4") as mock:
        assert mock is not None
        # Basic mock setup test


def test_session_recording():
    """Test session recording."""
    senytl = Senytl()
    
    # Test that we can create a recording context
    recording = senytl.record_session("test-session")
    assert recording is not None


def test_install_uninstall():
    """Test that we can install and uninstall patches."""
    senytl = Senytl()
    
    # Should not raise errors
    senytl.install()
    senytl.uninstall()


def test_senytl_reset():
    """Test reset functionality."""
    senytl = Senytl()
    
    # Should not raise errors
    senytl.reset()


def test_default_senytl():
    """Test default senytl instance."""
    from senytl.core import get_default_senytl
    
    default = get_default_senytl()
    assert isinstance(default, Senytl)


def test_senytl_config_loading():
    """Test config loading."""
    from senytl.config import load_config
    from pathlib import Path
    
    config = load_config(Path.cwd())
    assert config is not None


def test_session_recording_context():
    """Test session recording context workflow."""
    senytl = Senytl()
    
    with senytl.record_session("test-session") as session:
        assert session is not None
        # Basic test that context manager works


def test_replay_session_context():
    """Test session replay context workflow."""
    senytl = Senytl()
    
    with senytl.replay_session("test-session") as session:
        assert session is not None
        # Basic test that context manager works


def test_mock_model_builder():
    """Test mock model builder functionality."""
    senytl = Senytl()
    
    # Test mock() method
    mock_builder = senytl.mock("gpt-4")
    assert mock_builder is not None
    
    # Test when() method
    mock_rule_builder = mock_builder.when(contains="test")
    assert mock_rule_builder is not None


def test_run_context_creation():
    """Test run context creation."""
    from senytl.core import start_run
    
    senytl = Senytl()
    run_handle = start_run(senytl)
    
    assert run_handle is not None
    
    # Finish the run
    context, duration = run_handle.finish()
    assert context is not None
    assert duration >= 0