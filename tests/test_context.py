import logging
import warnings
from pylogshield.context import ContextFilter, log_context


def test_warned_keys_are_per_instance():
    """Two separate ContextFilter instances each emit their own warnings."""
    filter1 = ContextFilter()
    filter2 = ContextFilter()

    with log_context(name="reserved_value"):  # 'name' is reserved in LogRecord
        record1 = logging.LogRecord("t", logging.INFO, "", 0, "msg", (), None)
        with warnings.catch_warnings(record=True) as w1:
            warnings.simplefilter("always")
            filter1.filter(record1)

        record2 = logging.LogRecord("t", logging.INFO, "", 0, "msg", (), None)
        with warnings.catch_warnings(record=True) as w2:
            warnings.simplefilter("always")
            filter2.filter(record2)

    assert len(w1) >= 1, "filter1 should have warned about 'name'"
    assert len(w2) >= 1, "filter2 should also warn — it has its own warned_keys"


def test_same_instance_warns_only_once():
    """A single ContextFilter instance warns only once per key."""
    filt = ContextFilter()

    with log_context(name="reserved_value"):
        record1 = logging.LogRecord("t", logging.INFO, "", 0, "msg", (), None)
        record2 = logging.LogRecord("t", logging.INFO, "", 0, "msg", (), None)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            filt.filter(record1)
            filt.filter(record2)  # Second call — same key

    assert len(w) == 1, f"Expected 1 warning, got {len(w)}"


import asyncio  # noqa: E402
from pylogshield.context import async_log_context, get_log_context  # noqa: E402


async def _task(task_id: str, results: dict):
    async with async_log_context(task_id=task_id):
        await asyncio.sleep(0.01)  # Yield to allow interleaving
        results[task_id] = get_log_context().get("task_id")


def test_async_context_isolation_in_gather():
    """Concurrent asyncio tasks must have isolated context (no bleed-through)."""
    results = {}

    async def main():
        await asyncio.gather(
            _task("A", results),
            _task("B", results),
            _task("C", results),
        )

    asyncio.run(main())

    assert results["A"] == "A", f"Task A saw wrong context: {results['A']}"
    assert results["B"] == "B", f"Task B saw wrong context: {results['B']}"
    assert results["C"] == "C", f"Task C saw wrong context: {results['C']}"


def test_nested_log_context_merges_fields():
    """Inner log_context fields merge on top of outer; outer fields survive inner exit."""
    from pylogshield.context import get_log_context

    with log_context(service="payments"):
        outer = get_log_context()
        assert outer.get("service") == "payments"
        assert "tx_id" not in outer

        with log_context(tx_id="tx-99"):
            inner = get_log_context()
            assert inner.get("service") == "payments", (
                "Outer field 'service' must still be visible inside nested context"
            )
            assert inner.get("tx_id") == "tx-99", (
                "Inner field 'tx_id' must be visible inside nested context"
            )

        after_inner = get_log_context()
        assert after_inner.get("service") == "payments", (
            "Outer field 'service' must be restored after inner context exits"
        )
        assert "tx_id" not in after_inner, (
            "Inner field 'tx_id' must not leak back into outer context"
        )

    empty = get_log_context()
    assert empty == {}, "Context must be empty after all blocks exit"


def test_nested_log_context_restores_on_exception():
    """Outer context is fully restored even when inner block raises."""
    from pylogshield.context import get_log_context

    with log_context(service="billing"):
        try:
            with log_context(crash="yes"):
                raise RuntimeError("boom")
        except RuntimeError:
            pass

        ctx = get_log_context()
        assert ctx.get("service") == "billing", (
            "Outer field must survive an exception in inner context"
        )
        assert "crash" not in ctx, (
            "Inner field must not leak when inner context exits via exception"
        )
