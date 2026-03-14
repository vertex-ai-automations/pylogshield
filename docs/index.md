<div align="center">
<img src="img/pylogshield.png" alt="PyLogShield Logo" width="150">
<p>
<br />
📃
<a href="https://vertex-ai-automations.github.io/pylogshield"><strong>Examples and Docs</strong></a>
|🔧
<a href="https://github.com/vertex-ai-automations/pylogshield/issues/new">Report Bug/Issues</a>
|⛪
<a href="https://www.vertexaiautomations.com">Vertex AI Automations</a>|
</p>
</div>

## 📣 About The Project

PyLogShield is a Python logging library built for data professionals and developers who need reliable, secure logging with minimal setup. It extends Python's standard `logging` module with production-ready features commonly needed in data engineering and application development.

## Features

| Feature | Description |
|---------|-------------|
| **Sensitive Data Masking** | Automatically masks passwords, tokens, API keys, and other sensitive fields in logs |
| **Context Scrubbing** | Removes cloud credentials (AWS, Azure, GCP) from log records |
| **Rate Limiting** | Prevents log flooding by enforcing minimum intervals between identical messages |
| **Log Rotation** | Rotates log files based on size with configurable backup counts |
| **Asynchronous Logging** | Offloads logging to a background thread for improved performance |
| **JSON Formatting** | Structured JSON output with ISO 8601 timestamps for log aggregation tools |
| **Rich Console Output** | Color-coded terminal output using the Rich library |
| **Performance Metrics** | Track log counts and rates per level |
| **Log Filtering** | Filter logs by keywords (include or exclude mode) |
| **Dynamic Configuration** | Adjust log levels and settings at runtime |
| **Color-Coded Logs** | Enable `rich` integration for visually enhanced terminal output |
| **CLI Log Viewer** | View and follow logs from the command line with filtering |
| **Custom Log Levels** | Register custom levels like SECURITY, AUDIT at runtime |

## Quick Example

```python
from pylogshield import get_logger

# Create a logger with JSON output and sensitive data masking
logger = get_logger(
    "my_app",
    log_level="INFO",
    enable_json=True,
    rate_limit_seconds=1.0
)

# Log with automatic sensitive data masking
logger.info({"user": "john", "password": "secret123"}, mask=True)
# Output: {"user": "john", "password": "***"}

# Standard logging
logger.info("Application started")
logger.error("Something went wrong")
```

## Getting Started

Get started with the links on the left, or jump straight to:

- [Installation](installation.md) - Install the package
- [Basic Usage](usage.md) - Learn the fundamentals
- [CLI Usage](cli_usage.md) - Use the command-line viewer

## 👪 Contributors
All contributions are welcome. If you have a suggestion that would make this better, please fork the repo and create a merge request. You can also simply open an issue with the label 'enhancement'.

Don't forget to give the project a star! Thanks again!

 🔶 [View all contributors](https://github.com/vertex-ai-automations/pylogshield/graphs/contributors)
