"""Utilities and LogLevel enum, plus dynamic level registration.

This module provides utility functions and enums for working with log levels,
including parsing level names/values and registering custom log levels.
"""

from __future__ import annotations

import logging
from enum import IntEnum
from threading import RLock
from typing import Any, List, Type


class LogLevel(IntEnum):
    """Standard log levels as an IntEnum for type-safe level handling.

    The levels are ordered by severity (higher value = more severe):
    CRITICAL (50) > ERROR (40) > WARNING (30) > INFO (20) > DEBUG (10) > NOTSET (0)

    Attributes
    ----------
    CRITICAL : int
        Critical level (50).
    ERROR : int
        Error level (40).
    WARNING : int
        Warning level (30).
    INFO : int
        Info level (20).
    DEBUG : int
        Debug level (10).
    NOTSET : int
        Not set level (0).

    Examples
    --------
    >>> LogLevel.parse("INFO")
    20
    >>> LogLevel.parse("warn")  # case-insensitive, accepts "warn" alias
    30
    >>> LogLevel.INFO > LogLevel.DEBUG
    True
    """

    CRITICAL = logging.CRITICAL
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    NOTSET = logging.NOTSET

    @classmethod
    def valid_levels(cls) -> List[str]:
        """Return list of valid level names in descending severity order.

        Returns
        -------
        list of str
            List of level names from most to least severe.

        Examples
        --------
        >>> LogLevel.valid_levels()
        ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']
        """
        return [level.name for level in sorted(cls, reverse=True)]

    @classmethod
    def parse(cls, value: str | int) -> int:
        """Parse a level name or number to an integer.

        Parameters
        ----------
        value : str or int
            Level name (e.g., "INFO", "debug") or numeric value.

        Returns
        -------
        int
            The numeric log level.

        Raises
        ------
        ValueError
            If the value cannot be parsed as a valid log level.

        Examples
        --------
        >>> LogLevel.parse("INFO")
        20
        >>> LogLevel.parse("warn")  # "warn" is aliased to "WARNING"
        30
        >>> LogLevel.parse(10)
        10
        """
        if isinstance(value, int):
            if not (logging.DEBUG <= value <= logging.CRITICAL + 100):
                raise ValueError(f"Invalid log level integer: {value}")
            return value
        val = value.strip().upper()
        if val == "WARN":
            val = "WARNING"
        if val in cls.__members__:
            return int(cls.__members__[val].value)

        try:
            return int(val)
        except ValueError:
            raise ValueError(
                f"Unknown log level: {value!r}. Valid options: {', '.join(cls.valid_levels())}"
            ) from None

    @classmethod
    def from_name(cls, value: str | int) -> int:
        """Parse a level name or number to an integer.

        This is an alias for :meth:`parse` kept for backward compatibility.

        Parameters
        ----------
        value : str or int
            Level name or numeric value.

        Returns
        -------
        int
            The numeric log level.
        """
        return cls.parse(value)


LEVEL_REGISTRY_LOCK = RLock()


def add_log_level(name: str, value: int, *, logger_cls: Type[logging.Logger]) -> None:
    """Register a custom log level and attach a method to a logger class.

    The generated method will have the lowercase name of the level (e.g., "SECURITY"
    becomes ``.security(...)``) and supports the ``mask`` parameter for sensitive
    data redaction.

    Parameters
    ----------
    name : str
        The name of the custom level (e.g., "SECURITY", "TRACE").
    value : int
        The numeric value of the level. Should be unique and follow the
        convention where higher values indicate more severe levels.
    logger_cls : type[logging.Logger]
        The logger class to add the method to.

    Raises
    ------
    ValueError
        If the logger class already has an attribute with the method name.

    Examples
    --------
    >>> from pylogshield import PyLogShield, add_log_level
    >>> add_log_level("SECURITY", 35, logger_cls=PyLogShield)
    >>> logger = get_logger("app")
    >>> logger.security("Security event detected", mask=True)

    Notes
    -----
    This function is thread-safe. The generated method signature is:
    ``(self, msg, *args, mask: bool = False, **kwargs)``
    """
    lname = name.upper()
    method_name = lname.lower()

    with LEVEL_REGISTRY_LOCK:
        if hasattr(logger_cls, method_name):
            raise ValueError(f"Logger already has attribute {method_name!r}")

        logging.addLevelName(value, lname)

        def _log_method(
            self: logging.Logger,
            msg: Any,
            *args: Any,
            mask: bool = False,
            **kwargs: Any,
        ) -> None:
            if hasattr(self, "_log_with_processing"):
                self._log_with_processing(value, msg, *args, mask=mask, **kwargs)
            else:
                kwargs.pop("mask", None)
                if self.isEnabledFor(value):
                    self._log(value, msg, args, **kwargs)

        setattr(logger_cls, method_name, _log_method)


def ensure_log_dir(path: str | None) -> None:
    """Create the parent directory for a file path if it doesn't exist.

    Parameters
    ----------
    path : str or None
        The file path whose parent directory should be created.
        If None or empty, this function does nothing.

    Examples
    --------
    >>> ensure_log_dir("/var/log/myapp/app.log")
    # Creates /var/log/myapp/ if it doesn't exist
    """
    if not path:
        return
    from pathlib import Path

    p = Path(path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
