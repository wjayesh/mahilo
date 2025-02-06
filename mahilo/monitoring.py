from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import logging
import json
from enum import Enum
import time
import threading
from collections import defaultdict

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

class MetricsCollector:
    """Collects and aggregates monitoring metrics"""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: defaultdict(float))
        self.event_counts = defaultdict(int)
        self._lock = threading.Lock()
        
    def record_event(self, event: MonitoringEvent):
        with self._lock:
            # Update event counts
            self.event_counts[event.event_type] += 1
            
            # Record agent-specific metrics
            if event.agent_id:
                agent_metrics = self.metrics[event.agent_id]
                
                if event.event_type == EventType.MESSAGE_PROCESSED:
                    agent_metrics["messages_processed"] += 1
                    if event.duration_ms:
                        agent_metrics["total_processing_time_ms"] += event.duration_ms
                        agent_metrics["avg_processing_time_ms"] = (
                            agent_metrics["total_processing_time_ms"] / 
                            agent_metrics["messages_processed"]
                        )
                
                elif event.event_type == EventType.MESSAGE_FAILED:
                    agent_metrics["messages_failed"] += 1
                
                elif event.event_type == EventType.RETRY:
                    agent_metrics["retries"] += 1
    
    def get_metrics(self, agent_id: Optional[str] = None) -> Dict:
        """Get current metrics, optionally filtered by agent"""
        with self._lock:
            if agent_id:
                return dict(self.metrics[agent_id])
            return {
                "event_counts": dict(self.event_counts),
                "agent_metrics": {
                    agent: dict(metrics)
                    for agent, metrics in self.metrics.items()
                }
            }

class MessageMonitor:
    """Central monitoring system for message and agent events"""
    
    def __init__(self, log_file: str = "mahilo_events.log"):
        self.metrics = MetricsCollector()
        
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