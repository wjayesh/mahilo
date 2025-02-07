from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import logging
import json
from enum import Enum
import time
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from opentelemetry.metrics import Counter, UpDownCounter, Histogram
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

class EventType(Enum):
    # Message events
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_PROCESSED = "message_processed"
    MESSAGE_FAILED = "message_failed"
    
    # Agent events
    AGENT_ACTIVATED = "agent_activated"
    AGENT_DEACTIVATED = "agent_deactivated"
    AGENT_REGISTERED = "agent_registered"
    AGENT_UNREGISTERED = "agent_unregistered"
    
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

class MahiloTelemetry:
    """OpenTelemetry-based monitoring for Mahilo"""
    
    def __init__(self, service_name: str = "mahilo"):
        # Set up resource
        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: service_name
        })
        
        # Set up tracing
        trace.set_tracer_provider(TracerProvider(resource=resource))
        self.tracer = trace.get_tracer(__name__)
        
        # Set up metrics
        metrics.set_meter_provider(MeterProvider(resource=resource))
        self.meter = metrics.get_meter(__name__)
        
        # Create metrics
        self._setup_metrics()
        
        # Configure logging
        self.logger = logging.getLogger("mahilo.monitoring")
        
    def _setup_metrics(self):
        """Set up OpenTelemetry metrics"""
        # Message metrics
        self.message_counter = self.meter.create_counter(
            "mahilo.messages",
            description="Number of messages processed",
            unit="1"
        )
        
        self.message_processing_time = self.meter.create_histogram(
            "mahilo.message.processing_time",
            description="Time taken to process messages",
            unit="ms"
        )
        
        self.message_retry_counter = self.meter.create_counter(
            "mahilo.message.retries",
            description="Number of message retries",
            unit="1"
        )
        
        self.message_failure_counter = self.meter.create_counter(
            "mahilo.message.failures",
            description="Number of message failures",
            unit="1"
        )
        
        # Queue metrics
        self.queue_size = self.meter.create_up_down_counter(
            "mahilo.queue.size",
            description="Current queue size",
            unit="1"
        )
        
        # Agent metrics
        self.active_agents = self.meter.create_up_down_counter(
            "mahilo.agents.active",
            description="Number of active agents",
            unit="1"
        )
    
    def record_event(self, 
                    event_type: EventType,
                    correlation_id: Optional[str] = "",
                    agent_id: Optional[str] = "",
                    message_id: Optional[str] = "",
                    details: Dict = {}):
        """Record a monitoring event using OpenTelemetry"""
        attributes = {
            "event_type": event_type.value,
            "agent_id": agent_id or "",
            "message_id": message_id or "",
            "correlation_id": correlation_id or ""
        }
        
        # Start a span for the event
        with self.tracer.start_as_current_span(
            f"mahilo.event.{event_type.value}",
            attributes=attributes
        ) as span:
            # Record metrics based on event type
            if event_type == EventType.MESSAGE_PROCESSED:
                self.message_counter.add(1, attributes)
                if "duration_ms" in details:
                    self.message_processing_time.record(
                        details["duration_ms"],
                        attributes
                    )
                span.set_status(Status(StatusCode.OK))
                
            elif event_type == EventType.MESSAGE_FAILED:
                self.message_failure_counter.add(1, attributes)
                span.set_status(Status(StatusCode.ERROR))
                if "error" in details:
                    span.record_exception(details["error"])
                
            elif event_type == EventType.RETRY:
                self.message_retry_counter.add(1, attributes)
                
            elif event_type == EventType.QUEUE_LENGTH_CHANGED:
                self.queue_size.add(
                    details.get("queue_length", 0) - details.get("previous_length", 0),
                    attributes
                )
                
            elif event_type == EventType.AGENT_ACTIVATED:
                self.active_agents.add(1, attributes)
                
            elif event_type == EventType.AGENT_DEACTIVATED:
                self.active_agents.add(-1, attributes)
            
            # Add event details to span
            for key, value in details.items():
                span.set_attribute(key, str(value))
            
            # Log the event
            self.logger.info(json.dumps({
                "event_type": event_type.value,
                "timestamp": datetime.fromtimestamp(time.time()).isoformat(),
                "correlation_id": correlation_id,
                "agent_id": agent_id,
                "message_id": message_id,
                **details
            }))
    
    def start_processing_span(self, message_id: str, agent_id: str) -> trace.Span:
        """Start a processing span for message handling"""
        return self.tracer.start_span(
            "mahilo.message.processing",
            attributes={
                "message_id": message_id,
                "agent_id": agent_id
            }
        )
    
    def get_metrics(self) -> Dict:
        """Get current metrics (Note: In OpenTelemetry, metrics are typically
        collected by the backend, this is just for compatibility)"""
        # This would typically be handled by your metrics backend
        return {}

    def mark_span_success(self, span: trace.Span) -> None:
        """Mark a span as successful"""
        span.set_status(Status(StatusCode.OK))

    def mark_span_error(self, span: trace.Span, exception: Exception) -> None:
        """Mark a span as failed with an error"""
        span.set_status(Status(StatusCode.ERROR))
        span.record_exception(exception)