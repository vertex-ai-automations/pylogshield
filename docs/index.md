---
hide:
  - navigation
  - toc
---

<div class="pls-hero">

<span class="pls-hero__badge">Python 3.8+ &nbsp;·&nbsp; MIT License &nbsp;·&nbsp; Minimal Dependencies</span>

<img src="img/pylogshield.png" alt="PyLogShield" class="pls-hero__logo">

<h1 class="pls-hero__title">
  Secure. Structured.<br>
  <span>Production-Ready</span> Logging.
</h1>

<p class="pls-hero__subtitle">
  A logging library for data professionals and developers who need reliable, secure logging with minimal setup — built on Python's standard <code>logging</code> module.
</p>

<div class="pls-hero__actions">

<a href="installation.md" class="md-button md-button--primary">Get Started</a>
<a href="https://github.com/vertex-ai-automations/pylogshield" class="md-button">View on GitHub</a>

</div>

<div class="pls-terminal">
  <div class="pls-terminal__bar">
    <span class="pls-terminal__dot pls-terminal__dot--red"></span>
    <span class="pls-terminal__dot pls-terminal__dot--amber"></span>
    <span class="pls-terminal__dot pls-terminal__dot--green"></span>
    <span class="pls-terminal__label">python — app.py</span>
  </div>
  <div class="pls-terminal__body">
    <span class="pls-terminal__line pls-terminal__line--comment"># secure, structured logging in two lines</span>
    <span class="pls-terminal__line pls-terminal__line--prompt">from pylogshield import get_logger</span>
    <span class="pls-terminal__line pls-terminal__line--blank"></span>
    <span class="pls-terminal__line pls-terminal__line--prompt">logger = get_logger("api", enable_json=True, use_queue=True)</span>
    <span class="pls-terminal__line pls-terminal__line--blank"></span>
    <span class="pls-terminal__line pls-terminal__line--comment"># sensitive fields masked automatically</span>
    <span class="pls-terminal__line pls-terminal__line--prompt">logger.info({"user": "alice", "password": "s3cr3t"}, mask=True)</span>
    <span class="pls-terminal__line pls-terminal__line--masked">→ {"timestamp":"2026-04-17T10:22:01Z","level":"INFO","message":{"user":"alice","password":"***"}}</span>
    <span class="pls-terminal__line pls-terminal__line--blank"></span>
    <span class="pls-terminal__line pls-terminal__line--comment"># context propagates through the entire request</span>
    <span class="pls-terminal__line pls-terminal__line--prompt">with logger.context(request_id="req-8f2c", user_id=42):</span>
    <span class="pls-terminal__line pls-terminal__line--prompt">&nbsp;&nbsp;&nbsp;&nbsp;logger.info("Order processed")</span>
    <span class="pls-terminal__line pls-terminal__line--info">→ {"level":"INFO","request_id":"req-8f2c","user_id":42,"message":"Order processed"}</span>
    <span class="pls-terminal__line pls-terminal__line--blank"></span>
    <span class="pls-terminal__line pls-terminal__line--prompt"><span class="pls-terminal__cursor"></span></span>
  </div>
</div>

</div>

<div class="pls-stats">
  <div class="pls-stat">
    <span class="pls-stat__value">11</span>
    <span class="pls-stat__label">Features</span>
  </div>
  <div class="pls-stat">
    <span class="pls-stat__value">0</span>
    <span class="pls-stat__label">Required Deps</span>
  </div>
  <div class="pls-stat">
    <span class="pls-stat__value">3.8+</span>
    <span class="pls-stat__label">Python</span>
  </div>
  <div class="pls-stat">
    <span class="pls-stat__value">MIT</span>
    <span class="pls-stat__label">License</span>
  </div>
</div>

<div align="center" markdown>

[![PyPI](https://img.shields.io/pypi/v/pylogshield?color=%2300e5a0&logo=pypi&logoColor=white&labelColor=%230c1120)](https://pypi.org/project/pylogshield/)
[![Python](https://img.shields.io/pypi/pyversions/pylogshield?color=%2300e5a0&logo=python&logoColor=white&labelColor=%230c1120)](https://pypi.org/project/pylogshield/)
[![License](https://img.shields.io/badge/license-MIT-%2300e5a0.svg?labelColor=%230c1120)](https://github.com/vertex-ai-automations/pylogshield/blob/main/LICENSE.txt)
[![Downloads](https://img.shields.io/pypi/dm/pylogshield?color=%2300e5a0&labelColor=%230c1120)](https://pypi.org/project/pylogshield/)
[![CI](https://img.shields.io/github/actions/workflow/status/vertex-ai-automations/pylogshield/release.yml?branch=main&label=CI&logo=github&labelColor=%230c1120&color=%2300e5a0)](https://github.com/vertex-ai-automations/pylogshield/actions)

</div>

---

## Why PyLogShield?

PyLogShield extends Python's standard `logging` module with production-ready features commonly needed in data engineering and application development — without complexity. Requires only `rich` and `typer`.

<div class="feature-grid" markdown>

<div class="feature-item" markdown>

### :material-shield-lock: Sensitive Data Masking

Automatically masks passwords, tokens, API keys, and custom fields. Never accidentally leak credentials in your logs again.

```python
logger.info({"password": "secret"}, mask=True)
# Output: {"password": "***"}
```

</div>

<div class="feature-item" markdown>

### :material-speedometer: Rate Limiting

Prevent log flooding by suppressing duplicate messages within a configurable time window.

```python
logger = get_logger("app", rate_limit_seconds=2.0)
logger.info("Retry")  # Logged
logger.info("Retry")  # Suppressed (within 2s)
```

</div>

<div class="feature-item" markdown>

### :material-code-json: JSON Formatting

Structured JSON with ISO 8601 timestamps. Ready for ELK, Splunk, CloudWatch, and Datadog.

```python
logger = get_logger("app", enable_json=True)
logger.info("Started")
# {"timestamp": "...", "level": "INFO", ...}
```

</div>

<div class="feature-item" markdown>

### :material-rotate-3d-variant: Log Rotation

Automatically rotate log files based on size with configurable backup counts.

```python
logger = get_logger("app",
    rotate_file=True,
    rotate_max_bytes=5_000_000)
```

</div>

<div class="feature-item" markdown>

### :material-lightning-bolt: Async Logging

Offload logging to a background thread via `QueueHandler`. Non-blocking for high-throughput apps.

```python
logger = get_logger("app", use_queue=True)
# Non-blocking log writes
```

</div>

<div class="feature-item" markdown>

### :material-console: CLI Log Viewer

View and follow logs from the command line with rich formatting and level filtering.

```bash
pylogshield follow -f app.log -l ERROR
```

</div>

<div class="feature-item" markdown>

### :material-arrow-right-circle: Context Propagation

Inject structured fields into every log within a block — thread-safe and asyncio-safe via `contextvars`.

```python
with log_context(request_id="abc", user_id=42):
    logger.info("Processing")
# JSON output includes request_id and user_id
```

</div>

<div class="feature-item" markdown>

### :material-web: FastAPI Middleware

Automatically inject `request_id`, HTTP method, path, and client IP into every log during a request.

```python
app.add_middleware(PyLogShieldMiddleware, logger=logger)
# Every log in a request carries request context
```

</div>

</div>

---

## Quick Start

### Installation

```bash
pip install pylogshield
```

### Basic Usage

```python
from pylogshield import get_logger

# Create a logger
logger = get_logger("my_app", log_level="INFO")

# Standard logging
logger.info("Application started")
logger.warning("Low memory")
logger.error("Connection failed")

# Log with sensitive data masking
logger.info({
    "user": "john",
    "api_key": "sk-1234567890"
}, mask=True)
# Output: {"user": "john", "api_key": "***"}
```

### Production Configuration

```python
from pylogshield import get_logger, add_sensitive_fields

# Add custom sensitive fields
add_sensitive_fields(["ssn", "credit_card"])

# Create a production-ready logger
logger = get_logger(
    "production_app",
    log_level="INFO",
    enable_json=True,            # Structured JSON output
    rotate_file=True,            # Auto-rotate logs
    rotate_max_bytes=10_000_000, # 10 MB per file
    rate_limit_seconds=0.5,      # Prevent flooding
    use_queue=True,              # Async logging
    queue_maxsize=50_000,        # Cap queue memory
    enable_metrics=True,         # Track log stats
    enable_context=True,         # Structured context injection
)

logger.info("Production logger ready")
```

---

## Feature Comparison

| Feature | Standard Logging | PyLogShield |
|---------|-----------------|-------------|
| Basic logging | :material-check: | :material-check: |
| Sensitive data masking | :material-close: | :material-check: |
| Rate limiting | :material-close: | :material-check: |
| JSON formatting | Manual setup | :material-check: Built-in |
| Log rotation | Separate handler | :material-check: Integrated |
| Async logging | Manual setup | :material-check: One flag |
| CLI viewer | :material-close: | :material-check: |
| Metrics | :material-close: | :material-check: |
| Context propagation | :material-close: | :material-check: |
| FastAPI middleware | :material-close: | :material-check: |
| Cloud credential scrubbing | :material-close: | :material-check: |

---

## Architecture

PyLogShield wraps every log call in a processing pipeline before handing off to your configured output handlers.

```mermaid
flowchart LR
    APP(["Your Application\nlogger.info(msg, mask=True)"])

    subgraph PIPELINE ["Processing Pipeline"]
        direction TB
        A["🔒 Sensitive Data Masking"]
        B["🚦 Rate Limiter"]
        C["🧵 Context Injection"]
        D["☁️ Cloud Credential Scrubber"]
        A --> B --> C --> D
    end

    subgraph OUTPUT ["Output Handlers"]
        direction TB
        H1["Console / Rich"]
        H2["File / Rotating File"]
        H3["JSON Formatter"]
        H4["Async Queue → Background Thread"]
        H5["Metrics Tracker"]
    end

    APP --> PIPELINE --> OUTPUT
```

---

## Next Steps

<div class="feature-grid" markdown>

<div class="feature-item" markdown>

### :material-rocket-launch: Getting Started

Learn how to install and configure PyLogShield for your project.

<a href="installation.md" class="md-button">Installation Guide</a>

</div>

<div class="feature-item" markdown>

### :material-book-open-variant: Usage Guide

Explore all features with detailed examples.

<a href="usage.md" class="md-button">Basic Usage</a>

</div>

<div class="feature-item" markdown>

### :material-chef-hat: Recipes

End-to-end examples: FastAPI service, data pipelines, async workers, testing.

<a href="recipes.md" class="md-button">Recipes &amp; Cookbooks</a>

</div>

<div class="feature-item" markdown>

### :material-api: API Reference

Complete API documentation with all parameters and options.

<a href="references/logger.md" class="md-button">API Reference</a>

</div>

</div>

---

## Contributing

All contributions are welcome! If you have a suggestion that would make this better, please fork the repo and create a pull request.

<a href="https://github.com/vertex-ai-automations/pylogshield" class="md-button">View on GitHub</a>
<a href="https://github.com/vertex-ai-automations/pylogshield/issues/new" class="md-button">Report an Issue</a>
