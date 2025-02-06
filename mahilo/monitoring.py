from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import logging
import json
from enum import Enum
import time
import threading
from collections import defaultdict
import sqlite3

class EventType(Enum):
    # Message events
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_PROCESSED = "message_processed"
    MESSAGE_FAILED = "message_failed"
    
    # Agent events
    AGENT_ACTIVATED = "agent_activated"
    AGENT_DEACTIVATED = "agent_deactivated"
    
    # Processing events
    PROCESSING_STARTED = "processing_started"
    PROCESSING_COMPLETED = "processing_completed"
    
    # System events
    ERROR = "error"
    RETRY = "retry"
    QUEUE_LENGTH_CHANGED = "queue_length_changed"
    CONNECTION_EVENT = "connection_event"

@dataclass
class MonitoringEvent:
    event_type: EventType
    timestamp: float
    correlation_id: Optional[str]
    agent_id: Optional[str]
    message_id: Optional[str]
    details: Dict
    duration_ms: Optional[float] = None

class MetricsStore:
    """Persistent storage for monitoring metrics"""
    
    def __init__(self, db_path: str = "metrics.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Events table for raw event data
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    correlation_id TEXT,
                    agent_id TEXT,
                    message_id TEXT,
                    details TEXT,
                    duration_ms REAL
                )
            """)
            
            # Aggregated metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_metrics (
                    agent_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (agent_id, metric_name)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_id ON events(agent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
    
    def record_event(self, event: MonitoringEvent):
        """Record a monitoring event"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO events (
                    event_type, timestamp, correlation_id, agent_id,
                    message_id, details, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_type.value,
                event.timestamp,
                event.correlation_id,
                event.agent_id,
                event.message_id,
                json.dumps(event.details),
                event.duration_ms
            ))
            
            # Update aggregated metrics
            if event.agent_id:
                self._update_agent_metrics(conn, event)
    
    def _update_agent_metrics(self, conn: sqlite3.Connection, event: MonitoringEvent):
        """Update aggregated metrics for an agent"""
        timestamp = time.time()
        
        if event.event_type == EventType.MESSAGE_PROCESSED:
            self._increment_metric(conn, event.agent_id, "messages_processed", 1, timestamp)
            if event.duration_ms:
                # Update average processing time
                current_avg = self._get_metric(conn, event.agent_id, "avg_processing_time_ms")
                current_count = self._get_metric(conn, event.agent_id, "messages_processed")
                if current_count > 0:
                    new_avg = ((current_avg * (current_count - 1)) + event.duration_ms) / current_count
                    self._set_metric(conn, event.agent_id, "avg_processing_time_ms", new_avg, timestamp)
        
        elif event.event_type == EventType.MESSAGE_FAILED:
            self._increment_metric(conn, event.agent_id, "messages_failed", 1, timestamp)
        
        elif event.event_type == EventType.RETRY:
            self._increment_metric(conn, event.agent_id, "retries", 1, timestamp)
    
    def _increment_metric(self, conn: sqlite3.Connection, agent_id: str, 
                         metric_name: str, increment: float, timestamp: float):
        """Increment a metric value"""
        conn.execute("""
            INSERT INTO agent_metrics (agent_id, metric_name, metric_value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(agent_id, metric_name) DO UPDATE SET
                metric_value = metric_value + ?,
                updated_at = ?
        """, (agent_id, metric_name, increment, timestamp, increment, timestamp))
    
    def _set_metric(self, conn: sqlite3.Connection, agent_id: str, 
                    metric_name: str, value: float, timestamp: float):
        """Set a metric value"""
        conn.execute("""
            INSERT INTO agent_metrics (agent_id, metric_name, metric_value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(agent_id, metric_name) DO UPDATE SET
                metric_value = ?,
                updated_at = ?
        """, (agent_id, metric_name, value, timestamp, value, timestamp))
    
    def _get_metric(self, conn: sqlite3.Connection, agent_id: str, metric_name: str) -> float:
        """Get current value of a metric"""
        row = conn.execute("""
            SELECT metric_value FROM agent_metrics
            WHERE agent_id = ? AND metric_name = ?
        """, (agent_id, metric_name)).fetchone()
        return row[0] if row else 0
    
    def get_agent_metrics(self, agent_id: Optional[str] = None) -> Dict:
        """Get metrics for an agent or all agents"""
        with sqlite3.connect(self.db_path) as conn:
            if agent_id:
                rows = conn.execute("""
                    SELECT metric_name, metric_value
                    FROM agent_metrics
                    WHERE agent_id = ?
                """, (agent_id,)).fetchall()
                return {row[0]: row[1] for row in rows}
            
            # Get all agent metrics
            rows = conn.execute("""
                SELECT agent_id, metric_name, metric_value
                FROM agent_metrics
            """).fetchall()
            
            metrics = defaultdict(dict)
            for row in rows:
                metrics[row[0]][row[1]] = row[2]
            return dict(metrics)
    
    def cleanup_old_events(self, max_age_days: int = 30):
        """Clean up old events while preserving aggregated metrics"""
        cutoff = time.time() - (max_age_days * 24 * 60 * 60)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))

class MetricsCollector:
    """Collects and aggregates monitoring metrics"""
    
    def __init__(self, store: Optional[MetricsStore] = None):
        self.store = store
        self._lock = threading.Lock()
        
    def record_event(self, event: MonitoringEvent):
        with self._lock:
            if self.store:
                self.store.record_event(event)
    
    def get_metrics(self, agent_id: Optional[str] = None) -> Dict:
        """Get current metrics, optionally filtered by agent"""
        if self.store:
            return self.store.get_agent_metrics(agent_id)
        return {}

class MessageMonitor:
    """Central monitoring system for message and agent events"""
    
    def __init__(self, metrics_db: str = "metrics.db", log_file: str = "mahilo_events.log"):
        self.metrics = MetricsCollector(MetricsStore(metrics_db))
        
        # Configure logging
        self.logger = logging.getLogger("mahilo.monitoring")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        
        # Processing time tracking
        self.processing_start_times: Dict[str, float] = {}
    
    def record_event(self, 
                    event_type: EventType,
                    correlation_id: Optional[str] = None,
                    agent_id: Optional[str] = None,
                    message_id: Optional[str] = None,
                    details: Dict = None):
        """Record a monitoring event"""
        
        timestamp = time.time()
        duration_ms = None
        
        # Calculate duration for processing events
        if event_type == EventType.PROCESSING_STARTED:
            self.processing_start_times[message_id] = timestamp
        elif event_type == EventType.PROCESSING_COMPLETED:
            start_time = self.processing_start_times.get(message_id)
            if start_time:
                duration_ms = (timestamp - start_time) * 1000
                del self.processing_start_times[message_id]
        
        event = MonitoringEvent(
            event_type=event_type,
            timestamp=timestamp,
            correlation_id=correlation_id,
            agent_id=agent_id,
            message_id=message_id,
            details=details or {},
            duration_ms=duration_ms
        )
        
        # Update metrics
        self.metrics.record_event(event)
        
        # Log the event
        log_data = {
            "event_type": event_type.value,
            "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
            "correlation_id": correlation_id,
            "agent_id": agent_id,
            "message_id": message_id,
            "duration_ms": duration_ms,
            **details
        }
        self.logger.info(json.dumps(log_data))
    
    def get_metrics(self, agent_id: Optional[str] = None) -> Dict:
        """Get current metrics"""
        return self.metrics.get_metrics(agent_id)
    
    def get_agent_performance(self, agent_id: str) -> Dict:
        """Get detailed performance metrics for an agent"""
        metrics = self.metrics.get_metrics(agent_id)
        return {
            "messages_processed": metrics.get("messages_processed", 0),
            "messages_failed": metrics.get("messages_failed", 0),
            "avg_processing_time_ms": metrics.get("avg_processing_time_ms", 0),
            "retries": metrics.get("retries", 0)
        } 