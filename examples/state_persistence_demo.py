#!/usr/bin/env python3
"""
Example demonstrating the State Persistence & Replay System.

This example shows how to:
1. Capture system state at any point during tests
2. Replay tests from saved checkpoints
3. Use time-travel debugging
4. Work with fixture libraries for common states

Real agents maintain state across conversations, databases, and external systems.
This system enables testing stateful agents effectively.
"""

import senytl
from senytl import state
from unittest.mock import MagicMock

# Example agent class that maintains state
class ExampleAgent:
    def __init__(self):
        self.user_session = {}
        self.memory = {}
        self.database = {}
        
    def login(self, email: str) -> bool:
        """Simulate user login."""
        self.user_session = {
            "user_id": f"user_{hash(email) % 10000}",
            "email": email,
            "logged_in": True,
            "login_time": "2025-01-15T10:30:00"
        }
        # Simulate loading user data into memory
        self.memory["user_data"] = {
            "orders": ["order_123", "order_456"],
            "preferences": {"language": "en", "theme": "dark"}
        }
        return True
    
    def run(self, query: str) -> senytl.SenytlResponse:
        """Simulate agent processing."""
        if "show orders" in query.lower():
            orders = self.memory.get("user_data", {}).get("orders", [])
            return senytl.SenytlResponse(
                text=f"Found {len(orders)} orders: {', '.join(orders)}",
                tool_calls=[]
            )
        elif "cancel order" in query.lower():
            order_id = query.split()[-1]
            if order_id in self.memory.get("user_data", {}).get("orders", []):
                self.memory["user_data"]["orders"].remove(order_id)
                return senytl.SenytlResponse(
                    text=f"Successfully cancelled {order_id}",
                    tool_calls=[]
                )
            else:
                return senytl.SenytlResponse(
                    text=f"Order {order_id} not found",
                    tool_calls=[]
                )
        else:
            return senytl.SenytlResponse(
                text="I can help you with orders",
                tool_calls=[]
            )


# Example 1: Basic checkpoint creation and usage
def test_authenticated_flow():
    """Test authenticated user flow with checkpoint creation."""
    agent = ExampleAgent()
    
    # Setup - user logs in
    agent.login("user@example.com")
    
    # Verify the memory is populated before creating checkpoint
    response = agent.run("Show my orders")
    assert "order_123" in response.text
    
    # Create checkpoint at authenticated state
    checkpoint_name = state.save_checkpoint(
        name="after_user_login",
        description="User successfully logged in with session data"
    )
    
    print(f"✓ Checkpoint created: {checkpoint_name}")
    print("✓ Authenticated flow test completed")


def test_order_cancellation():
    """Test order cancellation starting from saved checkpoint."""
    agent = ExampleAgent()
    
    # Load checkpoint - starts with user already logged in
    with state.from_checkpoint("after_user_login"):
        print("✓ Loaded checkpoint: user is logged in")
        
        # Verify we have the user session
        assert agent.user_session.get("logged_in") is True
        assert "order_123" in agent.memory.get("user_data", {}).get("orders", [])
        
        # Test cancellation
        response = agent.run("Cancel order 123")
        assert "Successfully cancelled order_123" in response.text
        
        # Save new checkpoint after cancellation
        state.save_checkpoint("after_order_cancellation")
        print("✓ Order cancellation test completed")


# Example 2: Time-travel debugging
def test_time_travel_debugging():
    """Demonstrate time-travel debugging capabilities."""
    agent = ExampleAgent()
    
    # Create multiple checkpoints with timestamps
    agent.login("user@example.com")
    state.save_checkpoint("login_state", "Initial login state")
    
    # Simulate some operations
    response1 = agent.run("Show my orders")
    state.save_checkpoint("after_order_query", "After querying orders")
    
    response2 = agent.run("Cancel order 123")
    state.save_checkpoint("after_cancellation", "After cancelling order")
    
    # Time-travel debugging - replay from specific timestamp
    # This would replay the system state as it was at the given time
    state.replay_from("2025-01-15T10:30:00")
    
    print("✓ Time-travel debugging: Replayed to login state")
    
    # Now you can debug what happened after login
    current_state = state.get_current_state()
    assert current_state is not None
    print(f"✓ Current state metadata: {current_state.metadata.name}")


# Example 3: Checkpoint management
def test_checkpoint_management():
    """Test listing, managing, and deleting checkpoints."""
    
    # List available checkpoints
    checkpoints = state.list_checkpoints()
    print(f"Available checkpoints: {[cp.name for cp in checkpoints]}")
    
    # Add a fixture checkpoint for common test state
    state.save_checkpoint(
        "logged_in_user",
        "Fixture: Standard logged-in user state",
        custom_state={
            "fixture_type": "user_authentication",
            "permissions": ["read_orders", "cancel_orders"],
            "test_data": {
                "user_id": "test_user_123",
                "email": "test@example.com"
            }
        }
    )
    
    # Use the fixture
    with state.from_checkpoint("logged_in_user"):
        agent = ExampleAgent()
        agent.login("test@example.com")
        
        # Verify fixture data
        current_state = state.get_current_state()
        assert current_state is not None
        custom_data = current_state.custom_state
        assert custom_data["fixture_type"] == "user_authentication"
        print("✓ Fixture checkpoint loaded successfully")
    
    # Clean up test checkpoints
    test_checkpoints = ["login_state", "after_order_query", "after_cancellation"]
    for cp_name in test_checkpoints:
        try:
            state.delete_checkpoint(cp_name)
            print(f"✓ Deleted checkpoint: {cp_name}")
        except state.CheckpointNotFoundError:
            pass  # Already deleted or doesn't exist


# Example 4: Advanced custom state management
def test_custom_state_management():
    """Test advanced custom state management."""
    
    # Create checkpoint with complex custom state
    complex_state = {
        "database_snapshot": {
            "users": [
                {"id": 1, "name": "Alice", "orders": ["A1", "A2"]},
                {"id": 2, "name": "Bob", "orders": ["B1"]}
            ],
            "products": [
                {"id": "P1", "name": "Product 1", "price": 10.99},
                {"id": "P2", "name": "Product 2", "price": 25.99}
            ]
        },
        "api_mocks": {
            "payment_service": {"status": "active", "last_call": "2025-01-15T10:30:00"},
            "email_service": {"status": "active", "queue_size": 0}
        },
        "agent_config": {
            "max_retries": 3,
            "timeout": 30,
            "features": ["orders", "payments", "notifications"]
        }
    }
    
    state.save_checkpoint(
        "complex_system_state",
        "Complex system state with DB, APIs, and agent config",
        custom_state=complex_state
    )
    
    # Load and verify complex state
    with state.from_checkpoint("complex_system_state"):
        current_state = state.get_current_state()
        assert current_state is not None
        
        # Verify custom state structure
        db_data = current_state.custom_state["database_snapshot"]
        assert len(db_data["users"]) == 2
        assert db_data["users"][0]["name"] == "Alice"
        
        api_data = current_state.custom_state["api_mocks"]
        assert api_data["payment_service"]["status"] == "active"
        
        print("✓ Complex custom state management working correctly")


# Example 5: Decorator usage for automatic checkpoints
def test_decorator_checkpoint():
    """Test using the checkpoint decorator."""
    
    @state.checkpoint("automated_checkpoint", "Automated checkpoint test")
    def automated_test_function():
        """Function that automatically creates a checkpoint."""
        agent = ExampleAgent()
        agent.login("automated@example.com")
        
        # The checkpoint decorator will save state at function entry
        # but we can also manually save during execution
        state.save_checkpoint("during_automated_test")
        
        response = agent.run("Show my orders")
        return response
    
    # Run the decorated function
    result = automated_test_function()
    assert result is not None
    
    # Verify the checkpoint was created
    checkpoints = state.list_checkpoints()
    checkpoint_names = [cp.name for cp in checkpoints]
    assert "automated_checkpoint" in checkpoint_names
    assert "during_automated_test" in checkpoint_names
    
    print("✓ Decorator checkpoint functionality working")


# Example 6: Real-world integration with Senytl
def test_integration_with_senytl():
    """Test integration with Senytl framework."""
    
    # Use Senytl to wrap the agent
    agent = ExampleAgent()
    wrapped_agent = senytl.wrap(agent)
    
    # Create checkpoint with Senytl session recording
    with senytl.record_session("agent_session"):
        agent.login("integration@example.com")
        state.save_checkpoint("senytl_integration", "Integration test state")
    
    # Replay from checkpoint with Senytl
    with senytl.replay_session("agent_session"):
        with state.from_checkpoint("senytl_integration"):
            # Agent state is restored, session is replayed
            response = agent.run("Show my orders")
            assert "order_123" in response.text
            
    print("✓ Integration with Senytl working correctly")


if __name__ == "__main__":
    print("🚀 State Persistence & Replay System Demo")
    print("=" * 50)
    
    # Run examples
    try:
        print("\n1️⃣  Testing authenticated flow...")
        test_authenticated_flow()
        
        print("\n2️⃣  Testing order cancellation from checkpoint...")
        test_order_cancellation()
        
        print("\n3️⃣  Testing time-travel debugging...")
        test_time_travel_debugging()
        
        print("\n4️⃣  Testing checkpoint management...")
        test_checkpoint_management()
        
        print("\n5️⃣  Testing custom state management...")
        test_custom_state_management()
        
        print("\n6️⃣  Testing decorator checkpoint...")
        test_decorator_checkpoint()
        
        print("\n7️⃣  Testing Senytl integration...")
        test_integration_with_senytl()
        
        print("\n✅ All examples completed successfully!")
        
        # Show final checkpoint summary
        checkpoints = state.list_checkpoints()
        print(f"\n📊 Final checkpoint summary ({len(checkpoints)} checkpoints):")
        for cp in checkpoints:
            print(f"  - {cp.name}: {cp.description}")
            
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        raise