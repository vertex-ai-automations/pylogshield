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
#   'INFO': 0.5,    # logs/second for this level
#   'ERROR': 0.5,
#   'count': 2,
#   'elapsed': 4.0
# }

# Count only
if logger.metrics_handler:
    print(logger.metrics_handler.counts())
    # Counter({'INFO': 1, 'ERROR': 1})

# Reset counters
    logger.metrics_handler.reset()
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
