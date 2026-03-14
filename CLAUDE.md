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

### Public API (`__init__.py`)

Main export is `get_logger()` - returns a singleton `PyLogShield` instance by name, integrates with Python's logging manager.

### Key Patterns

- All logging methods (`info`, `debug`, `warning`, `error`, `critical`) accept `mask=True` to enable sensitive data redaction
- Async logging via `use_queue=True` uses `QueueHandler`/`QueueListener`
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

## Release Process

Releases are automated via GitHub Actions (`.github/workflows/release.yml`):
- Push to `main` triggers docs deployment
- Push a semver tag (e.g., `1.2.3`) triggers PyPI publish
