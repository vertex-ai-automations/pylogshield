# Log Viewer

The `LogViewer` class provides interactive log viewing capabilities with support for both JSON and plaintext log files.

## Quick Reference

```python
from pylogshield import LogViewer
from pathlib import Path

# Create a viewer for a log file
viewer = LogViewer(Path("~/.logs/my_app.log").expanduser())

# Display last 100 logs
viewer.display_logs(limit=100)

# Filter by level and keyword
viewer.display_logs(limit=50, level="ERROR", keyword="database")

# Live follow (like tail -f)
viewer.follow_logs(level="INFO", interval=0.5)
```

## Features

| Feature | Description |
|---------|-------------|
| **Static viewing** | Display last N lines with filtering |
| **Live following** | Real-time updates as logs are written |
| **Level filtering** | Show only logs at or above a level |
| **Keyword search** | Filter logs containing specific text |
| **JSON support** | Auto-detects and parses JSON logs |
| **Rich output** | Colorized table output with Rich |

## Examples

### Basic Log Viewing

```python
from pylogshield import LogViewer
from pathlib import Path

viewer = LogViewer(Path("/var/log/app.log"))

# Display last 200 lines (default)
viewer.display_logs()

# Display last 50 lines
viewer.display_logs(limit=50)
```

### Filtering by Log Level

```python
viewer = LogViewer(Path("app.log"))

# Show only ERROR and above
viewer.display_logs(level="ERROR")

# Show only WARNING and above
viewer.display_logs(level="WARNING", limit=100)

# Using numeric level
viewer.display_logs(level=30)  # WARNING = 30
```

### Keyword Filtering

```python
viewer = LogViewer(Path("app.log"))

# Search for logs containing "user_id"
viewer.display_logs(keyword="user_id")

# Combine level and keyword filters
viewer.display_logs(level="ERROR", keyword="timeout", limit=50)
```

### Live Following

```python
viewer = LogViewer(Path("app.log"))

# Follow logs in real-time (press Ctrl+C to stop)
viewer.follow_logs()

# With filtering
viewer.follow_logs(level="ERROR", keyword="critical")

# Custom refresh interval (default: 0.5 seconds)
viewer.follow_logs(interval=1.0)

# Limit buffer size (default: 500 lines)
viewer.follow_logs(max_lines=200)
```

### JSON Log Parsing

The viewer automatically detects and parses JSON-formatted logs:

```python
# If your log file contains lines like:
# {"timestamp": "2024-01-15T10:30:00", "level": "INFO", "message": "User logged in"}

viewer = LogViewer(Path("json_app.log"))
viewer.display_logs(limit=50)

# The viewer extracts timestamp, level, and message fields
```

---

## API Reference

::: pylogshield.viewer.LogViewer
    options:
      show_root_heading: true
      show_source: true
      members:
        - __init__
        - display_logs
        - follow_logs
