# Utilities

Utility functions and enums for working with log levels, including parsing level names and registering custom log levels.

## Quick Reference

```python
from pylogshield import LogLevel, add_log_level, PyLogShield

# Parse log level
level = LogLevel.parse("INFO")      # Returns 20
level = LogLevel.parse("warn")      # Returns 30 (alias for WARNING)
level = LogLevel.parse(10)          # Returns 10

# Get valid levels
levels = LogLevel.valid_levels()
# ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']

# Register custom level
add_log_level("SECURITY", 35, logger_cls=PyLogShield)
```

## LogLevel Enum

Type-safe enum for standard log levels, ordered by severity.

### Level Values

| Level | Value | Description |
|-------|-------|-------------|
| `CRITICAL` | 50 | Critical errors, system failure |
| `ERROR` | 40 | Errors that need attention |
| `WARNING` | 30 | Warning conditions |
| `INFO` | 20 | Informational messages |
| `DEBUG` | 10 | Debug information |
| `NOTSET` | 0 | No level set |

### Parsing Levels

```python
from pylogshield import LogLevel

# Parse string names (case-insensitive)
LogLevel.parse("INFO")      # 20
LogLevel.parse("error")     # 40
LogLevel.parse("Debug")     # 10

# "WARN" is aliased to "WARNING"
LogLevel.parse("warn")      # 30
LogLevel.parse("WARN")      # 30

# Parse numeric values
LogLevel.parse(20)          # 20
LogLevel.parse("30")        # 30 (string number)

# Invalid values raise ValueError
LogLevel.parse("INVALID")   # ValueError
```

### Comparing Levels

```python
from pylogshield import LogLevel

# Levels can be compared
LogLevel.ERROR > LogLevel.WARNING  # True
LogLevel.DEBUG < LogLevel.INFO     # True

# Check if a level is enabled
current_level = LogLevel.INFO
if LogLevel.DEBUG >= current_level:
    print("Debug is enabled")
```

### Getting Valid Levels

```python
from pylogshield import LogLevel

# Get all valid level names
levels = LogLevel.valid_levels()
print(levels)
# ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']

# Use for validation
user_input = "INFO"
if user_input.upper() in LogLevel.valid_levels():
    level = LogLevel.parse(user_input)
```

## Custom Log Levels

Register custom log levels with `add_log_level`.

### Basic Usage

```python
from pylogshield import get_logger, add_log_level, PyLogShield

# Register SECURITY level (between WARNING=30 and ERROR=40)
add_log_level("SECURITY", 35, logger_cls=PyLogShield)

# Now use it
logger = get_logger("secure_app")
logger.security("Unauthorized access attempt blocked")

# With masking
logger.security({"user": "admin", "token": "abc123"}, mask=True)
```

### Custom Levels Examples

```python
from pylogshield import PyLogShield, add_log_level, get_logger

# AUDIT level for compliance logging
add_log_level("AUDIT", 25, logger_cls=PyLogShield)

# TRACE level for detailed debugging
add_log_level("TRACE", 5, logger_cls=PyLogShield)

# ALERT level for urgent notifications
add_log_level("ALERT", 45, logger_cls=PyLogShield)

logger = get_logger("app")
logger.trace("Entering function xyz")
logger.audit("User 123 accessed resource ABC")
logger.alert("System approaching capacity limit!")
```

### Level Method Signature

Custom level methods support the same parameters as standard methods:

```python
# Generated method signature:
# logger.security(msg, *args, mask=False, **kwargs)

logger.security("Event occurred")
logger.security("Event: %s", event_name)
logger.security({"data": "value"}, mask=True)
logger.security("Event", extra={"user_id": 123})
```

## Utility Functions

### ensure_log_dir

Create parent directories for a log file path:

```python
from pylogshield.utils import ensure_log_dir

# Creates /var/log/myapp/ if it doesn't exist
ensure_log_dir("/var/log/myapp/app.log")

# Handles None safely
ensure_log_dir(None)  # Does nothing

# Expands user home directory
ensure_log_dir("~/logs/app.log")
```

---

## API Reference

::: pylogshield.utils
    options:
      show_root_heading: true
      show_source: true
      members:
        - LogLevel
        - add_log_level
        - ensure_log_dir
