<a name="readme-top"></a>

<div align="center">
<img src="https://github.com/vertex-ai-automations/pylogshield/raw/main/docs/img/pylogshield.png" alt="PyLogShield Logo" width="420">

<br/>

[![PyPI version](https://img.shields.io/pypi/v/pylogshield?color=indigo&logo=pypi&logoColor=white)](https://pypi.org/project/pylogshield/)
[![Python versions](https://img.shields.io/pypi/pyversions/pylogshield?color=indigo&logo=python&logoColor=white)](https://pypi.org/project/pylogshield/)
[![License: MIT](https://img.shields.io/badge/license-MIT-indigo.svg)](https://github.com/vertex-ai-automations/pylogshield/blob/main/LICENSE.txt)
[![Downloads](https://img.shields.io/pypi/dm/pylogshield?color=indigo)](https://pypi.org/project/pylogshield/)
[![CI](https://img.shields.io/github/actions/workflow/status/vertex-ai-automations/pylogshield/ci.yml?branch=main&label=CI&logo=github)](https://github.com/vertex-ai-automations/pylogshield/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-online-indigo?logo=readthedocs&logoColor=white)](https://vertex-ai-automations.github.io/pylogshield)

<br/>

<p>
<a href="https://vertex-ai-automations.github.io/pylogshield"><strong>📃 Documentation</strong></a>
&nbsp;·&nbsp;
<a href="https://github.com/vertex-ai-automations/pylogshield/issues/new">🔧 Report Bug</a>
&nbsp;·&nbsp;
<a href="https://www.vertexaiautomations.com">⛪ Vertex AI Automations</a>
</p>

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Quick Start](#-quick-start)
- [Interactive TUI Viewer](#-interactive-tui-viewer)
- [Terminal Demo](#-terminal-demo)
- [Security Notes](#️-security-notes)
- [Contributing](#-contributing)

---

## 📣 Overview

**PyLogShield** is a Python logging library for data professionals and developers who need reliable, secure logging with minimal setup. It extends Python's standard `logging` module with production-ready features: sensitive data masking, rate limiting, async logging, JSON formatting, context propagation, FastAPI middleware, and a rich CLI log viewer.

```
Your App  ──►  PyLogShield  ──►  Masking  ──►  Rate Limiter  ──►  Context  ──►  Handlers
                                                                              ├── Console / Rich
                                                                              ├── File / Rotating
                                                                              ├── JSON
                                                                              └── Async Queue
```

---

## 💡 Features

| Feature | Description |
|---------|-------------|
| 🔒 **Sensitive Data Masking** | Masks passwords, tokens, API keys in strings, dicts, and exception args |
| 🚦 **Rate Limiting** | Suppresses duplicate messages within a configurable time window |
| 📄 **JSON Formatting** | Structured ISO 8601 JSON for ELK, Splunk, CloudWatch |
| 🔄 **Log Rotation** | Size-based rotation with configurable backup counts |
| ⚡ **Async Logging** | Non-blocking background queue with configurable max size |
| 🎨 **Rich Console** | Color-coded terminal output via the `rich` library |
| 🔍 **CLI Log Viewer** | Static and live-follow modes with level/keyword filtering |
| 🖥️ **Interactive TUI** | Full-screen viewer with live search, filters, export (CSV/JSON/HTML), and live-follow mode |
| 🧵 **Context Propagation** | Thread-safe and asyncio-safe structured field injection |
| 🌐 **FastAPI Middleware** | Auto-injects `request_id`, method, path, and client IP |
| 📊 **Metrics** | Per-level log counts and logs/second tracking |
| ☁️ **Cloud Scrubbing** | Strips AWS_, AZURE_, GCP_, GOOGLE_, TOKEN prefixed fields |
| 🏷️ **Custom Log Levels** | Register `SECURITY`, `AUDIT`, `TRACE` levels at runtime |

---

## 📌 Quick Start

### Installation

```bash
pip install pylogshield

# FastAPI middleware support
pip install "pylogshield[fastapi]"
```

### Basic Usage

```python
from pylogshield import get_logger

logger = get_logger("my_app", log_level="INFO")

logger.info("Application started")
logger.warning("Low memory detected")
logger.error("Connection failed")

# Sensitive data is masked with mask=True
logger.info({"user": "john", "api_key": "sk-1234567890"}, mask=True)
# → {"user": "john", "api_key": "***"}
```

### Production Setup

```python
from pylogshield import get_logger, add_sensitive_fields
from pylogshield.context import log_context

add_sensitive_fields(["ssn", "credit_card"])

logger = get_logger(
    "production_app",
    log_level="INFO",
    enable_json=True,            # Structured JSON
    rotate_file=True,            # Auto-rotate log files
    rotate_max_bytes=10_000_000, # 10 MB per file
    rate_limit_seconds=0.5,      # Prevent log flooding
    use_queue=True,              # Non-blocking async logging
    queue_maxsize=50_000,        # Cap memory usage
    enable_metrics=True,         # Track log statistics
    enable_context=True,         # Structured context injection
)

with log_context(request_id="abc-123", user_id=42):
    logger.info("Processing payment", mask=True)
    # → {"message": "Processing payment", "request_id": "abc-123", "user_id": 42}
```

### FastAPI Middleware

```python
from fastapi import FastAPI
from pylogshield import get_logger
from pylogshield.middleware import PyLogShieldMiddleware

app = FastAPI()
logger = get_logger("api", enable_context=True, enable_json=True)
app.add_middleware(PyLogShieldMiddleware, logger=logger)

# Every log line automatically includes: request_id, http_method, http_path, client_ip
```

---

## 🖥️ Interactive TUI Viewer

Install the optional TUI extra and launch the full-screen interactive log viewer:

```bash
pip install "pylogshield[tui]"

pylogshield tui --file ~/.logs/myapp.log
pylogshield tui --file app.log --level ERROR        # start with ERROR+ filter
pylogshield tui --file app.log --follow             # start in live-follow mode
```

![PyLogShield Interactive TUI Viewer](https://github.com/vertex-ai-automations/pylogshield/raw/main/docs/screenshots/tui-demo.gif)

| Key | Action |
|-----|--------|
| `/` | Focus search bar — filters rows as you type, highlights matches |
| `Ctrl+F` | Open filter panel — level toggles, time range, logger name |
| `F` | Toggle live-follow mode — auto-pauses when you scroll up |
| `E` | Export current filtered view to CSV, JSON, plain text, or HTML |
| `?` | Show keyboard reference |
| `Q` | Quit |

---

## 🖥️ Terminal Demo

### Sensitive Data Masking — Before vs After

```
# Without mask=True
INFO  my_app  {"user": "john", "password": "hunter2", "token": "eyJhbGci..."}

# With mask=True  ✓
INFO  my_app  {"user": "john", "password": "***", "token": "***"}
```

### JSON Output

```json
{
  "timestamp": "2026-03-14T10:30:00.123+00:00",
  "host": "prod-server-01",
  "logger": "production_app",
  "level": "INFO",
  "message": "Processing payment",
  "request_id": "abc-123",
  "user_id": 42
}
```

### CLI Log Viewer

```
╭──────────────────── Log Viewer ────────────────────╮
│ File:    /var/log/app/production.log               │
│ Limit:   200 lines                                 │
│ Level:   ERROR                                     │
│ Keyword: "timeout"                                 │
╰────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ Timestamp                │ Level    │ Message                   │
├──────────────────────────┼──────────┼───────────────────────────┤
│ 2026-03-14T10:28:11.001  │ ERROR    │ DB timeout after 30s      │
│ 2026-03-14T10:29:54.332  │ ERROR    │ Connection timeout: redis  │
╰──────────────────────────┴──────────┴───────────────────────────╯
                          2 entries shown
```

```bash
# Follow live logs
pylogshield follow -f app.log -l ERROR -k "timeout"

# View last 50 lines
pylogshield view -f app.log -n 50 -l WARNING

# List log levels
pylogshield levels
```

---

## ⚠️ Security Notes

- `mask=True` masks sensitive values in strings, dicts, and exception `.args`. **Traceback source lines are not redacted** — they reflect the literal source text. Avoid storing sensitive values in local variables inside functions that may raise logged exceptions.
- `ContextFilter` skips context keys that conflict with standard `LogRecord` fields (e.g., `msg`, `levelname`) and emits a `warnings.warn`.
- `PyLogShieldMiddleware` sanitizes the incoming `X-Request-ID` header before injecting it into logs (truncated to 128 chars, non-alphanumeric characters stripped).

---


---

## CI Pipeline

Every push to `main` and every pull request runs automatically via [shared-workflows](https://github.com/vertex-ai-automations/shared-workflows):

| Job | What it checks |
|-----|----------------|
| **Test** | pytest on Python 3.9–3.12 x Ubuntu + Windows |
| **Lint** | `ruff check` + `ruff format --check` |
| **Type Check** | `mypy src/` |
| **Audit** | `pip-audit` — all dependencies scanned for known CVEs |
| **Coverage** | `pytest-cov` — report posted to the Actions job summary |
## 👪 Contributing

All contributions are welcome! Fork the repo, make your changes, and open a pull request. You can also open an issue with the label `enhancement`.

Don't forget to ⭐ star the project!

🔶 [View all contributors](https://github.com/vertex-ai-automations/pylogshield/graphs/contributors)

---

📃 [Full Docs](https://vertex-ai-automations.github.io/pylogshield) &nbsp;·&nbsp; 🔧 [Report a Bug](https://github.com/vertex-ai-automations/pylogshield/issues/new) &nbsp;·&nbsp; ⛪ [Vertex AI Automations](https://www.vertexaiautomations.com)

<p align="right">(<a href="#readme-top">back to top</a>)</p>
