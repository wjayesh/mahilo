import uuid
import time
import json
import jwt
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from enum import Enum

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
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key
        self.pending_messages: Dict[str, List[MessageEnvelope]] = {}
        self.retry_counts: Dict[str, int] = {}
        self.MAX_RETRIES = 3
        
    def send_message(self, message: MessageEnvelope) -> None:
        """Queue a message for delivery"""
        if message.recipient not in self.pending_messages:
            self.pending_messages[message.recipient] = []
        self.pending_messages[message.recipient].append(message)
        
    def get_pending_messages(self, recipient: str) -> List[MessageEnvelope]:
        """Get pending messages for a recipient"""
        return self.pending_messages.get(recipient, [])
        
    def acknowledge_message(self, message_id: str, recipient: str) -> None:
        """Acknowledge successful message processing"""
        if recipient in self.pending_messages:
            self.pending_messages[recipient] = [
                msg for msg in self.pending_messages[recipient] 
                if msg.message_id != message_id
            ]
            if message_id in self.retry_counts:
                del self.retry_counts[message_id]
                
    def handle_failure(self, message_id: str, recipient: str) -> bool:
        """Handle message processing failure
        Returns True if should retry, False if max retries exceeded
        """
        self.retry_counts[message_id] = self.retry_counts.get(message_id, 0) + 1
        return self.retry_counts[message_id] <= self.MAX_RETRIES 