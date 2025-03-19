"""
Example demonstrating the use of the message validator hook.

This example shows how to:
1. Create an agent manager with policy validation
2. Add custom policies
3. Send messages between agents that pass or fail validation
"""

import os
import sys
import asyncio
from typing import Dict, Optional, Tuple

# Add the parent directory to the path so we can import mahilo
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from mahilo.agent import BaseAgent
from mahilo.agent_manager import AgentManager
from mahilo.message_protocol import MessageEnvelope, MessageType

# You can set the model to use for policy validation via environment variables:
# MAHILO_POLICY_MODEL or MAHILO_LLM_MODEL
# If not set, it will use the default model from llm_config

# For debugging, we'll print the LLM responses
DEBUG = False

async def test_message(agent_manager, sender, recipient, content, test_name, previous_violations):
    """Test a single message and return the result."""
    print(f"\nTesting: {test_name}")
    print(f"Message: {content}")
    
    # Create a message envelope for direct testing
    envelope = MessageEnvelope.create(
        sender=sender,
        recipient=recipient,
        payload=content,
        message_type=MessageType.DIRECT
    )
    
    # Get context for validation
    context = agent_manager.message_broker._get_message_context(envelope)
    
    # Directly validate the message to see the results
    if DEBUG:
        print("\nDirect policy validation:")
        for policy in agent_manager.policy_manager.policies:
            try:
                passed, reason = await policy.evaluate(envelope, context, agent_manager.policy_manager.model_name)
                breakpoint()
                result = "✅ PASSED" if passed else "❌ FAILED"
                print(f"  {result} {policy.name}: {reason or 'No issues'}")
            except Exception as e:
                print(f"  ⚠️ ERROR evaluating {policy.name}: {str(e)}")
    
    # Send the message through the broker
    await agent_manager.send_message_to_agent(
        sender=sender,
        recipient=recipient,
        message=content
    )
    
    # Wait a moment for async processing to complete
    await asyncio.sleep(0.1)
    
    # Check for new violations
    all_violations = agent_manager.policy_manager.violation_history
    new_violations = [v for v in all_violations if v not in previous_violations]
    breakpoint()
    
    if new_violations:
        print(f"\nMessage REJECTED due to policy violations:")
        for v in new_violations:
            print(f"  ❌ {v.policy_name}: {v.reason}")
        result = {"passed": False, "violations": new_violations}
    else:
        print(f"\nMessage ACCEPTED (passed all policy checks)")
        result = {"passed": True, "violations": []}
    
    return result, all_violations

async def main():
    # Create an agent manager with a model name for natural language policies
    agent_manager = AgentManager(
        secret_key="example_secret",
        db_path="policy_example.db",
        service_name="policy_example",
        validator_model_name="gpt-4o-mini"  # You can specify the model directly
    )
    
    # Create two agents
    agent1 = BaseAgent(type="example", name="agent1", description="Example Agent 1")
    agent2 = BaseAgent(type="example", name="agent2", description="Example Agent 2")
    
    # Register the agents
    agent_manager.register_agent(agent1)
    agent_manager.register_agent(agent2)
    
    # Set up can_contact
    agent1.can_contact = ["agent2"]
    agent2.can_contact = ["agent1"]
    
    # Clear any existing policies to avoid duplicates
    for policy in list(agent_manager.get_policies()):
        agent_manager.remove_policy(policy.name)
    
    # Add a custom heuristic policy
    def no_keyword_policy(message: MessageEnvelope, context: Dict) -> Tuple[bool, Optional[str]]:
        """Policy that prevents messages containing a specific keyword."""
        # Check if the message contains the word "forbidden"
        if "forbidden" in message.payload.lower():
            return False, "Messages containing the word 'forbidden' are not allowed."
        return True, None
    
    agent_manager.add_heuristic_policy(
        name="no_keyword",
        description="Prevents messages containing the word 'forbidden'",
        policy_function=no_keyword_policy,
        priority=80
    )
    agent_manager.remove_policy()
    # Add a natural language policy
    agent_manager.add_natural_language_policy(
        name="professional_tone",
        description="Ensures messages maintain a professional tone",
        policy_text=(
            "All communication between agents should maintain a professional tone. "
            "Agents should not use slang, informal language, or emojis. "
            "Messages should be clear, concise, and focused on the task at hand. "
            "Informal phrases like 'hey yo', 'what's up', or 'sup' are not allowed."
        ),
        priority=70
    )
    
    # Add a natural language policy for sensitive information
    agent_manager.add_natural_language_policy(
        name="no_sensitive_info",
        description="Prevents sharing of sensitive information",
        policy_text=(
            "Messages should not contain sensitive information such as passwords, "
            "API keys, or personal identifiable information. "
            "Examples of sensitive information include: 'My password is 12345', 'API key is abcdef', etc."
        ),
        priority=100
    )
    
    print("\nPolicies configured:")
    for policy in agent_manager.get_policies():
        print(f"- {policy.name}: {policy.description} (Priority: {policy.priority})")
    print()
    
    # Test messages
    test_messages = [
        ("Valid message", "Hello, this is a valid message."),
        ("Message with forbidden word", "This message contains a forbidden word."),
        ("Informal message", "Hey yo what's up?"),
        ("Message with sensitive info", "My password is 12345 and my API key is abcdef.")
    ]
    
    # Clear any existing violations
    agent_manager.policy_manager.violation_history = []
    
    # Track violations for each test
    test_results = {}
    all_violations = []
    
    # Test each message
    for test_name, content in test_messages:
        result, all_violations = await test_message(
            agent_manager, 
            "agent1", 
            "agent2", 
            content, 
            test_name, 
            all_violations
        )
        test_results[test_name] = result
    
    # Print summary
    print("\n=== Test Summary ===")
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result["passed"] else "❌ FAILED"
        print(f"{status} {test_name}")

if __name__ == "__main__":
    asyncio.run(main()) 