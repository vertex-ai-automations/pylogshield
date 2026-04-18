"""Tests for PyLogShield core functionality."""

from __future__ import annotations

import io
import json
import logging
from pathlib import Path
from typing import Any, Dict

import pytest

from pylogshield import PyLogShield, get_logger
from pylogshield.config import add_sensitive_fields
from tests.conftest import close_logger



class TestPyLogShieldBasic:
    """Basic PyLogShield functionality tests."""

    def test_create_logger(self, temp_log_dir: Path) -> None:
        """Test basic logger creation."""
        logger = PyLogShield(
            name="test_basic",
            log_directory=temp_log_dir,
            add_console=False,
        )
        assert logger.name == "test_basic"
        assert logger.log_level == logging.INFO
        close_logger(logger)

    def test_log_level_string(self, temp_log_dir: Path) -> None:
        """Test logger creation with string log level."""
        logger = PyLogShield(
            name="test_level_str",
            log_level="DEBUG",
            log_directory=temp_log_dir,
            add_console=False,
        )
        assert logger.log_level == logging.DEBUG
        close_logger(logger)

    def test_log_level_int(self, temp_log_dir: Path) -> None:
        """Test logger creation with integer log level."""
        logger = PyLogShield(
            name="test_level_int",
            log_level=logging.WARNING,
            log_directory=temp_log_dir,
            add_console=False,
        )
        assert logger.log_level == logging.WARNING
        close_logger(logger)

    def test_set_log_level(self, basic_logger: PyLogShield) -> None:
        """Test dynamic log level changes."""
        basic_logger.set_log_level("DEBUG")
        assert basic_logger.log_level == logging.DEBUG

        basic_logger.set_log_level(logging.ERROR)
        assert basic_logger.log_level == logging.ERROR

    def test_log_file_created(self, basic_logger: PyLogShield) -> None:
        """Test that log file is created on first write."""
        basic_logger.info("Test message")
        assert basic_logger.log_file_path.exists()

    def test_repr(self, basic_logger: PyLogShield) -> None:
        """Test logger repr string."""
        repr_str = repr(basic_logger)
        assert "PyLogShield" in repr_str
        assert "test_logger" in repr_str


class TestPyLogShieldMasking:
    """Tests for sensitive data masking."""

    def test_mask_dict_password(self, basic_logger: PyLogShield) -> None:
        """Test masking password in dict."""
        data = {"user": "john", "password": "secret123"}
        masked = basic_logger._mask(data)
        assert masked["user"] == "john"
        assert masked["password"] == "***"

    def test_mask_dict_token(self, basic_logger: PyLogShield) -> None:
        """Test masking token in dict."""
        data = {"api_key": "abc123", "data": "value"}
        masked = basic_logger._mask(data)
        assert masked["api_key"] == "***"
        assert masked["data"] == "value"

    def test_mask_nested_dict(self, basic_logger: PyLogShield) -> None:
        """Test masking in nested dictionaries."""
        data = {
            "user": "john",
            "credentials": {
                "password": "secret",
                "token": "xyz"
            }
        }
        masked = basic_logger._mask(data)
        assert masked["user"] == "john"
        assert masked["credentials"]["password"] == "***"
        assert masked["credentials"]["token"] == "***"

    def test_mask_list_of_dicts(self, basic_logger: PyLogShield) -> None:
        """Test masking in list of dictionaries."""
        data = [
            {"user": "john", "password": "secret1"},
            {"user": "jane", "password": "secret2"}
        ]
        masked = basic_logger._mask(data)
        assert masked[0]["user"] == "john"
        assert masked[0]["password"] == "***"
        assert masked[1]["user"] == "jane"
        assert masked[1]["password"] == "***"

    def test_mask_tuple(self, basic_logger: PyLogShield) -> None:
        """Test masking preserves tuple type."""
        data = ({"password": "secret"},)
        masked = basic_logger._mask(data)
        assert isinstance(masked, tuple)
        assert masked[0]["password"] == "***"

    def test_mask_string_with_password(self, basic_logger: PyLogShield) -> None:
        """Test masking password pattern in string."""
        text = "Connection with password: secret123 established"
        masked = basic_logger._mask(text)
        assert "secret123" not in masked
        assert "***" in masked

    def test_mask_string_with_token(self, basic_logger: PyLogShield) -> None:
        """Test masking token pattern in string."""
        text = "Using api_key=myapikey123 for auth"
        masked = basic_logger._mask(text)
        assert "myapikey123" not in masked

    def test_no_mask_when_disabled(self, basic_logger: PyLogShield) -> None:
        """Test that masking can be disabled."""
        data = {"password": "secret"}
        # _process_message with mask=False should not mask
        processed = basic_logger._process_message(data, mask=False)
        assert processed["password"] == "secret"

    def test_mask_case_insensitive(self, basic_logger: PyLogShield) -> None:
        """Test that masking is case-insensitive."""
        data = {"PASSWORD": "secret", "Token": "xyz"}
        masked = basic_logger._mask(data)
        assert masked["PASSWORD"] == "***"
        assert masked["Token"] == "***"

    def test_mask_custom_field(self, basic_logger: PyLogShield) -> None:
        """Test masking with custom sensitive fields."""
        add_sensitive_fields(["custom_secret"])
        data = {"custom_secret": "value", "normal": "data"}
        masked = basic_logger._mask(data)
        assert masked["custom_secret"] == "***"
        assert masked["normal"] == "data"


class TestPyLogShieldLogging:
    """Tests for actual logging operations."""

    def test_info_log(self, basic_logger: PyLogShield) -> None:
        """Test info level logging."""
        basic_logger.info("Test info message")
        content = basic_logger.log_file_path.read_text()
        assert "Test info message" in content
        assert "INFO" in content

    def test_debug_log(self, temp_log_dir: Path) -> None:
        """Test debug level logging."""
        logger = PyLogShield(
            name="test_debug",
            log_level="DEBUG",
            log_directory=temp_log_dir,
            add_console=False,
        )
        logger.debug("Test debug message")
        content = logger.log_file_path.read_text()
        assert "Test debug message" in content
        assert "DEBUG" in content
        close_logger(logger)

    def test_warning_log(self, basic_logger: PyLogShield) -> None:
        """Test warning level logging."""
        basic_logger.warning("Test warning message")
        content = basic_logger.log_file_path.read_text()
        assert "Test warning message" in content
        assert "WARNING" in content

    def test_error_log(self, basic_logger: PyLogShield) -> None:
        """Test error level logging."""
        basic_logger.error("Test error message")
        content = basic_logger.log_file_path.read_text()
        assert "Test error message" in content
        assert "ERROR" in content

    def test_critical_log(self, basic_logger: PyLogShield) -> None:
        """Test critical level logging."""
        basic_logger.critical("Test critical message")
        content = basic_logger.log_file_path.read_text()
        assert "Test critical message" in content
        assert "CRITICAL" in content

    def test_warn_alias(self, basic_logger: PyLogShield) -> None:
        """Test warn alias for warning."""
        basic_logger.warn("Test warn message")
        content = basic_logger.log_file_path.read_text()
        assert "Test warn message" in content
        assert "WARNING" in content

    def test_log_with_mask(self, basic_logger: PyLogShield) -> None:
        """Test logging with masking enabled."""
        basic_logger.info({"password": "secret"}, mask=True)
        content = basic_logger.log_file_path.read_text()
        assert "secret" not in content
        assert "***" in content

    def test_exception_log(self, basic_logger: PyLogShield) -> None:
        """Test exception logging."""
        try:
            raise ValueError("Test error")
        except ValueError:
            basic_logger.exception("An error occurred")
        content = basic_logger.log_file_path.read_text()
        assert "An error occurred" in content
        assert "ValueError" in content


class TestPyLogShieldJSON:
    """Tests for JSON logging."""

    def test_json_format(self, json_logger: PyLogShield) -> None:
        """Test JSON formatted output."""
        json_logger.info("Test JSON message")
        content = json_logger.log_file_path.read_text().strip()
        data = json.loads(content)
        assert data["message"] == "Test JSON message"
        assert data["level"] == "INFO"
        assert "timestamp" in data
        assert "logger" in data

    def test_json_with_dict_message(self, json_logger: PyLogShield) -> None:
        """Test JSON logging with dict message."""
        json_logger.info({"key": "value"})
        content = json_logger.log_file_path.read_text().strip()
        data = json.loads(content)
        # Message should be JSON-serialized dict
        assert "key" in data["message"]


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_creates_new(
        self, temp_log_dir: Path, clean_logger_registry: None
    ) -> None:
        """Test get_logger creates new logger."""
        logger = get_logger(
            "test_new_logger",
            log_directory=temp_log_dir,
            add_console=False,
        )
        assert isinstance(logger, PyLogShield)
        assert logger.name == "test_new_logger"
        close_logger(logger)

    def test_get_logger_returns_existing(
        self, temp_log_dir: Path, clean_logger_registry: None
    ) -> None:
        """Test get_logger returns existing logger."""
        logger1 = get_logger(
            "test_existing",
            log_directory=temp_log_dir,
            add_console=False,
        )
        logger2 = get_logger("test_existing")
        assert logger1 is logger2
        close_logger(logger1)

    def test_get_logger_force_replace(
        self, temp_log_dir: Path, clean_logger_registry: None
    ) -> None:
        """Test get_logger force replacement."""
        # Create a standard logger first
        std_logger = logging.getLogger("test_force")
        logging.Logger.manager.loggerDict["test_force"] = std_logger

        # Should raise without force
        with pytest.raises(TypeError):
            get_logger("test_force")

        # Should succeed with force
        logger = get_logger(
            "test_force",
            force=True,
            log_directory=temp_log_dir,
            add_console=False,
        )
        assert isinstance(logger, PyLogShield)
        close_logger(logger)


class TestPyLogShieldFromConfig:
    """Tests for from_config class method."""

    def test_from_config_basic(self, temp_log_dir: Path) -> None:
        """Test creating logger from config dict."""
        config = {
            "level": "DEBUG",
            "enable_json": True,
            "log_directory": str(temp_log_dir),
            "add_console": False,
        }
        logger = PyLogShield.from_config("test_config", config)
        assert logger.log_level == logging.DEBUG
        assert logger.enable_json is True
        close_logger(logger)

    def test_from_config_with_filter(self, temp_log_dir: Path) -> None:
        """Test creating logger with filter from config."""
        config = {
            "log_directory": str(temp_log_dir),
            "add_console": False,
            "log_filter": ["error", "critical"],
        }
        logger = PyLogShield.from_config("test_config_filter", config)
        assert logger is not None
        close_logger(logger)


class TestExceptionMasking:
    """Tests for exception argument masking."""

    def test_mask_exception_args(self, basic_logger: PyLogShield) -> None:
        """Test that exception args are masked when mask=True."""
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        basic_logger.addHandler(handler)
        try:
            try:
                raise ValueError("password=supersecret")
            except ValueError:
                basic_logger.exception("auth error", mask=True)
        finally:
            basic_logger.removeHandler(handler)
            handler.close()

        output = stream.getvalue()
        # The exception repr (e.g. "ValueError: password=supersecret") must be masked.
        # Traceback source-code lines are formatter output and cannot be redacted
        # by masking — they reflect the literal source text, not the exception value.
        assert "ValueError: password=supersecret" not in output
        # The masked form should appear instead
        assert "ValueError:" in output


def test_exception_args_not_mutated(basic_logger):
    """Masking must not permanently alter the exception's .args."""
    err = ValueError("password: secret123")
    try:
        raise err
    except ValueError:
        basic_logger.exception("error occurred", mask=True, exc_info=True)

    # Original exception args must be intact after logging
    assert err.args == ("password: secret123",)


def test_exception_args_not_mutated_explicit_tuple(basic_logger):
    """Same guarantee when exc_info is passed as a tuple."""
    import sys
    err = ValueError("token: abc-123")
    try:
        raise err
    except ValueError:
        ei = sys.exc_info()
    basic_logger.error("oops", mask=True, exc_info=ei)
    assert err.args == ("token: abc-123",)


class TestQueueLogging:
    """Tests for async logging with use_queue=True."""

    def test_queue_logger_delivers_messages(self, tmp_path):
        """use_queue=True must deliver messages to the file handler."""
        logger = PyLogShield(
            name="test_queue_delivery",
            log_directory=tmp_path,
            log_file="queue.log",
            use_queue=True,
            add_console=False,
        )
        logger.info("queue_test_marker")
        logger.shutdown()

        log_content = (tmp_path / "queue.log").read_text()
        assert "queue_test_marker" in log_content
        close_logger(logger)

    def test_queue_logger_shutdown_flushes_all(self, tmp_path):
        """shutdown() must flush all queued messages before stopping."""
        logger = PyLogShield(
            name="test_queue_flush",
            log_directory=tmp_path,
            log_file="flush.log",
            use_queue=True,
            add_console=False,
        )
        for i in range(50):
            logger.info(f"msg_{i}")
        logger.shutdown()

        log_content = (tmp_path / "flush.log").read_text()
        for i in range(50):
            assert f"msg_{i}" in log_content, f"msg_{i} was dropped"
        close_logger(logger)

    def test_queue_logger_concurrent_writers(self, tmp_path):
        """Multiple threads writing via queue must not lose messages."""
        import threading

        logger = PyLogShield(
            name="test_queue_concurrent",
            log_directory=tmp_path,
            log_file="concurrent.log",
            use_queue=True,
            add_console=False,
        )

        def write_messages(thread_id: int):
            for i in range(20):
                logger.info(f"thread_{thread_id}_msg_{i}")

        threads = [
            threading.Thread(target=write_messages, args=(t,)) for t in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        logger.shutdown()

        log_content = (tmp_path / "concurrent.log").read_text()
        for thread_id in range(5):
            for i in range(20):
                assert f"thread_{thread_id}_msg_{i}" in log_content
        close_logger(logger)


def test_rotating_file_handler_rotates(tmp_path: Path) -> None:
    """rotate_file=True must produce backup files after the size threshold."""
    logger = PyLogShield(
        name="test_rotation_unique",
        log_directory=tmp_path,
        log_file="rotate.log",
        rotate_file=True,
        rotate_max_bytes=500,
        rotate_backup_count=2,
        add_console=False,
    )
    # Write enough data to force at least one rotation (500 bytes / ~30 bytes per line)
    for i in range(50):
        logger.info("x" * 20)
    for h in logger.handlers:
        h.flush()
    close_logger(logger)

    log_files = list(tmp_path.glob("rotate.log*"))
    assert len(log_files) > 1, (
        f"Expected rotation to create backup files, found: {log_files}"
    )
