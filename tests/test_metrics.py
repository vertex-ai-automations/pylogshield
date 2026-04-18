"""Tests for log metrics handler."""

from __future__ import annotations

import logging
import time

import pytest

from pylogshield.metrics import LogMetricsHandler


class TestLogMetricsHandler:
    """Tests for LogMetricsHandler."""

    def _make_record(self, level: int = logging.INFO) -> logging.LogRecord:
        """Create a LogRecord with the given level."""
        return logging.LogRecord(
            name="test",
            level=level,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

    def test_initial_state(self) -> None:
        """Test initial handler state."""
        handler = LogMetricsHandler()
        assert handler.total_count() == 0
        assert handler.counts() == {}
        assert handler.elapsed_seconds() >= 0

    def test_count_info_level(self) -> None:
        """Test counting INFO level logs."""
        handler = LogMetricsHandler()
        record = self._make_record(logging.INFO)

        handler.emit(record)
        handler.emit(record)
        handler.emit(record)

        counts = handler.counts()
        assert counts.get("INFO") == 3
        assert handler.total_count() == 3

    def test_count_multiple_levels(self) -> None:
        """Test counting multiple log levels."""
        handler = LogMetricsHandler()

        handler.emit(self._make_record(logging.DEBUG))
        handler.emit(self._make_record(logging.INFO))
        handler.emit(self._make_record(logging.INFO))
        handler.emit(self._make_record(logging.WARNING))
        handler.emit(self._make_record(logging.ERROR))
        handler.emit(self._make_record(logging.ERROR))
        handler.emit(self._make_record(logging.ERROR))

        counts = handler.counts()
        assert counts.get("DEBUG") == 1
        assert counts.get("INFO") == 2
        assert counts.get("WARNING") == 1
        assert counts.get("ERROR") == 3
        assert handler.total_count() == 7

    def test_elapsed_seconds(self) -> None:
        """Test elapsed time tracking."""
        handler = LogMetricsHandler()
        time.sleep(0.1)
        elapsed = handler.elapsed_seconds()
        assert elapsed >= 0.1

    def test_logs_per_second(self) -> None:
        """Test logs per second calculation."""
        handler = LogMetricsHandler()

        # Emit some logs
        for _ in range(10):
            handler.emit(self._make_record(logging.INFO))

        time.sleep(0.1)  # Ensure some time has passed

        metrics = handler.logs_per_second()

        assert "INFO" in metrics
        assert metrics["INFO"] > 0
        assert metrics["count"] == 10
        assert metrics["elapsed"] > 0
        assert "start" in metrics

    def test_reset(self) -> None:
        """Test reset functionality."""
        handler = LogMetricsHandler()

        handler.emit(self._make_record(logging.INFO))
        handler.emit(self._make_record(logging.ERROR))
        time.sleep(0.1)

        assert handler.total_count() == 2
        assert handler.elapsed_seconds() >= 0.1

        handler.reset()

        assert handler.total_count() == 0
        assert handler.counts() == {}
        assert handler.elapsed_seconds() < 0.1

    def test_repr(self) -> None:
        """Test handler repr string."""
        handler = LogMetricsHandler()
        handler.emit(self._make_record())

        repr_str = repr(handler)
        assert "LogMetricsHandler" in repr_str
        assert "total=1" in repr_str

    def test_integration_with_logger(self) -> None:
        """Test metrics handler with actual logger."""
        handler = LogMetricsHandler()
        logger = logging.getLogger("test_metrics_integration")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")

        counts = handler.counts()
        assert counts.get("DEBUG") == 1
        assert counts.get("INFO") == 1
        assert counts.get("WARNING") == 1

        # Cleanup
        logger.removeHandler(handler)

    def test_counts_is_thread_safe(self) -> None:
        """counts() must return a consistent snapshot under concurrent emit()."""
        import threading

        handler = LogMetricsHandler()
        errors = []

        def emit_many():
            r = logging.LogRecord("t", logging.INFO, "", 0, "m", (), None)
            for _ in range(1000):
                handler.emit(r)

        def read_many():
            for _ in range(1000):
                try:
                    c = handler.counts()
                    assert isinstance(c, dict)
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=emit_many) for _ in range(4)]
        threads += [threading.Thread(target=read_many) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety errors: {errors}"

    def test_logs_per_second_minimum_denominator(self) -> None:
        """Rates must not be astronomically high immediately after construction."""
        handler = LogMetricsHandler()
        r = logging.LogRecord("t", logging.INFO, "", 0, "m", (), None)
        handler.emit(r)
        metrics = handler.logs_per_second()
        # With max(1e-9, elapsed) rate could be ~1e9; with max(0.001) capped at 1000
        assert metrics["INFO"] <= 1001, f"Unrealistic rate: {metrics['INFO']}"
