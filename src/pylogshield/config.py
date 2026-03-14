"""Sensitive field configuration for log masking.

This module manages the registry of field names that should be automatically
masked in log output to prevent sensitive data leakage.

The module provides thread-safe functions to add, remove, and query sensitive
field names, as well as a compiled regex pattern for efficient matching.
"""

from __future__ import annotations

import re
import threading
from typing import FrozenSet, Iterable, Set

# Default sensitive identifiers (case-insensitive key match)
# These field names will trigger automatic masking when found in log messages
SENSITIVE_FIELDS: Set[str] = {
    "password",
    "passwd",
    "pwd",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "bearer",
    "client_secret",
    "private_key",
    "secret_key",
    # "credentials", this line breaks the code causing str issue.
    "session_token",
}

SENSITIVE_LOCK = threading.RLock()

# Cache for compiled regex. Invalidate whenever fields change.
__pattern_cache: re.Pattern[str] | None = None


def get_sensitive_pattern() -> re.Pattern[str]:
    """Return a compiled regex that matches 'key: value' for any sensitive field.

    The pattern is rebuilt lazily and cached until invalidated by adding or
    removing sensitive fields.

    Returns
    -------
    re.Pattern[str]
        A compiled regex pattern for matching sensitive field patterns.

    Notes
    -----
    The pattern matches formats like:
    - ``password: value``
    - ``token=value``
    - ``api_key: "value"``
    """
    global __pattern_cache
    with SENSITIVE_LOCK:
        if __pattern_cache is None:
            fields = sorted(SENSITIVE_FIELDS)
            if fields:
                joined = "|".join(map(re.escape, fields))
                __pattern_cache = re.compile(
                    rf"(?i)\b({joined})\b\s*[:=]\s*['\"]?([^'\"\s]+)['\"]?"
                )
            else:
                # Compile a never-matching pattern to avoid special-casing.
                __pattern_cache = re.compile(r"(?!x)x")  # never matches
        return __pattern_cache


def invalidate_sensitive_pattern_cache() -> None:
    """Invalidate the cached regex so it's rebuilt on next request.

    This function is called automatically when sensitive fields are added
    or removed. Users typically don't need to call this directly.
    """
    global __pattern_cache
    with SENSITIVE_LOCK:
        __pattern_cache = None


def add_sensitive_fields(fields: Iterable[str]) -> None:
    """Add new field names to the sensitive registry.

    Parameters
    ----------
    fields : Iterable[str]
        Iterable of field names to add. Fields are normalized to lowercase
        for case-insensitive matching.

    Examples
    --------
    >>> add_sensitive_fields(["ssn", "credit_card"])
    >>> add_sensitive_fields(["SSN"])  # Normalized to "ssn"
    """
    with SENSITIVE_LOCK:
        for f in fields:
            if f and f.strip():
                SENSITIVE_FIELDS.add(f.strip().lower())
        invalidate_sensitive_pattern_cache()


def remove_sensitive_fields(fields: Iterable[str]) -> None:
    """Remove field names from the sensitive registry.

    Parameters
    ----------
    fields : Iterable[str]
        Iterable of field names to remove.

    Examples
    --------
    >>> remove_sensitive_fields(["password"])
    """
    with SENSITIVE_LOCK:
        for f in fields:
            SENSITIVE_FIELDS.discard(f.strip().lower())
        invalidate_sensitive_pattern_cache()


def get_sensitive_fields() -> FrozenSet[str]:
    """Return a frozen copy of the current sensitive fields.

    Returns
    -------
    frozenset of str
        Immutable set of currently registered sensitive field names.

    Examples
    --------
    >>> fields = get_sensitive_fields()
    >>> "password" in fields
    True
    """
    with SENSITIVE_LOCK:
        return frozenset(SENSITIVE_FIELDS)
