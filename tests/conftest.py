"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from pylogshield import PyLogShield
from pylogshield.config import (
    add_sensitive_fields,
    get_sensitive_fields,
    remove_sensitive_fields,
)


def close_logger(logger: PyLogShield) -> None:
    """Properly close a logger and release all file handles."""
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    logger.shutdown()
    logging.Logger.manager.loggerDict.pop(logger.name, None)


@pytest.fixture
def temp_log_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_log_file(temp_log_dir: Path) -> Path:
    """Create a temporary log file path."""
    return temp_log_dir / "test.log"


@pytest.fixture
def basic_logger(temp_log_dir: Path) -> Generator[PyLogShield, None, None]:
    """Create a basic PyLogShield logger for testing."""
    logger = PyLogShield(
        name="test_logger",
        log_directory=temp_log_dir,
        log_file="test.log",
        add_console=False,
    )
    yield logger
    close_logger(logger)


@pytest.fixture
def json_logger(temp_log_dir: Path) -> Generator[PyLogShield, None, None]:
    """Create a JSON-formatted PyLogShield logger for testing."""
    logger = PyLogShield(
        name="test_json_logger",
        log_directory=temp_log_dir,
        log_file="test_json.log",
        enable_json=True,
        add_console=False,
    )
    yield logger
    close_logger(logger)


@pytest.fixture(autouse=True)
def reset_sensitive_fields() -> Generator[None, None, None]:
    """Reset sensitive fields to default after each test."""
    original = get_sensitive_fields()
    yield
    # Restore: remove any fields added during the test, re-add any removed.
    current = get_sensitive_fields()
    added = current - original
    removed = original - current
    if added:
        remove_sensitive_fields(added)
    if removed:
        add_sensitive_fields(removed)


@pytest.fixture
def clean_logger_registry() -> Generator[None, None, None]:
    """Clean up logger registry after test."""
    yield
    # Remove any test loggers from the registry
    to_remove = [
        name for name in logging.Logger.manager.loggerDict if name.startswith("test_")
    ]
    for name in to_remove:
        logging.Logger.manager.loggerDict.pop(name, None)
