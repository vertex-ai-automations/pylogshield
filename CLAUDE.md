# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyLogShield is a Python logging library extending the standard `logging` module with security and production features: sensitive data masking, rate limiting, log rotation, async logging, JSON formatting, and a CLI log viewer.

## Build & Development Commands

```bash
# Install in development mode
pip install -e .

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v --tb=short

# Build documentation locally
mkdocs serve

# Build package
python -m build
```

## Architecture

### Core Components (`src/pylogshield/`)

- **`core.py`** - `PyLogShield` class: Main logger extending `logging.Logger`. Handles message masking, rate limiting integration, and handler setup. Entry point for all logging calls.

- **`config.py`** - Thread-safe sensitive field registry with compiled regex caching. Fields like `password`, `token`, `api_key` are masked by default. Pattern invalidates on field changes.

- **`filters.py`** - Two filter types:
  - `KeywordFilter`: Include/exclude logs by keyword
  - `ContextScrubber`: Strips cloud credentials (AWS_, AZURE_, GCP_, GOOGLE_, TOKEN prefixes) from log records

- **`handlers.py`** - Factory functions for handlers:
  - `create_console_handler()` / `create_rich_handler()`
  - `create_file_handler()` / `create_rotating_file_handler()`
  - `JsonFormatter` class for structured JSON output

- **`limiter.py`** - `RateLimiter`: Thread-safe per-message rate limiting with bounded memory and automatic cleanup

- **`metrics.py`** - `LogMetricsHandler`: Counts logs by level, tracks logs/second

- **`viewer.py`** - `LogViewer`: Rich-based log viewer with tail and live-follow modes

- **`cli.py`** - Typer CLI app with `view`, `follow`, and `levels` commands

- **`utils.py`** - `LogLevel` enum and `add_log_level()` for custom runtime levels

- **`context.py`** - Context propagation via `contextvars`. `log_context` / `async_log_context` context managers inject key/value pairs into all log records within a block. `ContextFilter` is the logging filter that stamps these fields onto records. Works correctly with `asyncio.gather` (per-task isolation).

- **`middleware.py`** - `PyLogShieldMiddleware`: FastAPI/Starlette ASGI middleware that automatically injects `request_id`, `http_method`, `http_path`, and `client_ip` into every log record during a request. Requires `pip install "pylogshield[fastapi]"`. The logger passed to it should have `enable_context=True`.

### Public API (`__init__.py`)

Main export is `get_logger()` - returns a singleton `PyLogShield` instance by name, integrates with Python's logging manager.

### Key Patterns

- All logging methods (`info`, `debug`, `warning`, `error`, `critical`) accept `mask=True` to enable sensitive data redaction
- Async logging via `use_queue=True` uses `QueueHandler`/`QueueListener`; call `logger.shutdown()` to stop the background thread when done
- By default, `PyLogShield` always writes a log file at `~/.logs/{name}.log` even without explicit config; pass `log_directory` and `log_file` to override
- `enable_context_scrubber=True` by default — strips cloud credential prefixes (AWS_, AZURE_, GCP_, GOOGLE_, TOKEN) from all log records
- `enable_context=True` installs a `ContextFilter` on the logger; combined with `log_context()`/`async_log_context()` this propagates structured fields (e.g. `request_id`) to every log record in the block
- `PyLogShield.from_config(name, dict)` is an alternate constructor for dict-based configuration
- `get_logger()` raises `TypeError` if a non-PyLogShield logger with the same name already exists; use `force=True` to replace it
- Version auto-generated from git tags via `setuptools_scm` (see `_version.py`)

## CLI Usage

```bash
pylogshield view --file /path/to/log.log --limit 100 --level INFO
pylogshield follow --file /path/to/log.log --level ERROR --interval 0.5
pylogshield levels  # List supported log levels
```

## Testing

Tests are in `tests/` directory:

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run all tests
pytest tests/ -v --tb=short

# Run with coverage
pytest tests/ -v --cov=src/pylogshield --cov-report=term-missing

# Run specific test file
pytest tests/test_core.py -v

# Run specific test
pytest tests/test_core.py::TestPyLogShieldMasking::test_mask_dict_password -v
```

Test modules:
- `test_core.py` - PyLogShield class, masking, logging operations
- `test_config.py` - Sensitive field registry
- `test_filters.py` - KeywordFilter and ContextScrubber
- `test_limiter.py` - RateLimiter
- `test_metrics.py` - LogMetricsHandler
- `test_handlers.py` - Handler factories and JsonFormatter
- `test_utils.py` - LogLevel enum and add_log_level
- `test_viewer.py` - LogViewer

Key fixtures in `conftest.py`:
- `reset_sensitive_fields` (autouse) — restores `SENSITIVE_FIELDS` to defaults after every test
- `basic_logger` / `json_logger` — pre-built loggers writing to a temp dir with `add_console=False`
- `clean_logger_registry` — removes `test_*` loggers from `logging.Logger.manager.loggerDict`; use this in tests that call `get_logger()` directly
- `close_logger(logger)` helper — closes handlers, calls `shutdown()`, and removes the logger from the registry

## Release Process

Releases are automated via GitHub Actions (`.github/workflows/release.yml`):
- Push to `main` triggers docs deployment
- Push a semver tag (e.g., `1.2.3`) triggers PyPI publish
