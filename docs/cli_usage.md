# CLI Usage

The PyLogShield CLI provides an interactive way to view and follow log files directly from your terminal with rich formatting.

## Overview

### Features

- Search log with specific keywords
- Filter specific log lovel ('info', 'debug', 'error', etc)
- limit the number of logs to display in the console

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

| Arguments | Description |
|---------|-------------|
| `view` | 📜 View the last N logs from a file with optional level and keyword filtering. |
| `follow` | 📜 Live view, auto-refreshes output on new log lines. |
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
┏━━━━━━━━━━┳━━━━━━━┓
┃ Name     ┃ Value ┃
┡━━━━━━━━━━╇━━━━━━━┩
│ CRITICAL │    50 │
│ ERROR    │    40 │
│ WARNING  │    30 │
│ INFO     │    20 │
│ DEBUG    │    10 │
│ NOTSET   │     0 │
└──────────┴───────┘
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
