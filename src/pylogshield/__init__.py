from __future__ import annotations

import logging
from typing import Any

from pylogshield.config import (
    add_sensitive_fields,
    get_sensitive_fields,
    remove_sensitive_fields,
)
from pylogshield.context import ContextFilter, async_log_context, log_context
from pylogshield.core import PyLogShield
from pylogshield.filters import ContextScrubber, KeywordFilter
from pylogshield.utils import LogLevel, add_log_level
from pylogshield.viewer import LogViewer
from pylogshield.decorators import log_exceptions, trace

from ._version import __version__

# Optional middleware — requires pip install "pylogshield[fastapi]"
try:
    from pylogshield.middleware import PyLogShieldMiddleware
    _HAS_MIDDLEWARE = True
except ImportError:
    _HAS_MIDDLEWARE = False

__all__ = [
    # Main exports
    "get_logger",
    "PyLogShield",
    "LogLevel",
    "LogViewer",
    # Decorators
    "log_exceptions",
    "trace",
    # Utilities
    "add_log_level",
    "add_sensitive_fields",
    "remove_sensitive_fields",
    "get_sensitive_fields",
    # Filters
    "KeywordFilter",
    "ContextScrubber",
    "ContextFilter",
    # Context propagation
    "log_context",
    "async_log_context",
    # Version
    "__version__",
    # Middleware (requires pip install "pylogshield[fastapi]")
    "PyLogShieldMiddleware",
]


def get_logger(
    name: str = "default_logger", *, force: bool = False, **kwargs: Any
) -> PyLogShield:
    """Return a named PyLogShield instance, creating it if necessary.

    This is the recommended way to obtain a PyLogShield instance. It integrates
    with Python's logging manager to ensure logger names are unique and reusable.

    Parameters
    ----------
    name : str, optional
        Logger name. Default is "default_logger".
    force : bool, optional
        If True, replace a non-PyLogShield with the same name.
        Default is False.
    **kwargs : Any
        Additional arguments passed to the PyLogShield constructor when
        creating a new instance (e.g., log_level, enable_json, use_rich).

    Returns
    -------
    PyLogShield
        A PyLogShield instance with the specified name.

    Raises
    ------
    TypeError
        If a logger with the name exists but is not a PyLogShield
        and force=False.

    Examples
    --------
    >>> logger = get_logger("my_app", log_level="DEBUG", enable_json=True)
    >>> logger.info("Application started")

    >>> # Get the same logger instance later
    >>> same_logger = get_logger("my_app")
    >>> same_logger is logger
    True
    """
    logging._acquireLock()
    try:
        existing = logging.Logger.manager.loggerDict.get(name)
        if existing is not None:
            # Check if it's a PyLogShield (direct instance check is most reliable)
            if isinstance(existing, PyLogShield):
                return existing

            # Duck-typed compatibility check for subclasses or similar implementations
            if hasattr(existing, "_log_with_processing") and hasattr(existing, "_mask"):
                return existing  # type: ignore[return-value]

            if not force:
                raise TypeError(
                    f"Logger '{name}' already exists but is not a compatible PyLogShield. "
                    f"Actual type: {type(existing).__name__}. "
                    f"Use force=True to replace it."
                )

            logging.Logger.manager.loggerDict.pop(name, None)

        logger = PyLogShield(name=name, **kwargs)
        logging.Logger.manager.loggerDict[name] = logger
    finally:
        logging._releaseLock()
    return logger
