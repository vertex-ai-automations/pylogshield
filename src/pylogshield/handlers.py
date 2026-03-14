from __future__ import annotations

import json
import logging
import socket
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from rich.logging import RichHandler

    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False


def _standard_formatter() -> logging.Formatter:
    return logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class JsonFormatter(logging.Formatter):
    """JSON formatter that emits a structured log envelope.

    This formatter outputs log records as JSON objects with a consistent
    structure suitable for log aggregation systems like ELK, Splunk, etc.

    Parameters
    ----------
    indent : int or None, optional
        Indentation level for JSON output. None for compact output (default).
    include_extra : bool, optional
        Whether to include extra fields from LogRecord. Default is True.

    Attributes
    ----------
    indent : int or None
        Indentation level for JSON output.
    include_extra : bool
        Whether to include extra fields from LogRecord.
    hostname : str
        The hostname of the machine generating logs.

    Examples
    --------
    >>> formatter = JsonFormatter(indent=2)
    >>> handler = logging.StreamHandler()
    >>> handler.setFormatter(formatter)
    """

    # Standard LogRecord attributes to exclude from "extra" field
    _STANDARD_ATTRS = frozenset(
        {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
            "taskName",
        }
    )

    def __init__(
        self, *, indent: Optional[int] = None, include_extra: bool = True
    ) -> None:
        super().__init__()
        self.indent = indent
        self.include_extra = include_extra
        self.hostname = socket.gethostname()

    def formatTime(
        self, record: logging.LogRecord, datefmt: Optional[str] = None
    ) -> str:
        """Format the log record timestamp as ISO 8601 with timezone.

        Parameters
        ----------
        record : logging.LogRecord
            The log record to format.
        datefmt : str or None, optional
            Custom date format string. If None, uses ISO 8601 format.

        Returns
        -------
        str
            The formatted timestamp string in UTC timezone.
        """
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat(timespec="milliseconds")

    def format(self, record: logging.LogRecord) -> str:
        envelope: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "host": self.hostname,
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if record.exc_info:
            envelope["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            envelope["stack_info"] = record.stack_info

        if self.include_extra:
            extra: Dict[str, Any] = {}
            for k, v in record.__dict__.items():
                if k not in self._STANDARD_ATTRS:
                    extra[k] = v
            if extra:
                envelope["extra"] = extra

        return json.dumps(envelope, indent=self.indent, ensure_ascii=False, default=str)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(indent={self.indent}, include_extra={self.include_extra})"


def create_console_handler(level: int, *, json_format: bool = False) -> logging.Handler:
    """Create a console (stderr) handler with standard or JSON formatting.

    Parameters
    ----------
    level : int
        The logging level for the handler.
    json_format : bool, optional
        Whether to use JSON formatting. Default is False.

    Returns
    -------
    logging.Handler
        A configured StreamHandler instance.
    """
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter() if json_format else _standard_formatter())
    return handler


def create_rich_handler(level: int) -> logging.Handler:
    """Create a Rich console handler with colorized output.

    Falls back to a standard console handler if Rich is not installed.

    Parameters
    ----------
    level : int
        The logging level for the handler.

    Returns
    -------
    logging.Handler
        A RichHandler if Rich is available, otherwise a StreamHandler.
    """
    if _HAS_RICH:
        h = RichHandler(rich_tracebacks=True, show_time=False, show_path=False)
        h.setLevel(level)
        h.setFormatter(logging.Formatter("%(message)s"))
        return h
    return create_console_handler(level)


def create_file_handler(
    path: Path, level: int, *, json_format: bool = False
) -> logging.Handler:
    """Create a simple file handler.

    Parameters
    ----------
    path : Path
        The path to the log file. Parent directories are created if needed.
    level : int
        The logging level for the handler.
    json_format : bool, optional
        Whether to use JSON formatting. Default is False.

    Returns
    -------
    logging.Handler
        A configured FileHandler instance.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter() if json_format else _standard_formatter())
    return handler


def create_rotating_file_handler(
    path: Path,
    level: int,
    *,
    max_bytes: int = 5_000_000,
    backup_count: int = 5,
    json_format: bool = False,
) -> logging.Handler:
    """Create a rotating file handler that rotates logs based on file size.

    Parameters
    ----------
    path : Path
        The path to the log file. Parent directories are created if needed.
    level : int
        The logging level for the handler.
    max_bytes : int, optional
        Maximum file size in bytes before rotation. Default is 5,000,000.
    backup_count : int, optional
        Number of backup files to keep. Default is 5.
    json_format : bool, optional
        Whether to use JSON formatting. Default is False.

    Returns
    -------
    logging.Handler
        A configured RotatingFileHandler instance.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter() if json_format else _standard_formatter())
    return handler
