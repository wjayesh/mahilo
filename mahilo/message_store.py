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

    @abstractmethod
    def get_messages(self, 
                    sender: Optional[str] = None,
                    recipient: Optional[str] = None,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    limit: Optional[int] = None) -> List[MessageEnvelope]:
        """Get messages based on flexible criteria.
        
        This function can:
        a) Get messages sent BY a specific agent (only sender specified)
        b) Get messages sent TO a specific agent (only recipient specified)
        c) Get messages from a specific sender TO a specific recipient (both specified)
        d) Get recent messages across all agents (neither specified)
        
        Args:
            sender: Optional sender to filter by
            recipient: Optional recipient to filter by
            start_time: Optional start time for time range filter
            end_time: Optional end time for time range filter
            limit: Optional limit on number of messages returned
        """
        pass

    @abstractmethod
    def get_conversation_history(self, agent1: str, agent2: str,
                               start_time: Optional[datetime] = None,
                               end_time: Optional[datetime] = None,
                               limit: Optional[int] = None) -> List[MessageEnvelope]:
        """Get conversation history between two agents (messages in both directions)"""
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

    def get_messages(self,
                    sender: Optional[str] = None,
                    recipient: Optional[str] = None,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    limit: Optional[int] = None) -> List[MessageEnvelope]:
        """Get messages based on flexible criteria."""
        query_parts = ["SELECT * FROM messages"]
        params = []
        where_clauses = []
        
        # Handle sender/recipient filtering
        if sender and recipient:
            where_clauses.append("sender = ? AND recipient = ?")
            params.extend([sender, recipient])
        elif sender:
            where_clauses.append("sender = ?")
            params.append(sender)
        elif recipient:
            where_clauses.append("recipient = ?")
            params.append(recipient)
        
        # Add time range filters
        if start_time:
            where_clauses.append("timestamp >= ?")
            params.append(start_time.timestamp())
        if end_time:
            where_clauses.append("timestamp <= ?")
            params.append(end_time.timestamp())
        
        # Combine where clauses if any exist
        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))
        
        # Add ordering
        query_parts.append("ORDER BY timestamp DESC")
        
        # Add limit if specified
        if limit is not None:
            query_parts.append("LIMIT ?")
            params.append(limit)
        
        query = " ".join(query_parts)
        
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_envelope(row) for row in rows]

    def get_conversation_history(self, agent1: str, agent2: str,
                               start_time: Optional[datetime] = None,
                               end_time: Optional[datetime] = None,
                               limit: Optional[int] = None) -> List[MessageEnvelope]:
        """Get conversation history between two agents (messages in both directions)"""
        query_parts = ["SELECT * FROM messages"]
        params = []
        
        # Get messages in both directions between the agents
        where_clause = "((sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?))"
        params.extend([agent1, agent2, agent2, agent1])
        query_parts.append("WHERE " + where_clause)
        
        # Add time range filters
        if start_time:
            query_parts.append("AND timestamp >= ?")
            params.append(start_time.timestamp())
        if end_time:
            query_parts.append("AND timestamp <= ?")
            params.append(end_time.timestamp())
            
        # Add ordering
        query_parts.append("ORDER BY timestamp DESC")
        
        # Add limit if specified
        if limit is not None:
            query_parts.append("LIMIT ?")
            params.append(limit)
        
        query = " ".join(query_parts)
        
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_envelope(row) for row in rows] 