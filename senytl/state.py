from __future__ import annotations

import datetime
import json
import pickle
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, TypeVar

import yaml

from .models import SenytlError
from .recording import SessionRecorder
from .utils import stable_hash, stable_json_dumps


class StateError(SenytlError):
    """Base exception for state-related errors."""
    pass


class CheckpointNotFoundError(StateError):
    """Raised when a requested checkpoint is not found."""
    pass


class StateCorruptedError(StateError):
    """Raised when a checkpoint is corrupted or invalid."""
    pass


@dataclass
class CheckpointMetadata:
    """Metadata for a saved checkpoint."""
    name: str
    timestamp: str
    function_name: str
    description: Optional[str] = None
    agent_memory: Optional[dict] = None
    db_state: Optional[dict] = None
    api_mocks: Optional[dict] = None
    custom_state: Optional[dict] = None
    session_calls: Optional[List[dict]] = None
    file_path: Optional[str] = None


@dataclass
class SystemState:
    """Complete system state snapshot."""
    agent_memory: dict[str, Any] = field(default_factory=dict)
    db_state: dict[str, Any] = field(default_factory=dict)
    api_mocks: dict[str, Any] = field(default_factory=dict)
    custom_state: dict[str, Any] = field(default_factory=dict)
    metadata: CheckpointMetadata = None  # type: ignore
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_memory": self.agent_memory,
            "db_state": self.db_state,
            "api_mocks": self.api_mocks,
            "custom_state": self.custom_state,
            "metadata": self.metadata.__dict__ if self.metadata else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SystemState:
        """Create from dictionary."""
        metadata = data.get("metadata")
        if metadata:
            metadata = CheckpointMetadata(**metadata)
        
        return cls(
            agent_memory=data.get("agent_memory", {}),
            db_state=data.get("db_state", {}),
            api_mocks=data.get("api_mocks", {}),
            custom_state=data.get("custom_state", {}),
            metadata=metadata,
        )


class StateManager:
    """Manages state persistence and replay."""
    
    def __init__(self, checkpoints_dir: Optional[Path] = None):
        self.checkpoints_dir = checkpoints_dir or self._default_checkpoints_dir()
        # Ensure parent directories exist
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        
        # Registry of all checkpoints
        self._registry: dict[str, CheckpointMetadata] = {}
        self._load_registry()
        
        # Current active state
        self._current_state: Optional[SystemState] = None
        self._checkpoint_mode: bool = False
        self._current_checkpoint_name: Optional[str] = None
        
        # Session recorder for API calls
        self._session_recorder = SessionRecorder()
        
        # Thread safety
        self._lock = threading.RLock()
        
    def _default_checkpoints_dir(self) -> Path:
        """Get default checkpoints directory."""
        return Path.cwd() / ".senytl" / "checkpoints"
    
    def _registry_file(self) -> Path:
        """Get registry file path."""
        return self.checkpoints_dir / "registry.yaml"
    
    def _checkpoint_file(self, name: str) -> Path:
        """Get checkpoint file path."""
        return self.checkpoints_dir / f"{name}.yaml"
    
    def _load_registry(self) -> None:
        """Load checkpoint registry from disk."""
        registry_file = self._registry_file()
        if registry_file.exists():
            try:
                with open(registry_file, "r") as f:
                    data = yaml.safe_load(f) or {}
                self._registry = {
                    name: CheckpointMetadata(**metadata)
                    for name, metadata in data.items()
                }
            except Exception as e:
                print(f"Warning: Failed to load state registry: {e}")
    
    def _save_registry(self) -> None:
        """Save checkpoint registry to disk."""
        registry_file = self._registry_file()
        data = {
            name: metadata.__dict__
            for name, metadata in self._registry.items()
        }
        with open(registry_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def checkpoint(self, name: str, description: Optional[str] = None) -> Callable:
        """Decorator to create a checkpoint at function entry."""
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                with self.from_checkpoint(name):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @contextmanager
    def from_checkpoint(self, name: str) -> Generator[Optional[SystemState], None, None]:
        """Context manager to run from a specific checkpoint.
        
        Args:
            name: Name of the checkpoint to load
            
        Yields:
            SystemState: The loaded checkpoint state
            
        Example:
            with state.from_checkpoint("after_user_login") as loaded_state:
                # loaded_state contains the checkpoint data
                assert loaded_state.custom_state["user_id"] == "123"
        """
        if name not in self._registry:
            raise CheckpointNotFoundError(f"Checkpoint '{name}' not found. Available: {list(self._registry.keys())}")
        
        # Load the checkpoint
        checkpoint_path = self._checkpoint_file(name)
        try:
            with open(checkpoint_path, "r") as f:
                data = yaml.safe_load(f)
            state = SystemState.from_dict(data)
        except Exception as e:
            raise StateCorruptedError(f"Failed to load checkpoint '{name}': {e}")
        
        # Restore state
        with self._lock:
            previous_state = self._current_state
            self._current_state = state
            
            # Restore session recorder if needed
            if state.metadata and state.metadata.session_calls:
                self._restore_session_recorder(state.metadata.session_calls)
            
            # Execute with restored state
            try:
                yield state
            finally:
                # Restore previous state
                self._current_state = previous_state
    
    def save_checkpoint(self, name: Optional[str] = None, description: Optional[str] = None, 
                       custom_state: Optional[dict] = None) -> str:
        """Save current system state as a checkpoint."""
        with self._lock:
            if not name:
                # Auto-generate name from timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                name = f"checkpoint_{timestamp}"
            
            # Capture current state
            state = SystemState(
                agent_memory=self._capture_agent_memory(),
                db_state=self._capture_db_state(),
                api_mocks=self._capture_api_mocks(),
                custom_state=custom_state or {},
                metadata=CheckpointMetadata(
                    name=name,
                    timestamp=datetime.datetime.now().isoformat(),
                    function_name=self._get_caller_function_name(),
                    description=description,
                    file_path=self._get_caller_file_path(),
                ),
            )
            
            # Save to disk
            checkpoint_path = self._checkpoint_file(name)
            with open(checkpoint_path, "w") as f:
                yaml.dump(state.to_dict(), f, default_flow_style=False)
            
            # Update registry
            self._registry[name] = state.metadata
            self._save_registry()
            
            return name
    
    def list_checkpoints(self) -> list[CheckpointMetadata]:
        """List all available checkpoints."""
        return sorted(self._registry.values(), key=lambda x: x.timestamp)
    
    def delete_checkpoint(self, name: str) -> None:
        """Delete a checkpoint."""
        if name not in self._registry:
            raise CheckpointNotFoundError(f"Checkpoint '{name}' not found")
        
        # Remove file
        checkpoint_path = self._checkpoint_file(name)
        if checkpoint_path.exists():
            checkpoint_path.unlink()
        
        # Update registry
        del self._registry[name]
        self._save_registry()
    
    def replay_from(self, timestamp: str, until: Optional[str] = None) -> None:
        """Time-travel debugging: replay from specific timestamp."""
        # Find checkpoint created at or after timestamp
        target_time = datetime.datetime.fromisoformat(timestamp)
        
        checkpoints = self.list_checkpoints()
        matching_checkpoints = [
            cp for cp in checkpoints
            if datetime.datetime.fromisoformat(cp.timestamp) >= target_time
        ]
        
        if not matching_checkpoints:
            raise CheckpointNotFoundError(f"No checkpoints found from timestamp {timestamp}")
        
        # Load the first matching checkpoint
        checkpoint = min(matching_checkpoints, key=lambda x: x.timestamp)
        checkpoint_path = self._checkpoint_file(checkpoint.name)
        
        try:
            with open(checkpoint_path, "r") as f:
                data = yaml.safe_load(f)
            state = SystemState.from_dict(data)
            
            # Restore state
            with self._lock:
                self._current_state = state
                if state.metadata and state.metadata.session_calls:
                    self._restore_session_recorder(state.metadata.session_calls)
                    
        except Exception as e:
            raise StateCorruptedError(f"Failed to replay from timestamp {timestamp}: {e}")
    
    def _capture_agent_memory(self) -> dict[str, Any]:
        """Capture agent memory state."""
        # This is a placeholder - in a real implementation, this would capture
        # the actual agent's memory/knowledge base state
        memory = {}
        
        # Capture any global variables that might represent agent state
        for key, value in globals().items():
            if key.startswith('_agent_') or key.endswith('_memory'):
                try:
                    memory[key] = pickle.dumps(value)
                except (pickle.PicklingError, TypeError):
                    memory[key] = str(value)
        
        return memory
    
    def _capture_db_state(self) -> dict[str, Any]:
        """Capture database state."""
        # This is a placeholder - in a real implementation, this would capture
        # database state, possibly through database introspection
        db_state = {}
        
        # Capture any database connections or queries
        for key, value in globals().items():
            if 'db' in key.lower() or 'sql' in key.lower():
                try:
                    db_state[key] = pickle.dumps(value)
                except (pickle.PicklingError, TypeError):
                    db_state[key] = str(value)
        
        return db_state
    
    def _capture_api_mocks(self) -> dict[str, Any]:
        """Capture API mocks state."""
        # Use existing session recorder if available
        mocks = {}
        
        if hasattr(self, '_session_recorder') and self._session_recorder:
            # Capture the session recorder state
            if self._session_recorder.mode:
                mocks['recorder_mode'] = self._session_recorder.mode
                mocks['recorder_name'] = self._session_recorder.name
                mocks['recorder_calls'] = self._session_recorder._calls
        
        # Capture any mock-related global variables
        for key, value in globals().items():
            if 'mock' in key.lower() or 'patch' in key.lower():
                try:
                    mocks[key] = pickle.dumps(value)
                except (pickle.PicklingError, TypeError):
                    mocks[key] = str(value)
        
        return mocks
    
    def _restore_session_recorder(self, calls: List[dict]) -> None:
        """Restore session recorder state."""
        if hasattr(self, '_session_recorder') and self._session_recorder:
            # Recreate the calls from saved state
            self._session_recorder._calls = calls.copy()
    
    def _get_caller_function_name(self) -> str:
        """Get the name of the calling function."""
        import inspect
        frame = inspect.currentframe()
        try:
            # Go up the stack to find the actual test function
            for _ in range(5):  # Check 5 frames up
                if frame is None:
                    break
                frame = frame.f_back  # type: ignore
                if frame and frame.f_code.co_name.startswith('test_'):
                    return frame.f_code.co_name
            return frame.f_code.co_name if frame else "unknown"
        finally:
            del frame
    
    def _get_caller_file_path(self) -> Optional[str]:
        """Get the file path of the caller."""
        import inspect
        frame = inspect.currentframe()
        try:
            for _ in range(5):  # Check 5 frames up
                if frame is None:
                    break
                frame = frame.f_back  # type: ignore
                if frame and frame.f_code.co_filename.endswith('.py'):
                    return frame.f_code.co_filename
            return None
        finally:
            del frame
    
    def get_current_state(self) -> Optional[SystemState]:
        """Get the currently loaded state."""
        with self._lock:
            return self._current_state
    
    def add_custom_state(self, key: str, value: Any) -> None:
        """Add custom state to the current checkpoint."""
        with self._lock:
            if self._current_state:
                try:
                    self._current_state.custom_state[key] = pickle.dumps(value)
                except (pickle.PicklingError, TypeError):
                    self._current_state.custom_state[key] = str(value)
    
    def get_custom_state(self, key: str) -> Any:
        """Get custom state from the current checkpoint."""
        with self._lock:
            if self._current_state and key in self._current_state.custom_state:
                try:
                    return pickle.loads(self._current_state.custom_state[key])
                except (pickle.UnpicklingError, TypeError):
                    return self._current_state.custom_state[key]
            return None


# Global state manager instance
_state_manager: Optional[StateManager] = None


def _get_state_manager() -> StateManager:
    """Get or create the global state manager."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager


def reset_state_manager() -> None:
    """Reset the global state manager (useful for testing)."""
    global _state_manager
    _state_manager = None


def checkpoint(name: str, description: Optional[str] = None) -> Callable:
    """Create a checkpoint decorator.
    
    Args:
        name: Name of the checkpoint
        description: Optional description of what this checkpoint represents
    
    Returns:
        Decorator function
    
    Example:
        @state.checkpoint("after_user_login")
        def test_authenticated_flow():
            agent.login("user@example.com")
            state.save_checkpoint()  # Creates "after_user_login" checkpoint
    
            response = agent.run("Show my orders")
            assert response.success
    """
    return _get_state_manager().checkpoint(name, description)


def save_checkpoint(name: Optional[str] = None, description: Optional[str] = None, 
                   custom_state: Optional[dict] = None) -> str:
    """Save current system state as a checkpoint.
    
    Args:
        name: Optional name for the checkpoint (auto-generated if not provided)
        description: Optional description
        custom_state: Optional custom state dictionary
    
    Returns:
        The name of the created checkpoint
    
    Example:
        state.save_checkpoint("after_login", "User successfully logged in")
    """
    return _get_state_manager().save_checkpoint(name, description, custom_state)


def from_checkpoint(name: str) -> Generator[None, None, None]:
    """Context manager to run from a specific checkpoint.
    
    Args:
        name: Name of the checkpoint to load
    
    Example:
        with state.from_checkpoint("after_user_login"):
            # Code here runs with user already logged in
            response = agent.run("Cancel order 123")
            assert response.success
    """
    return _get_state_manager().from_checkpoint(name)


def replay_from(timestamp: str, until: Optional[str] = None) -> None:
    """Time-travel debugging: replay from specific timestamp.
    
    Args:
        timestamp: ISO format timestamp to replay from
        until: Optional end timestamp
    
    Example:
        state.replay_from("2025-01-15T10:30:00")
    """
    return _get_state_manager().replay_from(timestamp, until)


def list_checkpoints() -> list[CheckpointMetadata]:
    """List all available checkpoints."""
    return _get_state_manager().list_checkpoints()


def delete_checkpoint(name: str) -> None:
    """Delete a checkpoint."""
    return _get_state_manager().delete_checkpoint(name)


def get_current_state() -> Optional[SystemState]:
    """Get the currently loaded state."""
    return _get_state_manager().get_current_state()


def add_custom_state(key: str, value: Any) -> None:
    """Add custom state to the current checkpoint."""
    return _get_state_manager().add_custom_state(key, value)


def get_custom_state(key: str) -> Any:
    """Get custom state from the current checkpoint."""
    return _get_state_manager().get_custom_state(key)