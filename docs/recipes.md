# Recipes

End-to-end examples showing PyLogShield used in realistic production scenarios.

---

## FastAPI service with full observability

A complete FastAPI application with structured JSON logging, per-request context,
sensitive-data masking, and a metrics health endpoint.

```python
# app.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pylogshield import get_logger, add_sensitive_fields, log_exceptions
from pylogshield.middleware import PyLogShieldMiddleware

# ── Startup ──────────────────────────────────────────────────────────────────

add_sensitive_fields(["card_number", "cvv", "national_id"])

logger = get_logger(
    "payments-api",
    log_level="INFO",
    enable_json=True,
    rotate_file=True,
    rotate_max_bytes=100_000_000,   # 100 MB per file
    rotate_backup_count=10,
    use_queue=True,
    queue_maxsize=50_000,
    rate_limit_seconds=0.5,
    enable_metrics=True,
    enable_context=True,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Payments API starting up")
    yield
    logger.info("Payments API shutting down")
    logger.shutdown()   # flush async queue before process exits

app = FastAPI(lifespan=lifespan)
app.add_middleware(PyLogShieldMiddleware, logger=logger)

# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    metrics = logger.get_metrics()
    counts = logger.metrics_handler.counts() if logger.metrics_handler else {}
    return {"status": "ok", "log_counts": counts}


@log_exceptions(logger, log_calls=True, mask=True)
async def _charge_card(card_number: str, amount: float) -> dict:
    # card_number is masked in both the entry log and any exception message
    if amount <= 0:
        raise ValueError(f"Invalid amount: {amount}")
    return {"status": "authorised", "amount": amount}


@app.post("/charge")
async def charge(card_number: str, amount: float):
    result = await _charge_card(card_number, amount)
    logger.info({"event": "charge_ok", "amount": amount})
    return result
```

Every log line during a `POST /charge` request looks like:

```json
{
  "timestamp": "2026-05-10T09:00:01.234+00:00",
  "level": "INFO",
  "logger": "payments-api",
  "message": "charge_ok",
  "request_id": "a1b2c3d4",
  "http_method": "POST",
  "http_path": "/charge",
  "client_ip": "10.0.1.42",
  "amount": 99.99
}
```

---

## Data pipeline with per-batch context

A batch-processing job that stamps every log with the current batch ID and
records per-batch error counts.

```python
# pipeline.py
import time
from pylogshield import get_logger, log_exceptions
from pylogshield.context import log_context

logger = get_logger(
    "etl-pipeline",
    log_level="INFO",
    enable_json=True,
    enable_context=True,
    enable_metrics=True,
    rotate_file=True,
)


@log_exceptions(logger, raise_exception=False)
def process_record(record: dict) -> dict | None:
    """Returns None and logs an error on failure; does not abort the batch."""
    if "id" not in record:
        raise ValueError("Missing 'id' field")
    return {"id": record["id"], "processed": True}


def run_batch(batch_id: str, records: list[dict]) -> dict:
    with log_context(batch_id=batch_id, batch_size=len(records)):
        logger.info("Batch started")
        ok, failed = 0, 0

        for rec in records:
            result = process_record(rec)
            if result is None:
                failed += 1
            else:
                ok += 1

        logger.info({
            "event": "batch_complete",
            "ok": ok,
            "failed": failed,
        })
        return {"ok": ok, "failed": failed}


if __name__ == "__main__":
    batches = [
        ("batch-001", [{"id": 1}, {"id": 2}, {}]),          # {} will fail
        ("batch-002", [{"id": 3}, {"id": 4}, {"id": 5}]),
    ]
    for batch_id, records in batches:
        run_batch(batch_id, records)
```

Sample output (abbreviated):

```json
{"level":"INFO","batch_id":"batch-001","batch_size":3,"message":"Batch started"}
{"level":"ERROR","batch_id":"batch-001","batch_size":3,"message":"Exception in process_record ... Missing 'id' field"}
{"level":"INFO","batch_id":"batch-001","batch_size":3,"message":"batch_complete","ok":2,"failed":1}
{"level":"INFO","batch_id":"batch-002","batch_size":3,"message":"Batch started"}
{"level":"INFO","batch_id":"batch-002","batch_size":3,"message":"batch_complete","ok":3,"failed":0}
```

---

## Asyncio service with task-isolated context

`async_log_context` gives each `asyncio.gather` task its own context so
concurrent tasks cannot overwrite each other's fields.

```python
import asyncio
from pylogshield import get_logger
from pylogshield.context import async_log_context

logger = get_logger("async-worker", enable_context=True, enable_json=True)


async def handle_order(order_id: str, user_id: int) -> None:
    async with async_log_context(order_id=order_id, user_id=user_id):
        logger.info("Order received")
        await asyncio.sleep(0.1)    # simulate async work
        logger.info("Order dispatched")


async def main() -> None:
    # All three tasks run concurrently; contexts never bleed across tasks
    await asyncio.gather(
        handle_order("ORD-001", 101),
        handle_order("ORD-002", 202),
        handle_order("ORD-003", 303),
    )


asyncio.run(main())
```

Each log line carries only its own order/user pair:

```json
{"level":"INFO","order_id":"ORD-001","user_id":101,"message":"Order received"}
{"level":"INFO","order_id":"ORD-002","user_id":202,"message":"Order received"}
{"level":"INFO","order_id":"ORD-003","user_id":303,"message":"Order received"}
```

---

## Dict-config pattern (12-factor apps)

Load logger configuration from environment variables or a config file
using `PyLogShield.from_config`.

```python
# config.py
import os
from pylogshield import PyLogShield, add_sensitive_fields

ENV = os.environ.get("APP_ENV", "development")

LOG_CONFIGS = {
    "production": {
        "level": "INFO",
        "enable_json": True,
        "rotate_file": True,
        "rotate_max_bytes": 50_000_000,
        "rotate_backup_count": 10,
        "use_queue": True,
        "queue_maxsize": 100_000,
        "rate_limit_seconds": 1.0,
        "enable_metrics": True,
        "enable_context": True,
    },
    "development": {
        "level": "DEBUG",
        "enable_json": False,
        "add_console": True,
        "use_rich": True,
    },
    "test": {
        "level": "WARNING",
        "enable_json": False,
        "add_console": False,
    },
}

add_sensitive_fields(["ssn", "dob", "account_number"])

logger = PyLogShield.from_config("myapp", LOG_CONFIGS[ENV])
```

---

## Custom log level for security events

Register a `SECURITY` level (between `ERROR` and `WARNING`) for audit trails
that must survive even when the app runs at `WARNING`.

```python
from pylogshield import get_logger, add_log_level, PyLogShield
from pylogshield.context import log_context

# Register once at module import — before any logger is created
add_log_level("SECURITY", 35, logger_cls=PyLogShield)
add_log_level("AUDIT",    26, logger_cls=PyLogShield)

logger = get_logger(
    "secure-app",
    log_level="WARNING",    # DEBUG/INFO suppressed; AUDIT and above emitted
    enable_json=True,
    enable_context=True,
)


def login(username: str, ip_address: str, success: bool) -> None:
    with log_context(username=username, ip=ip_address):
        if success:
            logger.audit("User login succeeded")
        else:
            logger.security("User login FAILED — possible brute force")
```

---

## Exporting errors from a live log file

Use `LogReader` and `Exporter` in a maintenance script to pull recent errors
without launching the TUI.

```python
# export_errors.py
from datetime import date
from pathlib import Path
from pylogshield.tui.reader import LogReader
from pylogshield.tui.exporter import Exporter

LOG_FILE = Path("~/.logs/payments-api.log").expanduser()
reader = LogReader(LOG_FILE)

# Read last 10 000 lines and keep only errors
rows = reader.tail(limit=10_000)
errors = [r for r in rows if r.level in {"ERROR", "CRITICAL"}]

print(f"Found {len(errors)} errors in last 10 000 lines")

today = date.today().isoformat()
stem = f"payments-errors-{today}"

Exporter(errors, Path(f"{stem}.csv")).to_csv()
Exporter(errors, Path(f"{stem}.html")).to_html()

print(f"Saved {stem}.csv and {stem}.html")
```

---

## Testing with PyLogShield

Capture log output in tests without writing to disk.

```python
# test_payments.py
import io
import json
import logging
import pytest
from pylogshield import PyLogShield
from pylogshield.handlers import JsonFormatter


@pytest.fixture
def logger(tmp_path):
    """In-memory JSON logger — no console, no disk writes."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())

    lg = PyLogShield(
        "test-logger",
        log_directory=tmp_path,
        add_console=False,
    )
    # Remove the auto-added file handler and add our StringIO handler
    for h in list(lg.handlers):
        lg.removeHandler(h)
    lg.addHandler(handler)
    lg._buf = buf
    return lg


def test_charge_logs_amount(logger):
    logger.info({"event": "charge", "amount": 50.0})

    logger._buf.seek(0)
    record = json.loads(logger._buf.read())

    assert record["level"] == "INFO"
    assert record["amount"] == 50.0


def test_masking_redacts_card(logger):
    logger.info({"card_number": "4111111111111111", "amount": 10.0}, mask=True)

    logger._buf.seek(0)
    record = json.loads(logger._buf.read())

    assert "4111111111111111" not in json.dumps(record)
```
