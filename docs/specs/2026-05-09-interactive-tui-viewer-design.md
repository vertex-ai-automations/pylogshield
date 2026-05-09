# Interactive TUI Log Viewer — Design Spec

**Date:** 2026-05-09
**Status:** Approved

---

## Overview

Replace the existing `LogViewer` Rich-table display with a full interactive TUI built on **Textual**. The TUI supports two modes — static (forensic analysis of a log file) and live follow (real-time monitoring) — and exposes them through a single `pylogshield tui --file <path>` CLI command. All existing `view` and `follow` commands remain unchanged.

---

## Goals

- Keyboard-driven interface that works anywhere Python runs (SSH, CI, headless servers)
- Single entrypoint for both static analysis and live monitoring
- Search, multi-filter, stats, and export without leaving the terminal
- Suitable for auditing and incident investigation

---

## Architecture

### New dependency

Add `textual>=0.52.0` as an optional dependency under a new `[tui]` extra:

```toml
[project.optional-dependencies]
tui = ["textual>=0.52.0"]
fastapi = ["starlette>=0.27.0"]
```

The existing `rich` dependency is already in core requirements; Textual sits on top of it.

### New files

| File | Purpose |
|---|---|
| `src/pylogshield/tui/__init__.py` | Package marker |
| `src/pylogshield/tui/app.py` | `LogViewerApp` — the Textual `App` subclass |
| `src/pylogshield/tui/widgets.py` | Custom widgets: `StatsBar`, `LogTable`, `FilterBar`, `ExportModal`, `HelpModal` |
| `src/pylogshield/tui/reader.py` | `LogReader` — file reading, parsing, and live-follow logic (extracted from `viewer.py`) |
| `src/pylogshield/tui/exporter.py` | `Exporter` — write filtered rows to CSV / JSON / plain text / HTML |

### Existing files modified

| File | Change |
|---|---|
| `src/pylogshield/cli.py` | Add `tui` command calling `LogViewerApp` |
| `src/pylogshield/viewer.py` | Extract `_tail_lines`, `_parse_line` into `reader.py`; keep `LogViewer` for backward compat |
| `pyproject.toml` | Add `[tui]` optional extra |

---

## Layout (Layout C — Compact)

```
┌─────────────────────────────────────────────────────────────────────┐
│ PyLogShield  ~/.logs/myapp.log  [search box]  2C 8E 23W 412I  ○STATIC │  ← TopBar
├─────────────────────────────────────────────────────────────────────┤
│ Timestamp              Level    Logger  Location   Message           │
│ 2026-05-09 00:12:04    ERROR    myapp   payments:88  Payment failed  │  ← LogTable
│▶ 2026-05-09 00:15:31   WARNING  myapp   payments:102 Payment retry   │    (focused row)
│ 2026-05-09 00:18:09    INFO     myapp   payments:55  Payment ok      │
├─────────────────────────────────────────────────────────────────────┤
│ Filters: [ERROR+] [Last 1h]  + add filter                           │  ← FilterChipBar
├─────────────────────────────────────────────────────────────────────┤
│ 5 of 539 · / search  Ctrl+F filters  E export  ? help   ↑↓ scroll  │  ← Footer
└─────────────────────────────────────────────────────────────────────┘
```

In **live follow mode**, a yellow pause banner appears between TopBar and LogTable when the user scrolls up:
```
⏸ Scrolled up — live follow paused. Press End to resume.
```

---

## Components

### `TopBar` widget
- Left: app name + filename
- Centre: search input (focused with `/`, clears with `Esc`)
- Right: level badge counts (CRIT / ERR / WARN / INFO / DEBUG), time span of visible rows, live/static indicator
- Regex toggle: `Ctrl+R` switches search between plain text and regex; indicator shown inline (`[re]`)
- Badge counts update reactively as filters change

### `LogTable` widget
- Columns: Timestamp · Level · Logger · Location (module:lineno) · Message
- Level column is colour-coded (CRITICAL=bold red, ERROR=red, WARNING=yellow, INFO=green, DEBUG=dim)
- Search matches highlighted inline in the Message column
- Focused row indicated with `▶` gutter marker and blue highlight
- Keyboard: `↑↓` rows, `PgUp/PgDn` pages, `Home`/`End` first/last, `Enter` → row detail panel (plain Rich panel, no new widget needed)
- NEW badge on rows that arrive while in live follow mode
- Auto-pauses live follow when user scrolls up; resumes on `End`

### `FilterChipBar` widget
- Displays active filters as removable chips (click chip or `Del` to remove)
- `Ctrl+F` opens `FilterPanel` — a modal with:
  - Level toggles (CRITICAL / ERROR / WARNING / INFO / DEBUG, multi-select)
  - Time range (Last 1h / Last 6h / Last 24h / Custom date-time range)
  - Logger name (text input, substring match)
- Filters stack (AND logic). `Esc` closes, `R` resets all filters to defaults

### `ExportModal` (triggered by `E`)
- Lists four export formats, arrow-key navigable
- Auto-generates filename: `{logger}-export-{YYYY-MM-DD}.{ext}` in the current working directory
- Exports only the currently filtered/searched rows
- Formats:
  - **CSV** — columns: timestamp, level, logger, module, lineno, message, plus any context fields as extra columns
  - **JSON** — array of objects, same fields as CSV, preserving types
  - **Plain text** — same format as standard console handler output
  - **HTML report** — self-contained file with embedded CSS table, stats summary header, and timestamp footer

### `HelpModal` (triggered by `?`)
Two-column keyboard reference. All keybindings in one place.

Full keybinding table:

| Key | Action |
|---|---|
| `/` | Focus search bar |
| `Ctrl+R` | Toggle regex search mode |
| `Esc` | Clear search / close modal |
| `↑` `↓` | Navigate rows |
| `PgUp` `PgDn` | Page up / down |
| `Home` `End` | First / last row (End also resumes live follow when paused) |
| `Enter` | Expand row detail |
| `F` | Toggle live follow mode |
| `Ctrl+F` | Open filter panel |
| `E` | Open export modal |
| `?` | Show / hide help |
| `Q` / `Ctrl+C` | Quit |

---

## LogReader

Extracted from `viewer.py`, extended for TUI use:

- `LogReader(path: Path)` — synchronous, used for static mode initial load
- `LogReader.tail(limit: int) -> list[ParsedLine]` — reads last N lines (reuses existing `_tail_lines` logic)
- `LogReader.follow(callback: Callable[[ParsedLine], None])` — runs in a background thread, calls `callback` for each new line; handles log rotation (file truncation)
- `ParsedLine` — dataclass: `timestamp: str`, `level: str`, `logger: str`, `module: str`, `lineno: int`, `message: str`, `raw: str`, `extra: dict`

The existing `LogViewer` class in `viewer.py` is kept intact (backward compatible). `LogViewer._tail_lines` and `LogViewer._parse_line` are replaced with thin wrappers that delegate to `LogReader`.

---

## Exporter

`Exporter(rows: list[ParsedLine], filepath: Path)`

- `.to_csv()` — `csv.DictWriter`, UTF-8 with BOM for Excel compatibility
- `.to_json()` — `json.dumps` with `indent=2`, array of dicts
- `.to_text()` — one line per row in standard formatter style
- `.to_html()` — self-contained HTML with inline CSS; includes stats header (total rows, level counts, time range, export timestamp)

---

## CLI Command

```bash
pylogshield tui --file ~/.logs/myapp.log
pylogshield tui --file ~/.logs/myapp.log --level ERROR  # start with level filter pre-applied
pylogshield tui --file ~/.logs/myapp.log --follow       # start in live follow mode
```

Added to `cli.py` as a new `tui` subcommand alongside the existing `view`, `follow`, and `levels` commands.

---

## Error Handling

- File not found: show error panel in place of table, prompt to retry or quit
- Unreadable line: skip and continue (already handled in `_parse_line`)
- Export failure (permissions, disk full): show inline error message in `ExportModal`, do not close
- Textual not installed: `ImportError` caught at import time in `cli.py`; print a clear message: `"Install TUI support with: pip install 'pylogshield[tui]'"`

---

## Testing

New test file: `tests/test_tui_reader.py`
- Tests for `LogReader.tail()` (reuses existing `test_viewer.py` fixtures)
- Tests for `LogReader` parsing JSON and plain-text lines
- Tests for all four `Exporter` output formats against a fixed set of `ParsedLine` fixtures

Textual's `App` itself is not unit-tested (Textual provides its own pilot API for integration tests; out of scope for this phase).
