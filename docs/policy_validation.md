# Inter-Agent Message Validaton

The Message Validator Hook is a feature in Mahilo that enforces policies on messages exchanged between agents. This allows you to define rules that messages must adhere to, and messages that violate these policies will be rejected and sent back to the sender with appropriate feedback.

## Overview

In multi-agent systems, agents can sometimes engage in unproductive or harmful communication patterns. The Message Validator Hook helps prevent these issues by:

- Enforcing user-defined policies on all messages
- Preventing endless loops where agents keep sending similar messages back and forth
- Ensuring messages adhere to guidelines (e.g., professional tone, no sensitive information)
- Providing feedback to agents when their messages violate policies

## Types of Policies

Mahilo supports two types of policies:

1. **Heuristic Policies**: Rule-based, programmatic checks defined as Python functions
2. **Natural Language Policies**: Policies defined in natural language and evaluated using an LLM

## Policy Evaluation Process

When a message is sent between agents, it goes through the following validation process:

1. The message is passed to the `MessageValidator` which calls the `PolicyManager`
2. Policies are evaluated in order of priority (higher priority policies are evaluated first)
3. If a high-priority policy (priority >= 100) is violated, evaluation stops immediately
4. A list of all policy violations is returned
5. If there are no violations, the message is delivered; otherwise, it's rejected

## Model Selection for Natural Language Policies

Natural language policies require an LLM to evaluate messages. The model is selected in the following order:

1. The model specified when creating the `AgentManager` via `validator_model_name`
2. The model specified in the `MAHILO_POLICY_MODEL` environment variable
3. The model specified in the `MAHILO_LLM_MODEL` environment variable
4. The default model from `llm_config`

## Using Policies

### Creating an Agent Manager with Policy Validation

```python
from mahilo.agent_manager import AgentManager

# Create an agent manager with an LLM model for natural language policies
agent_manager = AgentManager(
    secret_key="your_secret_key",
    db_path="messages.db",
    service_name="your_service",
    validator_model_name="gpt-4o-mini"  # Optional, specify the model to use for policy validation
)
```

### Adding a Custom Heuristic Policy

```python
from typing import Dict, Optional, Tuple
from mahilo.message_protocol import MessageEnvelope

def no_keyword_policy(message: MessageEnvelope, context: Dict) -> Tuple[bool, Optional[str]]:
    """Policy that prevents messages containing a specific keyword."""
    if "forbidden" in message.payload.lower():
        return False, "Messages containing the word 'forbidden' are not allowed."
    return True, None

agent_manager.add_heuristic_policy(
    name="no_keyword",
    description="Prevents messages containing the word 'forbidden'",
    policy_function=no_keyword_policy,
    priority=80  # Higher priority policies are evaluated first
)
```

### Adding a Natural Language Policy

```python
agent_manager.add_natural_language_policy(
    name="professional_tone",
    description="Ensures messages maintain a professional tone",
    policy_text=(
        "All communication between agents should maintain a professional tone. "
        "Agents should not use slang, informal language, or emojis. "
        "Messages should be clear, concise, and focused on the task at hand."
    ),
    priority=70
)
```

## Built-in Policies

Mahilo comes with several built-in policies that are enabled by default:

### Anti-Loop Policy

- **Name**: `anti_loop`
- **Type**: Heuristic
- **Priority**: 90 (High)
- **Description**: Prevents agents from falling into repetitive conversation patterns
- **Implementation**: 
  - Detects when a message is >80% similar to the sender's previous message
  - Identifies ping-pong patterns (A→B→A→B) where messages from each agent are >70% similar
  - Requires at least 4 messages in the conversation history
  - Error message: "Your message is too similar to your previous message. Please provide new information or a different approach."
  - For ping-pong patterns: "It seems you're in a repetitive conversation pattern. Try a different approach or provide new information."

### Message Length Policy

- **Name**: `message_length`
- **Type**: Heuristic
- **Priority**: 50 (Medium)
- **Description**: Ensures messages aren't too long or too short
- **Implementation**:
  - Rejects messages shorter than 10 characters with: "Your message is too short. Please provide more information."
  - Rejects messages longer than 4,000 characters with: "Your message is too long. Please be more concise."

### Relevance Policy 

- **Name**: `relevance`
- **Type**: Natural Language (requires LLM)
- **Priority**: 70 (Medium-high)
- **Description**: Ensures messages are relevant to the task or topic
- **Policy Text**:
  ```
  The message must be relevant to the current task or topic of conversation.
  It should not introduce completely unrelated topics without clear justification.
  ```

### Toxicity Policy

- **Name**: `toxicity`
- **Type**: Natural Language (requires LLM)
- **Priority**: 100 (Highest)
- **Description**: Prevents harmful or inappropriate content
- **Policy Text**:
  ```
  The message must not contain harmful, offensive, or inappropriate content.
  This includes but is not limited to: hate speech, personal attacks, explicit content,
  or anything that could be considered harmful to individuals or groups.
  ```
  - Being the highest priority policy (100), if it's violated, no further policies are evaluated

### Managing Policies

```python
# Get all policies
policies = agent_manager.get_policies()

# Enable/disable a policy
agent_manager.enable_policy("no_keyword")
agent_manager.disable_policy("no_keyword")

# Remove a policy
agent_manager.remove_policy("no_keyword")

# Get policy violations
violations = agent_manager.get_policy_violations(limit=10)

# Get violations for a specific policy
violations = agent_manager.get_policy_violations(limit=10, policy_name="toxicity")
```

## Policy Context

When policies are evaluated, they receive a context dictionary that can include:

- `conversation_history`: Previous messages exchanged between the agents
- Other key-value pairs that might be relevant for policy evaluation

For natural language policies, this context is serialized and included in the prompt sent to the LLM.

## Example

See the [policy_example.py](../examples/policy_validation/policy_example.py) file for a complete example of how to use the Message Validator Hook.

## Integration with Existing Code

The Message Validator Hook is integrated with the existing message broker architecture. When a message is sent, it is first validated against all enabled policies. If it passes validation, it is delivered to the recipient. If it fails validation, an error message is sent back to the sender with information about which policy was violated and suggestions for how to modify the message.

## Performance Considerations

- Heuristic policies are fast and have minimal impact on message processing
- Natural language policies require an LLM call for each message, which can add latency
- Policies are evaluated in order of priority, with higher priority policies evaluated first
- High-priority policy violations (priority >= 100) stop further evaluation
- Failed policy evaluations are logged but do not prevent other policies from being evaluated 