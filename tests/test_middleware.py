"""Tests for PyLogShieldMiddleware and _sanitize_request_id."""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from pylogshield import PyLogShield
from pylogshield.middleware import PyLogShieldMiddleware, _sanitize_request_id


# ── _sanitize_request_id ──────────────────────────────────────────────────────

class TestSanitizeRequestId:
    def test_valid_uuid_passes_through(self):
        val = "550e8400-e29b-41d4-a716-446655440000"
        assert _sanitize_request_id(val) == val

    def test_valid_alphanumeric_passes_through(self):
        val = "req_ABC123"
        assert _sanitize_request_id(val) == val

    def test_strips_invalid_characters(self):
        result = _sanitize_request_id("req<script>alert(1)</script>")
        assert "<" not in result
        assert ">" not in result
        assert "(" not in result

    def test_empty_string_returns_uuid4(self):
        result = _sanitize_request_id("")
        assert len(result) == 36  # UUID4 format

    def test_all_invalid_chars_returns_uuid4(self):
        result = _sanitize_request_id("!@#$%^&*()")
        assert len(result) == 36

    def test_truncates_to_128_chars(self):
        long_val = "a" * 200
        result = _sanitize_request_id(long_val)
        assert len(result) == 128

    def test_oversized_with_invalid_chars_truncates_then_strips(self):
        # 128-char truncation gives "a"*100 + "!!!" + "b"*25; stripping "!" → 125 chars
        val = "a" * 100 + "!!!" + "b" * 100
        result = _sanitize_request_id(val)
        assert result == "a" * 100 + "b" * 25

    def test_allows_hyphens_and_underscores(self):
        val = "req-id_123"
        assert _sanitize_request_id(val) == val


# ── Middleware integration ────────────────────────────────────────────────────

def _make_app(logger: PyLogShield, **middleware_kwargs) -> Starlette:
    async def homepage(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    async def boom(request: Request) -> PlainTextResponse:
        raise RuntimeError("intentional error")

    app = Starlette(routes=[
        Route("/", homepage),
        Route("/boom", boom),
    ])
    app.add_middleware(PyLogShieldMiddleware, logger=logger, **middleware_kwargs)
    return app


@pytest.fixture()
def logger(tmp_path):
    inst = PyLogShield(
        "test_mw",
        log_directory=tmp_path,
        add_console=False,
        enable_context=True,
    )
    yield inst
    for h in inst.handlers[:]:
        h.close()
        inst.removeHandler(h)
    inst.shutdown()


class TestMiddlewareIntegration:
    def test_successful_request_logs_info(self, logger, tmp_path):
        client = TestClient(_make_app(logger))
        client.get("/")
        log_text = (tmp_path / "test_mw.log").read_text()
        assert "GET" in log_text
        assert "200" in log_text

    def test_request_id_echoed_in_response(self, logger):
        client = TestClient(_make_app(logger))
        resp = client.get("/", headers={"X-Request-ID": "abc-123"})
        assert resp.headers.get("X-Request-ID") == "abc-123"

    def test_generated_request_id_in_response(self, logger):
        client = TestClient(_make_app(logger))
        resp = client.get("/")
        rid = resp.headers.get("X-Request-ID", "")
        assert len(rid) > 0

    def test_malicious_request_id_sanitized(self, logger):
        client = TestClient(_make_app(logger))
        resp = client.get("/", headers={"X-Request-ID": "<script>alert(1)</script>"})
        rid = resp.headers.get("X-Request-ID", "")
        assert "<" not in rid
        assert ">" not in rid

    def test_custom_header_name(self, logger):
        client = TestClient(_make_app(logger, request_id_header="X-Correlation-ID"))
        resp = client.get("/", headers={"X-Correlation-ID": "corr-999"})
        assert resp.headers.get("X-Correlation-ID") == "corr-999"

    def test_log_requests_false_suppresses_info_log(self, logger, tmp_path):
        client = TestClient(_make_app(logger, log_requests=False))
        client.get("/")
        log_text = (tmp_path / "test_mw.log").read_text()
        assert "200" not in log_text

    def test_error_always_logged(self, logger, tmp_path):
        client = TestClient(_make_app(logger, log_requests=False), raise_server_exceptions=False)
        client.get("/boom")
        log_text = (tmp_path / "test_mw.log").read_text()
        assert "failed" in log_text.lower() or "error" in log_text.lower()
