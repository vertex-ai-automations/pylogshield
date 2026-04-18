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
