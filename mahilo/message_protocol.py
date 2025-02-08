import uuid
import time
import json
import jwt
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from mahilo.message_store import MessageStore
from mahilo.monitoring import EventType, MahiloTelemetry

class MessageType(Enum):
    DIRECT = "direct"
    BROADCAST = "broadcast"
    RESPONSE = "response"
    ERROR = "error"

@dataclass
class MessageEnvelope:
    """Message envelope containing metadata and payload"""
    message_id: str
    sender: str
    recipient: str
    message_type: MessageType
    payload: str
    timestamp: float
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    signature: Optional[str] = None
    
    @classmethod
    def create(cls, sender: str, recipient: str, payload: str, 
               message_type: MessageType = MessageType.DIRECT,
               correlation_id: Optional[str] = None,
               reply_to: Optional[str] = None,
               secret_key: Optional[str] = None) -> 'MessageEnvelope':
        """Create a new message envelope"""
        msg = cls(
            message_id=str(uuid.uuid4()),
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            payload=payload,
            timestamp=time.time(),
            correlation_id=correlation_id,
            reply_to=reply_to
        )
        
        if secret_key:
            # Sign the message if secret key is provided
            msg.signature = jwt.encode(
                {"message_id": msg.message_id, "payload": msg.payload},
                secret_key,
                algorithm="HS256"
            )
        
        return msg
    
    def verify(self, secret_key: str) -> bool:
        """Verify message signature"""
        if not self.signature:
            return False
        try:
            decoded = jwt.decode(self.signature, secret_key, algorithms=["HS256"])
            return (decoded["message_id"] == self.message_id and 
                   decoded["payload"] == self.payload)
        except jwt.InvalidTokenError:
            return False
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            k: str(v) if isinstance(v, MessageType) else v 
            for k, v in asdict(self).items()
        }

class MessageBroker:
    """Message broker for handling inter-agent communication"""
    def __init__(self, secret_key: Optional[str] = None, store: Optional["MessageStore"] = None, telemetry: Optional["MahiloTelemetry"] = None):
        self.secret_key = secret_key
        self.store = store
        self.telemetry = telemetry
        self.MAX_RETRIES = 3
        
    def send_message(self, message: MessageEnvelope) -> None:
        """Queue a message for delivery"""
        if self.store:
            self.store.save_message(message)
            
        if self.telemetry:
            self.telemetry.record_event(
                event_type=EventType.MESSAGE_SENT,
                correlation_id=message.correlation_id,
                agent_id=message.sender,
                message_id=message.message_id,
                details={
                    "recipient": message.recipient,
                    "message_type": message.message_type.value
                }
            )
        
    def get_pending_messages(self, recipient: str) -> List[MessageEnvelope]:
        """Get pending messages for a recipient"""
        messages = []
        if self.store:
            messages = self.store.get_pending_messages(recipient)
            
        if self.telemetry and messages:
            self.telemetry.record_event(
                event_type=EventType.QUEUE_LENGTH_CHANGED,
                agent_id=recipient,
                details={
                    "queue_length": len(messages),
                    "previous_length": 0  # We don't track previous length currently
                }
            )
            
        return messages
        
    def acknowledge_message(self, message_id: str, recipient: str) -> None:
        """Acknowledge successful message processing"""
        if self.store:
            message = self.store.get_message(message_id)
            if message:
                self.store.update_message_state(message_id, "processed")
                
                if self.telemetry:
                    self.telemetry.record_event(
                        event_type=EventType.MESSAGE_PROCESSED,
                        correlation_id=message.correlation_id,
                        agent_id=recipient,
                        message_id=message_id,
                        details={
                            "sender": message.sender,
                            "message_type": message.message_type.value
                        }
                    )
                
    def handle_failure(self, message_id: str, recipient: str) -> bool:
        """Handle message processing failure
        Returns True if should retry, False if max retries exceeded
        """
        if not self.store:
            return False
            
        message = self.store.get_message(message_id)
        if not message:
            return False
            
        retry_count = self.store.get_retry_count(message_id) + 1
            
        if retry_count <= self.MAX_RETRIES:
            self.store.update_message_state(message_id, "pending", retry_count)
            
            if self.telemetry:
                self.telemetry.record_event(
                    event_type=EventType.RETRY,
                    correlation_id=message.correlation_id,
                    agent_id=recipient,
                    message_id=message_id,
                    details={
                        "retry_count": retry_count,
                        "max_retries": self.MAX_RETRIES
                    }
                )
            return True
            
        self.store.update_message_state(message_id, "failed", retry_count)
        
        if self.telemetry:
            self.telemetry.record_event(
                event_type=EventType.MESSAGE_FAILED,
                correlation_id=message.correlation_id,
                agent_id=recipient,
                message_id=message_id,
                details={
                    "retry_count": retry_count,
                    "max_retries": self.MAX_RETRIES,
                    "sender": message.sender,
                    "message_type": message.message_type.value
                }
            )
        return False 