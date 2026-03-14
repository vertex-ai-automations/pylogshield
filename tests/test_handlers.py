"""Tests for log handlers and formatters."""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

import pytest

from pylogshield.handlers import (
    JsonFormatter,
    create_console_handler,
    create_file_handler,
    create_rich_handler,
    create_rotating_file_handler,
)


class TestJsonFormatter:
    """Tests for JsonFormatter."""

    def _make_record(
        self,
        message: str = "Test message",
        level: int = logging.INFO,
        **extra: str,
    ) -> logging.LogRecord:
        """Create a LogRecord with optional extra fields."""
        record = logging.LogRecord(
            name="test_logger",
            level=level,
            pathname="test.py",
            lineno=42,
            msg=message,
            args=(),
            exc_info=None,
        )
        for key, value in extra.items():
            setattr(record, key, value)
        return record

    def test_basic_format(self) -> None:
        """Test basic JSON formatting."""
        formatter = JsonFormatter()
        record = self._make_record("Hello World")

        output = formatter.format(record)
        data = json.loads(output)

        assert data["message"] == "Hello World"
        assert data["level"] == "INFO"
        assert data["logger"] == "test_logger"
        assert "timestamp" in data
        assert "host" in data

    def test_format_with_indent(self) -> None:
        """Test JSON formatting with indentation."""
        formatter = JsonFormatter(indent=2)
        record = self._make_record()

        output = formatter.format(record)

        # Indented JSON has newlines
        assert "\n" in output
        data = json.loads(output)
        assert data["message"] == "Test message"

    def test_format_different_levels(self) -> None:
        """Test formatting different log levels."""
        formatter = JsonFormatter()

        levels = [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]

        for level_num, level_name in levels:
            record = self._make_record(level=level_num)
            output = formatter.format(record)
            data = json.loads(output)
            assert data["level"] == level_name

    def test_format_with_extra_fields(self) -> None:
        """Test formatting with extra fields included."""
        formatter = JsonFormatter(include_extra=True)
        record = self._make_record(
            custom_field="custom_value",
            request_id="req123",
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "extra" in data
        assert data["extra"]["custom_field"] == "custom_value"
        assert data["extra"]["request_id"] == "req123"

    def test_format_without_extra_fields(self) -> None:
        """Test formatting with extra fields excluded."""
        formatter = JsonFormatter(include_extra=False)
        record = self._make_record(custom_field="custom_value")

        output = formatter.format(record)
        data = json.loads(output)

        assert "extra" not in data

    def test_timestamp_format(self) -> None:
        """Test timestamp is ISO 8601 format."""
        formatter = JsonFormatter()
        record = self._make_record()

        output = formatter.format(record)
        data = json.loads(output)

        # Should be ISO format with timezone
        timestamp = data["timestamp"]
        assert "T" in timestamp  # ISO format separator
        assert "+" in timestamp or "Z" in timestamp  # Timezone indicator

    def test_exception_info(self) -> None:
        """Test formatting with exception info."""
        formatter = JsonFormatter()
        record = self._make_record()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            record.exc_info = sys.exc_info()

        output = formatter.format(record)
        data = json.loads(output)

        assert "exc_info" in data
        assert "ValueError" in data["exc_info"]

    def test_repr(self) -> None:
        """Test formatter repr string."""
        formatter = JsonFormatter(indent=2, include_extra=False)
        repr_str = repr(formatter)
        assert "JsonFormatter" in repr_str
        assert "indent=2" in repr_str


class TestCreateConsoleHandler:
    """Tests for create_console_handler."""

    def test_creates_stream_handler(self) -> None:
        """Test creating a StreamHandler."""
        handler = create_console_handler(logging.INFO)
        assert isinstance(handler, logging.StreamHandler)
        assert handler.level == logging.INFO

    def test_standard_formatter(self) -> None:
        """Test standard (non-JSON) formatter."""
        handler = create_console_handler(logging.INFO, json_format=False)
        formatter = handler.formatter
        assert formatter is not None
        assert not isinstance(formatter, JsonFormatter)

    def test_json_formatter(self) -> None:
        """Test JSON formatter option."""
        handler = create_console_handler(logging.INFO, json_format=True)
        assert isinstance(handler.formatter, JsonFormatter)


class TestCreateFileHandler:
    """Tests for create_file_handler."""

    def test_creates_file_handler(self, temp_log_dir: Path) -> None:
        """Test creating a FileHandler."""
        log_path = temp_log_dir / "test.log"
        handler = create_file_handler(log_path, logging.INFO)

        assert isinstance(handler, logging.FileHandler)
        assert handler.level == logging.INFO
        handler.close()

    def test_creates_parent_directories(self, temp_log_dir: Path) -> None:
        """Test that parent directories are created."""
        log_path = temp_log_dir / "subdir" / "nested" / "test.log"
        handler = create_file_handler(log_path, logging.INFO)

        assert log_path.parent.exists()
        handler.close()

    def test_json_format(self, temp_log_dir: Path) -> None:
        """Test JSON formatter option."""
        log_path = temp_log_dir / "json.log"
        handler = create_file_handler(log_path, logging.INFO, json_format=True)

        assert isinstance(handler.formatter, JsonFormatter)
        handler.close()


class TestCreateRotatingFileHandler:
    """Tests for create_rotating_file_handler."""

    def test_creates_rotating_handler(self, temp_log_dir: Path) -> None:
        """Test creating a RotatingFileHandler."""
        from logging.handlers import RotatingFileHandler

        log_path = temp_log_dir / "rotating.log"
        handler = create_rotating_file_handler(log_path, logging.INFO)

        assert isinstance(handler, RotatingFileHandler)
        assert handler.level == logging.INFO
        handler.close()

    def test_rotation_settings(self, temp_log_dir: Path) -> None:
        """Test rotation parameters are applied."""
        log_path = temp_log_dir / "rotating.log"
        handler = create_rotating_file_handler(
            log_path,
            logging.INFO,
            max_bytes=1_000_000,
            backup_count=3,
        )

        assert handler.maxBytes == 1_000_000
        assert handler.backupCount == 3
        handler.close()

    def test_json_format(self, temp_log_dir: Path) -> None:
        """Test JSON formatter option."""
        log_path = temp_log_dir / "rotating_json.log"
        handler = create_rotating_file_handler(
            log_path, logging.INFO, json_format=True
        )

        assert isinstance(handler.formatter, JsonFormatter)
        handler.close()


class TestCreateRichHandler:
    """Tests for create_rich_handler."""

    def test_creates_handler(self) -> None:
        """Test creating a handler (Rich or fallback)."""
        handler = create_rich_handler(logging.INFO)
        assert isinstance(handler, logging.Handler)
        assert handler.level == logging.INFO

    def test_fallback_to_console(self) -> None:
        """Test fallback behavior when Rich unavailable."""
        # The handler should always work, either as Rich or console
        handler = create_rich_handler(logging.DEBUG)
        assert handler is not None
        assert handler.level == logging.DEBUG
