from __future__ import annotations

import csv
import json
import os
import threading
import time
from pathlib import Path

import pytest

from datetime import timezone

from pylogshield.tui.reader import LogReader, ParsedLine

# LogViewerApp requires the optional textual dependency.
# Tests that use it are skipped when the extra is not installed.
try:
    from pylogshield.tui.app import LogViewerApp as _LogViewerApp
    _HAS_TEXTUAL = True
except ImportError:
    _LogViewerApp = None  # type: ignore[assignment]
    _HAS_TEXTUAL = False


# ── ParsedLine ────────────────────────────────────────────────────────────

def test_parsed_line_fields():
    p = ParsedLine(
        timestamp="2026-05-09 00:12:04.221",
        level="ERROR",
        logger="myapp",
        module="payments",
        lineno=88,
        message="Payment failed",
        raw="2026-05-09 00:12:04.221  ERROR     myapp  payments:88  Payment failed",
        extra={},
    )
    assert p.level == "ERROR"
    assert p.module == "payments"
    assert p.lineno == 88


# ── LogReader._parse_line ─────────────────────────────────────────────────

def test_parse_new_standard_format():
    reader = LogReader(Path(os.devnull))
    line = "2026-05-09 00:12:04.221  ERROR     myapp  payments:88  Payment failed"
    result = reader._parse_line(line)
    assert result.timestamp == "2026-05-09 00:12:04.221"
    assert result.level == "ERROR"
    assert result.logger == "myapp"
    assert result.module == "payments"
    assert result.lineno == 88
    assert result.message == "Payment failed"


def test_parse_json_format():
    reader = LogReader(Path(os.devnull))
    entry = {
        "timestamp": "2026-05-09T05:29:39.884+00:00",
        "level": "INFO",
        "logger": "myapp",
        "message": "User login",
    }
    result = reader._parse_line(json.dumps(entry))
    assert result.timestamp == "2026-05-09T05:29:39.884+00:00"
    assert result.level == "INFO"
    assert result.logger == "myapp"
    assert result.message == "User login"
    assert result.module == ""
    assert result.lineno == 0


def test_parse_old_standard_format():
    reader = LogReader(Path(os.devnull))
    line = "2026-05-09 00:12:04,221 - myapp - ERROR - Payment failed"
    result = reader._parse_line(line)
    assert result.level == "ERROR"
    assert result.logger == "myapp"
    assert result.message == "Payment failed"


def test_parse_unparseable_line():
    reader = LogReader(Path(os.devnull))
    result = reader._parse_line("garbled log text")
    assert result.level == "N/A"
    assert result.message == "garbled log text"


def test_parse_empty_line():
    reader = LogReader(Path(os.devnull))
    result = reader._parse_line("")
    assert result.message == ""


# ── LogReader.tail ────────────────────────────────────────────────────────

def test_tail_returns_parsed_lines(tmp_path):
    log = tmp_path / "app.log"
    log.write_text(
        "2026-05-09 00:12:04.221  ERROR     myapp  payments:88  Payment failed\n"
        "2026-05-09 00:12:05.001  INFO      myapp  auth:42  User login\n"
    )
    reader = LogReader(log)
    results = reader.tail(limit=10)
    assert len(results) == 2
    assert results[0].level == "ERROR"
    assert results[1].level == "INFO"


def test_tail_respects_limit(tmp_path):
    log = tmp_path / "app.log"
    lines = "\n".join(
        f"2026-05-09 00:00:0{i}.000  INFO      myapp  core:{i}  msg {i}"
        for i in range(8)
    )
    log.write_text(lines + "\n")
    reader = LogReader(log)
    results = reader.tail(limit=3)
    assert len(results) == 3
    assert results[-1].message == "msg 7"


def test_tail_nonexistent_file(tmp_path):
    reader = LogReader(tmp_path / "does_not_exist.log")
    assert reader.tail(limit=100) == []


def test_tail_large_file_multi_chunk(tmp_path):
    """_tail_lines must return correct lines when the file exceeds the chunk size."""
    log = tmp_path / "big.log"
    # Build a file > 1 MB so _tail_lines uses the backwards binary chunked path.
    padding = "x" * 90
    num_lines = 12_000
    lines = [
        f"2026-05-09 00:00:00.000  INFO      myapp  core:{i}  msg_{i} {padding}"
        for i in range(num_lines)
    ]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert log.stat().st_size > 1_000_000, "File must exceed 1 MB to exercise chunked read"

    reader = LogReader(log)
    results = reader.tail(limit=50)

    assert len(results) == 50, f"Expected 50 rows, got {len(results)}"
    # The last returned row must correspond to the very last line written
    assert results[-1].message.startswith(f"msg_{num_lines - 1}"), (
        f"Last row message does not match last written line: {results[-1].message!r}"
    )
    # All rows must parse cleanly (no N/A level from garbled lines)
    assert all(r.level == "INFO" for r in results), (
        "Some rows have unexpected level — chunked reassembly may be corrupted"
    )


# ── LogReader.follow ──────────────────────────────────────────────────────

def test_follow_delivers_new_lines(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("2026-05-09 00:12:04.221  INFO      myapp  core:1  initial\n")

    received = []
    reader = LogReader(log)

    def run():
        reader.follow(received.append, interval=0.05)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(0.1)  # let follow reach EOF

    with log.open("a") as f:
        f.write("2026-05-09 00:12:05.000  ERROR     myapp  core:2  new line\n")

    time.sleep(0.2)  # wait for poll
    reader.stop()
    t.join(timeout=1.0)

    assert any(r.message == "new line" for r in received)


def test_follow_stop_terminates(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("")

    reader = LogReader(log)
    t = threading.Thread(target=reader.follow, args=(lambda r: None,), kwargs={"interval": 0.05}, daemon=True)
    t.start()
    time.sleep(0.1)
    reader.stop()
    t.join(timeout=1.0)
    assert not t.is_alive()


# ── Exporter ──────────────────────────────────────────────────────────────

from pylogshield.tui.exporter import Exporter


@pytest.fixture
def sample_rows() -> list:
    return [
        ParsedLine("2026-05-09 00:12:04.221", "ERROR", "myapp", "payments", 88,
                   "Payment failed order_id=ORD-12", "raw1", {}),
        ParsedLine("2026-05-09 00:15:31.004", "WARNING", "myapp", "payments", 102,
                   "Payment retry attempt=2", "raw2", {"user_id": 42}),
        ParsedLine("2026-05-09 00:18:09.441", "INFO", "myapp", "payments", 55,
                   "Payment ok", "raw3", {}),
    ]


def test_export_csv(tmp_path, sample_rows):
    path = tmp_path / "out.csv"
    Exporter(sample_rows, path).to_csv()
    assert path.exists()
    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 3
    assert rows[0]["level"] == "ERROR"
    assert rows[0]["module"] == "payments"
    assert rows[0]["lineno"] == "88"


def test_export_json(tmp_path, sample_rows):
    path = tmp_path / "out.json"
    Exporter(sample_rows, path).to_json()
    data = json.loads(path.read_text())
    assert isinstance(data, list)
    assert len(data) == 3
    assert data[1]["level"] == "WARNING"
    assert data[1]["extra"] == {"user_id": 42}


def test_export_text(tmp_path, sample_rows):
    path = tmp_path / "out.txt"
    Exporter(sample_rows, path).to_text()
    content = path.read_text()
    assert "ERROR" in content
    assert "Payment failed" in content
    assert "Payment ok" in content


def test_export_html(tmp_path, sample_rows):
    path = tmp_path / "out.html"
    Exporter(sample_rows, path).to_html()
    content = path.read_text()
    assert "<!DOCTYPE html>" in content
    assert "Payment failed" in content
    assert "3 rows" in content


def test_export_csv_headers(tmp_path, sample_rows):
    path = tmp_path / "out.csv"
    Exporter(sample_rows, path).to_csv()
    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
    assert "timestamp" in headers
    assert "level" in headers
    assert "logger" in headers
    assert "module" in headers
    assert "lineno" in headers
    assert "message" in headers


def test_export_html_escapes_content(tmp_path):
    rows = [ParsedLine("2026-05-09 00:12:04.221", "ERROR", "myapp", "core", 1,
                       "<script>alert('xss')</script>", "raw", {})]
    path = tmp_path / "out.html"
    Exporter(rows, path).to_html()
    content = path.read_text()
    assert "<script>" not in content
    assert "&lt;script&gt;" in content


# ── LogViewerApp._parse_ts ────────────────────────────────────────────────

@pytest.mark.skipif(not _HAS_TEXTUAL, reason="pylogshield[tui] not installed")
class TestParseTsMethod:
    """_parse_ts must handle all timestamp formats the library emits."""

    def _parse(self, ts: str):
        return _LogViewerApp._parse_ts(ts)

    def test_iso8601_with_full_offset(self):
        """JSON-format timestamps include a full +HH:MM offset — must not be truncated."""
        dt = self._parse("2026-05-09T05:29:39.884+00:00")
        assert dt.year == 2026
        assert dt.month == 5
        assert dt.day == 9
        assert dt.hour == 5
        assert dt.minute == 29
        assert dt.tzinfo is not None

    def test_iso8601_utc_zero_offset(self):
        dt = self._parse("2026-01-01T00:00:00.000+00:00")
        assert dt.year == 2026
        assert dt.tzinfo is not None

    def test_new_standard_format(self):
        """New plain-text formatter: YYYY-MM-DD HH:MM:SS.mmm"""
        dt = self._parse("2026-05-09 00:12:04.221")
        assert dt.year == 2026
        assert dt.hour == 0
        assert dt.tzinfo is not None   # should be UTC-filled

    def test_old_standard_format(self):
        """Old plain-text formatter uses comma for milliseconds."""
        dt = self._parse("2026-05-09 00:12:04,221")
        assert dt.year == 2026
        assert dt.tzinfo is not None

    def test_unparseable_returns_datetime_min(self):
        from datetime import datetime
        dt = self._parse("not a timestamp at all")
        assert dt == datetime.min.replace(tzinfo=timezone.utc)

    def test_all_formats_comparable_for_filtering(self):
        """A JSON timestamp and a plain-text timestamp for the same moment must compare equal."""
        from datetime import datetime, timezone
        dt_json = self._parse("2026-05-09T05:29:39.884+00:00")
        dt_plain = self._parse("2026-05-09 05:29:39.884")
        # Both should resolve to the same UTC moment
        dt_json_utc = dt_json.astimezone(timezone.utc)
        dt_plain_utc = dt_plain.astimezone(timezone.utc)
        assert dt_json_utc.replace(microsecond=0) == dt_plain_utc.replace(microsecond=0)


# ── LogReader follow restart ──────────────────────────────────────────────

def test_follow_restarts_after_stop(tmp_path):
    """LogReader.follow() must work correctly on a second call after stop()."""
    log = tmp_path / "app.log"
    log.write_text("")

    received_first = []
    received_second = []

    reader = LogReader(log)

    # First follow session
    t1 = threading.Thread(
        target=reader.follow,
        args=(received_first.append,),
        kwargs={"interval": 0.05},
        daemon=True,
    )
    t1.start()
    time.sleep(0.1)
    with log.open("a") as f:
        f.write("2026-05-09 00:00:01.000  INFO      myapp  core:1  first session\n")
    time.sleep(0.2)
    reader.stop()
    t1.join(timeout=1.0)
    assert not t1.is_alive(), "first thread did not stop"

    # Second follow session — must work after stop/restart
    t2 = threading.Thread(
        target=reader.follow,
        args=(received_second.append,),
        kwargs={"interval": 0.05},
        daemon=True,
    )
    t2.start()
    time.sleep(0.1)
    with log.open("a") as f:
        f.write("2026-05-09 00:00:02.000  ERROR     myapp  core:2  second session\n")
    time.sleep(0.2)
    reader.stop()
    t2.join(timeout=1.0)
    assert not t2.is_alive(), "second thread did not stop"

    assert any("first session" in r.message for r in received_first)
    assert any("second session" in r.message for r in received_second)
