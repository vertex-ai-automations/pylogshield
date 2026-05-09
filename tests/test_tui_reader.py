from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from pylogshield.tui.reader import LogReader, ParsedLine


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
    reader = LogReader(Path("/dev/null"))
    line = "2026-05-09 00:12:04.221  ERROR     myapp  payments:88  Payment failed"
    result = reader._parse_line(line)
    assert result.timestamp == "2026-05-09 00:12:04.221"
    assert result.level == "ERROR"
    assert result.logger == "myapp"
    assert result.module == "payments"
    assert result.lineno == 88
    assert result.message == "Payment failed"


def test_parse_json_format():
    reader = LogReader(Path("/dev/null"))
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
    reader = LogReader(Path("/dev/null"))
    line = "2026-05-09 00:12:04,221 - myapp - ERROR - Payment failed"
    result = reader._parse_line(line)
    assert result.level == "ERROR"
    assert result.logger == "myapp"
    assert result.message == "Payment failed"


def test_parse_unparseable_line():
    reader = LogReader(Path("/dev/null"))
    result = reader._parse_line("garbled log text")
    assert result.level == "N/A"
    assert result.message == "garbled log text"


def test_parse_empty_line():
    reader = LogReader(Path("/dev/null"))
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


def test_tail_nonexistent_file():
    reader = LogReader(Path("/nonexistent/app.log"))
    assert reader.tail(limit=100) == []
