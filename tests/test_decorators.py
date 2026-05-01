"""Tests for log_exceptions and trace decorators."""

from __future__ import annotations

import pytest

from pylogshield import PyLogShield, log_exceptions, trace


class TestSyncExceptions:

    def test_sync_exception_reraised(self, basic_logger: PyLogShield) -> None:
        @log_exceptions(basic_logger)
        def risky() -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            risky()

        content = basic_logger.log_file_path.read_text()
        assert "Exception in" in content
        assert "boom" in content

    def test_sync_exception_suppressed(self, basic_logger: PyLogShield) -> None:
        @log_exceptions(basic_logger, raise_exception=False)
        def risky() -> int:
            raise ValueError("boom")

        result = risky()

        assert result is None
        content = basic_logger.log_file_path.read_text()
        assert "Exception in" in content

    def test_no_exception_no_error_log(self, basic_logger: PyLogShield) -> None:
        @log_exceptions(basic_logger)
        def safe() -> int:
            return 42

        safe()

        content = basic_logger.log_file_path.read_text()
        assert "ERROR" not in content


class TestAsyncExceptions:

    async def test_async_exception_reraised(self, basic_logger: PyLogShield) -> None:
        @log_exceptions(basic_logger)
        async def risky() -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await risky()

        content = basic_logger.log_file_path.read_text()
        assert "Exception in" in content
        assert "boom" in content

    async def test_async_exception_suppressed(self, basic_logger: PyLogShield) -> None:
        @log_exceptions(basic_logger, raise_exception=False)
        async def risky() -> int:
            raise ValueError("boom")

        result = await risky()

        assert result is None
        content = basic_logger.log_file_path.read_text()
        assert "Exception in" in content


class TestCallAndReturnLogging:

    def test_log_calls(self, basic_logger: PyLogShield) -> None:
        basic_logger.set_log_level("DEBUG")

        @log_exceptions(basic_logger, log_calls=True)
        def greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"

        greet("Alice", greeting="Hi")

        content = basic_logger.log_file_path.read_text()
        assert "Calling" in content
        assert "greet" in content

    def test_log_returns(self, basic_logger: PyLogShield) -> None:
        basic_logger.set_log_level("DEBUG")

        @log_exceptions(basic_logger, log_returns=True)
        def add(a: int, b: int) -> int:
            return a + b

        add(1, 41)

        content = basic_logger.log_file_path.read_text()
        assert "returned:" in content
        assert "42" in content

    async def test_async_log_calls(self, basic_logger: PyLogShield) -> None:
        basic_logger.set_log_level("DEBUG")

        @log_exceptions(basic_logger, log_calls=True)
        async def fetch(url: str) -> str:
            return f"data from {url}"

        await fetch("https://example.com")

        content = basic_logger.log_file_path.read_text()
        assert "Calling" in content
        assert "fetch" in content


class TestMasking:

    def test_mask_applied_to_return_value(self, basic_logger: PyLogShield) -> None:
        basic_logger.set_log_level("DEBUG")

        @log_exceptions(basic_logger, log_returns=True, mask=True)
        def get_secret() -> str:
            return "password: mysecret"

        get_secret()

        content = basic_logger.log_file_path.read_text()
        assert "mysecret" not in content


class TestTrace:

    def test_trace_enables_calls_and_returns(self, basic_logger: PyLogShield) -> None:
        basic_logger.set_log_level("DEBUG")

        @trace(basic_logger)
        def add(a: int, b: int) -> int:
            return a + b

        add(3, 4)

        content = basic_logger.log_file_path.read_text()
        assert "Calling" in content
        assert "returned:" in content
