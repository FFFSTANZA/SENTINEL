#!/usr/bin/env python3
"""
Tests for the state persistence and replay system.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import senytl.state as state_module


class TestStatePersistence:
    """Test state persistence and replay functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Reset state manager to ensure clean state
        state_module.reset_state_manager()
        
    def teardown_method(self):
        """Cleanup test environment."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_checkpoint(self):
        """Test saving a checkpoint."""
        # Add some test data
        os.environ["TEST_VAR"] = "test_value"
        
        # Get the state manager
        state_manager = state_module._get_state_manager()
        
        # Save checkpoint
        checkpoint_name = state_manager.save_checkpoint(
            name="test_checkpoint",
            description="Test checkpoint",
            custom_state={"test": "data"}
        )
        
        assert checkpoint_name == "test_checkpoint"
        
        # Verify checkpoint exists in registry
        assert "test_checkpoint" in state_manager._registry
        
        metadata = state_manager._registry["test_checkpoint"]
        assert metadata.name == "test_checkpoint"
        assert metadata.description == "Test checkpoint"
        
        # Load the checkpoint to verify custom state is saved correctly
        with state_manager.from_checkpoint("test_checkpoint"):
            current_state = state_manager.get_current_state()
            assert "test" in current_state.custom_state
            assert current_state.custom_state["test"] == "data"
        
        # Verify file exists
        checkpoint_file = state_manager._checkpoint_file("test_checkpoint")
        assert checkpoint_file.exists()
    
    def test_load_checkpoint(self):
        """Test loading a checkpoint."""
        # First save a checkpoint
        state_manager = state_module._get_state_manager()
        state_manager.save_checkpoint(
            name="load_test",
            description="Test loading",
            custom_state={"load": "value"}
        )
        
        # Load the checkpoint
        with state_manager.from_checkpoint("load_test"):
            current_state = state_manager.get_current_state()
            assert current_state is not None
            assert current_state.metadata.name == "load_test"
            assert current_state.metadata.description == "Test loading"
            assert "load" in current_state.custom_state
            assert current_state.custom_state["load"] == "value"
    
    def test_checkpoint_not_found(self):
        """Test that loading non-existent checkpoint raises error."""
        state_manager = state_module._get_state_manager()
        with pytest.raises(state_module.CheckpointNotFoundError):
            with state_manager.from_checkpoint("nonexistent"):
                pass
    
    def test_list_checkpoints(self):
        """Test listing checkpoints."""
        state_manager = state_module._get_state_manager()
        
        # Save multiple checkpoints
        state_manager.save_checkpoint("cp1", "First checkpoint")
        state_manager.save_checkpoint("cp2", "Second checkpoint")
        
        checkpoints = state_manager.list_checkpoints()
        assert len(checkpoints) >= 2
        
        checkpoint_names = [cp.name for cp in checkpoints]
        assert "cp1" in checkpoint_names
        assert "cp2" in checkpoint_names
    
    def test_delete_checkpoint(self):
        """Test deleting checkpoints."""
        state_manager = state_module._get_state_manager()
        
        # Save checkpoint
        state_manager.save_checkpoint("delete_test", "Test deletion")
        assert "delete_test" in state_manager._registry
        
        # Delete it
        state_manager.delete_checkpoint("delete_test")
        assert "delete_test" not in state_manager._registry
        
        # Verify file is deleted
        checkpoint_file = state_manager._checkpoint_file("delete_test")
        assert not checkpoint_file.exists()
    
    def test_custom_state(self):
        """Test custom state management."""
        state_manager = state_module._get_state_manager()
        
        # Load a checkpoint
        state_manager.save_checkpoint("custom_state_test", custom_state={"initial": "value"})
        
        with state_manager.from_checkpoint("custom_state_test"):
            # Add custom state
            state_manager.add_custom_state("new_key", {"nested": "data"})
            
            # Get it back
            retrieved = state_manager.get_custom_state("new_key")
            assert retrieved["nested"] == "data"
    
    def test_registry_persistence(self):
        """Test that registry is saved and loaded correctly."""
        state_manager = state_module._get_state_manager()
        
        # Save checkpoint
        state_manager.save_checkpoint("registry_test", "Registry test")
        
        # Create new instance (simulates new process)
        new_manager = state_module.StateManager()
        
        # Should load the registry
        assert "registry_test" in new_manager._registry
        metadata = new_manager._registry["registry_test"]
        assert metadata.name == "registry_test"
        assert metadata.description == "Registry test"


class TestStateAPI:
    """Test the public API functions."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Reset state manager to ensure clean state
        state_module.reset_state_manager()
        
    def teardown_method(self):
        """Cleanup test environment."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_checkpoint_api(self):
        """Test the public save_checkpoint function."""
        checkpoint_name = state_module.save_checkpoint(
            name="api_test",
            description="API test",
            custom_state={"api": "data"}
        )
        
        assert checkpoint_name == "api_test"
        
        # Verify it exists
        checkpoints = state_module.list_checkpoints()
        checkpoint_names = [cp.name for cp in checkpoints]
        assert "api_test" in checkpoint_names
    
    def test_from_checkpoint_api(self):
        """Test the public from_checkpoint function."""
        # Save checkpoint first
        state_module.save_checkpoint("api_load_test", "API load test")
        
        # Load it via API
        with state_module.from_checkpoint("api_load_test"):
            current_state = state_module.get_current_state()
            assert current_state is not None
            assert current_state.metadata.name == "api_load_test"
            assert current_state.metadata.description == "API load test"
    
    def test_list_checkpoints_api(self):
        """Test the public list_checkpoints function."""
        # Should be empty initially
        checkpoints = state_module.list_checkpoints()
        initial_count = len(checkpoints)
        
        # Add one
        state_module.save_checkpoint("list_api_test", "List API test")
        
        # Should have one more
        new_checkpoints = state_module.list_checkpoints()
        assert len(new_checkpoints) == initial_count + 1
        
        checkpoint_names = [cp.name for cp in new_checkpoints]
        assert "list_api_test" in checkpoint_names
    
    def test_delete_checkpoint_api(self):
        """Test the public delete_checkpoint function."""
        # Save and delete
        state_module.save_checkpoint("delete_api_test", "Delete API test")
        state_module.delete_checkpoint("delete_api_test")
        
        # Should not exist anymore
        checkpoints = state_module.list_checkpoints()
        checkpoint_names = [cp.name for cp in checkpoints]
        assert "delete_api_test" not in checkpoint_names


if __name__ == "__main__":
    pytest.main([__file__])