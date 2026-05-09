# CLI Usage

The PyLogShield CLI provides an interactive way to view and follow log files directly from your terminal with rich formatting.

## Overview

### Features

- Search log with specific keywords
- Filter specific log level ('info', 'debug', 'error', etc)
- Limit the number of logs to display in the console

```bash
pylogshield --help
```

```
Usage: pylogshield [OPTIONS] COMMAND [ARGS]...

Commands:
  follow  Live-follow a log file (tail -f style) with a rich table that updates in place.
  levels  List supported log levels and their numeric values.
  view    Pretty-print logs from a file, attempting JSON first and falling back to plain text.
```

## Commands

| Command | Description |
|---------|-------------|
| `tui` | 🖥️ Full-screen interactive TUI viewer with live search, filters, and export. |
| `view` | 📜 View the last N logs from a file with optional level and keyword filtering. |
| `follow` | 📡 Live view, auto-refreshes output on new log lines. |
| `levels` | 🔍 Show all valid logging levels. |

## Common Options

| Option | Short | Description |
|--------|-------|-------------|
| `--file` | `-f` | Log file path (required for view/follow) |
| `--limit` | `-n` | Number of lines to display (view only) |
| `--level` | `-l` | Filter logs by log level (e.g., INFO, ERROR) |
| `--keyword` | `-k` | Filter logs containing this text (case-insensitive) |
| `--interval` | `-i` | Refresh interval in seconds (follow only) |
| `--max-lines` | `-m` | Maximum lines in live view buffer (follow only) |

---

## Interactive TUI Viewer

The TUI provides a full-screen log viewer with live search, multi-filter, export, and live-follow mode — all keyboard-driven, no browser required.

!!! info "Optional dependency"
    Requires the `[tui]` extra:
    ```bash
    pip install "pylogshield[tui]"
    ```

### Launch

```bash
# Open a log file in the TUI
pylogshield tui --file ~/.logs/myapp.log

# Start with ERROR+ level filter already applied
pylogshield tui --file app.log --level ERROR

# Start directly in live-follow mode
pylogshield tui --file app.log --follow

# Combine: follow only critical issues
pylogshield tui --file app.log --level CRITICAL --follow
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--file` | `-f` | Path to the log file (required) |
| `--level` | `-l` | Pre-apply a minimum level filter on launch (e.g. `ERROR`) |
| `--follow` | | Start in live-follow mode |

### Keyboard Reference

| Key | Action |
|-----|--------|
| `/` | Focus the search bar — rows filter as you type |
| `Ctrl+R` | Toggle regex search mode |
| `Esc` | Clear search or close any modal |
| `↑` `↓` | Navigate rows |
| `PgUp` `PgDn` | Page up / down |
| `Home` / `End` | First / last row (End also resumes live follow) |
| `Enter` | Expand full row detail (all fields, raw line) |
| `Ctrl+F` | Open filter panel (level, time range, logger name) |
| `F` | Toggle live-follow mode |
| `E` | Open export modal |
| `?` | Show keyboard reference |
| `Q` / `Ctrl+C` | Quit |

### Search

Type `/` to focus the search bar. Rows are filtered instantly as you type, and matching text is **highlighted bold** in the Message column.

Enable regex with `Ctrl+R` — the `[re]` indicator appears in the search bar:

```
# Plain text search
/payment

# Regex — match "ERROR" or "CRITICAL" messages
/^(ERROR|CRITICAL)
```

### Filter Panel (`Ctrl+F`)

The filter panel stacks multiple filters with AND logic:

- **Level toggles** — show only CRITICAL, ERROR, WARNING, INFO, DEBUG (any combination)
- **Time range** — Last 1h, Last 6h, Last 24h, or All time
- **Logger name** — substring match against the logger name field

Active filters appear as removable chips in the bar below the log table. Press `R` inside the panel to reset all filters to defaults.

### Live Follow Mode (`F`)

Press `F` to toggle live-follow — new log lines appear automatically as they are written to the file. The top bar shows `● LIVE` in green when active.

Scrolling up **automatically pauses** follow to let you read without the view jumping. A yellow banner confirms the pause:

```
⏸  Scrolled up — live follow paused. Press End to resume.
```

Press `End` to jump to the bottom and resume.

### Export (`E`)

Opens a modal to export the **currently filtered view** (not the full file):

| Format | Output | Use case |
|--------|--------|----------|
| **CSV** | UTF-8 with BOM | Open directly in Excel / Google Sheets |
| **JSON** | Indented array of objects | Programmatic processing, log pipelines |
| **Plain text** | One line per row | Copy-paste, ticket attachments |
| **HTML report** | Self-contained file with stats header | Share with stakeholders via email |

Files are saved to the **current working directory** with an auto-generated name:

```
myapp-export-2026-05-09.csv
myapp-export-2026-05-09.json
myapp-export-2026-05-09.txt
myapp-export-2026-05-09.html
```

### Row Detail (`Enter`)

Press `Enter` on any row to open a detail panel showing every field:

```
Row Detail
──────────────────────────────
Timestamp:  2026-05-09 00:12:04.221
Level:      ERROR
Logger:     payments
Location:   payments:88
Message:    Payment failed order_id=ORD-002 reason=card_declined
Extra:      {"gateway": "stripe"}

2026-05-09 00:12:04.221  ERROR     payments  payments:88  Payment failed...
──────────────────────────────
Esc to close
```

---

### ▶️ View Logs (Plain or JSON)

Display the last N lines from a log file in a formatted table.

### Basic Usage

```bash
pylogshield view --file logs/app.log
```

### Limit Number of Lines

```bash
pylogshield view --file logs/app.log --limit 50
# or short form
pylogshield view -f logs/app.log -n 50
```

### Filter by Log Level

Show only logs at or above a certain level:

```bash
pylogshield view -f logs/app.log --level ERROR
pylogshield view -f logs/app.log -l WARNING
```

### Filter by Keyword

Show only logs containing a specific keyword:

```bash
pylogshield view -f logs/app.log --keyword "database"
pylogshield view -f logs/app.log -k timeout
```

### Combined Filters

```bash
pylogshield view -f logs/app.log -l ERROR -k "connection" -n 100
```

---

## Follow Logs (Live)

Live-follow a log file with automatic updates, similar to `tail -f`.

### Basic Usage

```bash
pylogshield follow --file logs/app.log
```

Press `Ctrl+C` to stop following.

### With Level Filter

```bash
pylogshield follow -f logs/app.log --level ERROR
```

### With Keyword Filter

```bash
pylogshield follow -f logs/app.log --keyword "user_id"
```

### Custom Refresh Interval

Set how often the display updates (default: 0.5 seconds):

```bash
pylogshield follow -f logs/app.log --interval 1.0
# or
pylogshield follow -f logs/app.log -i 0.25
```

### Limit Buffer Size

Control how many lines are kept in the live view (default: 500):

```bash
pylogshield follow -f logs/app.log --max-lines 200
# or
pylogshield follow -f logs/app.log -m 1000
```

### Full Example

```bash
pylogshield follow -f logs/app.log -l INFO -k "api" -i 0.5 -m 300
```

---

## Show Log Levels

Display all supported log levels and their numeric values:

```bash
pylogshield levels
```

Output:

```
╭──────────┬───────┬──────────────────────────────────────────╮
│ Level    │ Value │ Description                              │
├──────────┼───────┼──────────────────────────────────────────┤
│ CRITICAL │    50 │ System failure — immediate attention req… │
│ ERROR    │    40 │ An operation failed                      │
│ WARNING  │    30 │ Unexpected condition, app still running  │
│ INFO     │    20 │ General operational messages             │
│ DEBUG    │    10 │ Detailed diagnostic information          │
│ NOTSET   │     0 │ No level assigned                        │
╰──────────┴───────┴──────────────────────────────────────────╯
```

---

## Examples

### View last 50 ERROR logs containing "timeout"

```bash
pylogshield view -f ./app.log -n 50 -l ERROR -k timeout
```

### Follow production logs for critical issues

```bash
pylogshield follow -f /var/log/myapp/production.log -l ERROR
```

### View JSON-formatted logs

The CLI automatically detects and parses JSON log format:

```bash
pylogshield view -f logs/json_app.log -n 20
```

### Monitor multiple keywords

Run multiple follow sessions in different terminals:

```bash
# Terminal 1: Watch for authentication issues
pylogshield follow -f app.log -k "auth"

# Terminal 2: Watch for database issues
pylogshield follow -f app.log -k "database"
```

---

## Tips

1. **Log file location**: By default, PyLogShield writes to `~/.logs/<logger_name>.log`

2. **JSON vs Plain text**: The CLI automatically detects the log format and parses accordingly

3. **Large files**: For very large log files, use `--limit` to avoid memory issues

4. **Log rotation**: The `follow` command automatically handles log rotation (detects when the file is truncated)

5. **Performance**: Use a longer `--interval` for lower CPU usage when following logs
