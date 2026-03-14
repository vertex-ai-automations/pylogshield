# Handlers

Handler factories and formatters for log output. These utilities create pre-configured handlers for various output destinations.

## Quick Reference

```python
from pylogshield.handlers import (
    create_console_handler,
    create_file_handler,
    create_rotating_file_handler,
    create_rich_handler,
    JsonFormatter
)
import logging
from pathlib import Path

# Console handler with JSON output
console = create_console_handler(logging.INFO, json_format=True)

# File handler
file_handler = create_file_handler(Path("app.log"), logging.DEBUG)

# Rotating file handler (5MB max, 3 backups)
rotating = create_rotating_file_handler(
    Path("app.log"),
    logging.INFO,
    max_bytes=5_000_000,
    backup_count=3
)

# Rich console handler (colorized output)
rich_handler = create_rich_handler(logging.DEBUG)
```

## JsonFormatter

Format log records as structured JSON for log aggregation systems.

### Output Format

```json
{
    "timestamp": "2024-01-15T10:30:00.123+00:00",
    "host": "server-01",
    "logger": "my_app",
    "level": "INFO",
    "message": "User logged in",
    "extra": {
        "user_id": "12345"
    }
}
```

### Basic Usage

```python
from pylogshield.handlers import JsonFormatter
import logging

# Create formatter
formatter = JsonFormatter()

# With pretty printing
formatter = JsonFormatter(indent=2)

# Without extra fields
formatter = JsonFormatter(include_extra=False)

# Apply to handler
handler = logging.StreamHandler()
handler.setFormatter(formatter)
```

### ISO 8601 Timestamps

All timestamps are formatted in ISO 8601 format with millisecond precision and UTC timezone:

```python
# Example output:
# "2024-01-15T10:30:00.123+00:00"
```

## Handler Factory Functions

### create_console_handler

Create a console (stderr) handler:

```python
from pylogshield.handlers import create_console_handler
import logging

# Standard format
handler = create_console_handler(logging.INFO)

# JSON format
handler = create_console_handler(logging.INFO, json_format=True)
```

### create_file_handler

Create a simple file handler:

```python
from pylogshield.handlers import create_file_handler
from pathlib import Path

# Standard format
handler = create_file_handler(Path("app.log"), logging.DEBUG)

# JSON format
handler = create_file_handler(
    Path("app.log"),
    logging.DEBUG,
    json_format=True
)

# Parent directories are created automatically
handler = create_file_handler(
    Path("/var/log/myapp/app.log"),
    logging.INFO
)
```

### create_rotating_file_handler

Create a handler that rotates logs based on file size:

```python
from pylogshield.handlers import create_rotating_file_handler
from pathlib import Path

handler = create_rotating_file_handler(
    Path("app.log"),
    logging.INFO,
    max_bytes=5_000_000,  # 5 MB (default)
    backup_count=5,       # Keep 5 backups (default)
    json_format=False     # Standard format (default)
)
```

This creates files:
- `app.log` (current)
- `app.log.1` (previous)
- `app.log.2`
- ... up to `app.log.5`

### create_rich_handler

Create a Rich console handler with colorized output:

```python
from pylogshield.handlers import create_rich_handler
import logging

handler = create_rich_handler(logging.DEBUG)

# Falls back to standard console handler if Rich is not installed
```

Rich handler features:
- Colorized output by log level
- Rich tracebacks for exceptions
- Clean, formatted output

## Custom Handler Setup

### Adding Multiple Handlers

```python
import logging
from pathlib import Path
from pylogshield.handlers import (
    create_console_handler,
    create_rotating_file_handler
)

logger = logging.getLogger("my_app")
logger.setLevel(logging.DEBUG)

# Console: INFO and above
logger.addHandler(create_console_handler(logging.INFO))

# File: DEBUG and above, with rotation
logger.addHandler(create_rotating_file_handler(
    Path("debug.log"),
    logging.DEBUG,
    max_bytes=10_000_000,
    backup_count=10
))
```

### JSON Logging for Production

```python
from pylogshield.handlers import create_console_handler, create_file_handler
from pathlib import Path
import logging

logger = logging.getLogger("production_app")

# JSON to stdout for container logs
logger.addHandler(create_console_handler(logging.INFO, json_format=True))

# JSON to file for log aggregation
logger.addHandler(create_file_handler(
    Path("/var/log/app/app.json"),
    logging.DEBUG,
    json_format=True
))
```

---

## API Reference

::: pylogshield.handlers
    options:
      show_root_heading: true
      show_source: true
      members:
        - JsonFormatter
        - create_console_handler
        - create_file_handler
        - create_rotating_file_handler
        - create_rich_handler
