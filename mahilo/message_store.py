from abc import ABC, abstractmethod
from typing import List, Optional
import sqlite3
import json
from datetime import datetime, timedelta
from .message_protocol import MessageEnvelope, MessageType

class MessageState:
    PENDING = "pending"
    PROCESSED = "processed" 
    FAILED = "failed"

class MessageStore(ABC):
    """Protocol defining message persistence operations"""
    
    @abstractmethod
    def save_message(self, message: MessageEnvelope, state: str = MessageState.PENDING) -> None:
        """Save a message to persistent storage"""
        pass
    
    @abstractmethod
    def get_message(self, message_id: str) -> Optional[MessageEnvelope]:
        """Retrieve a message by ID"""
        pass
    
    @abstractmethod
    def get_pending_messages(self, recipient: str) -> List[MessageEnvelope]:
        """Get all pending messages for a recipient"""
        pass
    
    @abstractmethod
    def get_message_history(self, agent_id: str, 
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> List[MessageEnvelope]:
        """Get message history for an agent"""
        pass
    
    @abstractmethod
    def update_message_state(self, message_id: str, state: str, 
                           retry_count: Optional[int] = None) -> None:
        """Update message state and retry information"""
        pass
    
    @abstractmethod
    def cleanup_old_messages(self, max_age_days: int = 30) -> None:
        """Remove processed messages older than specified age"""
        pass

    @abstractmethod
    def get_retry_count(self, message_id: str) -> int:
        """Get the current retry count for a message"""
        pass

class SQLiteMessageStore(MessageStore):
    """SQLite implementation of MessageStore"""
    
    def __init__(self, db_path: str = "messages.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    correlation_id TEXT,
                    reply_to TEXT,
                    signature TEXT,
                    state TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    last_retry REAL,
                    created_at REAL NOT NULL
                )
            """)
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_message_id ON messages(message_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sender ON messages(sender)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_recipient ON messages(recipient)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_state ON messages(state)")
    
    def save_message(self, message: MessageEnvelope, state: str = MessageState.PENDING) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO messages (
                    message_id, sender, recipient, message_type, payload,
                    timestamp, correlation_id, reply_to, signature,
                    state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.message_id, message.sender, message.recipient,
                message.message_type.value, message.payload, message.timestamp,
                message.correlation_id, message.reply_to, message.signature,
                state, datetime.now().timestamp()
            ))
    
    def get_message(self, message_id: str) -> Optional[MessageEnvelope]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM messages WHERE message_id = ?", 
                (message_id,)
            ).fetchone()
            
            if row:
                return self._row_to_envelope(row)
            return None
    
    def get_pending_messages(self, recipient: str) -> List[MessageEnvelope]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE recipient = ? AND state = ?",
                (recipient, MessageState.PENDING)
            ).fetchall()
            return [self._row_to_envelope(row) for row in rows]
    
    def get_message_history(self, agent_id: str, 
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> List[MessageEnvelope]:
        query = """
            SELECT * FROM messages 
            WHERE (sender = ? OR recipient = ?)
        """
        params = [agent_id, agent_id]
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.timestamp())
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.timestamp())
            
        query += " ORDER BY timestamp DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_envelope(row) for row in rows]
    
    def update_message_state(self, message_id: str, state: str, 
                           retry_count: Optional[int] = None) -> None:
        query = """
            UPDATE messages 
            SET state = ?,
                last_retry = ?
        """
        params = [state, datetime.now().timestamp()]
        
        if retry_count is not None:
            query += ", retry_count = ?"
            params.append(retry_count)
            
        query += " WHERE message_id = ?"
        params.append(message_id)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query, params)
    
    def cleanup_old_messages(self, max_age_days: int = 30) -> None:
        cutoff = datetime.now() - timedelta(days=max_age_days)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM messages WHERE state = ? AND timestamp < ?",
                (MessageState.PROCESSED, cutoff.timestamp())
            )
    
    def get_retry_count(self, message_id: str) -> int:
        """Get the current retry count for a message"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT retry_count FROM messages WHERE message_id = ?",
                (message_id,)
            ).fetchone()
            return row[0] if row else 0
    
    def _row_to_envelope(self, row) -> MessageEnvelope:
        """Convert a database row to MessageEnvelope"""
        return MessageEnvelope(
            message_id=row[0],
            sender=row[1],
            recipient=row[2],
            message_type=MessageType(row[3]),
            payload=row[4],
            timestamp=row[5],
            correlation_id=row[6],
            reply_to=row[7],
            signature=row[8]
        ) 