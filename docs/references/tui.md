# Interactive TUI

The `pylogshield.tui` package provides the full-screen interactive log viewer and its supporting components.

!!! info "Optional dependency"
    Install the `[tui]` extra before importing:
    ```bash
    pip install "pylogshield[tui]"
    ```

---

## Quick Start

```python
from pathlib import Path
from pylogshield.tui.app import LogViewerApp

# Open the TUI programmatically
app = LogViewerApp(log_path=Path("~/.logs/myapp.log").expanduser())
app.run()

# Pre-apply an ERROR+ level filter
app = LogViewerApp(log_path=Path("app.log"), initial_level="ERROR")
app.run()

# Start in live-follow mode
app = LogViewerApp(log_path=Path("app.log"), start_following=True)
app.run()
```

---

## `LogViewerApp`

::: pylogshield.tui.app.LogViewerApp
    options:
      show_root_heading: true
      show_source: false
      members:
        - __init__

---

## `FilterState`

Dataclass holding the active filter configuration. Passed to `LogViewerApp` or returned from the filter panel modal.

::: pylogshield.tui.app.FilterState
    options:
      show_root_heading: true
      show_source: false

### Example

```python
from pylogshield.tui.app import FilterState

# Show only ERROR and CRITICAL from the last hour
state = FilterState(
    levels={"ERROR", "CRITICAL"},
    time_range="1h",
    logger_name="",
    search_text="payment",
    search_regex=False,
)
```

---

## `LogReader`

Reads, parses, and optionally tails a log file. Supports JSON-formatted logs (from [`JsonFormatter`](handlers.md)), the current PyLogShield standard plain-text format, and the legacy plain-text format.

::: pylogshield.tui.reader.LogReader
    options:
      show_root_heading: true
      show_source: false
      members:
        - __init__
        - tail
        - follow
        - stop

### Example — tail last N lines

```python
from pathlib import Path
from pylogshield.tui.reader import LogReader

reader = LogReader(Path("~/.logs/myapp.log").expanduser())
lines = reader.tail(limit=100)

for line in lines:
    print(f"[{line.level}] {line.message}")
```

### Example — live follow in a background thread

```python
import threading
from pylogshield.tui.reader import LogReader, ParsedLine

def on_new_line(line: ParsedLine) -> None:
    print(f"{line.timestamp}  {line.level}  {line.message}")

reader = LogReader(Path("app.log"))
t = threading.Thread(target=reader.follow, args=(on_new_line,), daemon=True)
t.start()

# ... later, stop the thread:
reader.stop()
t.join(timeout=1.0)
```

---

## `ParsedLine`

Dataclass representing a single parsed log line, returned by `LogReader.tail()` and passed to `LogReader.follow()` callbacks.

::: pylogshield.tui.reader.ParsedLine
    options:
      show_root_heading: true
      show_source: false

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `str` | ISO 8601 or plain-text timestamp string |
| `level` | `str` | Level name: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, or `N/A` |
| `logger` | `str` | Logger name passed to `get_logger()` |
| `module` | `str` | Module name where the log call originated (`module:lineno` source) |
| `lineno` | `int` | Line number in `module` where the log call originated |
| `message` | `str` | The formatted log message |
| `raw` | `str` | The original unparsed line from the file |
| `extra` | `dict` | Any extra key/value fields from JSON-formatted logs |

---

## `Exporter`

Writes a list of `ParsedLine` rows to one of four formats. Exports only the rows passed in — combine with `LogReader.tail()` or filtering to export a subset.

::: pylogshield.tui.exporter.Exporter
    options:
      show_root_heading: true
      show_source: false
      members:
        - __init__
        - to_csv
        - to_json
        - to_text
        - to_html

### Example — export filtered rows to CSV

```python
from pathlib import Path
from pylogshield.tui.reader import LogReader
from pylogshield.tui.exporter import Exporter

reader = LogReader(Path("app.log"))
all_rows = reader.tail(limit=5000)

# Keep only ERROR and CRITICAL
errors = [r for r in all_rows if r.level in {"ERROR", "CRITICAL"}]

Exporter(errors, Path("errors-export.csv")).to_csv()
Exporter(errors, Path("errors-export.html")).to_html()
```

### Example — export to all four formats

```python
from pathlib import Path
from pylogshield.tui.reader import LogReader
from pylogshield.tui.exporter import Exporter
from datetime import date

reader = LogReader(Path("app.log"))
rows = reader.tail(limit=1000)

stem = f"myapp-export-{date.today().isoformat()}"
exp = Exporter(rows, Path(f"{stem}.csv"))
exp.to_csv()                                      # → myapp-export-2026-05-09.csv

Exporter(rows, Path(f"{stem}.json")).to_json()    # → myapp-export-2026-05-09.json
Exporter(rows, Path(f"{stem}.txt")).to_text()     # → myapp-export-2026-05-09.txt
Exporter(rows, Path(f"{stem}.html")).to_html()    # → myapp-export-2026-05-09.html
```
