# Interactive TUI Log Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Textual-based interactive TUI log viewer accessible via `pylogshield tui --file <path>`, supporting live search, filters, stats, export, and live-follow mode.

**Architecture:** A new `src/pylogshield/tui/` package contains four focused modules: `reader.py` (file I/O + parsing), `exporter.py` (four export formats), `widgets.py` (all custom Textual widgets), and `app.py` (the `LogViewerApp` wiring everything together). The existing `viewer.py` is refactored to delegate its parsing and tail-reading to `LogReader`, keeping full backward compatibility.

**Tech Stack:** Python 3.8+, Textual ≥ 0.52.0 (optional `[tui]` extra), existing Rich + Typer stack.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `src/pylogshield/tui/__init__.py` | Package marker |
| Create | `src/pylogshield/tui/reader.py` | `ParsedLine` dataclass, `LogReader` (tail + follow + parse) |
| Create | `src/pylogshield/tui/exporter.py` | `Exporter` — CSV, JSON, plain text, HTML |
| Create | `src/pylogshield/tui/widgets.py` | `TopBar`, `LogTable`, `FilterChipBar`, `FilterPanel`, `ExportModal`, `HelpModal` |
| Create | `src/pylogshield/tui/app.py` | `LogViewerApp`, `FilterState` |
| Create | `tests/test_tui_reader.py` | Tests for `LogReader` + `Exporter` |
| Modify | `src/pylogshield/viewer.py` | Delegate `_tail_lines` + `_parse_line` to `LogReader` |
| Modify | `src/pylogshield/cli.py` | Add `tui` subcommand |
| Modify | `pyproject.toml` | Add `[tui]` optional extra |

---

## Task 1: `ParsedLine` dataclass + `LogReader`

**Files:**
- Create: `src/pylogshield/tui/__init__.py`
- Create: `src/pylogshield/tui/reader.py`
- Create: `tests/test_tui_reader.py`

- [ ] **Step 1: Create the tui package marker**

```python
# src/pylogshield/tui/__init__.py
```

- [ ] **Step 2: Write failing tests for `ParsedLine` and `LogReader`**

```python
# tests/test_tui_reader.py
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
```

- [ ] **Step 3: Run tests to confirm they all fail**

```
pytest tests/test_tui_reader.py -v
```
Expected: `ModuleNotFoundError: No module named 'pylogshield.tui'`

- [ ] **Step 4: Implement `reader.py`**

```python
# src/pylogshield/tui/reader.py
from __future__ import annotations

import json
import os
import re
import threading
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

# Matches the current PyLogShield standard formatter:
# "%(asctime)s.%(msecs)03d  %(levelname)-8s  %(name)s  %(module)s:%(lineno)d  %(message)s"
_NEW_STD = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s{2}"
    r"(\w+)\s+"
    r"(\S+)\s+"
    r"(\S+):(\d+)\s{2}"
    r"(.+)$"
)
# Matches the old PyLogShield standard formatter:
# "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_OLD_STD = re.compile(
    r"^(.+?) - (\S+) - (\w+) - (.+)$"
)


@dataclass
class ParsedLine:
    timestamp: str
    level: str
    logger: str
    module: str
    lineno: int
    message: str
    raw: str
    extra: Dict[str, object] = field(default_factory=dict)


class LogReader:
    """Reads, parses, and optionally follows a log file."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self._stop = threading.Event()

    # ── parsing ──────────────────────────────────────────────────────────

    def _parse_line(self, line: str) -> ParsedLine:
        line = line.rstrip("\n")
        if not line.strip():
            return ParsedLine("", "N/A", "", "", 0, "", line)

        # JSON format
        try:
            entry = json.loads(line)
            extra = {
                k: v for k, v in entry.items()
                if k not in {"timestamp", "level", "logger", "message", "host",
                             "exc_info", "stack_info", "module", "lineno"}
            }
            return ParsedLine(
                timestamp=entry.get("timestamp", "N/A"),
                level=entry.get("level", "N/A"),
                logger=entry.get("logger", ""),
                module=str(entry.get("module", "")),
                lineno=int(entry.get("lineno", 0)),
                message=str(entry.get("message", "")),
                raw=line,
                extra=extra,
            )
        except (json.JSONDecodeError, ValueError):
            pass

        # New standard format
        m = _NEW_STD.match(line)
        if m:
            ts, lvl, logger, module, lineno, msg = m.groups()
            return ParsedLine(
                timestamp=ts,
                level=lvl.strip(),
                logger=logger,
                module=module,
                lineno=int(lineno),
                message=msg,
                raw=line,
            )

        # Old standard format
        m = _OLD_STD.match(line)
        if m:
            ts, logger, lvl, msg = m.groups()
            return ParsedLine(
                timestamp=ts,
                level=lvl,
                logger=logger,
                module="",
                lineno=0,
                message=msg,
                raw=line,
            )

        return ParsedLine("N/A", "N/A", "", "", 0, line, line)

    # ── tail ─────────────────────────────────────────────────────────────

    def _tail_lines(self, limit: int) -> List[str]:
        if not self.path.exists():
            return []
        file_size = self.path.stat().st_size
        if file_size < 1_000_000:
            with self.path.open("r", encoding="utf-8", errors="replace") as f:
                return list(deque(f, maxlen=limit))

        chunk_size = 8192
        byte_lines: List[bytes] = []
        with self.path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            remaining = f.tell()
            buffer: bytes = b""
            while remaining > 0 and len(byte_lines) < limit:
                read_size = min(chunk_size, remaining)
                remaining -= read_size
                f.seek(remaining)
                chunk = f.read(read_size)
                buffer = chunk + buffer
                split_lines = buffer.splitlines()
                if len(split_lines) > 1:
                    byte_lines = split_lines[1:] + byte_lines
                    buffer = split_lines[0]
            if buffer:
                byte_lines = [buffer.strip()] + byte_lines

        lines = [bl.decode("utf-8", errors="replace") for bl in byte_lines]
        return lines[-limit:]

    def tail(self, limit: int = 5000) -> List[ParsedLine]:
        return [
            self._parse_line(line)
            for line in self._tail_lines(limit)
            if line.strip()
        ]

    # ── follow ────────────────────────────────────────────────────────────

    def follow(
        self,
        callback: Callable[[ParsedLine], None],
        interval: float = 0.25,
    ) -> None:
        """Block until stop() is called, invoking callback for each new line."""
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(0, os.SEEK_END)
            last_size = f.tell()
            while not self._stop.is_set():
                try:
                    cur_size = os.fstat(f.fileno()).st_size
                except OSError:
                    cur_size = 0
                if cur_size < last_size:          # log rotation
                    f.seek(0)
                line = f.readline()
                if not line:
                    last_size = cur_size
                    self._stop.wait(interval)
                    continue
                callback(self._parse_line(line))
                last_size = cur_size

    def stop(self) -> None:
        self._stop.set()
```

- [ ] **Step 5: Run tests**

```
pytest tests/test_tui_reader.py -v
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/pylogshield/tui/__init__.py src/pylogshield/tui/reader.py tests/test_tui_reader.py
git commit -m "feat(tui): add ParsedLine dataclass and LogReader"
```

---

## Task 2: `Exporter` with tests

**Files:**
- Create: `src/pylogshield/tui/exporter.py`
- Modify: `tests/test_tui_reader.py` (append exporter tests)

- [ ] **Step 1: Write failing exporter tests (append to `tests/test_tui_reader.py`)**

```python
# append to tests/test_tui_reader.py

import csv
from datetime import date

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
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_tui_reader.py -k "export" -v
```
Expected: `ImportError: cannot import name 'Exporter'`

- [ ] **Step 3: Implement `exporter.py`**

```python
# src/pylogshield/tui/exporter.py
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from pylogshield.tui.reader import ParsedLine


class Exporter:
    """Write a list of ParsedLine rows to one of four formats."""

    def __init__(self, rows: List[ParsedLine], filepath: Path) -> None:
        self._rows = rows
        self._filepath = Path(filepath)

    def to_csv(self) -> None:
        """UTF-8 with BOM so Excel opens it correctly."""
        fieldnames = ["timestamp", "level", "logger", "module", "lineno", "message"]
        extra_keys: list[str] = []
        for row in self._rows:
            for k in row.extra:
                if k not in extra_keys:
                    extra_keys.append(k)
        all_fields = fieldnames + extra_keys

        with self._filepath.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction="ignore")
            writer.writeheader()
            for row in self._rows:
                d = {
                    "timestamp": row.timestamp,
                    "level": row.level,
                    "logger": row.logger,
                    "module": row.module,
                    "lineno": row.lineno,
                    "message": row.message,
                }
                d.update(row.extra)
                writer.writerow(d)

    def to_json(self) -> None:
        data = [
            {
                "timestamp": r.timestamp,
                "level": r.level,
                "logger": r.logger,
                "module": r.module,
                "lineno": r.lineno,
                "message": r.message,
                "extra": r.extra,
            }
            for r in self._rows
        ]
        self._filepath.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def to_text(self) -> None:
        lines = []
        for r in self._rows:
            loc = f"{r.module}:{r.lineno}" if r.module else ""
            parts = [r.timestamp, f"{r.level:<8}", r.logger]
            if loc:
                parts.append(loc)
            parts.append(r.message)
            lines.append("  ".join(parts))
        self._filepath.write_text("\n".join(lines), encoding="utf-8")

    def to_html(self) -> None:
        from collections import Counter
        counts: Counter[str] = Counter(r.level for r in self._rows)
        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        ts_range = ""
        if self._rows:
            ts_range = f"{self._rows[0].timestamp} → {self._rows[-1].timestamp}"

        stats_html = " &nbsp;·&nbsp; ".join(
            f'<span style="color:{_LEVEL_COLOURS.get(lvl,"#ccc")}">'
            f'{cnt} {lvl}</span>'
            for lvl, cnt in sorted(counts.items(),
                                   key=lambda x: _LEVEL_ORDER.get(x[0], 99))
        )

        rows_html = "\n".join(
            f"<tr>"
            f'<td>{r.timestamp}</td>'
            f'<td style="color:{_LEVEL_COLOURS.get(r.level,"#ccc")}">{r.level}</td>'
            f"<td>{r.logger}</td>"
            f"<td>{r.module}:{r.lineno}</td>"
            f"<td>{r.message}</td>"
            f"</tr>"
            for r in self._rows
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8">
<title>PyLogShield Export</title>
<style>
body {{ font-family: monospace; background: #0d1117; color: #c9d1d9; padding: 20px; }}
h1 {{ color: #58a6ff; }}
.stats {{ margin-bottom: 16px; color: #8b949e; }}
table {{ border-collapse: collapse; width: 100%; }}
th {{ background: #161b22; color: #8b949e; padding: 6px 12px; text-align: left; border-bottom: 1px solid #30363d; }}
td {{ padding: 4px 12px; border-bottom: 1px solid #1c2128; }}
tr:hover td {{ background: #1c2128; }}
.footer {{ margin-top: 16px; color: #6e7681; font-size: 12px; }}
</style>
</head>
<body>
<h1>PyLogShield Log Export</h1>
<div class="stats">
  {len(self._rows)} rows &nbsp;·&nbsp; {stats_html}<br>
  Time range: {ts_range}
</div>
<table>
<tr><th>Timestamp</th><th>Level</th><th>Logger</th><th>Location</th><th>Message</th></tr>
{rows_html}
</table>
<div class="footer">Exported: {now}</div>
</body>
</html>"""
        self._filepath.write_text(html, encoding="utf-8")


_LEVEL_COLOURS = {
    "CRITICAL": "#ff7b72",
    "ERROR": "#f85149",
    "WARNING": "#d29922",
    "INFO": "#3fb950",
    "DEBUG": "#6e7681",
}
_LEVEL_ORDER = {"CRITICAL": 0, "ERROR": 1, "WARNING": 2, "INFO": 3, "DEBUG": 4}
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_tui_reader.py -v
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/pylogshield/tui/exporter.py tests/test_tui_reader.py
git commit -m "feat(tui): add Exporter (CSV, JSON, text, HTML)"
```

---

## Task 3: Delegate `viewer.py` to `LogReader`

**Files:**
- Modify: `src/pylogshield/viewer.py`

- [ ] **Step 1: Replace `_tail_lines` and `_parse_line` in `viewer.py` with delegating wrappers**

Open `src/pylogshield/viewer.py`. Replace the two private methods (keeping their signatures) with thin wrappers that call `LogReader`:

```python
# At the top of viewer.py, add:
from pylogshield.tui.reader import LogReader as _LogReader
```

Replace `_tail_lines`:
```python
def _tail_lines(self, limit: int) -> List[str]:
    return _LogReader(self.log_file)._tail_lines(limit)
```

Replace `_parse_line`:
```python
def _parse_line(self, line: str) -> Tuple[str, str, str]:
    p = _LogReader(self.log_file)._parse_line(line)
    return p.timestamp, p.level, p.message
```

- [ ] **Step 2: Run the full test suite to confirm nothing broke**

```
pytest tests/ -v --tb=short
```
Expected: all 171 existing tests pass.

- [ ] **Step 3: Commit**

```bash
git add src/pylogshield/viewer.py
git commit -m "refactor(viewer): delegate _tail_lines and _parse_line to LogReader"
```

---

## Task 4: Add `[tui]` optional dependency

**Files:**
- Modify: `pyproject.toml`
- Modify: `tests/requirements.txt`

- [ ] **Step 1: Add the optional extra to `pyproject.toml`**

Find the `[project.optional-dependencies]` section and add:

```toml
[project.optional-dependencies]
tui = ["textual>=0.52.0"]
fastapi = ["starlette>=0.27.0"]
```

- [ ] **Step 2: Install Textual for development**

```
pip install "textual>=0.52.0"
```

Expected: `Successfully installed textual-X.Y.Z`

- [ ] **Step 3: Add textual to test requirements**

Append to `tests/requirements.txt`:
```
textual>=0.52.0
```

- [ ] **Step 4: Run tests to confirm nothing broke**

```
pytest tests/ -q
```
Expected: 171 passed.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/requirements.txt
git commit -m "feat(tui): add [tui] optional dependency (textual>=0.52.0)"
```

---

## Task 5: `FilterState` + `LogViewerApp` skeleton

**Files:**
- Create: `src/pylogshield/tui/app.py`

- [ ] **Step 1: Create `app.py` with `FilterState` and a minimal runnable app**

```python
# src/pylogshield/tui/app.py
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Set

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Static

from pylogshield.tui.reader import LogReader, ParsedLine


@dataclass
class FilterState:
    levels: Set[str] = field(
        default_factory=lambda: {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
    )
    time_range: str = "all"       # "1h", "6h", "24h", "all"
    logger_name: str = ""         # substring match, case-insensitive
    search_text: str = ""
    search_regex: bool = False


_ALL_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
_LEVEL_SEVERITY = {"CRITICAL": 50, "ERROR": 40, "WARNING": 30, "INFO": 20, "DEBUG": 10}


class LogViewerApp(App[None]):
    """Interactive TUI log viewer."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("f", "toggle_follow", "Follow"),
        Binding("ctrl+f", "open_filters", "Filters"),
        Binding("e", "open_export", "Export"),
        Binding("question_mark", "open_help", "Help"),
        Binding("/", "focus_search", "Search", show=False),
        Binding("ctrl+r", "toggle_regex", "Regex", show=False),
    ]

    CSS = """
    Screen { layers: base overlay; }
    #pause-banner {
        height: 1;
        background: $warning 30%;
        color: $warning;
        content-align: center middle;
        display: none;
    }
    #pause-banner.visible { display: block; }
    """

    def __init__(
        self,
        log_path: Path,
        initial_level: Optional[str] = None,
        start_following: bool = False,
    ) -> None:
        super().__init__()
        self._path = log_path
        self._reader = LogReader(log_path)
        self._all_rows: List[ParsedLine] = []
        self._filtered_rows: List[ParsedLine] = []
        self._filter_state = FilterState()
        if initial_level:
            severity = _LEVEL_SEVERITY.get(initial_level.upper(), 0)
            self._filter_state.levels = {
                lvl for lvl, sev in _LEVEL_SEVERITY.items() if sev >= severity
            }
        self._following = start_following
        self._paused = False
        self._follow_thread: Optional[threading.Thread] = None

    def compose(self) -> ComposeResult:
        # Widgets imported here to avoid circular import at module level;
        # replaced with real widgets in Tasks 6-9.
        from pylogshield.tui.widgets import FilterChipBar, LogTable, TopBar
        yield TopBar(self._path, id="top-bar")
        yield Static("⏸  Scrolled up — live follow paused. Press End to resume.",
                     id="pause-banner")
        yield LogTable(id="log-table")
        yield FilterChipBar(id="filter-chips")
        yield Footer()

    def on_mount(self) -> None:
        if not self._path.exists():
            self.query_one("#log-table").show_error(
                f"File not found: {self._path}"
            )
            return
        self._all_rows = self._reader.tail(5000)
        self._apply_filters()
        if self._following:
            self._start_follow()

    # ── filter pipeline ───────────────────────────────────────────────────

    def _apply_filters(self) -> None:
        fs = self._filter_state
        rows = self._all_rows

        if fs.levels != _ALL_LEVELS:
            rows = [r for r in rows if r.level in fs.levels]

        if fs.time_range != "all":
            cutoff = self._time_cutoff(fs.time_range)
            if cutoff:
                rows = [r for r in rows if self._parse_ts(r.timestamp) >= cutoff]

        if fs.logger_name:
            needle = fs.logger_name.lower()
            rows = [r for r in rows if needle in r.logger.lower()]

        if fs.search_text:
            if fs.search_regex:
                try:
                    pat = re.compile(fs.search_text, re.IGNORECASE)
                    rows = [r for r in rows if pat.search(r.message)]
                except re.error:
                    pass
            else:
                needle = fs.search_text.lower()
                rows = [r for r in rows if needle in r.message.lower()]

        self._filtered_rows = rows
        self._refresh_table()
        self._refresh_stats()

    @staticmethod
    def _time_cutoff(time_range: str) -> Optional[datetime]:
        hours = {"1h": 1, "6h": 6, "24h": 24}.get(time_range)
        if hours is None:
            return None
        return datetime.now(tz=timezone.utc) - timedelta(hours=hours)

    @staticmethod
    def _parse_ts(ts: str) -> datetime:
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S,%f",
        ):
            try:
                dt = datetime.strptime(ts[:26], fmt[:len(fmt)])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        return datetime.min.replace(tzinfo=timezone.utc)

    def _refresh_table(self) -> None:
        try:
            self.query_one("#log-table").load_rows(
                self._filtered_rows, self._filter_state.search_text,
                self._filter_state.search_regex,
            )
        except Exception:
            pass

    def _refresh_stats(self) -> None:
        try:
            self.query_one("#top-bar").update_stats(self._filtered_rows, self._all_rows)
        except Exception:
            pass

    # ── live follow ───────────────────────────────────────────────────────

    def _start_follow(self) -> None:
        self._following = True
        self._paused = False
        self._follow_thread = threading.Thread(
            target=self._reader.follow,
            args=(self._on_new_line,),
            daemon=True,
        )
        self._follow_thread.start()
        try:
            self.query_one("#top-bar").set_following(True)
        except Exception:
            pass

    def _stop_follow(self) -> None:
        self._reader.stop()
        self._following = False
        self._paused = False
        try:
            self.query_one("#top-bar").set_following(False)
            self.query_one("#pause-banner").remove_class("visible")
        except Exception:
            pass

    def _on_new_line(self, line: ParsedLine) -> None:
        """Called from the follow background thread."""
        self.call_from_thread(self._append_live_row, line)

    def _append_live_row(self, line: ParsedLine) -> None:
        self._all_rows.append(line)
        self._apply_filters()

    # ── actions ───────────────────────────────────────────────────────────

    def action_toggle_follow(self) -> None:
        if self._following:
            self._stop_follow()
        else:
            self._start_follow()

    def action_focus_search(self) -> None:
        try:
            self.query_one("#search-input").focus()
        except Exception:
            pass

    def action_toggle_regex(self) -> None:
        self._filter_state.search_regex = not self._filter_state.search_regex
        self._apply_filters()
        try:
            self.query_one("#top-bar").set_regex(self._filter_state.search_regex)
        except Exception:
            pass

    def action_open_filters(self) -> None:
        from pylogshield.tui.widgets import FilterPanel
        self.push_screen(FilterPanel(self._filter_state), self._on_filter_result)

    def _on_filter_result(self, state: FilterState) -> None:
        self._filter_state = state
        self._apply_filters()
        try:
            self.query_one("#filter-chips").update_chips(state)
        except Exception:
            pass

    def action_open_export(self) -> None:
        from pylogshield.tui.widgets import ExportModal
        self.push_screen(ExportModal(self._filtered_rows, self._path))

    def action_open_help(self) -> None:
        from pylogshield.tui.widgets import HelpModal
        self.push_screen(HelpModal())

    def on_log_table_scrolled_up(self) -> None:
        if self._following and not self._paused:
            self._paused = True
            self.query_one("#pause-banner").add_class("visible")

    def on_log_table_resumed(self) -> None:
        self._paused = False
        try:
            self.query_one("#pause-banner").remove_class("visible")
        except Exception:
            pass

    def on_input_changed(self, event) -> None:
        if event.input.id == "search-input":
            self._filter_state.search_text = event.value
            self._apply_filters()
```

- [ ] **Step 2: Verify the module imports cleanly**

```
python -c "from pylogshield.tui.app import LogViewerApp, FilterState; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/pylogshield/tui/app.py
git commit -m "feat(tui): add FilterState and LogViewerApp skeleton"
```

---

## Task 6: `TopBar` widget

**Files:**
- Create: `src/pylogshield/tui/widgets.py`

- [ ] **Step 1: Create `widgets.py` with `TopBar`**

```python
# src/pylogshield/tui/widgets.py
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Input, Label, Static


# ── TopBar ────────────────────────────────────────────────────────────────

class TopBar(Static):
    """Search input + stats + live/static indicator in one compact bar."""

    DEFAULT_CSS = """
    TopBar {
        height: 3;
        background: $surface;
        border-bottom: solid $accent 50%;
        layout: horizontal;
        padding: 0 1;
        align: left middle;
    }
    TopBar #app-label { color: $accent; width: auto; margin-right: 1; }
    TopBar #file-label { color: $text-muted; width: auto; margin-right: 2; }
    TopBar #search-input { width: 1fr; }
    TopBar #regex-label { color: $warning; width: auto; margin-left: 1; display: none; }
    TopBar #regex-label.active { display: block; }
    TopBar #stats-label { color: $text-muted; width: auto; margin-left: 2; }
    TopBar #mode-label { width: auto; margin-left: 1; }
    TopBar #mode-label.live { color: $success; }
    TopBar #mode-label.static { color: $text-muted; }
    """

    def __init__(self, path: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._path = path

    def compose(self) -> ComposeResult:
        yield Label("PyLogShield", id="app-label")
        yield Label(str(self._path), id="file-label")
        yield Input(placeholder="search…", id="search-input")
        yield Label("[re]", id="regex-label")
        yield Label("", id="stats-label")
        yield Label("○ STATIC", id="mode-label", classes="static")

    def update_stats(self, filtered: list, all_rows: list) -> None:
        counts: Counter = Counter(r.level for r in all_rows)
        parts = []
        for lvl, abbr, colour in [
            ("CRITICAL", "C", "red"),
            ("ERROR", "E", "red"),
            ("WARNING", "W", "yellow"),
            ("INFO", "I", "green"),
            ("DEBUG", "D", "dim"),
        ]:
            n = counts.get(lvl, 0)
            if n:
                parts.append(f"[{colour}]{n}{abbr}[/{colour}]")
        total = f"{len(filtered)} of {len(all_rows)}"
        self.query_one("#stats-label", Label).update(
            "  ".join(parts) + f"  [{total}]" if parts else total
        )

    def set_following(self, active: bool) -> None:
        lbl = self.query_one("#mode-label", Label)
        if active:
            lbl.update("● LIVE")
            lbl.set_classes("live")
        else:
            lbl.update("○ STATIC")
            lbl.set_classes("static")

    def set_regex(self, active: bool) -> None:
        lbl = self.query_one("#regex-label", Label)
        if active:
            lbl.add_class("active")
        else:
            lbl.remove_class("active")
```

- [ ] **Step 2: Verify imports work**

```
python -c "from pylogshield.tui.widgets import TopBar; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/pylogshield/tui/widgets.py
git commit -m "feat(tui): add TopBar widget"
```

---

## Task 7: `LogTable` widget

**Files:**
- Modify: `src/pylogshield/tui/widgets.py`

- [ ] **Step 1: Append `LogTable` to `widgets.py`**

```python
# append to src/pylogshield/tui/widgets.py

import re as _re
from textual.message import Message
from textual.widgets import DataTable
from textual.widgets._data_table import RowKey
from rich.text import Text

_LEVEL_STYLES = {
    "CRITICAL": "bold red",
    "ERROR": "red",
    "WARNING": "yellow",
    "INFO": "green",
    "DEBUG": "dim",
}


class LogTable(Static):
    """Scrollable, colour-coded log table backed by a Textual DataTable."""

    class ScrolledUp(Message):
        """Posted when the user scrolls up while in follow mode."""

    class Resumed(Message):
        """Posted when the user presses End to go back to the bottom."""

    DEFAULT_CSS = """
    LogTable { height: 1fr; }
    LogTable DataTable { height: 1fr; }
    LogTable #error-panel { height: 1fr; color: $error; content-align: center middle; }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(cursor_type="row", zebra_stripes=True, id="data-table")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        tbl.add_columns(
            "Timestamp", "Level", "Logger", "Location", "Message"
        )

    def load_rows(
        self,
        rows: list,
        search_text: str = "",
        use_regex: bool = False,
        mark_new: bool = False,
    ) -> None:
        tbl = self.query_one(DataTable)
        tbl.clear()
        self._row_map: dict[str, object] = {}   # row key → ParsedLine
        pat = None
        if search_text:
            try:
                pat = _re.compile(
                    search_text if use_regex else _re.escape(search_text),
                    _re.IGNORECASE,
                )
            except _re.error:
                pass

        for i, row in enumerate(rows):
            style = _LEVEL_STYLES.get(row.level, "")
            loc = f"{row.module}:{row.lineno}" if row.module else "N/A"

            msg = row.message
            if mark_new and i == len(rows) - 1:
                msg = msg + "  [NEW]"

            if pat:
                msg_text = Text(msg)
                for m in pat.finditer(msg):
                    msg_text.stylize("bold yellow", m.start(), m.end())
                message_cell = msg_text
            else:
                message_cell = Text(msg, style=style)

            key = str(id(row))
            self._row_map[key] = row
            tbl.add_row(
                Text(row.timestamp, style="dim"),
                Text(row.level, style=style),
                Text(row.logger, style=style),
                Text(loc, style="dim"),
                message_cell,
                key=key,
            )

    def show_error(self, message: str) -> None:
        self.query_one(DataTable).display = False
        self.mount(Label(message, id="error-panel"))

    def on_data_table_row_selected(self, event) -> None:
        """Expand a detail panel for the selected row (Enter key)."""
        key = str(event.row_key.value) if event.row_key else None
        if not key:
            return
        row = getattr(self, "_row_map", {}).get(key)
        if row is None:
            return
        self.app.push_screen(DetailModal(row))

    def on_key(self, event) -> None:
        if event.key == "end":
            self.post_message(self.Resumed())
        elif event.key in ("up", "pageup"):
            self.post_message(self.ScrolledUp())
```

- [ ] **Step 2: Verify**

```
python -c "from pylogshield.tui.widgets import LogTable; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add src/pylogshield/tui/widgets.py
git commit -m "feat(tui): add LogTable widget with colour coding and search highlight"
```

---

## Task 8: `FilterChipBar` + `FilterPanel` modal

**Files:**
- Modify: `src/pylogshield/tui/widgets.py`

- [ ] **Step 1: Append `FilterChipBar` and `FilterPanel` to `widgets.py`**

```python
# append to src/pylogshield/tui/widgets.py

from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, RadioButton, RadioSet


class FilterChipBar(Static):
    """Shows active filters as removable chip labels."""

    DEFAULT_CSS = """
    FilterChipBar {
        height: 3;
        background: $surface-darken-1;
        layout: horizontal;
        align: left middle;
        padding: 0 1;
        border-top: solid $accent 20%;
    }
    FilterChipBar .chip-label { color: $text-muted; margin-right: 1; }
    FilterChipBar .chip { background: $accent 20%; color: $accent;
                          margin-right: 1; padding: 0 1; }
    FilterChipBar .add-hint { color: $text-muted; opacity: 0.6; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._state = None

    def compose(self) -> ComposeResult:
        yield Label("Filters", classes="chip-label")
        yield Label("none active", classes="add-hint", id="chip-list")

    def update_chips(self, state) -> None:
        from pylogshield.tui.app import FilterState, _ALL_LEVELS
        self._state = state
        chips = []
        if state.levels != _ALL_LEVELS:
            min_sev = min(
                {"CRITICAL": 50, "ERROR": 40, "WARNING": 30,
                 "INFO": 20, "DEBUG": 10}.get(l, 0)
                for l in state.levels
            )
            label = {50: "CRITICAL+", 40: "ERROR+", 30: "WARNING+",
                     20: "INFO+", 10: "DEBUG+"}.get(min_sev, "custom")
            chips.append(label)
        if state.time_range != "all":
            chips.append(state.time_range)
        if state.logger_name:
            chips.append(f"logger:{state.logger_name}")

        chip_lbl = self.query_one("#chip-list", Label)
        if chips:
            chip_lbl.update("  ".join(f"[{c}]" for c in chips) + "  + add filter")
        else:
            chip_lbl.update("none active  + add filter")


class DetailModal(ModalScreen[None]):
    """Full detail view for a single log row (Enter to open, Esc to close)."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    DEFAULT_CSS = """
    DetailModal { align: center middle; }
    DetailModal > Vertical {
        width: 80; height: auto; max-height: 80%;
        background: $surface; border: solid $accent; padding: 1 2;
    }
    DetailModal .detail-title { color: $accent; margin-bottom: 1; }
    DetailModal .detail-field { margin-bottom: 0; }
    """

    def __init__(self, row, **kwargs) -> None:
        super().__init__(**kwargs)
        self._row = row

    def compose(self) -> ComposeResult:
        from textual.containers import Vertical
        r = self._row
        with Vertical():
            yield Label("Row Detail", classes="detail-title")
            for label, value in [
                ("Timestamp", r.timestamp),
                ("Level", r.level),
                ("Logger", r.logger),
                ("Location", f"{r.module}:{r.lineno}" if r.module else "N/A"),
                ("Message", r.message),
            ]:
                yield Label(f"[bold]{label}:[/bold]  {value}", classes="detail-field")
            if r.extra:
                import json as _json
                yield Label(
                    f"[bold]Extra:[/bold]  {_json.dumps(r.extra, default=str)}",
                    classes="detail-field",
                )
            yield Label("", classes="detail-field")
            yield Label(f"[dim]{r.raw}[/dim]", classes="detail-field")
            yield Label("Esc to close", classes="section-title")


class FilterPanel(ModalScreen["FilterState"]):
    """Modal filter configuration panel."""

    BINDINGS = [
        Binding("escape", "dismiss_default", "Close"),
        Binding("r", "reset_filters", "Reset"),
    ]

    DEFAULT_CSS = """
    FilterPanel {
        align: center middle;
    }
    FilterPanel > Vertical {
        width: 60;
        height: auto;
        background: $surface;
        border: solid $accent;
        padding: 1 2;
    }
    FilterPanel .panel-title { color: $accent; margin-bottom: 1; }
    FilterPanel .section-title { color: $text-muted; margin-top: 1; }
    FilterPanel Button { margin-top: 1; }
    """

    def __init__(self, state, **kwargs) -> None:
        super().__init__(**kwargs)
        self._state = state

    def compose(self) -> ComposeResult:
        from textual.containers import Vertical
        from pylogshield.tui.app import _ALL_LEVELS
        with Vertical():
            yield Label("Filter Panel", classes="panel-title")

            yield Label("Log Levels", classes="section-title")
            for lvl in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
                yield Checkbox(
                    lvl,
                    value=(lvl in self._state.levels),
                    id=f"lvl-{lvl.lower()}",
                )

            yield Label("Time Range", classes="section-title")
            with RadioSet(id="time-range"):
                for label, value in [
                    ("All time", "all"),
                    ("Last 1h", "1h"),
                    ("Last 6h", "6h"),
                    ("Last 24h", "24h"),
                ]:
                    yield RadioButton(
                        label,
                        value=(self._state.time_range == value),
                        id=f"tr-{value}",
                    )

            yield Label("Logger name (substring)", classes="section-title")
            yield Input(
                value=self._state.logger_name,
                placeholder="e.g. myapp",
                id="logger-input",
            )

            yield Button("Apply  [Esc]", variant="primary", id="apply-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply-btn":
            self._collect_and_dismiss()

    def action_dismiss_default(self) -> None:
        self._collect_and_dismiss()

    def action_reset_filters(self) -> None:
        from pylogshield.tui.app import FilterState
        self.dismiss(FilterState())

    def _collect_and_dismiss(self) -> None:
        from pylogshield.tui.app import FilterState
        levels = set()
        for lvl in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
            cb = self.query_one(f"#lvl-{lvl.lower()}", Checkbox)
            if cb.value:
                levels.add(lvl)

        time_range = "all"
        for label, value in [("All time", "all"), ("Last 1h", "1h"),
                              ("Last 6h", "6h"), ("Last 24h", "24h")]:
            rb = self.query_one(f"#tr-{value}", RadioButton)
            if rb.value:
                time_range = value
                break

        logger_name = self.query_one("#logger-input", Input).value.strip()
        new_state = FilterState(
            levels=levels or {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"},
            time_range=time_range,
            logger_name=logger_name,
            search_text=self._state.search_text,
            search_regex=self._state.search_regex,
        )
        self.dismiss(new_state)
```

- [ ] **Step 2: Verify**

```
python -c "from pylogshield.tui.widgets import FilterChipBar, FilterPanel; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add src/pylogshield/tui/widgets.py
git commit -m "feat(tui): add FilterChipBar and FilterPanel modal"
```

---

## Task 9: `ExportModal`

**Files:**
- Modify: `src/pylogshield/tui/widgets.py`

- [ ] **Step 1: Append `ExportModal` to `widgets.py`**

```python
# append to src/pylogshield/tui/widgets.py

from datetime import date


class ExportModal(ModalScreen[None]):
    """Four-format export picker."""

    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    DEFAULT_CSS = """
    ExportModal { align: center middle; }
    ExportModal > Vertical {
        width: 60; height: auto;
        background: $surface; border: solid $accent; padding: 1 2;
    }
    ExportModal .modal-title { color: $accent; margin-bottom: 1; }
    ExportModal .export-opt { margin-bottom: 0; }
    ExportModal #export-status { color: $success; margin-top: 1; display: none; }
    ExportModal #export-status.visible { display: block; }
    ExportModal #export-error { color: $error; margin-top: 1; display: none; }
    ExportModal #export-error.visible { display: block; }
    """

    _FORMATS = [
        ("csv",  "CSV (Excel-compatible)"),
        ("json", "JSON"),
        ("txt",  "Plain text"),
        ("html", "HTML report"),
    ]

    def __init__(self, rows: list, log_path: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._rows = rows
        self._log_path = log_path

    def compose(self) -> ComposeResult:
        from textual.containers import Vertical
        stem = self._log_path.stem
        today = date.today().isoformat()
        with Vertical():
            yield Label(
                f"Export {len(self._rows)} rows",
                classes="modal-title",
            )
            for ext, label in self._FORMATS:
                filename = f"{stem}-export-{today}.{ext}"
                yield Button(
                    f"{label}  →  {filename}",
                    id=f"export-{ext}",
                    classes="export-opt",
                )
            yield Label("", id="export-status")
            yield Label("", id="export-error")
            yield Label(
                "Esc to cancel · Exports to current directory",
                classes="section-title",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        ext = event.button.id.removeprefix("export-")
        stem = self._log_path.stem
        today = date.today().isoformat()
        out = Path(f"{stem}-export-{today}.{ext}")
        from pylogshield.tui.exporter import Exporter
        exp = Exporter(self._rows, out)
        try:
            {"csv": exp.to_csv, "json": exp.to_json,
             "txt": exp.to_text, "html": exp.to_html}[ext]()
            status = self.query_one("#export-status", Label)
            status.update(f"Saved → {out.resolve()}")
            status.add_class("visible")
        except Exception as exc:
            err = self.query_one("#export-error", Label)
            err.update(f"Export failed: {exc}")
            err.add_class("visible")
```

- [ ] **Step 2: Verify**

```
python -c "from pylogshield.tui.widgets import ExportModal; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add src/pylogshield/tui/widgets.py
git commit -m "feat(tui): add ExportModal with all four formats"
```

---

## Task 10: `HelpModal`

**Files:**
- Modify: `src/pylogshield/tui/widgets.py`

- [ ] **Step 1: Append `HelpModal` to `widgets.py`**

```python
# append to src/pylogshield/tui/widgets.py


class HelpModal(ModalScreen[None]):
    """Two-column keyboard reference overlay."""

    BINDINGS = [Binding("escape", "dismiss", "Close"),
                Binding("question_mark", "dismiss", "Close")]

    DEFAULT_CSS = """
    HelpModal { align: center middle; }
    HelpModal > Vertical {
        width: 72; height: auto;
        background: $surface; border: solid $accent; padding: 1 2;
    }
    HelpModal .help-title { color: $accent; margin-bottom: 1; }
    HelpModal .col { width: 1fr; }
    HelpModal .section-title { color: $accent; }
    """

    _BINDINGS_TABLE = [
        ("Navigation", [
            ("↑ ↓", "Move between rows"),
            ("PgUp PgDn", "Page up / down"),
            ("Home / End", "First / last row (End resumes follow)"),
            ("Enter", "Expand row detail"),
        ]),
        ("Search & Filter", [
            ("/", "Focus search bar"),
            ("Ctrl+R", "Toggle regex mode"),
            ("Esc", "Clear search / close modal"),
            ("Ctrl+F", "Open filter panel"),
        ]),
        ("View & Actions", [
            ("F", "Toggle live follow"),
            ("E", "Open export modal"),
            ("?", "Show / hide this help"),
            ("Q / Ctrl+C", "Quit"),
        ]),
    ]

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal, Vertical
        with Vertical():
            yield Label("PyLogShield — Keyboard Reference", classes="help-title")
            with Horizontal():
                for section, keys in self._BINDINGS_TABLE:
                    with Vertical(classes="col"):
                        yield Label(section, classes="section-title")
                        for key, desc in keys:
                            yield Label(f"  [{key}]  {desc}")
            yield Label("Press Esc or ? to close", classes="section-title")
```

- [ ] **Step 2: Verify**

```
python -c "from pylogshield.tui.widgets import HelpModal; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add src/pylogshield/tui/widgets.py
git commit -m "feat(tui): add HelpModal keyboard reference overlay"
```

---

## Task 11: `pylogshield tui` CLI command

**Files:**
- Modify: `src/pylogshield/cli.py`

- [ ] **Step 1: Add the `tui` command to `cli.py`**

Add these imports at the top of `cli.py`, below the existing imports:

```python
# (add after existing imports)
import sys as _sys
```

Add the new command at the bottom of `cli.py` (before or after `show_levels`):

```python
# ---------------------------------------------------------------------------
# tui
# ---------------------------------------------------------------------------

@app.command("tui")
def tui_viewer(
    file: Path = typer.Option(
        ..., "--file", "-f", exists=True, readable=True,
        help="Path to the log file.",
    ),
    level: Optional[str] = typer.Option(
        None, "--level", "-l",
        help="Start with this minimum level pre-filtered (e.g. ERROR).",
    ),
    follow: bool = typer.Option(
        False, "--follow", is_flag=True,
        help="Start in live-follow mode.",
    ),
) -> None:
    """Launch the [bold]interactive TUI[/bold] log viewer.

    Requires: [cyan]pip install 'pylogshield\\[tui\\]'[/cyan]

    [bold]Examples:[/bold]

      pylogshield tui -f app.log
      pylogshield tui -f app.log -l ERROR --follow
    """
    try:
        from pylogshield.tui.app import LogViewerApp
    except ImportError:
        _console.print(
            "[red]TUI support is not installed.[/red]\n"
            "Run: [cyan]pip install 'pylogshield\\[tui\\]'[/cyan]"
        )
        raise typer.Exit(code=1)

    app_instance = LogViewerApp(
        log_path=file,
        initial_level=level,
        start_following=follow,
    )
    app_instance.run()
```

- [ ] **Step 2: Verify the command is registered**

```
python -m pylogshield --help
```
Expected: output includes `tui` in the list of commands.

- [ ] **Step 3: Run the full test suite to confirm nothing broke**

```
pytest tests/ -q
```
Expected: 171 passed.

- [ ] **Step 4: Commit**

```bash
git add src/pylogshield/cli.py
git commit -m "feat(tui): add 'pylogshield tui' CLI command"
```

---

## Task 12: Smoke-test the full TUI

- [ ] **Step 1: Generate a sample log file to test against**

```python
# run this once to generate test data
python -c "
import tempfile, pathlib
from pylogshield import PyLogShield
import logging

d = pathlib.Path('.')
logger = PyLogShield('demo', log_directory=d, log_file='demo.log',
                     add_console=False, log_level='DEBUG')
for i in range(50):
    logger.debug(f'Debug message {i}')
    logger.info(f'User login user_id={i}')
    if i % 5 == 0:
        logger.warning(f'Rate limit threshold=80%')
    if i % 10 == 0:
        logger.error(f'Payment failed order_id=ORD-{i}')
logger.shutdown()
print('Written demo.log')
"
```

- [ ] **Step 2: Launch the TUI in static mode**

```
python -m pylogshield tui --file demo.log
```

Verify manually:
- TopBar shows filename, badge counts, `○ STATIC`
- Table renders with colour-coded levels
- `/` focuses search input; typing filters rows and highlights matches
- `Ctrl+F` opens FilterPanel; selecting ERROR+ and applying shows only errors
- `E` opens ExportModal; selecting CSV creates the file
- `?` shows HelpModal
- `Q` exits cleanly

- [ ] **Step 3: Launch in follow mode (tail a growing file in background)**

Open two terminals. In terminal 1:

```
python -m pylogshield tui --file demo.log --follow
```

In terminal 2 (append lines while TUI is open):

```python
python -c "
import time, pathlib
from pylogshield import PyLogShield
logger = PyLogShield('demo', log_directory=pathlib.Path('.'),
                     log_file='demo.log', add_console=False)
for i in range(10):
    logger.info(f'Live line {i}')
    time.sleep(0.5)
logger.shutdown()
"
```

Verify: new rows appear with `[NEW]` badge; scrolling up shows the pause banner; pressing `End` resumes.

- [ ] **Step 4: Clean up demo file**

```bash
rm demo.log
```

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "feat(tui): complete interactive TUI log viewer"
```

---

## Self-Review Checklist (completed inline)

| Spec requirement | Task |
|---|---|
| Textual TUI, `[tui]` extra | Task 4 |
| `ParsedLine` dataclass | Task 1 |
| `LogReader.tail()` | Task 1 |
| `LogReader.follow()` + log rotation | Task 1 |
| `Exporter` CSV/JSON/text/HTML | Task 2 |
| `viewer.py` backward compat | Task 3 |
| `LogViewerApp` layout (C) | Task 5 |
| `TopBar` (search + stats + mode) | Task 6 |
| `LogTable` (colours, highlight, keyboard) | Task 7 |
| Enter → row detail panel (`DetailModal`) | Task 7 |
| `FilterChipBar` + `FilterPanel` modal | Task 8 |
| Live follow + pause banner | Task 5 (`_start_follow`, `_append_live_row`) |
| `ExportModal` (auto filename, 4 formats) | Task 9 |
| `HelpModal` (full keybinding table) | Task 10 |
| `pylogshield tui` CLI command | Task 11 |
| ImportError message for missing Textual | Task 11 |
| File-not-found error handling | Task 5 (`on_mount`) |
| Export failure shown inline | Task 9 |
| Tests: `LogReader` + `Exporter` | Tasks 1–2 |
