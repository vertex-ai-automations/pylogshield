import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar, cast, Any

from pylogshield.core import PyLogShield


def _get_caller_info(func: Callable) -> dict:
    return {
        "filename": func.__code__.co_filename,
        "line_number": func.__code__.co_firstlineno,
        "function_name": func.__qualname__,
    }


def _log_calls(
    logger: PyLogShield,
    args: tuple,
    kwargs: dict,
    caller_info: dict,
    mask: bool = False,
) -> None:
    logger.debug(
        f"Calling {caller_info['function_name']}("
        f"args={args}, kwargs={kwargs}) "
        f"from {caller_info['filename']}:{caller_info['line_number']}",
        mask=mask,
    )


def _log_returns(
    logger: PyLogShield,
    func_name: str,
    result: Any,
    mask: bool = False,
) -> None:
    logger.debug(f"{func_name} returned: {result}", mask=mask)


P = ParamSpec("P")
R = TypeVar("R")


def log_exceptions(
    logger: PyLogShield,
    log_calls: bool = False,
    log_returns: bool = False,
    raise_exception: bool = True,
    mask: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Wrap a function to log exceptions, and optionally calls and return values.

    Parameters
    ----------
    logger : PyLogShield
        The logger to emit records to.
    log_calls : bool
        If True, log function name, args, and kwargs at DEBUG level on entry.
    log_returns : bool
        If True, log the return value at DEBUG level on success.
    raise_exception : bool
        If True (default), re-raise caught exceptions after logging.
        If False, suppress the exception and return None.
    mask : bool
        If True, apply PyLogShield sensitive-data masking to all log messages.
        Note: masking matches ``key: value`` / ``key=value`` patterns only --
        raw dict repr in ``kwargs`` is not masked.
    """

    def decorator(func):  # type: ignore[return]

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
                caller_info = _get_caller_info(func)

                if log_calls:
                    _log_calls(logger, args, kwargs, caller_info, mask=mask)

                try:
                    result = await func(*args, **kwargs)

                    if log_returns:
                        _log_returns(logger, caller_info["function_name"], result, mask=mask)

                    return result

                except Exception as e:
                    logger.exception(
                        f"Exception in {caller_info['function_name']} "
                        f"(called from {caller_info['filename']}"
                        f":{caller_info['line_number']}): {e}",
                        mask=mask,
                    )

                    if raise_exception:
                        raise

                    return None

            return cast(Callable[P, Awaitable[R]], async_wrapper)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs):
            caller_info = _get_caller_info(func)

            if log_calls:
                _log_calls(logger, args, kwargs, caller_info, mask=mask)

            try:
                result = func(*args, **kwargs)

                if log_returns:
                    _log_returns(logger, caller_info["function_name"], result, mask=mask)

                return result

            except Exception as e:
                logger.exception(
                    f"Exception in {caller_info['function_name']} "
                    f"(called from {caller_info['filename']}"
                    f":{caller_info['line_number']}): {e}",
                    mask=mask,
                )

                if raise_exception:
                    raise

                return None

        return cast(Callable[P, R], sync_wrapper)

    return decorator


def trace(
    logger: PyLogShield,
    mask: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Shorthand decorator for full entry/exit/exception tracing.

    Equivalent to ``log_exceptions(logger, log_calls=True, log_returns=True)``.
    ``raise_exception`` is always ``True``.

    Parameters
    ----------
    logger : PyLogShield
        The logger to emit records to.
    mask : bool
        If True, apply sensitive-data masking to all log messages.
    """
    return log_exceptions(logger, log_calls=True, log_returns=True, mask=mask)
