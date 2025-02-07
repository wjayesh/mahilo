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
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader

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
        
        # Store traces and metrics in memory
        self.traces = []
        self.metrics_data = {
            "messages": 0,
            "message_failures": 0,
            "message_retries": 0,
            "active_agents": 0,
            "queue_size": 0,
            "processing_times": []  # List to store processing times for histogram
        }
        
        # Set up tracing with in-memory storage
        trace_provider = TracerProvider(resource=resource)
        class InMemorySpanExporter:
            def __init__(self, traces_list):
                self.traces = traces_list
            
            def export(self, spans):
                for span in spans:
                    self.traces.append({
                        "name": span.name,
                        "trace_id": format(span.context.trace_id, "032x"),
                        "span_id": format(span.context.span_id, "016x"),
                        "parent_id": format(span.parent.span_id, "016x") if span.parent else None,
                        "start_time": span.start_time,
                        "end_time": span.end_time,
                        "attributes": dict(span.attributes),
                        "status": span.status.status_code.name,
                        "events": [{
                            "name": event.name,
                            "timestamp": event.timestamp,
                            "attributes": dict(event.attributes)
                        } for event in span.events]
                    })
                return True
            
            def shutdown(self):
                pass
        
        trace_provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter(self.traces)))
        trace.set_tracer_provider(trace_provider)
        self.tracer = trace.get_tracer(__name__)
        
        # Set up metrics (now updating in-memory dict instead of console)
        meter_provider = MeterProvider(resource=resource)
        metrics.set_meter_provider(meter_provider)
        self.meter = metrics.get_meter(__name__)
        
        # Create metrics
        self._setup_metrics()
        
        # Configure logging
        self.logger = logging.getLogger("mahilo.monitoring")
        
        # Log initialization
        self.logger.info(f"MahiloTelemetry initialized with in-memory storage for service: {service_name}")
        
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
        
        # Queue size should be a gauge since it represents a current value
        self.queue_size = self.meter.create_observable_gauge(
            "mahilo.queue.size",
            description="Current queue size",
            unit="1",
            callbacks=[lambda result: result.observe(self.metrics_data["queue_size"])]
        )
        
        # Agent metrics - this should stay as up_down_counter since we're tracking cumulative changes
        self.active_agents = self.meter.create_up_down_counter(
            "mahilo.agents.active",
            description="Number of active agents",
            unit="1"
        )

    def record_event(self, 
                    event_type: EventType,
                    correlation_id: Optional[str] = None,
                    agent_id: Optional[str] = None,
                    message_id: Optional[str] = None,
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
            # Update metrics based on event type
            if event_type == EventType.MESSAGE_PROCESSED:
                self.message_counter.add(1, attributes)
                self.metrics_data["messages"] += 1
                if "duration_ms" in details:
                    duration = details["duration_ms"]
                    self.message_processing_time.record(duration, attributes)
                    self.metrics_data["processing_times"].append(duration)
                span.set_status(Status(StatusCode.OK))
                
            elif event_type == EventType.MESSAGE_FAILED:
                self.message_failure_counter.add(1, attributes)
                self.metrics_data["message_failures"] += 1
                span.set_status(Status(StatusCode.ERROR))
                if "error" in details:
                    span.record_exception(details["error"])
                
            elif event_type == EventType.RETRY:
                self.message_retry_counter.add(1, attributes)
                self.metrics_data["message_retries"] += 1
                
            elif event_type == EventType.QUEUE_LENGTH_CHANGED:
                # For queue size, we just set the new value since it's a gauge
                new_size = details.get("queue_length", 0)
                self.metrics_data["queue_size"] = new_size
                # The gauge will pick up this value via its callback
                
            elif event_type == EventType.AGENT_ACTIVATED:
                self.active_agents.add(1, attributes)
                self.metrics_data["active_agents"] += 1
                
            elif event_type == EventType.AGENT_DEACTIVATED:
                self.active_agents.add(-1, attributes)
                self.metrics_data["active_agents"] -= 1
            
            # Add event details to span
            for key, value in details.items():
                span.set_attribute(key, str(value))
            
            # Log the event (keeping minimal logging)
            self.logger.debug(json.dumps({
                "event_type": event_type.value,
                "timestamp": datetime.fromtimestamp(time.time()).isoformat(),
                "correlation_id": correlation_id,
                "agent_id": agent_id,
                "message_id": message_id
            }))

    def get_metrics(self, agent_id: Optional[str] = None) -> Dict:
        """Get current metrics"""
        metrics = {
            "messages_processed": self.metrics_data["messages"],
            "message_failures": self.metrics_data["message_failures"],
            "message_retries": self.metrics_data["message_retries"],
            "active_agents": self.metrics_data["active_agents"],
            "queue_size": self.metrics_data["queue_size"],
        }
        
        # Calculate processing time statistics if we have data
        if self.metrics_data["processing_times"]:
            times = self.metrics_data["processing_times"]
            metrics["processing_time"] = {
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "count": len(times)
            }
        
        # Filter by agent if specified
        if agent_id:
            # Filter traces to get agent-specific metrics
            agent_traces = [t for t in self.traces if t["attributes"].get("agent_id") == agent_id]
            metrics["agent_specific"] = {
                "total_events": len(agent_traces),
                "errors": len([t for t in agent_traces if t["status"] == "ERROR"])
            }
        
        return metrics

    def get_traces(self, limit: int = 100, agent_id: Optional[str] = None) -> List[Dict]:
        """Get recent traces, optionally filtered by agent"""
        if agent_id:
            filtered_traces = [t for t in self.traces if t["attributes"].get("agent_id") == agent_id]
        else:
            filtered_traces = self.traces
            
        # Return most recent traces first
        return sorted(filtered_traces, key=lambda x: x["start_time"], reverse=True)[:limit]

    def start_processing_span(self, message_id: str, agent_id: str) -> trace.Span:
        """Start a processing span for message handling"""
        return self.tracer.start_span(
            "mahilo.message.processing",
            attributes={
                "message_id": message_id,
                "agent_id": agent_id
            }
        )

    def mark_span_success(self, span: trace.Span) -> None:
        """Mark a span as successful"""
        span.set_status(Status(StatusCode.OK))

    def mark_span_error(self, span: trace.Span, exception: Exception) -> None:
        """Mark a span as failed with an error"""
        span.set_status(Status(StatusCode.ERROR))
        span.record_exception(exception)