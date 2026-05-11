# Metrics

`LogMetricsHandler` counts log records by level and computes a logs-per-second rate. Attach it to a logger with `enable_metrics=True`.

## Quick Reference

```python
from pylogshield import get_logger

logger = get_logger("app", enable_metrics=True)

logger.info("Start")
logger.error("Something failed")

metrics = logger.get_metrics()
# {
#   'INFO': 0.5,      # logs/second for this level
#   'ERROR': 0.5,
#   'count': 2,       # total log count
#   'elapsed': 4.0,   # seconds since creation or last reset
#   'start': 12345.6  # monotonic timestamp of handler creation
# }

# Count only
if logger.metrics_handler:
    print(logger.metrics_handler.counts())
    # {'INFO': 1, 'ERROR': 1}

# Reset counters
    logger.metrics_handler.reset()
```

## Examples

### Health-check endpoint (FastAPI)

Expose log metrics through a `/health` endpoint so your monitoring stack can
alert when error rates spike.

```python
from fastapi import FastAPI
from pylogshield import get_logger

app = FastAPI()
logger = get_logger("api", enable_metrics=True, enable_json=True)

@app.get("/health")
def health():
    metrics = logger.get_metrics()
    if metrics is None:
        return {"status": "ok"}
    error_rate = metrics.get("ERROR", 0.0)
    return {
        "status": "degraded" if error_rate > 5.0 else "ok",
        "log_counts": logger.metrics_handler.counts(),
        "error_rate_per_sec": round(error_rate, 3),
        "total_logs": metrics["count"],
        "uptime_seconds": round(metrics["elapsed"], 1),
    }
```

### Periodic metrics emission

Reset counters every minute and log a summary line:

```python
import threading
from pylogshield import get_logger

logger = get_logger("worker", enable_metrics=True, enable_json=True)

def _emit_and_reset():
    while True:
        threading.Event().wait(60)  # wait 60 s
        metrics = logger.get_metrics()
        if metrics:
            logger.info({
                "event": "metrics",
                "counts": logger.metrics_handler.counts(),
                "error_rate": metrics.get("ERROR", 0.0),
                "elapsed": metrics["elapsed"],
            })
            logger.metrics_handler.reset()

threading.Thread(target=_emit_and_reset, daemon=True).start()
```

## Thread Safety

All methods on `LogMetricsHandler` are thread-safe. `emit()`, `counts()`, `logs_per_second()`, and `reset()` are all protected by an internal `threading.Lock`.

## API Reference

::: pylogshield.metrics.LogMetricsHandler
    options:
      show_root_heading: true
      show_source: true
      members:
        - __init__
        - emit
        - counts
        - logs_per_second
        - reset
