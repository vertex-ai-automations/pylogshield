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
