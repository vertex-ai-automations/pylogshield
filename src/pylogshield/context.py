"""Context propagation for PyLogShield using Python's contextvars.

This module provides thread-safe and asyncio-safe log context injection via
``contextvars.ContextVar``.  Any key/value pairs set inside a ``log_context``
or ``async_log_context`` block are automatically attached to every log record
emitted by a logger that has ``enable_context=True`` (or that has a
:class:`ContextFilter` installed).

Usage::

    from pylogshield import get_logger
    from pylogshield.context import log_context, async_log_context

    logger = get_logger("app", enable_context=True, enable_json=True)

    # Sync
    with log_context(request_id="abc-123", user_id=42):
        logger.info("Processing order")  # JSON includes request_id + user_id

    # Async
    async with async_log_context(request_id="xyz-999"):
        logger.info("Async handler")

    # Nested — inner fields are merged on top of outer fields
    with log_context(service="payments"):
        with log_context(transaction_id="tx-7"):
            logger.info("Charge applied")  # has both fields
        logger.info("Done")               # only service remains
"""
from __future__ import annotations

import logging
import warnings
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar, Token
from typing import Any, AsyncIterator, Dict, FrozenSet, Iterator

# Single ContextVar holding the current context dict for this thread/task.
# Using an immutable-ish snapshot model: we replace the entire dict on entry
# and restore the previous dict on exit, which keeps nesting correct.
_log_context: ContextVar[Dict[str, Any]] = ContextVar(
    "pylogshield_context", default={}
)


def get_log_context() -> Dict[str, Any]:
    """Return the current log context dict for this thread / asyncio task.

    Returns an empty dict when no context block is active.

    Returns
    -------
    dict
        The active context key/value pairs.
    """
    return _log_context.get()


@contextmanager
def log_context(**fields: Any) -> Iterator[None]:
    """Sync context manager that injects *fields* into every log within the block.

    Fields are merged on top of any already-active context, so nesting works
    as expected.  The previous context is restored on exit (including on
    exceptions).

    Parameters
    ----------
    **fields : Any
        Arbitrary key/value pairs to attach to log records.

    Examples
    --------
    >>> with log_context(request_id="abc", user_id=42):
    ...     logger.info("Processing")   # record carries request_id and user_id
    """
    token: Token[Dict[str, Any]] = _log_context.set({**_log_context.get(), **fields})
    try:
        yield
    finally:
        _log_context.reset(token)


@asynccontextmanager
async def async_log_context(**fields: Any) -> AsyncIterator[None]:
    """Async context manager that injects *fields* into every log within the block.

    Safe to use with ``asyncio.gather`` — each task gets its own copy of the
    ``ContextVar`` so contexts do not bleed between concurrent tasks.

    Parameters
    ----------
    **fields : Any
        Arbitrary key/value pairs to attach to log records.

    Examples
    --------
    >>> async with async_log_context(request_id="xyz"):
    ...     logger.info("Async handler")  # record carries request_id
    """
    token: Token[Dict[str, Any]] = _log_context.set({**_log_context.get(), **fields})
    try:
        yield
    finally:
        _log_context.reset(token)


_LOGRECORD_RESERVED: FrozenSet[str] = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname",
    "filename", "module", "exc_info", "exc_text", "stack_info",
    "lineno", "funcName", "created", "msecs", "relativeCreated",
    "thread", "threadName", "processName", "process", "message",
    "taskName",
})

# Track keys that have already triggered a warning to warn only once each.
_warned_keys: set = set()


class ContextFilter(logging.Filter):
    """Logging filter that injects the active log context into every LogRecord.

    Add this filter to a :class:`~pylogshield.PyLogShield` instance (or any
    ``logging.Logger`` / ``logging.Handler``) to have context variables
    automatically stamped onto log records.

    When :class:`~pylogshield.handlers.JsonFormatter` is used the context
    fields are promoted to the **top level** of the JSON envelope (alongside
    ``timestamp``, ``level``, etc.) rather than being nested under ``extra``.

    Notes
    -----
    This filter always returns ``True`` — it never suppresses records.
    Context keys that conflict with standard ``LogRecord`` attribute names are
    silently skipped (a ``warnings.warn`` is emitted once per conflicting key).

    Examples
    --------
    >>> from pylogshield.context import ContextFilter, log_context
    >>> logger.addFilter(ContextFilter())
    >>> with log_context(env="prod"):
    ...     logger.info("deployed")   # record.env == "prod"
    """

    def filter(self, record: logging.LogRecord) -> bool:
        ctx: Dict[str, Any] = get_log_context()
        safe_ctx: Dict[str, Any] = {}
        for key, val in ctx.items():
            if key in _LOGRECORD_RESERVED:
                if key not in _warned_keys:
                    _warned_keys.add(key)
                    warnings.warn(
                        f"pylogshield: context key {key!r} conflicts with a "
                        f"standard LogRecord attribute and will be ignored.",
                        stacklevel=2,
                    )
            else:
                safe_ctx[key] = val
        # Inject each field directly onto the record so every formatter can
        # access them via record.<field>.
        record.__dict__.update(safe_ctx)
        # Tag which keys came from context so JsonFormatter can promote them.
        record.__dict__["_pylogshield_ctx_keys"] = frozenset(safe_ctx.keys())
        return True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
