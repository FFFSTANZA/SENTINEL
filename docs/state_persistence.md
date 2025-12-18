# State Persistence & Replay System

The State Persistence & Replay System is a powerful feature in Senytl that enables testing of stateful agents by capturing and restoring system state at any point during test execution.

## Overview

Real AI agents maintain state across conversations, databases, and external systems. This system provides:

- **Snapshot entire system state** (agent memory, DB state, API mocks)
- **Replay tests from any state** for consistent testing
- **Time-travel debugging** to investigate issues
- **Fixture library** for common test states

## Core Features

### 1. Checkpoint Creation and Management

```python
from senytl import state

# Save current system state
checkpoint_name = state.save_checkpoint(
    name="after_user_login",
    description="User successfully logged in with session data"
)

# List all available checkpoints
checkpoints = state.list_checkpoints()
for cp in checkpoints:
    print(f"{cp.name}: {cp.description}")

# Delete a checkpoint
state.delete_checkpoint("checkpoint_name")
```

### 2. Loading and Replaying Checkpoints

```python
# Load a checkpoint - runs with restored state
with state.from_checkpoint("after_user_login"):
    # Code here executes with the saved system state
    response = agent.run("Show my orders")
    assert response.success
```

### 3. Time-Travel Debugging

```python
# Replay system from specific timestamp
state.replay_from("2025-01-15T10:30:00")

# Replay from timestamp until another timestamp
state.replay_from("2025-01-15T10:30:00", until="2025-01-15T11:00:00")
```

### 4. Custom State Management

```python
# Save custom state with checkpoint
custom_data = {
    "user_preferences": {"theme": "dark", "language": "en"},
    "database_snapshot": {"users": 150, "orders": 320}
}

state.save_checkpoint(
    name="user_configured_state",
    description="User with custom preferences",
    custom_state=custom_data
)

# Access custom state during replay
with state.from_checkpoint("user_configured_state"):
    current_state = state.get_current_state()
    preferences = current_state.custom_state["user_preferences"]
```

### 5. Decorator for Automatic Checkpoints

```python
@state.checkpoint("authenticated_user", "Auto checkpoint for authenticated users")
def test_authenticated_operations():
    agent.login("user@example.com")
    # The checkpoint is automatically created at function entry
    response = agent.run("Show my orders")
    assert response.success
```

## Integration with Senytl

The state system integrates seamlessly with existing Senytl features:

```python
import senytl
from senytl import state

# Wrap agent with Senytl
agent = senytl.wrap(my_agent)

# Record session and create checkpoint
with senytl.record_session("test_session"):
    agent.setup_user("user@example.com")
    state.save_checkpoint("session_state")

# Replay with both session and state
with senytl.replay_session("test_session"):
    with state.from_checkpoint("session_state"):
        response = agent.run("Show orders")
```

## System State Components

The system captures four types of state:

1. **Agent Memory**: Agent's internal memory and knowledge base
2. **Database State**: Database contents and connections
3. **API Mocks**: Mocked API responses and call history
4. **Custom State**: User-defined state data

## Use Cases

### 1. Authentication Testing
```python
def test_order_management():
    # Setup: login user
    agent.login("user@example.com")
    state.save_checkpoint("authenticated")
    
    # Test: user can view orders
    with state.from_checkpoint("authenticated"):
        response = agent.run("Show my orders")
        assert response.success

def test_order_cancellation():
    # Reuse the authenticated state
    with state.from_checkpoint("authenticated"):
        response = agent.run("Cancel order 123")
        assert response.success
```

### 2. Complex Workflow Testing
```python
def test_multi_step_workflow():
    # Step 1: User registration
    agent.register("new@example.com")
    state.save_checkpoint("after_registration")
    
    # Step 2: Profile setup
    agent.setup_profile({"name": "John Doe"})
    state.save_checkpoint("profile_complete")
    
    # Step 3: First order
    agent.place_order("Product A")
    state.save_checkpoint("first_order_placed")
    
    # Replay from any step for testing
    with state.from_checkpoint("profile_complete"):
        # Test workflows starting from profile completion
        pass
```

### 3. Debugging Failed Tests
```python
def test_debugging_example():
    # When a test fails, you can time-travel to investigate
    state.replay_from("2025-01-15T14:30:00")
    
    # Examine the current state
    current_state = state.get_current_state()
    print(f"Debugging from: {current_state.metadata.timestamp}")
    
    # Step through the failing scenario
    agent.debug_step("Show what went wrong")
```

## Error Handling

The system provides specific exceptions for different error conditions:

- `StateError`: Base exception for all state-related errors
- `CheckpointNotFoundError`: When a requested checkpoint doesn't exist
- `StateCorruptedError`: When a checkpoint file is corrupted

```python
try:
    with state.from_checkpoint("nonexistent"):
        pass
except state.CheckpointNotFoundError as e:
    print(f"Checkpoint not found: {e}")
```

## File Structure

Checkpoints are stored in `.senytl/checkpoints/` directory:

```
.senytl/
└── checkpoints/
    ├── registry.yaml          # Index of all checkpoints
    ├── after_user_login.yaml  # Individual checkpoint files
    ├── order_cancelled.yaml
    └── ...
```

## Best Practices

1. **Use Descriptive Names**: Name checkpoints meaningfully (e.g., "user_logged_in" vs "cp1")

2. **Add Descriptions**: Always provide descriptions for better documentation

3. **Clean Up**: Delete test checkpoints after use to avoid clutter

4. **Version Control**: Checkpoint files are automatically gitignored

5. **Custom State**: Use custom_state for complex data structures

6. **Thread Safety**: The system is thread-safe for parallel test execution

## Limitations

- Checkpoint files are YAML format for human readability
- Large state snapshots may impact performance
- Database state capture requires appropriate database access
- External system state capture depends on available interfaces

This system makes testing stateful agents practical and reliable, enabling comprehensive testing of real-world AI agent behaviors.