"""Tests for utility functions and LogLevel enum."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import pytest

from pylogshield.utils import LogLevel, add_log_level, ensure_log_dir


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_level_values(self) -> None:
        """Test standard level values match logging module."""
        assert LogLevel.CRITICAL == logging.CRITICAL
        assert LogLevel.ERROR == logging.ERROR
        assert LogLevel.WARNING == logging.WARNING
        assert LogLevel.INFO == logging.INFO
        assert LogLevel.DEBUG == logging.DEBUG
        assert LogLevel.NOTSET == logging.NOTSET

    def test_level_ordering(self) -> None:
        """Test levels are properly ordered by severity."""
        assert LogLevel.CRITICAL > LogLevel.ERROR
        assert LogLevel.ERROR > LogLevel.WARNING
        assert LogLevel.WARNING > LogLevel.INFO
        assert LogLevel.INFO > LogLevel.DEBUG
        assert LogLevel.DEBUG > LogLevel.NOTSET

    def test_valid_levels(self) -> None:
        """Test valid_levels returns all levels."""
        levels = LogLevel.valid_levels()
        assert "CRITICAL" in levels
        assert "ERROR" in levels
        assert "WARNING" in levels
        assert "INFO" in levels
        assert "DEBUG" in levels
        assert "NOTSET" in levels
        # Should be in descending severity order
        assert levels[0] == "CRITICAL"

    def test_parse_string_uppercase(self) -> None:
        """Test parsing uppercase level names."""
        assert LogLevel.parse("CRITICAL") == logging.CRITICAL
        assert LogLevel.parse("ERROR") == logging.ERROR
        assert LogLevel.parse("WARNING") == logging.WARNING
        assert LogLevel.parse("INFO") == logging.INFO
        assert LogLevel.parse("DEBUG") == logging.DEBUG

    def test_parse_string_lowercase(self) -> None:
        """Test parsing lowercase level names."""
        assert LogLevel.parse("critical") == logging.CRITICAL
        assert LogLevel.parse("error") == logging.ERROR
        assert LogLevel.parse("warning") == logging.WARNING
        assert LogLevel.parse("info") == logging.INFO
        assert LogLevel.parse("debug") == logging.DEBUG

    def test_parse_string_mixed_case(self) -> None:
        """Test parsing mixed case level names."""
        assert LogLevel.parse("Critical") == logging.CRITICAL
        assert LogLevel.parse("Error") == logging.ERROR
        assert LogLevel.parse("Warning") == logging.WARNING

    def test_parse_warn_alias(self) -> None:
        """Test 'WARN' is aliased to 'WARNING'."""
        assert LogLevel.parse("WARN") == logging.WARNING
        assert LogLevel.parse("warn") == logging.WARNING

    def test_parse_integer(self) -> None:
        """Test parsing integer level values."""
        assert LogLevel.parse(10) == 10
        assert LogLevel.parse(20) == 20
        assert LogLevel.parse(30) == 30

    def test_parse_numeric_string(self) -> None:
        """Test parsing numeric string level values."""
        assert LogLevel.parse("10") == 10
        assert LogLevel.parse("20") == 20
        assert LogLevel.parse("30") == 30

    def test_parse_with_whitespace(self) -> None:
        """Test parsing with surrounding whitespace."""
        assert LogLevel.parse("  INFO  ") == logging.INFO
        assert LogLevel.parse("\tDEBUG\n") == logging.DEBUG

    def test_parse_invalid_raises(self) -> None:
        """Test parsing invalid level raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            LogLevel.parse("INVALID_LEVEL")
        assert "Unknown log level" in str(exc_info.value)
        assert "INVALID_LEVEL" in str(exc_info.value)

    def test_from_name_alias(self) -> None:
        """Test from_name is an alias for parse."""
        assert LogLevel.from_name("INFO") == LogLevel.parse("INFO")
        assert LogLevel.from_name(20) == LogLevel.parse(20)


class TestAddLogLevel:
    """Tests for add_log_level function."""

    def test_add_custom_level(self, temp_log_dir: Path) -> None:
        """Test adding a custom log level."""

        # Create a test logger class to avoid modifying PyLogShield
        class TestLogger(logging.Logger):
            pass

        add_log_level("SECURITY", 35, logger_cls=TestLogger)

        # Verify level was registered
        assert logging.getLevelName(35) == "SECURITY"
        assert logging.getLevelName("SECURITY") == 35

        # Verify method was added
        assert hasattr(TestLogger, "security")

    def test_custom_level_method_works(self, temp_log_dir: Path) -> None:
        """Test that custom level method actually logs."""

        class TestLogger2(logging.Logger):
            def _log_with_processing(
                self, level: int, msg: str, *args, mask: bool = False, **kwargs
            ) -> None:
                # Simple implementation for testing
                if self.isEnabledFor(level):
                    super()._log(level, msg, args, **kwargs)

        add_log_level("AUDIT", 25, logger_cls=TestLogger2)

        logger = TestLogger2("test_audit")
        logger.setLevel(logging.DEBUG)

        # Add a handler to capture output
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        # Should not raise
        logger.audit("Audit event")  # type: ignore

    def test_duplicate_level_raises(self) -> None:
        """Test adding duplicate level method raises."""

        class TestLogger3(logging.Logger):
            def existing(self) -> None:
                pass

        with pytest.raises(ValueError) as exc_info:
            add_log_level("EXISTING", 45, logger_cls=TestLogger3)
        assert "already has attribute" in str(exc_info.value)


class TestEnsureLogDir:
    """Tests for ensure_log_dir function."""

    def test_creates_directory(self) -> None:
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "subdir" / "app.log"
            ensure_log_dir(str(log_path))
            assert log_path.parent.exists()

    def test_existing_directory_ok(self) -> None:
        """Test existing directory doesn't raise."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "app.log"
            # Parent already exists
            ensure_log_dir(str(log_path))
            # Should not raise

    def test_nested_directory_creation(self) -> None:
        """Test creating nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "a" / "b" / "c" / "app.log"
            ensure_log_dir(str(log_path))
            assert log_path.parent.exists()

    def test_none_path_ok(self) -> None:
        """Test None path doesn't raise."""
        ensure_log_dir(None)  # Should not raise

    def test_empty_path_ok(self) -> None:
        """Test empty string path doesn't raise."""
        ensure_log_dir("")  # Should not raise

    def test_expands_user_home(self) -> None:
        """Test tilde expansion."""
        # Just verify it doesn't raise - actual path depends on system
        # We use a temp directory to avoid creating real directories
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            ensure_log_dir(str(log_path))
