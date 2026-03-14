# Filters

Log filters for controlling which log records are processed. Filters can include or exclude messages based on keywords or scrub sensitive context data.

## Quick Reference

```python
from pylogshield import KeywordFilter, ContextScrubber

# Include only logs containing specific keywords
include_filter = KeywordFilter(["error", "critical"], include=True)

# Exclude logs containing debug info
exclude_filter = KeywordFilter(["debug", "trace"], include=False)

# Remove cloud credentials from log context
scrubber = ContextScrubber()
```

## KeywordFilter

Filter log records based on keywords in the message.

### Include Mode (Default)

Only allow messages containing specified keywords:

```python
from pylogshield import get_logger, KeywordFilter
import logging

# Using get_logger parameter
logger = get_logger("my_app", log_filter=["error", "warning", "failed"])

logger.info("Application started")    # Not logged (no keyword match)
logger.info("Operation failed")       # Logged (contains "failed")
logger.error("An error occurred")     # Logged (contains "error")
```

### Exclude Mode

Block messages containing specified keywords:

```python
from pylogshield import KeywordFilter
import logging

# Create filter manually
exclude_filter = KeywordFilter(
    keywords=["debug", "trace", "verbose"],
    include=False,  # Exclude mode
    case_insensitive=True
)

# Add to handler
handler = logging.StreamHandler()
handler.addFilter(exclude_filter)
```

### Case Sensitivity

```python
# Case-insensitive matching (default)
filter1 = KeywordFilter(["ERROR"], case_insensitive=True)
# Matches: "error", "ERROR", "Error"

# Case-sensitive matching
filter2 = KeywordFilter(["ERROR"], case_insensitive=False)
# Matches only: "ERROR"
```

## ContextScrubber

Automatically remove cloud provider credentials and tokens from log records.

### Default Prefixes

The scrubber removes attributes starting with:

| Prefix | Description |
|--------|-------------|
| `AWS_` | Amazon Web Services credentials |
| `AZURE_` | Microsoft Azure credentials |
| `GCP_` | Google Cloud Platform credentials |
| `GOOGLE_` | Google services credentials |
| `TOKEN` | Various token attributes |

### Basic Usage

```python
from pylogshield import get_logger

# Enabled by default
logger = get_logger("my_app", enable_context_scrubber=True)

# Disable if not needed
logger = get_logger("my_app", enable_context_scrubber=False)
```

### Custom Prefixes

```python
from pylogshield import ContextScrubber
import logging

# Create scrubber with custom prefixes
scrubber = ContextScrubber(
    forbidden_prefixes=("SECRET_", "PRIVATE_", "INTERNAL_")
)

# Add to handler
handler = logging.StreamHandler()
handler.addFilter(scrubber)
```

### How It Works

The scrubber inspects log record attributes and removes any that match the forbidden prefixes:

```python
import logging

# If code accidentally adds cloud credentials to the record:
record.AWS_SECRET_ACCESS_KEY = "..."  # Will be scrubbed
record.AZURE_CLIENT_SECRET = "..."    # Will be scrubbed

# Normal attributes are preserved:
record.user_id = "12345"              # Kept
```

---

## API Reference

::: pylogshield.filters
    options:
      show_root_heading: true
      show_source: true
      members:
        - KeywordFilter
        - ContextScrubber

## ContextFilter

For context propagation (injecting request IDs and other structured fields into log records), see the dedicated [Context Propagation](context.md) reference.
