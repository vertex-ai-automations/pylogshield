"""Tests for rate limiter."""

from __future__ import annotations

import threading
import time

import pytest

from pylogshield.limiter import RateLimiter


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_first_message_allowed(self) -> None:
        """Test that first message is always allowed."""
        limiter = RateLimiter(min_interval=1.0)
        assert limiter.should_log("app", 20, "Hello") is True

    def test_duplicate_within_interval_blocked(self) -> None:
        """Test duplicate message within interval is blocked."""
        limiter = RateLimiter(min_interval=1.0)
        assert limiter.should_log("app", 20, "Hello") is True
        assert limiter.should_log("app", 20, "Hello") is False

    def test_duplicate_after_interval_allowed(self) -> None:
        """Test duplicate message after interval is allowed."""
        limiter = RateLimiter(min_interval=0.1)
        assert limiter.should_log("app", 20, "Hello") is True
        time.sleep(0.15)
        assert limiter.should_log("app", 20, "Hello") is True

    def test_different_messages_allowed(self) -> None:
        """Test different messages are independently tracked."""
        limiter = RateLimiter(min_interval=1.0)
        assert limiter.should_log("app", 20, "Hello") is True
        assert limiter.should_log("app", 20, "World") is True

    def test_different_levels_tracked_separately(self) -> None:
        """Test same message at different levels tracked separately."""
        limiter = RateLimiter(min_interval=1.0)
        assert limiter.should_log("app", 20, "Hello") is True  # INFO
        assert limiter.should_log("app", 40, "Hello") is True  # ERROR

    def test_different_loggers_tracked_separately(self) -> None:
        """Test same message from different loggers tracked separately."""
        limiter = RateLimiter(min_interval=1.0)
        assert limiter.should_log("app1", 20, "Hello") is True
        assert limiter.should_log("app2", 20, "Hello") is True

    def test_suppressed_count(self) -> None:
        """Test suppressed count tracking."""
        limiter = RateLimiter(min_interval=1.0)
        assert limiter.suppressed_count == 0

        limiter.should_log("app", 20, "Hello")  # allowed
        limiter.should_log("app", 20, "Hello")  # suppressed
        limiter.should_log("app", 20, "Hello")  # suppressed

        assert limiter.suppressed_count == 2

    def test_tracked_messages_count(self) -> None:
        """Test tracked messages count."""
        limiter = RateLimiter(min_interval=1.0)
        assert limiter.tracked_messages == 0

        limiter.should_log("app", 20, "Message 1")
        limiter.should_log("app", 20, "Message 2")
        limiter.should_log("app", 20, "Message 3")

        assert limiter.tracked_messages == 3

    def test_reset(self) -> None:
        """Test reset clears state."""
        limiter = RateLimiter(min_interval=1.0)
        limiter.should_log("app", 20, "Hello")
        limiter.should_log("app", 20, "Hello")  # suppressed

        assert limiter.tracked_messages > 0
        assert limiter.suppressed_count > 0

        limiter.reset()

        assert limiter.tracked_messages == 0
        assert limiter.suppressed_count == 0
        # After reset, same message should be allowed again
        assert limiter.should_log("app", 20, "Hello") is True

    def test_max_entries_bounded(self) -> None:
        """Test that entries are bounded by max_entries."""
        limiter = RateLimiter(min_interval=1.0, max_entries=5, purge_after=0.01)

        # Add more than max entries
        for i in range(10):
            limiter.should_log("app", 20, f"Message {i}")
            time.sleep(0.02)  # Trigger purge

        # Should be bounded
        assert limiter.tracked_messages <= 5

    def test_repr(self) -> None:
        """Test limiter repr string."""
        limiter = RateLimiter(min_interval=1.0)
        limiter.should_log("app", 20, "Hello")
        repr_str = repr(limiter)
        assert "RateLimiter" in repr_str
        assert "min_interval=1.0" in repr_str


class TestRateLimiterThreadSafety:
    """Thread safety tests for RateLimiter."""

    def test_concurrent_logging(self) -> None:
        """Test concurrent logging from multiple threads."""
        limiter = RateLimiter(min_interval=0.01)
        errors: list = []
        results: list = []

        def log_messages(thread_id: int) -> None:
            try:
                for i in range(20):
                    result = limiter.should_log(f"thread_{thread_id}", 20, f"msg_{i}")
                    results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=log_messages, args=(i,))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Each thread should have at least some messages allowed
        assert sum(results) > 0

    def test_concurrent_reset(self) -> None:
        """Test concurrent reset operations."""
        limiter = RateLimiter(min_interval=0.01)
        errors: list = []

        def reset_and_log() -> None:
            try:
                for _ in range(10):
                    limiter.should_log("app", 20, "test")
                    limiter.reset()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=reset_and_log)
            for _ in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


def test_overflow_eviction_removes_oldest():
    """When max_entries is exceeded, the oldest entry is evicted."""
    from pylogshield.limiter import RateLimiter
    limiter = RateLimiter(min_interval=0.0, max_entries=3, purge_after=100.0)

    limiter.should_log("app", 20, "msg_a")
    limiter.should_log("app", 20, "msg_b")
    limiter.should_log("app", 20, "msg_c")
    assert limiter.tracked_messages == 3

    # Adding msg_d should evict msg_a (the oldest)
    limiter.should_log("app", 20, "msg_d")
    assert limiter.tracked_messages <= 3

    # msg_a should be allowed again (treated as new — it was evicted)
    allowed = limiter.should_log("app", 20, "msg_a")
    assert allowed, "Evicted entry should be allowed as a new message"


def test_eviction_respects_lru_order():
    """The least-recently-used message is evicted first, not insertion order."""
    from pylogshield.limiter import RateLimiter
    import time
    limiter = RateLimiter(min_interval=0.0, max_entries=2, purge_after=100.0)

    limiter.should_log("app", 20, "old_msg")
    time.sleep(0.01)
    limiter.should_log("app", 20, "new_msg")
    assert limiter.tracked_messages == 2

    # Adding a third should evict old_msg, not new_msg
    limiter.should_log("app", 20, "third_msg")
    assert limiter.tracked_messages <= 2
    # old_msg should be re-allowed (it was evicted)
    assert limiter.should_log("app", 20, "old_msg")
