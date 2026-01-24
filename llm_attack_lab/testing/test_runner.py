"""
Continuous Test Runner with Streaming Support

Provides functionality to run pytest tests continuously and stream results
via Server-Sent Events (SSE) for real-time monitoring.
"""

import pytest
import threading
import queue
import time
import json
import sys
import io
from dataclasses import dataclass, field, asdict
from typing import Generator, Optional, List, Dict, Any
from enum import Enum


class TestStatus(str, Enum):
    """Status of a test execution"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """Result of a single test"""
    nodeid: str
    name: str
    status: TestStatus
    duration: float = 0.0
    message: str = ""
    output: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "nodeid": self.nodeid,
            "name": self.name,
            "status": self.status.value,
            "duration": self.duration,
            "message": self.message,
            "output": self.output,
            "timestamp": self.timestamp,
        }


@dataclass
class TestRunSummary:
    """Summary of a test run"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    status: str = "pending"

    def to_dict(self) -> dict:
        return asdict(self)


class StreamingTestPlugin:
    """Pytest plugin that streams test results to a queue"""

    def __init__(self, result_queue: queue.Queue):
        self.result_queue = result_queue
        self.summary = TestRunSummary()
        self.start_time = None

    def pytest_sessionstart(self, session):
        """Called before test session starts"""
        self.start_time = time.time()
        self.summary = TestRunSummary(status="running")
        self._emit_event("session_start", {"timestamp": self.start_time})

    def pytest_collection_finish(self, session):
        """Called after collection is finished"""
        self.summary.total = len(session.items)
        self._emit_event("collection_finish", {
            "total_tests": self.summary.total,
            "test_items": [item.nodeid for item in session.items]
        })

    def pytest_runtest_logstart(self, nodeid, location):
        """Called before running a test"""
        result = TestResult(
            nodeid=nodeid,
            name=nodeid.split("::")[-1],
            status=TestStatus.RUNNING,
        )
        self._emit_event("test_start", result.to_dict())

    def pytest_runtest_logreport(self, report):
        """Called after each test phase (setup, call, teardown)"""
        if report.when != "call":
            return

        status = TestStatus.PASSED
        message = ""
        output = ""

        if report.failed:
            status = TestStatus.FAILED
            self.summary.failed += 1
            if report.longrepr:
                message = str(report.longrepr)
        elif report.skipped:
            status = TestStatus.SKIPPED
            self.summary.skipped += 1
            if hasattr(report, 'wasxfail'):
                message = f"Expected fail: {report.wasxfail}"
            elif report.longrepr:
                message = str(report.longrepr[2]) if isinstance(report.longrepr, tuple) else str(report.longrepr)
        else:
            self.summary.passed += 1

        # Capture any captured output
        if hasattr(report, 'capstdout') and report.capstdout:
            output = report.capstdout
        elif hasattr(report, 'sections'):
            for section_name, content in report.sections:
                if 'stdout' in section_name.lower():
                    output += content

        result = TestResult(
            nodeid=report.nodeid,
            name=report.nodeid.split("::")[-1],
            status=status,
            duration=report.duration,
            message=message[:1000] if message else "",  # Truncate long messages
            output=output[:500] if output else "",  # Truncate output
        )
        self._emit_event("test_result", result.to_dict())

    def pytest_sessionfinish(self, session, exitstatus):
        """Called after test session finishes"""
        self.summary.duration = time.time() - self.start_time
        self.summary.status = "completed" if exitstatus == 0 else "failed"
        self._emit_event("session_finish", {
            "summary": self.summary.to_dict(),
            "exit_status": exitstatus,
        })

    def _emit_event(self, event_type: str, data: Any):
        """Put an event on the queue"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": time.time(),
        }
        self.result_queue.put(event)


class ContinuousTestRunner:
    """Runs tests continuously with streaming support"""

    def __init__(self, test_path: str = "tests"):
        self.test_path = test_path
        self.result_queue: queue.Queue = queue.Queue()
        self.is_running = False
        self.should_stop = False
        self.run_thread: Optional[threading.Thread] = None
        self.current_run_id = 0
        self.run_interval = 0  # 0 means single run, >0 means continuous
        self.subscribers: List[queue.Queue] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        """Subscribe to test events"""
        subscriber_queue = queue.Queue()
        with self._lock:
            self.subscribers.append(subscriber_queue)
        return subscriber_queue

    def unsubscribe(self, subscriber_queue: queue.Queue):
        """Unsubscribe from test events"""
        with self._lock:
            if subscriber_queue in self.subscribers:
                self.subscribers.remove(subscriber_queue)

    def _broadcast_event(self, event: dict):
        """Broadcast event to all subscribers"""
        with self._lock:
            dead_subscribers = []
            for sub_queue in self.subscribers:
                try:
                    sub_queue.put_nowait(event)
                except queue.Full:
                    dead_subscribers.append(sub_queue)
            for dead in dead_subscribers:
                self.subscribers.remove(dead)

    def start_continuous(self, interval: float = 30.0, test_args: Optional[List[str]] = None):
        """Start continuous test running"""
        if self.is_running:
            return {"status": "already_running", "run_id": self.current_run_id}

        self.run_interval = interval
        self.should_stop = False
        self.current_run_id += 1

        self.run_thread = threading.Thread(
            target=self._continuous_run_loop,
            args=(test_args or [],),
            daemon=True
        )
        self.run_thread.start()
        self.is_running = True

        return {"status": "started", "run_id": self.current_run_id, "interval": interval}

    def start_single_run(self, test_args: Optional[List[str]] = None):
        """Start a single test run"""
        if self.is_running:
            return {"status": "already_running", "run_id": self.current_run_id}

        self.run_interval = 0
        self.should_stop = False
        self.current_run_id += 1

        self.run_thread = threading.Thread(
            target=self._single_run,
            args=(test_args or [],),
            daemon=True
        )
        self.run_thread.start()
        self.is_running = True

        return {"status": "started", "run_id": self.current_run_id}

    def stop(self):
        """Stop continuous test running"""
        self.should_stop = True
        self._broadcast_event({
            "type": "run_stopped",
            "data": {"run_id": self.current_run_id},
            "timestamp": time.time(),
        })
        return {"status": "stopping", "run_id": self.current_run_id}

    def get_status(self) -> dict:
        """Get current runner status"""
        return {
            "is_running": self.is_running,
            "run_id": self.current_run_id,
            "continuous": self.run_interval > 0,
            "interval": self.run_interval,
            "subscribers": len(self.subscribers),
        }

    def _single_run(self, test_args: List[str]):
        """Execute a single test run"""
        try:
            self._execute_tests(test_args)
        finally:
            self.is_running = False

    def _continuous_run_loop(self, test_args: List[str]):
        """Main loop for continuous test execution"""
        try:
            while not self.should_stop:
                self._execute_tests(test_args)

                if self.run_interval > 0 and not self.should_stop:
                    # Wait for next run with periodic checks for stop signal
                    wait_time = 0
                    while wait_time < self.run_interval and not self.should_stop:
                        time.sleep(min(1.0, self.run_interval - wait_time))
                        wait_time += 1.0
                else:
                    break  # Single run mode
        finally:
            self.is_running = False

    def _execute_tests(self, test_args: List[str]):
        """Execute pytest with streaming plugin"""
        run_queue = queue.Queue()
        plugin = StreamingTestPlugin(run_queue)

        # Broadcast run start
        self._broadcast_event({
            "type": "run_start",
            "data": {"run_id": self.current_run_id},
            "timestamp": time.time(),
        })

        # Start event forwarding thread
        forward_thread = threading.Thread(
            target=self._forward_events,
            args=(run_queue, plugin),
            daemon=True
        )
        forward_thread.start()

        # Build pytest arguments
        args = [self.test_path] + test_args + [
            "-v",
            "--tb=short",
            "-q",
        ]

        # Capture stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        try:
            pytest.main(args, plugins=[plugin])
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        # Wait for all events to be forwarded
        run_queue.put(None)  # Sentinel to stop forwarding
        forward_thread.join(timeout=5.0)

    def _forward_events(self, run_queue: queue.Queue, plugin: StreamingTestPlugin):
        """Forward events from run queue to subscribers"""
        while True:
            try:
                event = run_queue.get(timeout=1.0)
                if event is None:
                    break
                self._broadcast_event(event)
            except queue.Empty:
                continue


# Global test runner instance
_test_runner: Optional[ContinuousTestRunner] = None


def get_test_runner() -> ContinuousTestRunner:
    """Get or create the global test runner instance"""
    global _test_runner
    if _test_runner is None:
        _test_runner = ContinuousTestRunner()
    return _test_runner


def stream_test_events() -> Generator[str, None, None]:
    """Generator that yields SSE-formatted test events"""
    runner = get_test_runner()
    subscriber_queue = runner.subscribe()

    try:
        while True:
            try:
                event = subscriber_queue.get(timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                # Send keepalive
                yield f": keepalive\n\n"
    except GeneratorExit:
        pass
    finally:
        runner.unsubscribe(subscriber_queue)
