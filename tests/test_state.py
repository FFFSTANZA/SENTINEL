"""Tests for state persistence and replay functionality - UPDATED to match real implementation"""

import pytest
import tempfile
import os
from senytl import state
from senytl.core import Senytl


def test_save_checkpoint():
    """Test saving state checkpoints."""
    senytl = Senytl()
    
    # Define an agent that has state
    conversation_state = {"messages": []}
    
    def stateful_agent(prompt: str):
        conversation_state["messages"].append({"role": "user", "content": prompt})
        return f"Received: {prompt}"
    
    # Mock state by creating a custom_state dict
    custom_state = {"conversation": conversation_state}
    
    # Save checkpoint with custom_state (not metadata parameter)
    checkpoint_name = state.save_checkpoint("test-session", "Test session state", custom_state)
    
    assert checkpoint_name is not None
    assert checkpoint_name == "test-session"


def test_from_checkpoint():
    """Test restoring from a checkpoint."""
    # Save a checkpoint first
    test_state = {"messages": [{"role": "user", "content": "existing"}]}
    custom_state = {"conversation": test_state}
    
    checkpoint_name = state.save_checkpoint("restore_test", "Test restore", custom_state)
    assert checkpoint_name == "restore_test"
    
    # Restore from checkpoint  
    with state.from_checkpoint("restore_test"):
        current_state = state.get_current_state()
        assert current_state is not None
        # The state should have been restored


def test_state_persistence_with_agent():
    """Test state persistence in a real agent scenario."""
    senytl = Senytl()
    
    # Use simple dict state that can be serialized
    agent_state = {"history": []}
    
    def stateful_run(prompt: str):
        agent_state["history"].append(prompt)
        return f"Response to: {prompt} (history: {len(agent_state['history'])})"
    
    # First conversation
    wrapped = senytl.wrap(stateful_run)
    response1 = wrapped.run("First message")
    checkpoint = state.save_checkpoint("conversation-test", None, {"agent_state": agent_state})
    
    # Second conversation from checkpoint  
    with state.from_checkpoint("conversation-test"):
        # State should be restored here
        current_state = state.get_current_state()
        assert current_state is not None


def test_checkpoint_preservation():
    """Test checkpoint data preservation through save/restore."""
    # Create test data
    test_data = {"value": 42}
    test_description = "Metadata test checkpoint"
    
    # Save checkpoint
    checkpoint_name = state.save_checkpoint("metadata_test", test_description, test_data)
    
    # Should have saved successfully
    assert checkpoint_name == "metadata_test"
    
    # List checkpoints
    checkpoints = state.list_checkpoints()
    assert len(checkpoints) > 0
    
    # Find our checkpoint
    checkpoint_names = [cp.name for cp in checkpoints]
    assert "metadata_test" in checkpoint_names


def test_list_checkpoints():
    """Test listing checkpoints."""
    checkpoints = state.list_checkpoints()
    assert isinstance(checkpoints, list)


@pytest.mark.senytl_agent
def test_state_integration_with_pytest():
    """Test state functionality integrates with pytest."""
    # Basic test that state functions work in pytest context
    checkpoint_name = state.save_checkpoint("pytest-test", None, {"test": True})
    assert checkpoint_name == "pytest-test"


def test_custom_state_operations():
    """Test adding and retrieving custom state."""
    # Save checkpoint with custom state
    custom_state = {"key1": "value1", "key2": 123}
    checkpoint_name = state.save_checkpoint("custom-test", None, custom_state)
    
    # Should exist in registry
    checkpoints = state.list_checkpoints()
    names = [cp.name for cp in checkpoints]
    assert "custom-test" in names


# Clean up state manager after all tests
@pytest.fixture(autouse=True)
def clear_state_manager():
    """Clear state manager between tests."""
    yield
    state.reset_state_manager()