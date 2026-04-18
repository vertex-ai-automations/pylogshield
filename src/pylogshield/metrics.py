from __future__ import annotations

import logging
import threading
import time
from collections import Counter
from typing import Any, Dict


class LogMetricsHandler(logging.Handler):
    """Lightweight handler that counts emitted logs by level and estimates logs per second.

    This handler is useful for monitoring log volume and identifying potential issues
    like excessive logging that could impact performance.

    Attributes
    ----------
    _counts : Counter
        Counter tracking log counts by level name.
    _start : float
        Monotonic timestamp when the handler was created or last reset.

    Examples
    --------
    >>> logger = PyLogShield("app", enable_metrics=True)
    >>> logger.info("test")
    >>> metrics = logger.metrics_handler.logs_per_second()
    >>> print(f"Total logs: {metrics['count']}")
    """

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._counts: Counter[str] = Counter()
        self._start = time.monotonic()

    def emit(self, record: logging.LogRecord) -> None:
        """Count the log record by its level name.

        Parameters
        ----------
        record : logging.LogRecord
            The log record to count.
        """
        with self._lock:
            self._counts[record.levelname] += 1

    def counts(self) -> Dict[str, int]:
        """Return counts by level.

        Returns
        -------
        dict of str to int
            Dictionary mapping level names (e.g., "INFO", "ERROR") to their counts.
        """
        with self._lock:
            return dict(self._counts)

    def total_count(self) -> int:
        """Return the total number of logs emitted.

        Returns
        -------
        int
            Total count across all levels.
        """
        with self._lock:
            return sum(self._counts.values())

    def elapsed_seconds(self) -> float:
        """Return seconds elapsed since handler creation or last reset.

        Returns
        -------
        float
            Elapsed time in seconds.
        """
        return time.monotonic() - self._start

    def logs_per_second(self) -> Dict[str, Any]:
        """Return a metrics dictionary including per-level rates and totals.

        Returns
        -------
        dict
            Dictionary containing:
            - Per-level log rates (logs/second)
            - ``count``: Total log count
            - ``elapsed``: Elapsed time in seconds
            - ``start``: Start timestamp (monotonic)
        """
        with self._lock:
            elapsed = max(0.001, self.elapsed_seconds())
            rates: Dict[str, Any] = {
                lvl: cnt / elapsed for lvl, cnt in self._counts.items()
            }
            rates["count"] = sum(self._counts.values())
            rates["elapsed"] = elapsed
            rates["start"] = self._start
            return rates

    def reset(self) -> None:
        """Reset counters and timing.

        Clears all level counts and restarts the elapsed time measurement.
        Useful for testing or periodic metric snapshots.
        """
        with self._lock:
            self._counts.clear()
            self._start = time.monotonic()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(total={self.total_count()}, elapsed={self.elapsed_seconds():.2f}s)"
