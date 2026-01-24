"""
OpenTelemetry Integration Module

Provides comprehensive observability with:
- Distributed tracing
- Metrics export to Prometheus/VictoriaMetrics
- Integration with OpenTelemetry Collector
"""
from __future__ import annotations

import os
import time
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
from contextlib import contextmanager

# Type checking imports
if TYPE_CHECKING:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.resources import Resource

# OpenTelemetry imports with fallback
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    metrics = None

# Prometheus exporter for local metrics endpoint
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    from prometheus_client import start_http_server as start_prometheus_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


logger = logging.getLogger(__name__)


class OTelConfig:
    """Configuration for OpenTelemetry"""

    def __init__(self):
        self.service_name = os.getenv("OTEL_SERVICE_NAME", "llm-attack-lab")
        self.service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
        self.otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
        self.prometheus_port = int(os.getenv("PROMETHEUS_METRICS_PORT", "8000"))
        self.enable_tracing = os.getenv("OTEL_ENABLE_TRACING", "true").lower() == "true"
        self.enable_metrics = os.getenv("OTEL_ENABLE_METRICS", "true").lower() == "true"


class OTelManager:
    """
    OpenTelemetry Manager for LLM Attack Lab

    Handles initialization and management of:
    - Tracers for distributed tracing
    - Meters for metrics collection
    - Export to OTLP collector and Prometheus
    """

    def __init__(self, config: Optional[OTelConfig] = None):
        self.config = config or OTelConfig()
        self._tracer = None
        self._meter = None
        self._initialized = False

        # Prometheus metrics (local)
        self._prom_metrics: Dict[str, Any] = {}

    def initialize(self) -> bool:
        """Initialize OpenTelemetry providers"""
        if self._initialized:
            return True

        if not OTEL_AVAILABLE:
            logger.warning("OpenTelemetry packages not available. Running without OTEL.")
            self._initialize_prometheus_only()
            return False

        try:
            # Create resource
            resource = Resource.create({
                SERVICE_NAME: self.config.service_name,
                SERVICE_VERSION: self.config.service_version,
                "deployment.environment": os.getenv("ENVIRONMENT", "development"),
            })

            # Initialize tracing
            if self.config.enable_tracing:
                self._init_tracing(resource)

            # Initialize metrics
            if self.config.enable_metrics:
                self._init_metrics(resource)

            # Start Prometheus endpoint
            self._init_prometheus()

            self._initialized = True
            logger.info(f"OpenTelemetry initialized for {self.config.service_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")
            self._initialize_prometheus_only()
            return False

    def _init_tracing(self, resource):
        """Initialize tracing provider"""
        tracer_provider = TracerProvider(resource=resource)

        try:
            otlp_exporter = OTLPSpanExporter(endpoint=self.config.otlp_endpoint, insecure=True)
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        except Exception as e:
            logger.warning(f"Could not connect to OTLP endpoint: {e}")

        trace.set_tracer_provider(tracer_provider)
        self._tracer = trace.get_tracer(self.config.service_name)

    def _init_metrics(self, resource):
        """Initialize metrics provider"""
        try:
            otlp_metric_exporter = OTLPMetricExporter(endpoint=self.config.otlp_endpoint, insecure=True)
            metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter, export_interval_millis=10000)
            meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        except Exception as e:
            logger.warning(f"Could not create OTLP metric exporter: {e}")
            meter_provider = MeterProvider(resource=resource)

        metrics.set_meter_provider(meter_provider)
        self._meter = metrics.get_meter(self.config.service_name)

    def _init_prometheus(self):
        """Initialize Prometheus metrics endpoint"""
        if not PROMETHEUS_AVAILABLE:
            return

        try:
            # Create Prometheus metrics
            self._prom_metrics["attacks_total"] = Counter(
                "llm_attacks_total",
                "Total number of attack simulations",
                ["attack_type", "success", "detected"]
            )
            self._prom_metrics["attack_duration"] = Histogram(
                "llm_attack_duration_seconds",
                "Attack simulation duration",
                ["attack_type"],
                buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
            )
            self._prom_metrics["defense_actions"] = Counter(
                "llm_defense_actions_total",
                "Total defense actions taken",
                ["defense_type", "action", "threat_level"]
            )
            self._prom_metrics["requests_total"] = Counter(
                "llm_requests_total",
                "Total requests processed",
                ["endpoint", "status"]
            )
            self._prom_metrics["request_latency"] = Histogram(
                "llm_request_latency_seconds",
                "Request latency",
                ["endpoint"],
                buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
            )
            self._prom_metrics["security_level"] = Gauge(
                "llm_security_level",
                "Current security level (0-4)"
            )
            self._prom_metrics["compromised_status"] = Gauge(
                "llm_compromised_status",
                "System compromise status (0=safe, 1=compromised)"
            )

            # Start Prometheus HTTP server in a separate thread
            start_prometheus_server(self.config.prometheus_port)
            logger.info(f"Prometheus metrics server started on port {self.config.prometheus_port}")

        except Exception as e:
            logger.error(f"Failed to start Prometheus server: {e}")

    def _initialize_prometheus_only(self):
        """Fallback: Initialize only Prometheus metrics"""
        self._init_prometheus()
        self._initialized = True

    @property
    def tracer(self):
        """Get the tracer instance"""
        return self._tracer

    @property
    def meter(self):
        """Get the meter instance"""
        return self._meter

    @contextmanager
    def trace_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Context manager for creating traced spans"""
        if self._tracer:
            with self._tracer.start_as_current_span(name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))
                try:
                    yield span
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        else:
            yield None

    def record_attack(self, attack_type: str, success: bool, detected: bool, duration: float):
        """Record attack metrics"""
        # Prometheus metrics
        if "attacks_total" in self._prom_metrics:
            self._prom_metrics["attacks_total"].labels(
                attack_type=attack_type,
                success=str(success).lower(),
                detected=str(detected).lower()
            ).inc()

        if "attack_duration" in self._prom_metrics:
            self._prom_metrics["attack_duration"].labels(
                attack_type=attack_type
            ).observe(duration)

        # OTEL metrics
        if self._meter:
            counter = self._meter.create_counter(
                "attacks_total",
                description="Total attack simulations"
            )
            counter.add(1, {"attack_type": attack_type, "success": str(success), "detected": str(detected)})

    def record_defense(self, defense_type: str, action: str, threat_level: str):
        """Record defense action metrics"""
        if "defense_actions" in self._prom_metrics:
            self._prom_metrics["defense_actions"].labels(
                defense_type=defense_type,
                action=action,
                threat_level=threat_level
            ).inc()

    def record_request(self, endpoint: str, status: str, duration: float):
        """Record request metrics"""
        if "requests_total" in self._prom_metrics:
            self._prom_metrics["requests_total"].labels(
                endpoint=endpoint,
                status=status
            ).inc()

        if "request_latency" in self._prom_metrics:
            self._prom_metrics["request_latency"].labels(
                endpoint=endpoint
            ).observe(duration)

    def set_security_level(self, level: int):
        """Update security level gauge"""
        if "security_level" in self._prom_metrics:
            self._prom_metrics["security_level"].set(level)

    def set_compromised_status(self, compromised: bool):
        """Update compromised status gauge"""
        if "compromised_status" in self._prom_metrics:
            self._prom_metrics["compromised_status"].set(1 if compromised else 0)


# Global OTel manager instance
_otel_manager: Optional[OTelManager] = None


def get_otel_manager() -> OTelManager:
    """Get or create the global OTel manager"""
    global _otel_manager
    if _otel_manager is None:
        _otel_manager = OTelManager()
    return _otel_manager


def init_telemetry() -> OTelManager:
    """Initialize and return the telemetry manager"""
    manager = get_otel_manager()
    manager.initialize()
    return manager
