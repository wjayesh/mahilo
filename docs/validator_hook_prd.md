# Message Validator Hook - Product Requirements Document

## 1. Overview

The Message Validator Hook is a new feature that will be added to the Mahilo message broker to enforce policies on messages exchanged between agents. This feature will allow users to define policies that messages must adhere to, and messages that violate these policies will be rejected and sent back to the sender with appropriate feedback.

## 2. Problem Statement

In multi-agent systems, agents can sometimes engage in unproductive or harmful communication patterns, such as:
- Falling into endless loops where agents keep sending similar messages back and forth
- Sending messages that violate user-defined constraints or guidelines
- Sharing sensitive information that should be restricted
- Engaging in off-topic conversations that don't contribute to the task at hand

Currently, there's no mechanism to enforce policies on messages exchanged between agents, which can lead to inefficient or undesirable agent behaviors.

## 3. Goals and Objectives

1. Implement a validator hook in the message broker that checks all messages against user-defined policies
2. Support two types of policies:
   - Heuristic-based policies (rule-based, programmatic checks)
   - Natural language policies (using LLMs to evaluate compliance)
3. Provide a simple interface for users to define and manage policies
4. Include default policies to prevent common issues like endless loops
5. Ensure minimal performance impact on message processing

## 4. User Experience

### 4.1 Policy Definition

Users will be able to define policies in two ways:

1. **Heuristic Policies**: Defined as Python functions that take a message and its context as input and return a boolean indicating whether the message passes the policy check, along with a reason if it fails.

```python
def no_repetition_policy(message, context):
    # Check if the message is too similar to previous messages
    # Return (True, None) if the message passes, (False, reason) if it fails
    pass
```

2. **Natural Language Policies**: Defined as strings that describe the policy in natural language. These will be evaluated by an LLM.

```python
natural_language_policy = "Agents should not share sensitive information like passwords or API keys."
```

### 4.2 Policy Management

Users will be able to:
- Add policies to an agent manager (team)
- Enable/disable policies
- Set policy priorities
- View policy violation logs

### 4.3 Policy Violation Handling

When a message violates a policy:
1. The message will be rejected and not delivered to the recipient
2. A response will be sent back to the sender with:
   - Information about which policy was violated
   - Suggestions for how to modify the message to comply with the policy
3. The violation will be logged for monitoring and debugging

## 5. Technical Design

### 5.1 Architecture

We'll extend the current message broker architecture by adding a validator hook:

```
                  ┌─────────────┐
                  │   Storage   │
                  └─────────────┘
                        ▲
                        │
┌─────────┐      ┌─────┴─────┐      ┌─────────────┐
│  Agent   │─────►   Message  │─────►  Validator   │
│  Sender  │      │   Broker  │      │    Hook     │
└─────────┘      └─────┬─────┘      └──────┬──────┘
                        │                   │
                        ▼                   ▼
                  ┌─────────────┐    ┌─────────────┐
                  │  Telemetry  │    │   Policy    │
                  └─────────────┘    │  Evaluator  │
                                     └─────────────┘
                                           │
                                           ▼
                                     ┌─────────────┐
                                     │   Agent     │
                                     │  Recipient  │
                                     └─────────────┘
```

### 5.2 Components

#### 5.2.1 Policy Class

```python
class Policy:
    def __init__(self, name, description, policy_type, policy_content, enabled=True, priority=0):
        self.name = name
        self.description = description
        self.policy_type = policy_type  # "heuristic" or "natural_language"
        self.policy_content = policy_content  # function or string
        self.enabled = enabled
        self.priority = priority
        
    def evaluate(self, message, context):
        # Evaluate the policy and return (passed, reason)
        pass
```

#### 5.2.2 PolicyManager Class

```python
class PolicyManager:
    def __init__(self, llm_client=None):
        self.policies = []
        self.llm_client = llm_client
        
    def add_policy(self, policy):
        self.policies.append(policy)
        
    def remove_policy(self, policy_name):
        # Remove policy by name
        pass
        
    def evaluate_message(self, message, context):
        # Evaluate message against all enabled policies
        # Return (passed, failed_policies)
        pass
```

#### 5.2.3 MessageValidator Class

```python
class MessageValidator:
    def __init__(self, policy_manager):
        self.policy_manager = policy_manager
        
    def validate(self, message, context):
        # Validate message against policies
        # Return (valid, reasons)
        pass
```

### 5.3 Integration with MessageBroker

We'll modify the `MessageBroker.send_message` method to include validation:

```python
def send_message(self, message: MessageEnvelope) -> None:
    # Validate message
    valid, reasons = self.validator.validate(message, self._get_message_context(message))
    
    if not valid:
        # Create error response
        error_message = self._create_error_response(message, reasons)
        # Send error back to sender
        self.store.save_message(error_message)
        
        if self.telemetry:
            self.telemetry.record_event(
                event_type=EventType.MESSAGE_VALIDATION_FAILED,
                correlation_id=message.correlation_id,
                agent_id=message.sender,
                message_id=message.message_id,
                details={
                    "recipient": message.recipient,
                    "reasons": reasons
                }
            )
        return
    
    # Original message processing
    if self.store:
        previous_length = len(self.store.get_pending_messages(message.recipient))
        self.store.save_message(message)
        new_length = len(self.store.get_pending_messages(message.recipient))
        
        if self.telemetry:
            # Existing telemetry code...
```

### 5.4 Default Policies

We'll implement several default policies:

1. **Anti-Loop Policy**: Prevents agents from falling into repetitive conversation patterns
   - Tracks message similarity over time
   - Detects when messages become too similar or repetitive
   - Suggests breaking the pattern with new information or approaches

2. **Message Length Policy**: Ensures messages aren't too long or too short
   - Prevents extremely verbose messages that might waste tokens
   - Ensures messages contain sufficient information to be useful

3. **Relevance Policy**: Ensures messages are relevant to the task or topic
   - Uses LLM to evaluate if the message is on-topic
   - Suggests refocusing if the conversation drifts

4. **Toxicity Policy**: Prevents harmful or inappropriate content
   - Uses LLM to detect potentially harmful content
   - Rejects messages with inappropriate language or content

### 5.5 Loop Detection Algorithm

For the anti-loop policy, we'll implement a specialized algorithm:

1. Maintain a history of recent messages between each agent pair
2. Calculate similarity scores between new messages and historical messages
3. Track patterns of back-and-forth exchanges
4. Use a combination of:
   - Text similarity metrics (cosine similarity, Jaccard similarity)
   - Semantic similarity (using embeddings)
   - Pattern detection (repeated phrases, similar structures)
5. Trigger a violation when similarity and pattern metrics exceed thresholds

## 6. Implementation Plan

### 6.1 Phase 1: Core Infrastructure

1. Create the `Policy`, `PolicyManager`, and `MessageValidator` classes
2. Integrate the validator with the `MessageBroker`
3. Implement the basic policy evaluation logic
4. Add telemetry for policy violations

### 6.2 Phase 2: Default Policies

1. Implement the anti-loop policy
2. Implement the message length policy
3. Implement the relevance policy
4. Implement the toxicity policy

### 6.3 Phase 3: User Interface

1. Add methods to `AgentManager` for policy management
2. Create a simple API for defining and managing policies
3. Implement policy violation logging and reporting

### 6.4 Phase 4: Testing and Optimization

1. Test with various agent configurations
2. Optimize performance for minimal impact on message processing
3. Fine-tune default policies based on real-world usage

## 7. Implementation Details

### 7.1 Policy and PolicyManager Classes

We'll implement the core policy classes in a new file `policy.py`:

```python
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple, Union
import json
import time
from dataclasses import dataclass

class PolicyType(Enum):
    HEURISTIC = "heuristic"
    NATURAL_LANGUAGE = "natural_language"

@dataclass
class PolicyViolation:
    policy_name: str
    reason: str
    timestamp: float = time.time()

class Policy:
    def __init__(self, 
                 name: str, 
                 description: str, 
                 policy_type: PolicyType,
                 policy_content: Union[Callable, str],
                 enabled: bool = True,
                 priority: int = 0):
        self.name = name
        self.description = description
        self.policy_type = policy_type
        self.policy_content = policy_content
        self.enabled = enabled
        self.priority = priority
    
    def evaluate(self, 
                message: 'MessageEnvelope', 
                context: Dict,
                llm_client = None) -> Tuple[bool, Optional[str]]:
        """Evaluate if a message passes this policy."""
        # Implementation details...
```

### 7.2 Default Policies

We'll implement default policies including the anti-loop policy:

```python
def create_default_policies(llm_client=None) -> List[Policy]:
    """Create default policies for the policy manager."""
    policies = []
    
    # Anti-Loop Policy
    def anti_loop_policy(message, context):
        # Implementation details...
        pass
    
    policies.append(Policy(
        name="anti_loop",
        description="Prevents agents from falling into repetitive conversation patterns",
        policy_type=PolicyType.HEURISTIC,
        policy_content=anti_loop_policy,
        priority=90  # High priority
    ))
    
    # Additional default policies...
    
    return policies
```

## 8. Usage Examples

### 8.1 Adding a Custom Heuristic Policy

```python
from mahilo.agent_manager import AgentManager

# Create agent manager
agent_manager = AgentManager()

# Define a custom policy function
def no_long_code_blocks(message, context):
    content = message.payload
    
    # Check for code blocks (```...```)
    code_blocks = re.findall(r'```[\s\S]*?```', content)
    
    for block in code_blocks:
        if len(block) > 500:
            return False, "Code blocks should be less than 500 characters. Please break up long code blocks."
    
    return True, None

# Add the policy to the agent manager
agent_manager.add_heuristic_policy(
    name="no_long_code_blocks",
    description="Prevents agents from sending very long code blocks",
    policy_function=no_long_code_blocks,
    priority=60
)
```

### 8.2 Adding a Natural Language Policy

```python
# Add a natural language policy
agent_manager.add_natural_language_policy(
    name="stay_professional",
    description="Ensures agents maintain professional communication",
    policy_text=(
        "All communication between agents should maintain a professional tone. "
        "Agents should not use slang, informal language, or emojis. "
        "Messages should be clear, concise, and focused on the task at hand."
    ),
    priority=80
)
```

## 9. Conclusion

The Message Validator Hook will provide a powerful mechanism for enforcing policies on messages exchanged between agents in the Mahilo framework. By supporting both heuristic and natural language policies, it offers flexibility for users to define constraints that suit their specific needs.

The default policies, particularly the anti-loop policy, will help prevent common issues in multi-agent systems, making them more reliable and efficient. The integration with the existing message broker architecture ensures minimal disruption to the current codebase while adding significant new functionality.

This feature will enhance the overall robustness and usability of the Mahilo framework, making it more suitable for production environments where controlled agent behavior is critical. 