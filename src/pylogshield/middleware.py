"""FastAPI / Starlette ASGI middleware for automatic request context logging.

Install the optional dependency before using this module::

    pip install "pylogshield[fastapi]"

Usage::

    from fastapi import FastAPI
    from pylogshield import get_logger
    from pylogshield.middleware import PyLogShieldMiddleware

    app = FastAPI()
    logger = get_logger("api", enable_context=True, enable_json=True)
    app.add_middleware(PyLogShieldMiddleware, logger=logger)

    @app.get("/items")
    async def list_items():
        logger.info("Listing items")
        # Every log line automatically includes:
        #   request_id, http_method, http_path, client_ip
        return []

The middleware also echoes the ``X-Request-ID`` header back in the response so
callers can correlate their own traces with server-side logs.
"""
from __future__ import annotations

import re
import time
import uuid
from typing import Any, Callable

_REQUEST_ID_PATTERN = re.compile(r"[^A-Za-z0-9\-_]")


def _sanitize_request_id(value: str) -> str:
    """Sanitize an ``X-Request-ID`` header value.

    1. Truncates to 128 characters.
    2. Strips any character not matching ``[A-Za-z0-9\\-_]``.
    3. Falls back to a fresh ``uuid4()`` if the sanitized result is empty.
    """
    truncated = value[:128]
    sanitized = _REQUEST_ID_PATTERN.sub("", truncated)
    return sanitized if sanitized else str(uuid.uuid4())

from pylogshield.context import async_log_context

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.types import ASGIApp

    _HAS_STARLETTE = True
except ImportError:
    _HAS_STARLETTE = False


if _HAS_STARLETTE:

    class PyLogShieldMiddleware(BaseHTTPMiddleware):
        """FastAPI/Starlette middleware for automatic request context logging.

        For every incoming request the middleware:

        1. Reads (or generates) a ``request_id`` correlation ID.
        2. Opens a :func:`~pylogshield.context.async_log_context` block that
           injects ``request_id``, ``http_method``, ``http_path``, and
           ``client_ip`` into every log record emitted during the request.
        3. Logs request completion at INFO level (status code + duration).
        4. Echoes ``request_id`` back in the response via the configured header.

        Parameters
        ----------
        app : ASGIApp
            The ASGI application to wrap.
        logger : PyLogShield
            Logger used to emit the request/response summary lines.  Should be
            created with ``enable_context=True`` so context fields are included
            in its output.
        request_id_header : str, optional
            Name of the HTTP header used to read / write the correlation ID.
            If the incoming request carries this header its value is reused;
            otherwise a fresh UUID4 is generated.  Default is
            ``"X-Request-ID"``.
        log_requests : bool, optional
            Emit an INFO log line when each request completes (includes HTTP
            method, path, status code, and duration_ms).  Errors are always
            logged regardless of this setting.  Default is ``True``.

        Examples
        --------
        ::

            from fastapi import FastAPI
            from pylogshield import get_logger
            from pylogshield.middleware import PyLogShieldMiddleware

            app = FastAPI()
            logger = get_logger("api", enable_context=True, enable_json=True)
            app.add_middleware(
                PyLogShieldMiddleware,
                logger=logger,
                request_id_header="X-Correlation-ID",
            )
        """

        def __init__(
            self,
            app: ASGIApp,
            logger: Any,
            *,
            request_id_header: str = "X-Request-ID",
            log_requests: bool = True,
        ) -> None:
            super().__init__(app)
            self.logger = logger
            self.request_id_header = request_id_header
            self.log_requests = log_requests

        async def dispatch(self, request: Request, call_next: Callable) -> Response:
            raw_id = request.headers.get(self.request_id_header) or str(uuid.uuid4())
            request_id = _sanitize_request_id(raw_id)
            client_ip = request.client.host if request.client else None
            start = time.monotonic()

            async with async_log_context(
                request_id=request_id,
                http_method=request.method,
                http_path=request.url.path,
                client_ip=client_ip,
            ):
                try:
                    response = await call_next(request)
                except Exception:
                    duration_ms = round((time.monotonic() - start) * 1000, 2)
                    self.logger.error(
                        f"{request.method} {request.url.path} failed "
                        f"after {duration_ms}ms",
                        exc_info=True,
                    )
                    raise

                duration_ms = round((time.monotonic() - start) * 1000, 2)

                if self.log_requests:
                    self.logger.info(
                        f"{request.method} {request.url.path} {response.status_code}",
                        extra={
                            "duration_ms": duration_ms,
                            "status_code": response.status_code,
                        },
                    )

                response.headers[self.request_id_header] = request_id
                return response

else:

    class PyLogShieldMiddleware:  # type: ignore[no-redef]
        """Stub that raises ``ImportError`` when starlette is not installed."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError(
                "PyLogShieldMiddleware requires starlette. "
                "Install it with: pip install 'pylogshield[fastapi]'"
            )
