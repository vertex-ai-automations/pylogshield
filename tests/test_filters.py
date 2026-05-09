"""Tests for log filters."""

from __future__ import annotations

import logging

import pytest

from pylogshield.filters import ContextScrubber, KeywordFilter


class TestKeywordFilter:
    """Tests for KeywordFilter."""

    def _make_record(self, message: str) -> logging.LogRecord:
        """Create a LogRecord with the given message."""
        return logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )

    def test_include_mode_matches(self) -> None:
        """Test include mode allows matching messages."""
        filter_ = KeywordFilter(["error", "critical"], include=True)
        record = self._make_record("An error occurred")
        assert filter_.filter(record) is True

    def test_include_mode_no_match(self) -> None:
        """Test include mode blocks non-matching messages."""
        filter_ = KeywordFilter(["error", "critical"], include=True)
        record = self._make_record("Everything is fine")
        assert filter_.filter(record) is False

    def test_exclude_mode_matches(self) -> None:
        """Test exclude mode blocks matching messages."""
        filter_ = KeywordFilter(["debug", "trace"], include=False)
        record = self._make_record("Debug information here")
        assert filter_.filter(record) is False

    def test_exclude_mode_no_match(self) -> None:
        """Test exclude mode allows non-matching messages."""
        filter_ = KeywordFilter(["debug", "trace"], include=False)
        record = self._make_record("Important message")
        assert filter_.filter(record) is True

    def test_case_insensitive_default(self) -> None:
        """Test case-insensitive matching by default."""
        filter_ = KeywordFilter(["error"], include=True)
        assert filter_.filter(self._make_record("ERROR")) is True
        assert filter_.filter(self._make_record("Error")) is True
        assert filter_.filter(self._make_record("error")) is True

    def test_case_sensitive(self) -> None:
        """Test case-sensitive matching when disabled."""
        filter_ = KeywordFilter(["Error"], include=True, case_insensitive=False)
        assert filter_.filter(self._make_record("Error")) is True
        assert filter_.filter(self._make_record("error")) is False
        assert filter_.filter(self._make_record("ERROR")) is False

    def test_empty_keywords(self) -> None:
        """Empty keyword list is a passthrough regardless of include mode."""
        filter_ = KeywordFilter([], include=True)
        record = self._make_record("Any message")
        assert filter_.filter(record) is True

    def test_empty_keywords_exclude(self) -> None:
        """Empty keyword list is a passthrough regardless of include mode."""
        filter_ = KeywordFilter([], include=False)
        record = self._make_record("Any message")
        assert filter_.filter(record) is True

    def test_filter_from_iterable(self) -> None:
        """Test creating filter from various iterables."""
        # From list
        filter1 = KeywordFilter(["a", "b"])
        assert len(filter1.keywords) == 2

        # From set
        filter2 = KeywordFilter({"x", "y"})
        assert len(filter2.keywords) == 2

        # From generator
        filter3 = KeywordFilter(k for k in ["p", "q"])
        assert len(filter3.keywords) == 2

    def test_repr(self) -> None:
        """Test filter repr string."""
        filter_ = KeywordFilter(["error"], include=True)
        repr_str = repr(filter_)
        assert "KeywordFilter" in repr_str
        assert "error" in repr_str
        assert "include" in repr_str


class TestContextScrubber:
    """Tests for ContextScrubber filter."""

    def _make_record_with_extra(self, **extra: str) -> logging.LogRecord:
        """Create a LogRecord with extra attributes."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        for key, value in extra.items():
            setattr(record, key, value)
        return record

    def test_scrubs_aws_prefix(self) -> None:
        """Test scrubbing AWS_ prefixed attributes."""
        scrubber = ContextScrubber()
        record = self._make_record_with_extra(
            AWS_ACCESS_KEY="key123",
            AWS_SECRET_KEY="secret456",
        )
        assert hasattr(record, "AWS_ACCESS_KEY")

        result = scrubber.filter(record)

        assert result is True  # Always allows record through
        assert not hasattr(record, "AWS_ACCESS_KEY")
        assert not hasattr(record, "AWS_SECRET_KEY")

    def test_scrubs_azure_prefix(self) -> None:
        """Test scrubbing AZURE_ prefixed attributes."""
        scrubber = ContextScrubber()
        record = self._make_record_with_extra(
            AZURE_CLIENT_ID="client123",
            AZURE_TENANT_ID="tenant456",
        )

        scrubber.filter(record)

        assert not hasattr(record, "AZURE_CLIENT_ID")
        assert not hasattr(record, "AZURE_TENANT_ID")

    def test_scrubs_gcp_prefix(self) -> None:
        """Test scrubbing GCP_ prefixed attributes."""
        scrubber = ContextScrubber()
        record = self._make_record_with_extra(
            GCP_PROJECT_ID="project123",
        )

        scrubber.filter(record)

        assert not hasattr(record, "GCP_PROJECT_ID")

    def test_scrubs_google_prefix(self) -> None:
        """Test scrubbing GOOGLE_ prefixed attributes."""
        scrubber = ContextScrubber()
        record = self._make_record_with_extra(
            GOOGLE_APPLICATION_CREDENTIALS="/path/to/creds",
        )

        scrubber.filter(record)

        assert not hasattr(record, "GOOGLE_APPLICATION_CREDENTIALS")

    def test_scrubs_token_prefix(self) -> None:
        """Test scrubbing TOKEN prefixed attributes."""
        scrubber = ContextScrubber()
        record = self._make_record_with_extra(
            TOKEN_VALUE="abc123",
        )

        scrubber.filter(record)

        assert not hasattr(record, "TOKEN_VALUE")

    def test_preserves_normal_attributes(self) -> None:
        """Test that normal attributes are preserved."""
        scrubber = ContextScrubber()
        record = self._make_record_with_extra(
            user_id="user123",
            request_id="req456",
        )

        scrubber.filter(record)

        assert hasattr(record, "user_id")
        assert hasattr(record, "request_id")

    def test_scrubs_extra_dict(self) -> None:
        """Test scrubbing 'extra' dict attribute."""
        scrubber = ContextScrubber()
        record = self._make_record_with_extra()
        record.extra = {
            "AWS_KEY": "secret",
            "normal_key": "value",
        }

        scrubber.filter(record)

        assert "AWS_KEY" not in record.extra
        assert "normal_key" in record.extra

    def test_custom_prefixes(self) -> None:
        """Test custom forbidden prefixes."""
        scrubber = ContextScrubber(forbidden_prefixes=("SECRET_", "PRIVATE_"))
        record = self._make_record_with_extra(
            SECRET_VALUE="hidden",
            PRIVATE_DATA="confidential",
            AWS_KEY="kept",  # Should be kept with custom prefixes
        )

        scrubber.filter(record)

        assert not hasattr(record, "SECRET_VALUE")
        assert not hasattr(record, "PRIVATE_DATA")
        assert hasattr(record, "AWS_KEY")

    def test_case_insensitive_scrubbing(self) -> None:
        """Test that scrubbing is case-insensitive."""
        scrubber = ContextScrubber()
        record = self._make_record_with_extra(
            aws_access_key="key123",
            Aws_Secret="secret456",
        )

        scrubber.filter(record)

        assert not hasattr(record, "aws_access_key")
        assert not hasattr(record, "Aws_Secret")

    def test_repr(self) -> None:
        """Test scrubber repr string."""
        scrubber = ContextScrubber()
        repr_str = repr(scrubber)
        assert "ContextScrubber" in repr_str
        assert "AWS_" in repr_str

    def test_context_scrubber_does_not_mutate_extra(self) -> None:
        """ContextScrubber must not modify the original extra dict on the record."""
        scrubber = ContextScrubber()
        record = logging.LogRecord("t", logging.INFO, "", 0, "msg", (), None)
        original_extra = {"AWS_SECRET": "abc", "user": "john"}
        record.__dict__["extra"] = original_extra

        scrubber.filter(record)

        # The original dict must be untouched
        assert "AWS_SECRET" in original_extra, "Scrubber mutated the original extra dict"
        # The record's extra should have the key removed
        assert "AWS_SECRET" not in record.__dict__.get("extra", {}), \
            "Scrubber did not remove the forbidden key from the record"
        assert record.__dict__["extra"].get("user") == "john", \
            "Scrubber removed a non-forbidden key"
