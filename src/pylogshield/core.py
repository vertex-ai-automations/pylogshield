from __future__ import annotations

import json
import logging
import os
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from queue import Queue
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Union

from pylogshield.config import add_sensitive_fields as cfg_add_sensitive_fields
from pylogshield.config import get_sensitive_fields, get_sensitive_pattern
from pylogshield.context import ContextFilter, async_log_context, log_context
from pylogshield.filters import ContextScrubber, KeywordFilter
from pylogshield.handlers import (
    create_console_handler,
    create_file_handler,
    create_rich_handler,
    create_rotating_file_handler,
)
from pylogshield.limiter import RateLimiter
from pylogshield.metrics import LogMetricsHandler
from pylogshield.utils import LogLevel, ensure_log_dir


class PyLogShield(logging.Logger):
    """A structured logger with redaction, rate limiting, async support, and context scrubbing.

    This logger extends Python's standard logging.Logger with features commonly needed
    in data engineering and production environments:

    - **Sensitive Data Masking**: Automatically redact passwords, tokens, API keys, etc.
    - **Rate Limiting**: Prevent log flooding from repetitive messages.
    - **JSON Formatting**: Structured logging for log aggregation systems.
    - **Async Logging**: Non-blocking logging via queue handlers.
    - **Rich Console**: Colorized output for development environments.
    - **Context Scrubbing**: Remove cloud credentials from log records.
    - **Metrics**: Track log volume and rates.

    Parameters
    ----------
    name : str
        The name of the logger.
    log_level : LogLevel or str or int, optional
        The logging level. Default is logging.INFO.
    enable_json : bool, optional
        Whether to output logs in JSON format. Default is False.
    use_queue : bool, optional
        Whether to use async logging via queue handlers. Default is False.
    use_rich : bool, optional
        Whether to use Rich library for colorized console output. Default is False.
    rate_limit_seconds : float, optional
        Minimum seconds between identical log messages. Default is 0.0 (disabled).
    log_directory : str or Path or None, optional
        Directory for log files. Default is ~/.logs.
    log_file : str or None, optional
        Name of the log file. Default is "{name}.log".
    rotate_file : bool, optional
        Whether to enable log file rotation. Default is False.
    rotate_max_bytes : int, optional
        Maximum file size before rotation. Default is 5,000,000 bytes.
    rotate_backup_count : int, optional
        Number of backup files to keep. Default is 5.
    add_console : bool, optional
        Whether to add a console handler. Default is True.
    enable_metrics : bool, optional
        Whether to enable logging metrics. Default is False.
    log_filter : logging.Filter or KeywordFilter or Iterable[str] or None, optional
        Filter for log messages. Default is None.
    enable_context_scrubber : bool, optional
        Whether to scrub cloud credentials from log records. Default is True.
    enable_context : bool, optional
        Whether to enable context propagation via
        :func:`~pylogshield.context.log_context` /
        :func:`~pylogshield.context.async_log_context`.  When ``True`` a
        :class:`~pylogshield.context.ContextFilter` is added to the logger so
        that any fields set in the active context block are automatically
        attached to every log record.  Default is ``False``.
    queue_maxsize : int, optional
        Maximum size of the async logging queue when ``use_queue=True``.
        ``0`` means unbounded. Positive integers cap the queue size; when the
        queue is full, new messages are dropped (non-blocking put). Default
        is ``0``.

    Attributes
    ----------
    log_level : int
        Current logging level.
    enable_json : bool
        Whether JSON formatting is enabled.
    limiter : RateLimiter or None
        Rate limiter instance (if rate limiting is enabled).
    metrics_handler : LogMetricsHandler or None
        Metrics handler (if metrics are enabled).
    log_directory : Path
        Directory where log files are stored.
    log_file : str
        Name of the log file.
    log_file_path : Path
        Full path to the log file.

    Examples
    --------
    >>> from pylogshield import get_logger
    >>> logger = get_logger("my_app", log_level="INFO", enable_json=True)
    >>> logger.info({"user": "john", "password": "secret123"}, mask=True)
    # Output: {"user": "john", "password": "***"}
    """

    def __init__(
        self,
        name: str,
        *,
        log_level: Union[LogLevel, str, int] = logging.INFO,
        enable_json: bool = False,
        use_queue: bool = False,
        use_rich: bool = False,
        rate_limit_seconds: float = 0.0,
        log_directory: Union[str, Path, None] = None,
        log_file: Optional[str] = None,
        rotate_file: bool = False,
        rotate_max_bytes: int = 5_000_000,
        rotate_backup_count: int = 5,
        add_console: bool = True,
        enable_metrics: bool = False,
        log_filter: Optional[
            Union[logging.Filter, KeywordFilter, Iterable[str]]
        ] = None,
        enable_context_scrubber: bool = True,
        enable_context: bool = False,
        queue_maxsize: int = 0,
    ) -> None:
        resolved_level = self._resolve_log_level(log_level)
        super().__init__(name, level=resolved_level)
        self.log_level = resolved_level

        self.enable_json = enable_json
        self.limiter = (
            RateLimiter(min_interval=rate_limit_seconds)
            if rate_limit_seconds > 0
            else None
        )
        self.metrics_handler = LogMetricsHandler() if enable_metrics else None
        self._queue_listener: Optional[QueueListener] = None
        self.log_directory = self._initialize_log_directory(log_directory)
        self.log_file = log_file or f"{name}.log"
        self.log_file_path = self.log_directory / self.log_file

        handlers: List[logging.Handler] = []

        if add_console:
            handlers.append(
                create_rich_handler(self.log_level)
                if use_rich
                else create_console_handler(self.log_level, json_format=enable_json)
            )

        if self.log_file_path:
            ensure_log_dir(str(self.log_file_path))
            if rotate_file:
                handlers.append(
                    create_rotating_file_handler(
                        self.log_file_path,
                        self.log_level,
                        max_bytes=rotate_max_bytes,
                        backup_count=rotate_backup_count,
                        json_format=enable_json,
                    )
                )
            else:
                handlers.append(
                    create_file_handler(
                        self.log_file_path, self.log_level, json_format=enable_json
                    )
                )

        if enable_metrics and self.metrics_handler is not None:
            handlers.append(self.metrics_handler)

        if log_filter is not None:
            filt = self._normalize_log_filter(log_filter)
            for h in handlers:
                h.addFilter(filt)

        if enable_context_scrubber:
            scrubber = ContextScrubber()
            for h in handlers:
                h.addFilter(scrubber)

        if enable_context:
            # Add to the logger (not individual handlers) so the filter fires
            # once per record in the calling thread/task — before the record
            # is handed off to any QueueHandler — ensuring the ContextVar is
            # read while the correct context is still active.
            self.addFilter(ContextFilter())

        if use_queue and handlers:
            q: Queue = Queue(queue_maxsize)
            self.addHandler(QueueHandler(q))
            self._queue_listener = QueueListener(
                q, *handlers, respect_handler_level=True
            )
            self._queue_listener.start()
        else:
            for h in handlers:
                self.addHandler(h)

    # -------------- helpers --------------

    @staticmethod
    def _resolve_log_level(log_level: Union[LogLevel, str, int]) -> int:
        if isinstance(log_level, LogLevel):
            return log_level.value
        if isinstance(log_level, str):
            return LogLevel.parse(log_level)
        if isinstance(log_level, int):
            return log_level
        raise ValueError(
            f"Invalid log level: {log_level}. Must be LogLevel, str, or int."
        )

    def _get_default_log_directory(self) -> Path:
        """Get the default logs directory under the user's profile/home.

        Returns
        -------
        Path
            The default log directory path (~/.logs).
        """
        return Path.home() / ".logs"

    def _initialize_log_directory(
        self, log_directory: Union[str, Path, None] = None
    ) -> Path:
        p = Path(log_directory or self._get_default_log_directory()).resolve()
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise RuntimeError(f"Failed to create log directory {p}: {e}") from e
        if not os.access(p, os.W_OK):
            raise RuntimeError(
                f"Directory {p} is not writable. Please check permissions."
            )
        return p

    @staticmethod
    def _normalize_log_filter(
        log_filter: Union[logging.Filter, KeywordFilter, Iterable[str]],
    ) -> logging.Filter:
        """Normalize a log filter to a logging.Filter instance.

        Parameters
        ----------
        log_filter : logging.Filter or KeywordFilter or Iterable[str]
            A pre-built Filter, KeywordFilter, or an iterable of keywords.

        Returns
        -------
        logging.Filter
            A normalized logging filter instance.
        """
        if isinstance(log_filter, logging.Filter):
            return log_filter
        return KeywordFilter(list(log_filter), include=True, case_insensitive=True)

    # -------------- masking --------------

    def _mask_mapping(
        self,
        obj: MutableMapping[str, Any],
        sensitive_keys: Optional[frozenset] = None,
        pattern: Optional[Any] = None,
    ) -> MutableMapping[str, Any]:
        if sensitive_keys is None:
            sensitive_keys = frozenset(s.lower() for s in get_sensitive_fields())
        if pattern is None:
            pattern = get_sensitive_pattern()
        masked: Dict[str, Any] = {}
        for k, v in obj.items():
            k_lc = str(k).lower()
            if isinstance(v, str):
                if k_lc in sensitive_keys:
                    masked[k] = "***"
                else:
                    masked[k] = pattern.sub(lambda m: f"{m.group(1)}: ***", v)
            elif isinstance(v, dict):
                masked[k] = self._mask_mapping(v, sensitive_keys, pattern)
            elif isinstance(v, (list, tuple)):
                masked[k] = self._mask_sequence(v, sensitive_keys, pattern)
            else:
                masked[k] = v
        return masked

    def _mask_sequence(
        self,
        seq: Any,
        sensitive_keys: Optional[frozenset] = None,
        pattern: Optional[Any] = None,
    ) -> Any:
        if sensitive_keys is None:
            sensitive_keys = frozenset(s.lower() for s in get_sensitive_fields())
        if pattern is None:
            pattern = get_sensitive_pattern()
        out = []
        for item in seq:
            if isinstance(item, dict):
                out.append(self._mask_mapping(item, sensitive_keys, pattern))
            elif isinstance(item, (list, tuple)):
                out.append(self._mask_sequence(item, sensitive_keys, pattern))
            elif isinstance(item, str):
                out.append(
                    "***" if pattern.search(item or "") else item
                )
            else:
                out.append(item)
        return type(seq)(out) if isinstance(seq, tuple) else out

    def _mask_text(self, text: str) -> str:
        pattern = get_sensitive_pattern()
        return pattern.sub(lambda m: f"{m.group(1)}: ***", text)

    def _mask(self, payload: Any) -> Any:
        sensitive_keys = frozenset(s.lower() for s in get_sensitive_fields())
        pattern = get_sensitive_pattern()
        if isinstance(payload, str):
            return pattern.sub(lambda m: f"{m.group(1)}: ***", payload)
        if isinstance(payload, dict):
            return self._mask_mapping(payload, sensitive_keys, pattern)
        if isinstance(payload, (list, tuple)):
            return self._mask_sequence(payload, sensitive_keys, pattern)
        return payload

    # -------------- rate limiting --------------

    def _allowed(self, level: int, msg: Any) -> bool:
        if self.limiter is None:
            return True
        return self.limiter.should_log(self.name, level, str(msg))

    # -------------- processing --------------

    def _process_message(self, msg: Any, *, mask: bool) -> Any:
        return self._mask(msg) if mask else msg

    def _mask_string(self, text: str) -> str:
        """Apply the sensitive pattern to a single string and return the masked result."""
        pattern = get_sensitive_pattern()
        return pattern.sub(lambda m: f"{m.group(1)}: ***", text)

    def _log_with_processing(
        self, level: int, msg: Any, *args: Any, mask: bool = False, **kwargs: Any
    ) -> None:
        if not self._allowed(level, msg):
            return
        processed = self._process_message(msg, mask=mask)
        if not isinstance(processed, (str, bytes)):
            try:
                processed = json.dumps(processed, ensure_ascii=False)
            except Exception:
                processed = str(processed)

        if mask:
            # Scrub sensitive data from exception args so they don't leak
            # through the formatted traceback.
            exc_info = kwargs.get("exc_info")
            if exc_info and exc_info is not True:
                # exc_info may be a (type, value, tb) tuple
                exc_val = exc_info[1] if isinstance(exc_info, tuple) else None
                if exc_val is not None and hasattr(exc_val, "args"):
                    masked_args = tuple(
                        self._mask_string(a) if isinstance(a, str) else a
                        for a in exc_val.args
                    )
                    try:
                        exc_val.args = masked_args
                    except AttributeError:
                        pass
            elif exc_info is True:
                import sys
                exc_val = sys.exc_info()[1]
                if exc_val is not None and hasattr(exc_val, "args"):
                    masked_args = tuple(
                        self._mask_string(a) if isinstance(a, str) else a
                        for a in exc_val.args
                    )
                    try:
                        exc_val.args = masked_args
                    except AttributeError:
                        pass

        super().log(level, processed, *args, **kwargs)

    # -------------- runtime control --------------

    def set_log_level(self, level: Union[LogLevel, str, int]) -> None:
        """Change the logger and handler levels at runtime.

        Parameters
        ----------
        level : LogLevel or str or int
            The new logging level to set.
        """
        resolved = self._resolve_log_level(level)
        self.setLevel(resolved)
        self.log_level = resolved
        for handler in self.handlers:
            handler.setLevel(resolved)

    # -------------- context propagation --------------

    def context(self, **fields: Any):
        """Return a sync context manager that injects *fields* into all logs.

        Shorthand for :func:`~pylogshield.context.log_context`.  Requires the
        logger to have been created with ``enable_context=True``.

        Parameters
        ----------
        **fields : Any
            Key/value pairs to attach to every log record emitted inside the
            ``with`` block.

        Examples
        --------
        >>> with logger.context(request_id="abc", user_id=42):
        ...     logger.info("Processing order")
        """
        return log_context(**fields)

    def async_context(self, **fields: Any):
        """Return an async context manager that injects *fields* into all logs.

        Shorthand for :func:`~pylogshield.context.async_log_context`.
        Requires the logger to have been created with ``enable_context=True``.

        Parameters
        ----------
        **fields : Any
            Key/value pairs to attach to every log record emitted inside the
            ``async with`` block.

        Examples
        --------
        >>> async with logger.async_context(request_id="xyz"):
        ...     logger.info("Async handler")
        """
        return async_log_context(**fields)

    # -------------- public methods (names unchanged) --------------

    def info(self, msg: Any, *args: Any, mask: bool = False, **kwargs: Any) -> None:
        self._log_with_processing(logging.INFO, msg, *args, mask=mask, **kwargs)

    def debug(self, msg: Any, *args: Any, mask: bool = False, **kwargs: Any) -> None:
        self._log_with_processing(logging.DEBUG, msg, *args, mask=mask, **kwargs)

    def warning(self, msg: Any, *args: Any, mask: bool = False, **kwargs: Any) -> None:
        self._log_with_processing(logging.WARNING, msg, *args, mask=mask, **kwargs)

    def error(self, msg: Any, *args: Any, mask: bool = False, **kwargs: Any) -> None:
        self._log_with_processing(logging.ERROR, msg, *args, mask=mask, **kwargs)

    def critical(self, msg: Any, *args: Any, mask: bool = False, **kwargs: Any) -> None:
        self._log_with_processing(logging.CRITICAL, msg, *args, mask=mask, **kwargs)

    # Alias for warning (common alternative spelling)
    warn = warning

    def exception(
        self,
        msg: Any,
        *args: Any,
        mask: bool = False,
        exc_info: bool = True,
        **kwargs: Any,
    ) -> None:
        """Log an error with exception info.

        When ``mask=True``, string args of the active exception are scrubbed
        before the record is emitted.

        Note: traceback *locals* are not masked — use a traceback-filtering
        tool if local variable values must also be redacted.
        """
        self._log_with_processing(
            logging.ERROR, msg, *args, mask=mask, exc_info=exc_info, **kwargs
        )

    # -------------- static / class helpers --------------

    @classmethod
    def from_config(cls, name: str, config: Mapping[str, Any]) -> "PyLogShield":
        """Create a PyLogShield instance from a dictionary configuration.

        Parameters
        ----------
        name : str
            The name of the logger.
        config : Mapping[str, Any]
            Configuration dictionary with optional keys: level, enable_json,
            use_queue, use_rich, rate_limit_seconds, log_directory, log_file,
            rotate_file, rotate_max_bytes, rotate_backup_count, add_console,
            enable_metrics, log_filter, enable_context_scrubber, enable_context.

        Returns
        -------
        PyLogShield
            A new PyLogShield instance configured from the provided dictionary.

        Examples
        --------
        >>> config = {"level": "DEBUG", "enable_json": True, "rotate_file": True}
        >>> logger = PyLogShield.from_config("my_app", config)
        """
        # Optional log-filter construction from config
        lf = config.get("log_filter")
        lf_obj: Optional[logging.Filter] = None
        if isinstance(lf, dict) and "keywords" in lf:
            lf_obj = KeywordFilter(
                lf.get("keywords", []),
                include=bool(lf.get("include", True)),
                case_insensitive=bool(lf.get("case_insensitive", True)),
            )
        elif isinstance(lf, (list, tuple, set)):
            lf_obj = KeywordFilter(list(lf))
        elif isinstance(lf, logging.Filter):
            lf_obj = lf

        return cls(
            name,
            log_level=LogLevel.parse(config.get("level", "INFO")),
            enable_json=bool(config.get("enable_json", False)),
            use_queue=bool(config.get("use_queue", False)),
            use_rich=bool(config.get("use_rich", False)),
            rate_limit_seconds=float(config.get("rate_limit_seconds", 0.0)),
            log_directory=config.get("log_directory"),
            log_file=config.get("log_file"),
            rotate_file=bool(config.get("rotate_file", False)),
            rotate_max_bytes=int(config.get("rotate_max_bytes", 5_000_000)),
            rotate_backup_count=int(config.get("rotate_backup_count", 5)),
            add_console=bool(config.get("add_console", True)),
            enable_metrics=bool(config.get("enable_metrics", False)),
            log_filter=lf_obj,
            enable_context_scrubber=bool(config.get("enable_context_scrubber", True)),
            enable_context=bool(config.get("enable_context", False)),
        )

    @staticmethod
    def add_sensitive_fields(fields: List[str]) -> None:
        """Add field names to the sensitive data redaction registry.

        Parameters
        ----------
        fields : list of str
            List of field names to add to the sensitive registry.

        Examples
        --------
        >>> PyLogShield.add_sensitive_fields(["ssn", "credit_card"])
        """
        cfg_add_sensitive_fields(fields)

    def shutdown(self) -> None:
        """Stop any background listener and clean up resources.

        This should be called when the logger is no longer needed to properly
        stop the background queue listener thread if async logging is enabled.
        """
        if self._queue_listener is not None:
            self._queue_listener.stop()
            self._queue_listener = None

    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Return logging metrics if metrics are enabled.

        Returns
        -------
        dict or None
            Dictionary with log counts and rates per level, total count,
            and elapsed time. Returns None if metrics are disabled.

        Examples
        --------
        >>> logger = get_logger("app", enable_metrics=True)
        >>> logger.info("test")
        >>> metrics = logger.get_metrics()
        >>> print(f"Total logs: {metrics['count']}")
        """
        if self.metrics_handler is not None:
            return self.metrics_handler.logs_per_second()
        return None

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"level={logging.getLevelName(self.log_level)}, "
            f"handlers={len(self.handlers)})"
        )
