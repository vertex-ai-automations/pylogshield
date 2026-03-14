# PyLogShield Logger

The main logger class that extends Python's standard `logging.Logger` with additional features.

## Quick Reference

```python
from pylogshield import get_logger, PyLogShield

# Recommended: Use get_logger for singleton pattern
logger = get_logger("my_app", log_level="INFO", enable_json=True)

# Alternative: Direct instantiation
logger = PyLogShield("my_app", log_level="INFO")
```

## Common Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | Required | Logger name |
| `log_level` | `str \| int` | `INFO` | Logging level |
| `enable_json` | `bool` | `False` | Output JSON format |
| `use_queue` | `bool` | `False` | Async logging |
| `use_rich` | `bool` | `False` | Rich console output |
| `rate_limit_seconds` | `float` | `0.0` | Rate limiting interval |
| `log_directory` | `str \| Path` | `~/.logs` | Log file directory |
| `log_file` | `str` | `{name}.log` | Log file name |
| `rotate_file` | `bool` | `False` | Enable log rotation |
| `rotate_max_bytes` | `int` | `5000000` | Max file size before rotation |
| `rotate_backup_count` | `int` | `5` | Number of backup files |
| `enable_metrics` | `bool` | `False` | Enable metrics tracking |
| `enable_context_scrubber` | `bool` | `True` | Remove cloud credentials |
| `enable_context` | `bool` | `False` | Install `ContextFilter`; pairs with `log_context()`/`async_log_context()` |
| `queue_maxsize` | `int` | `0` | Max async queue size (0 = unbounded); only used when `use_queue=True` |

```mermaid
flowchart TB
    INIT(["PyLogShield(\n  enable_json=True,\n  use_queue=True,\n  enable_context=True\n)"])

    subgraph HANDLERS ["Configured Handlers"]
        F["FileHandler / RotatingFileHandler\n(log_directory / rotate_file)"]
        C["ConsoleHandler / RichHandler\n(add_console / use_rich)"]
        J["JsonFormatter\n(enable_json=True)"]
        Q["QueueHandler → QueueListener\n(use_queue=True, queue_maxsize)"]
    end

    subgraph FILTERS ["Active Filters"]
        CF["ContextFilter\n(enable_context=True)"]
        CS["ContextScrubber\n(enable_context_scrubber=True)"]
        KF["KeywordFilter\n(log_filter=...)"]
    end

    subgraph FEATURES ["Runtime Features"]
        RL["RateLimiter\n(rate_limit_seconds > 0)"]
        MT["LogMetricsHandler\n(enable_metrics=True)"]
    end

    INIT --> HANDLERS
    INIT --> FILTERS
    INIT --> FEATURES
```

## Examples

### Basic Logging

```python
from pylogshield import get_logger

logger = get_logger("my_app")

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")
```

### Sensitive Data Masking

```python
logger = get_logger("secure_app")

# Enable masking with mask=True
logger.info({"user": "john", "password": "secret"}, mask=True)
# Output: {"user": "john", "password": "***"}
```

### JSON Logging

```python
logger = get_logger("json_app", enable_json=True)

logger.info("User logged in")
# Output: {"timestamp": "2024-01-15T10:30:00+00:00", "level": "INFO", ...}
```

### Log Rotation

```python
logger = get_logger(
    "rotating_app",
    rotate_file=True,
    rotate_max_bytes=10_000_000,  # 10 MB
    rotate_backup_count=5
)
```

### Context Propagation

```python
from pylogshield import get_logger
from pylogshield.context import log_context

logger = get_logger("api", enable_context=True, enable_json=True)

with log_context(request_id="abc-123"):
    logger.info("Processing")
    # JSON output includes request_id field
```

### Exception Logging with Masking

```python
try:
    connect_db(password=secret)
except Exception:
    logger.exception("DB connection failed", mask=True)
    # exception .args are masked; traceback locals are NOT redacted
```

!!! warning
    `mask=True` does not redact traceback frame locals. See [Sensitive Data Masking](../usage.md#sensitive-data-masking) for details.

---

## API Reference

::: pylogshield.core.PyLogShield
    options:
      show_root_heading: true
      show_source: true
      members:
        - __init__
        - info
        - debug
        - warning
        - error
        - critical
        - exception
        - set_log_level
        - get_metrics
        - shutdown
        - from_config
        - add_sensitive_fields

---

## get_logger Function

::: pylogshield.get_logger
    options:
      show_root_heading: true
      show_source: true
