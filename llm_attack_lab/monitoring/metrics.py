"""
Metrics Collection Module

Provides comprehensive metrics collection for monitoring
attack simulations, defense effectiveness, and system performance.
"""

import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import json


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """Individual metric data point"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
            "unit": self.unit,
        }


@dataclass
class HistogramBucket:
    """Histogram bucket for distribution tracking"""
    le: float  # less than or equal
    count: int = 0


class MetricsCollector:
    """
    Centralized metrics collection and aggregation.

    Collects various metrics about:
    - Attack execution (count, success rate, detection rate)
    - Defense performance (blocks, warnings, response time)
    - System health (requests/sec, latency)
    - Session statistics
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timers: Dict[str, List[float]] = defaultdict(list)
        self._labels: Dict[str, Dict[str, str]] = {}
        self._start_time = datetime.now()
        self._metric_history: List[Metric] = []
        self._max_history = 10000
        self._observers: List[Callable[[Metric], None]] = []

    def add_observer(self, callback: Callable[[Metric], None]):
        """Add an observer for metric updates"""
        self._observers.append(callback)

    def _notify_observers(self, metric: Metric):
        """Notify all observers of a new metric"""
        for observer in self._observers:
            try:
                observer(metric)
            except Exception:
                pass

    def _record_metric(self, metric: Metric):
        """Record metric to history"""
        with self._lock:
            self._metric_history.append(metric)
            if len(self._metric_history) > self._max_history:
                self._metric_history = self._metric_history[-self._max_history:]
        self._notify_observers(metric)

    # Counter operations
    def increment(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] += value
            if labels:
                self._labels[key] = labels
            metric = Metric(
                name=name,
                value=self._counters[key],
                metric_type=MetricType.COUNTER,
                labels=labels or {},
            )
            self._record_metric(metric)

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value"""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0)

    # Gauge operations
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value"""
        with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value
            if labels:
                self._labels[key] = labels
            metric = Metric(
                name=name,
                value=value,
                metric_type=MetricType.GAUGE,
                labels=labels or {},
            )
            self._record_metric(metric)

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get current gauge value"""
        key = self._make_key(name, labels)
        return self._gauges.get(key)

    # Histogram operations
    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record an observation for histogram"""
        with self._lock:
            key = self._make_key(name, labels)
            self._histograms[key].append(value)
            if labels:
                self._labels[key] = labels
            metric = Metric(
                name=name,
                value=value,
                metric_type=MetricType.HISTOGRAM,
                labels=labels or {},
            )
            self._record_metric(metric)

    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict:
        """Get histogram statistics"""
        key = self._make_key(name, labels)
        values = self._histograms.get(key, [])
        if not values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}

        sorted_values = sorted(values)
        count = len(values)
        return {
            "count": count,
            "sum": sum(values),
            "avg": sum(values) / count,
            "min": min(values),
            "max": max(values),
            "p50": sorted_values[int(count * 0.5)] if count else 0,
            "p95": sorted_values[int(count * 0.95)] if count else 0,
            "p99": sorted_values[int(count * 0.99)] if count else 0,
        }

    # Timer operations
    def time(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations"""
        return TimerContext(self, name, labels)

    def record_time(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None):
        """Record a timing value"""
        with self._lock:
            key = self._make_key(name, labels)
            self._timers[key].append(duration)
            if labels:
                self._labels[key] = labels
            metric = Metric(
                name=name,
                value=duration,
                metric_type=MetricType.TIMER,
                labels=labels or {},
                unit="seconds",
            )
            self._record_metric(metric)

    def get_timer_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict:
        """Get timer statistics"""
        key = self._make_key(name, labels)
        return self._compute_stats(self._timers.get(key, []))

    # Attack-specific metrics
    def record_attack(self, attack_type: str, success: bool, detected: bool, duration: float):
        """Record an attack execution"""
        labels = {"attack_type": attack_type}
        self.increment("attacks_total", labels=labels)
        if success:
            self.increment("attacks_successful", labels=labels)
        if detected:
            self.increment("attacks_detected", labels=labels)
        self.record_time("attack_duration", duration, labels=labels)

    def record_defense_action(self, defense_type: str, action: str, threat_level: str):
        """Record a defense action"""
        labels = {"defense_type": defense_type, "action": action, "threat_level": threat_level}
        self.increment("defense_actions_total", labels=labels)

    def record_request(self, duration: float, blocked: bool = False):
        """Record a request"""
        self.increment("requests_total")
        if blocked:
            self.increment("requests_blocked")
        self.record_time("request_latency", duration)

    # Utility methods
    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create a unique key for a metric with labels"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _compute_stats(self, values: List[float]) -> Dict:
        """Compute statistics for a list of values"""
        if not values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }

    def get_all_metrics(self) -> Dict:
        """Get all current metrics"""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: self.get_histogram_stats(k) for k in self._histograms},
                "timers": {k: self.get_timer_stats(k) for k in self._timers},
                "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
            }

    def get_attack_summary(self) -> Dict:
        """Get attack-specific summary"""
        total = self.get_counter("attacks_total")
        successful = self.get_counter("attacks_successful")
        detected = self.get_counter("attacks_detected")

        # Get breakdown by attack type
        by_type = {}
        with self._lock:
            for key, value in self._counters.items():
                if key.startswith("attacks_total{attack_type="):
                    # Extract attack type from key like "attacks_total{attack_type=prompt_injection}"
                    attack_type = key.split("=")[1].rstrip("}")
                    display_name = attack_type.replace("_", " ").title()
                    by_type[display_name] = int(value)

        return {
            "total_attacks": int(total),
            "successful_attacks": int(successful),
            "detected_attacks": int(detected),
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "detection_rate": (detected / total * 100) if total > 0 else 0,
            "attack_duration": self.get_timer_stats("attack_duration"),
            "by_type": by_type,
        }

    def get_defense_summary(self) -> Dict:
        """Get defense-specific summary"""
        total_actions = self.get_counter("defense_actions_total")
        blocked = self.get_counter("requests_blocked")
        total_requests = self.get_counter("requests_total")

        return {
            "total_defense_actions": int(total_actions),
            "blocked_requests": int(blocked),
            "total_requests": int(total_requests),
            "block_rate": (blocked / total_requests * 100) if total_requests > 0 else 0,
            "request_latency": self.get_timer_stats("request_latency"),
        }

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        with self._lock:
            for key, value in self._counters.items():
                lines.append(f"# TYPE {key.split('{')[0]} counter")
                lines.append(f"{key} {value}")

            for key, value in self._gauges.items():
                lines.append(f"# TYPE {key.split('{')[0]} gauge")
                lines.append(f"{key} {value}")

        return "\n".join(lines)

    def export_json(self) -> str:
        """Export all metrics as JSON"""
        return json.dumps(self.get_all_metrics(), indent=2, default=str)

    def reset(self):
        """Reset all metrics"""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()
            self._labels.clear()
            self._metric_history.clear()
            self._start_time = datetime.now()


class TimerContext:
    """Context manager for timing operations"""

    def __init__(self, collector: MetricsCollector, name: str, labels: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.name = name
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.collector.record_time(self.name, duration, self.labels)
        return False


# Global metrics collector instance
_global_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector"""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector
