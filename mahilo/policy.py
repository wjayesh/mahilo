from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple, Union, Any
import json
import time
import os
from dataclasses import dataclass
from difflib import SequenceMatcher
import re

# Import MessageEnvelope for type hints
from .message_protocol import MessageEnvelope
from .llm_config import llm_config

class PolicyType(Enum):
    """Types of policies that can be defined."""
    HEURISTIC = "heuristic"
    NATURAL_LANGUAGE = "natural_language"

@dataclass
class PolicyViolation:
    """Represents a policy violation."""
    policy_name: str
    reason: str
    timestamp: float = time.time()

class Policy:
    """A policy that can be applied to messages between agents."""
    
    def __init__(self, 
                 name: str, 
                 description: str, 
                 policy_type: PolicyType,
                 policy_content: Union[Callable, str],
                 enabled: bool = True,
                 priority: int = 0):
        """Initialize a policy.
        
        Args:
            name: Unique name for the policy
            description: Human-readable description of what the policy does
            policy_type: Type of policy (heuristic or natural language)
            policy_content: For heuristic policies, a callable that evaluates messages;
                           for natural language policies, a string describing the policy
            enabled: Whether the policy is currently active
            priority: Priority of the policy (higher values = higher priority)
        """
        self.name = name
        self.description = description
        self.policy_type = policy_type
        self.policy_content = policy_content
        self.enabled = enabled
        self.priority = priority
    
    async def evaluate(self, 
                message: MessageEnvelope, 
                context: Dict,
                model_name: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Evaluate if a message passes this policy.
        
        Args:
            message: The message to evaluate
            context: Additional context for evaluation (e.g., conversation history)
            model_name: Model name to use for natural language policies
            
        Returns:
            Tuple of (passed, reason) where reason is None if passed is True
        """
        if not self.enabled:
            return True, None
            
        if self.policy_type == PolicyType.HEURISTIC:
            if callable(self.policy_content):
                return self.policy_content(message, context)
            else:
                raise ValueError(f"Heuristic policy {self.name} has non-callable content")
                
        elif self.policy_type == PolicyType.NATURAL_LANGUAGE:
            if model_name is None:
                # Try to get model from environment variable
                model_name = os.getenv("MAHILO_POLICY_MODEL", os.getenv("MAHILO_LLM_MODEL", None))
                
            # If still None, use the default model from llm_config
            if model_name is None:
                # No need to raise an error, just use the default model
                model_name = None  # This will make llm_config use its default model
                
            # Prepare message data in a serializable format
            message_data = {
                "sender": message.sender,
                "recipient": message.recipient,
                "payload": message.payload,
                "message_type": message.message_type.value,
                "message_id": message.message_id
            }
            
            # Prepare context in a serializable format
            serializable_context = {}
            for key, value in context.items():
                if key == "conversation_history":
                    # Convert MessageEnvelope objects to dictionaries
                    serializable_context[key] = [
                        {
                            "sender": msg.sender,
                            "recipient": msg.recipient,
                            "payload": msg.payload,
                            "message_type": msg.message_type.value if hasattr(msg, "message_type") else "unknown",
                            "message_id": msg.message_id if hasattr(msg, "message_id") else "unknown"
                        }
                        for msg in value
                    ]
                else:
                    serializable_context[key] = value
            
            # Prepare prompt for LLM
            prompt = f"""
            You are evaluating if a message complies with a policy.
            
            POLICY: {self.policy_content}
            
            MESSAGE FROM: {message.sender}
            MESSAGE TO: {message.recipient}
            MESSAGE CONTENT: {message.payload}
            
            CONTEXT: {json.dumps(serializable_context, indent=2)}
            
            Does this message comply with the policy? Answer with YES or NO, followed by your reasoning.
            Be strict in your evaluation. If there's any doubt, the message should not comply.
            
            Format your response exactly as:
            COMPLIANCE: YES/NO
            REASON: Your detailed reasoning here
            """
            
            # Get LLM response using LiteLLM
            messages = [{"role": "user", "content": prompt}]
            response = await llm_config.chat_completion(messages=messages, model=model_name)
            response_text = response.choices[0].message.content
            
            print(f"Policy '{self.name}' evaluation response: {response_text}")
            
            # Parse response
            if "COMPLIANCE: YES" in response_text.upper():
                return True, None
            elif "COMPLIANCE: NO" in response_text.upper():
                # Extract reason from response
                reason_match = re.search(r"REASON:\s*(.*?)(?:\n|$)", response_text, re.IGNORECASE | re.DOTALL)
                reason = reason_match.group(1).strip() if reason_match else "Message violates policy"
                return False, reason
            else:
                # Fallback to the old parsing method
                if response_text.lower().startswith("yes"):
                    return True, None
                else:
                    # Extract reason from response
                    reason_lines = response_text.split("\n")[1:]  # Skip the YES/NO line
                    reason = " ".join(reason_lines).strip()
                    return False, reason or "Message violates policy"
                
        return True, None  # Default pass if policy type is unknown

class PolicyManager:
    """Manages a collection of policies and evaluates messages against them."""
    
    def __init__(self, validator_model_name: Optional[str] = None):
        """Initialize a policy manager.
        
        Args:
            validator_model_name: Optional model name for natural language policies.
                       If not provided, will try to use MAHILO_POLICY_MODEL or MAHILO_LLM_MODEL env var.
                       If env vars are not set, will use the default model from llm_config.
        """
        self.policies: List[Policy] = []
        self.model_name = validator_model_name
        self.violation_history: List[PolicyViolation] = []
        
    def add_policy(self, policy: Policy) -> None:
        """Add a policy to the manager.
        
        Args:
            policy: The policy to add
        """
        self.policies.append(policy)
        # Sort policies by priority (higher priority first)
        self.policies.sort(key=lambda p: -p.priority)
        
    def remove_policy(self, policy_name: str) -> None:
        """Remove a policy by name.
        
        Args:
            policy_name: Name of the policy to remove
        """
        self.policies = [p for p in self.policies if p.name != policy_name]
        
    def get_policy(self, policy_name: str) -> Optional[Policy]:
        """Get a policy by name.
        
        Args:
            policy_name: Name of the policy to get
            
        Returns:
            The policy if found, None otherwise
        """
        for policy in self.policies:
            if policy.name == policy_name:
                return policy
        return None
        
    def enable_policy(self, policy_name: str) -> None:
        """Enable a policy by name.
        
        Args:
            policy_name: Name of the policy to enable
        """
        policy = self.get_policy(policy_name)
        if policy:
            policy.enabled = True
            
    def disable_policy(self, policy_name: str) -> None:
        """Disable a policy by name.
        
        Args:
            policy_name: Name of the policy to disable
        """
        policy = self.get_policy(policy_name)
        if policy:
            policy.enabled = False
            
    async def evaluate_message(self, 
                        message: MessageEnvelope, 
                        context: Dict) -> Tuple[bool, List[PolicyViolation]]:
        """Evaluate a message against all enabled policies.
        
        Args:
            message: The message to evaluate
            context: Additional context for evaluation
            
        Returns:
            Tuple of (passed, violations) where violations is a list of PolicyViolation objects
        """
        violations = []
        
        for policy in self.policies:
            if not policy.enabled:
                continue
                
            try:
                passed, reason = await policy.evaluate(message, context, self.model_name)
                if not passed:
                    violation = PolicyViolation(
                        policy_name=policy.name,
                        reason=reason or f"Violated policy: {policy.name}"
                    )
                    violations.append(violation)
                    self.violation_history.append(violation)
                    
                    # If this is a high priority policy, stop evaluation
                    if policy.priority >= 100:
                        break
            except Exception as e:
                # Log error but continue with other policies
                print(f"Error evaluating policy {policy.name}: {str(e)}")
                
        return len(violations) == 0, violations

class MessageValidator:
    """Validates messages against policies."""
    
    def __init__(self, policy_manager: PolicyManager):
        """Initialize a message validator.
        
        Args:
            policy_manager: The policy manager to use for validation
        """
        self.policy_manager = policy_manager
        
    async def validate(self, 
                message: MessageEnvelope, 
                context: Dict) -> Tuple[bool, List[PolicyViolation]]:
        """Validate a message against all policies.
        
        Args:
            message: The message to validate
            context: Additional context for validation
            
        Returns:
            Tuple of (valid, violations) where violations is a list of PolicyViolation objects
        """
        return await self.policy_manager.evaluate_message(message, context)

def create_default_policies(validator_model_name: Optional[str] = None) -> List[Policy]:
    """Create default policies for the policy manager.
    
    Args:
        validator_model_name: Optional model name for natural language policies.
                   If not provided, will try to use MAHILO_POLICY_MODEL or MAHILO_LLM_MODEL env var.
                   If env vars are not set, will use the default model from llm_config.
        
    Returns:
        List of default policies
    """
    policies = []
    
    # Anti-Loop Policy
    def anti_loop_policy(message: MessageEnvelope, context: Dict) -> Tuple[bool, Optional[str]]:
        """Prevent agents from falling into repetitive conversation patterns."""
        # Get conversation history between these agents
        sender = message.sender
        recipient = message.recipient
        
        # We need conversation history in context
        if 'conversation_history' not in context:
            return True, None
            
        history = context['conversation_history']
        if len(history) < 4:  # Need at least 2 back-and-forth exchanges
            return True, None
            
        # Check for repetitive patterns
        current_message = message.payload
        
        # Check similarity with recent messages from the same sender
        sender_messages = [msg.payload for msg in history if msg.sender == sender]
        if sender_messages:
            last_sender_message = sender_messages[-1]
            similarity = SequenceMatcher(None, current_message, last_sender_message).ratio()
            
            if similarity > 0.8:  # High similarity threshold
                return False, "Your message is too similar to your previous message. Please provide new information or a different approach."
        
        # Check for ping-pong pattern (A->B->A->B with similar content)
        if len(history) >= 4:
            last_4_messages = history[-4:]
            
            # Check if the pattern is A->B->A->B
            if (last_4_messages[0].sender == sender and 
                last_4_messages[1].sender == recipient and
                last_4_messages[2].sender == sender and
                last_4_messages[3].sender == recipient):
                
                # Check content similarity
                similarity_1_3 = SequenceMatcher(
                    None, last_4_messages[0].payload, last_4_messages[2].payload
                ).ratio()
                
                similarity_2_4 = SequenceMatcher(
                    None, last_4_messages[1].payload, last_4_messages[3].payload
                ).ratio()
                
                if similarity_1_3 > 0.7 and similarity_2_4 > 0.7:
                    return False, "It seems you're in a repetitive conversation pattern. Try a different approach or provide new information."
        
        return True, None
    
    policies.append(Policy(
        name="anti_loop",
        description="Prevents agents from falling into repetitive conversation patterns",
        policy_type=PolicyType.HEURISTIC,
        policy_content=anti_loop_policy,
        priority=90  # High priority
    ))
    
    # Message Length Policy
    def message_length_policy(message: MessageEnvelope, context: Dict) -> Tuple[bool, Optional[str]]:
        """Ensure messages aren't too long or too short."""
        content = message.payload
        
        # Check if message is too short
        if len(content.strip()) < 10:
            return False, "Your message is too short. Please provide more information."
            
        # Check if message is too long
        if len(content) > 4000:
            return False, "Your message is too long. Please be more concise."
            
        return True, None
    
    policies.append(Policy(
        name="message_length",
        description="Ensures messages aren't too long or too short",
        policy_type=PolicyType.HEURISTIC,
        policy_content=message_length_policy,
        priority=50  # Medium priority
    ))
    
    # Relevance Policy (requires model name)
    policies.append(Policy(
        name="relevance",
        description="Ensures messages are relevant to the task or topic",
        policy_type=PolicyType.NATURAL_LANGUAGE,
        policy_content=(
            "The message must be relevant to the current task or topic of conversation. "
            "It should not introduce completely unrelated topics without clear justification."
        ),
        priority=70  # Medium-high priority
    ))
    
    # Toxicity Policy (requires model name)
    policies.append(Policy(
        name="toxicity",
        description="Prevents harmful or inappropriate content",
        policy_type=PolicyType.NATURAL_LANGUAGE,
        policy_content=(
            "The message must not contain harmful, offensive, or inappropriate content. "
            "This includes but is not limited to: hate speech, personal attacks, explicit content, "
            "or anything that could be considered harmful to individuals or groups."
        ),
        priority=100  # Highest priority
    ))
    
    return policies 