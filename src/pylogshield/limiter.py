from __future__ import annotations

import time
from threading import RLock
from typing import Dict, Tuple


class RateLimiter:
    """Per-message rate limiter using monotonic time and bounded state.

    Prevents duplicate log messages from flooding the output by enforcing
    a minimum interval between identical messages (same logger, level, and content).

    The limiter uses bounded memory with automatic cleanup of stale entries.

    Parameters
    ----------
    min_interval : float, optional
        Minimum seconds between two identical messages. Default is 1.0.
    max_entries : int, optional
        Maximum number of tracked messages to bound memory. Default is 10,000.
    purge_after : float, optional
        How often (in seconds) to check and remove stale entries. Default is 5.0.

    Attributes
    ----------
    min_interval : float
        The minimum interval between identical messages.
    max_entries : int
        Maximum number of tracked messages.
    purge_after : float
        Interval for stale entry cleanup.

    Examples
    --------
    >>> limiter = RateLimiter(min_interval=1.0)
    >>> limiter.should_log("app", 20, "Hello")  # True (first time)
    True
    >>> limiter.should_log("app", 20, "Hello")  # False (within interval)
    False
    """

    def __init__(
        self,
        min_interval: float = 1.0,
        *,
        max_entries: int = 10_000,
        purge_after: float = 5.0,
    ) -> None:
        self.min_interval = float(min_interval)
        self.max_entries = int(max_entries)
        self.purge_after = float(purge_after)
        self._last_log_time: Dict[Tuple[str, int, str], float] = {}
        self._last_purge = time.monotonic()
        self._lock = RLock()
        self._suppressed_count = 0  # Track how many messages were suppressed

    def _key(self, logger_name: str, level: int, message: str) -> Tuple[str, int, str]:
        return (logger_name, level, message)

    def should_log(self, logger_name: str, level: int, message: str) -> bool:
        """Check if a log message should be emitted based on rate limiting.

        Parameters
        ----------
        logger_name : str
            The name of the logger.
        level : int
            The logging level (e.g., logging.INFO).
        message : str
            The log message content.

        Returns
        -------
        bool
            True if the message should be logged, False if it should be suppressed.
        """
        now = time.monotonic()
        k = self._key(logger_name, level, message)
        with self._lock:
            if now - self._last_purge >= self.purge_after:
                cutoff = now - (self.purge_after * 5)
                self._last_log_time = {
                    kk: t for kk, t in self._last_log_time.items() if t >= cutoff
                }
                if len(self._last_log_time) > self.max_entries:
                    # drop oldest
                    to_drop = len(self._last_log_time) - self.max_entries
                    for kk, _ in sorted(
                        self._last_log_time.items(), key=lambda kv: kv[1]
                    )[:to_drop]:
                        self._last_log_time.pop(kk, None)
                self._last_purge = now

            prev = self._last_log_time.get(k, -1e12)
            if (now - prev) >= self.min_interval:
                self._last_log_time[k] = now
                return True
            self._suppressed_count += 1
            return False

    @property
    def suppressed_count(self) -> int:
        """Return the number of messages suppressed by rate limiting.

        Returns
        -------
        int
            Total count of suppressed messages since creation or last reset.
        """
        with self._lock:
            return self._suppressed_count

    @property
    def tracked_messages(self) -> int:
        """Return the number of currently tracked unique messages.

        Returns
        -------
        int
            Number of unique (logger, level, message) tuples being tracked.
        """
        with self._lock:
            return len(self._last_log_time)

    def reset(self) -> None:
        """Reset the rate limiter state.

        Clears all tracked messages and resets the suppressed count.
        Useful for testing or periodic resets.
        """
        with self._lock:
            self._last_log_time.clear()
            self._suppressed_count = 0
            self._last_purge = time.monotonic()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"min_interval={self.min_interval}, "
            f"tracked={self.tracked_messages}, "
            f"suppressed={self.suppressed_count})"
        )
