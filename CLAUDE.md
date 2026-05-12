# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyLogShield is a Python logging library extending the standard `logging` module with security and production features: sensitive data masking, rate limiting, log rotation, async logging, JSON formatting, and a CLI log viewer.

## Build & Development Commands

Declared `requires-python = ">=3.8"` in `pyproject.toml`; CI matrix tests 3.9–3.12.

```bash
# Install in development mode (core only)
pip install -e .

# Install with all optional extras (required to run the full test suite)
pip install -e ".[tui,fastapi]"

# Install test dependencies
pip install -r tests/requirements.txt

# Run tests
pytest tests/ -v --tb=short

# Run with coverage
pytest tests/ -v --cov=src/pylogshield --cov-report=term-missing

# Run specific test file / single test
pytest tests/test_core.py -v
pytest tests/test_core.py::TestPyLogShieldMasking::test_mask_dict_password -v

# Build documentation locally
mkdocs serve

# Build package
python -m build
```

## Architecture

### Core Components (`src/pylogshield/`)

- **`core.py`** - `PyLogShield` class: Main logger extending `logging.Logger`. Handles message masking, rate limiting integration, and handler setup. Entry point for all logging calls.

- **`config.py`** - Thread-safe sensitive field registry with compiled regex caching. Fields like `password`, `token`, `api_key` are masked by default. All fields are stored and matched **lowercase** (`add_sensitive_fields` normalizes input). Pattern invalidates on field changes. The masking regex matches both `key: value` and `key=value` forms (case-insensitive, optional quotes around value).

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

- **`decorators.py`** - `log_exceptions` and `trace` decorators: wrap sync or async functions to log exceptions, call args, and return values. `log_exceptions(logger, log_calls, log_returns, raise_exception, mask)` — sync/async dispatch is automatic. `trace(logger, mask)` is shorthand for `log_exceptions(log_calls=True, log_returns=True)`. Masking applies to message strings via the standard regex but does **not** apply to raw `kwargs` dict repr.

- **`tui/`** - Textual-based TUI log viewer (requires `pip install "pylogshield[tui]"`):
  - `tui/app.py` - `LogViewerApp`: full interactive TUI app; `_parse_ts()` normalises all timestamp formats (ISO 8601 with offset, `YYYY-MM-DD HH:MM:SS.mmm`, legacy comma-millisecond) to UTC-aware `datetime` for filtering
  - `tui/reader.py` - `LogReader` / `ParsedLine`: parses plain-text and JSON log lines, supports `tail(limit)` and `follow(callback, interval)` with `stop()` for thread-safe cancellation
  - `tui/exporter.py` - `Exporter`: exports a list of `ParsedLine` rows to CSV, JSON, plain text, or HTML; HTML output HTML-escapes content to prevent XSS
  - `tui/widgets.py` - Reusable Textual widgets for the TUI

### Public API (`__init__.py`)

Main export is `get_logger()` - returns a singleton `PyLogShield` instance by name, integrates with Python's logging manager.

### Key Patterns

- All logging methods (`info`, `debug`, `warning`, `error`, `critical`, `exception`) accept `mask=True` to enable sensitive data redaction. `exception(mask=True)` scrubs exception `.args` strings but does **not** mask traceback local variables. **Masking limitations:** URL-format credentials (`postgresql://user:pass@host`) and base64-encoded secrets are not matched by the regex pattern. Pass sensitive values as dict keys in `SENSITIVE_FIELDS` rather than inline strings for reliable redaction.
- Async logging via `use_queue=True` uses `QueueHandler`/`QueueListener`; call `logger.shutdown()` to stop the background thread when done
- By default, `PyLogShield` always writes a log file at `~/.logs/{name}.log` even without explicit config; pass `log_directory` and `log_file` to override
- `enable_context_scrubber=True` by default — strips cloud credential prefixes (AWS_, AZURE_, GCP_, GOOGLE_, TOKEN) from all log records
- `enable_context=True` installs a `ContextFilter` on the logger; combined with `log_context()`/`async_log_context()` this propagates structured fields (e.g. `request_id`) to every log record in the block. Shorthand: `logger.context(**fields)` / `logger.async_context(**fields)` instead of importing the context manager directly.
- `PyLogShield.from_config(name, dict)` is an alternate constructor for dict-based configuration. Note: the dict key is `"level"` (not `"log_level"`) for the log level.
- `logger.set_log_level(level)` changes the logger and all its handlers at runtime
- `logger.get_metrics()` returns counts and rates per level when `enable_metrics=True`; returns `None` otherwise
- `get_logger()` raises `TypeError` if a non-PyLogShield logger with the same name already exists; use `force=True` to replace it
- `queue_maxsize` (default `0` = unbounded) caps the async queue when `use_queue=True`; when full, new messages are **dropped silently** via non-blocking put
- `log_context` / `async_log_context` support nesting — inner fields merge on top of outer; the prior context is fully restored on exit (including on exception). Use `get_log_context()` from `pylogshield.context` to read the active context dict
- `ContextFilter` warns once per conflicting key if a context field name matches a reserved `LogRecord` attribute (e.g. `name`, `msg`) — these keys are skipped, not overwritten
- `warn` is an alias for `warning` on `PyLogShield`
- `from_config` accepts `log_filter` as a dict `{"keywords": [...], "include": bool, "case_insensitive": bool}`, a list/set of keywords, or a `logging.Filter` instance
- Version auto-generated from git tags via `setuptools_scm` (see `_version.py`)
- The package is also runnable as `python -m pylogshield` (entry point: `__main__.py`)
- `get_sensitive_pattern()` is **not** re-exported from `pylogshield.__init__`; import it directly from `pylogshield.config`
- `LogViewer` calls `.expanduser().resolve()` on the path — pass `Path("~/.logs/app.log").expanduser()` or an absolute path
- Optional extras: `fastapi` (`pip install "pylogshield[fastapi]"`) adds Starlette middleware; `tui` (`pip install "pylogshield[tui]"`) adds the Textual interactive log viewer
- When `enable_json=True` and `enable_context=True`, `JsonFormatter` promotes context fields to the **top level** of the JSON envelope alongside `timestamp` and `level` — they are not nested
- `log_exceptions(raise_exception=False)` suppresses the caught exception entirely and returns `None`; use this for non-critical operations where a failed call should not propagate
- `caller_info` in decorators is captured at **decoration time** from `func.__code__`, so logged file/line always points to the function definition, not the call site
- When `use_queue=True` and `queue_maxsize > 0`, records are **dropped silently** when the queue is full — a custom `_SilentQueueHandler` subclass catches `queue.Full` without writing to stderr
- `queue_maxsize=0` (the default) is unbounded and never drops messages

## CLI Usage

```bash
pylogshield view --file /path/to/log.log --limit 100 --level INFO
pylogshield follow --file /path/to/log.log --level ERROR --interval 0.5
pylogshield levels  # List supported log levels
```

## Testing

Tests are in `tests/` directory. `asyncio_mode = "auto"` is set in `pyproject.toml` — async test functions run without `@pytest.mark.asyncio`. `test_tui_reader.py` requires the `tui` extra; `test_handlers.py` requires the `fastapi` extra — install both before running the full suite.

Test modules:
- `test_core.py` - PyLogShield class, masking, logging operations
- `test_config.py` - Sensitive field registry
- `test_context.py` - ContextFilter warnings, async context isolation
- `test_filters.py` - KeywordFilter and ContextScrubber
- `test_limiter.py` - RateLimiter
- `test_metrics.py` - LogMetricsHandler
- `test_decorators.py` - log_exceptions and trace decorators (sync, async, masking, trace shorthand)
- `test_handlers.py` - Handler factories and JsonFormatter
- `test_utils.py` - LogLevel enum and add_log_level
- `test_viewer.py` - LogViewer
- `test_tui_reader.py` - TUI `LogReader`, `ParsedLine`, `Exporter`, `LogViewerApp._parse_ts` (requires `tui` extra)

Key fixtures in `conftest.py`:
- `reset_sensitive_fields` (autouse) — restores `SENSITIVE_FIELDS` to defaults after every test
- `basic_logger` / `json_logger` — pre-built loggers writing to a temp dir with `add_console=False`
- `temp_log_dir` / `temp_log_file` — provide a `Path` to a temporary directory/file for tests that need raw file handles
- `clean_logger_registry` — removes `test_*` loggers from `logging.Logger.manager.loggerDict`; use this in tests that call `get_logger()` directly
- `close_logger(logger)` helper — closes handlers, calls `shutdown()`, and removes the logger from the registry

## Release Process

Releases are automated via GitHub Actions (`.github/workflows/release.yml`):
- Push to `main` triggers docs deployment to GitHub Pages
- Push a bare semver tag (e.g., `git tag 1.2.3 && git push origin 1.2.3`) triggers PyPI publish only (`publish-target: "pypi"`)
- Secrets required: `PYPI_API_TOKEN` (trusted publishing is disabled in this workflow)
