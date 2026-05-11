# Decorators

PyLogShield provides two function decorators for automatic exception logging,
call tracing, and return-value logging: `log_exceptions` and its shorthand `trace`.

## Quick Reference

```python
from pylogshield import get_logger, log_exceptions, trace

logger = get_logger("my_app")

@log_exceptions(logger)
def fetch_data(url: str) -> dict:
    ...

@trace(logger)
async def process_item(item_id: int) -> dict:
    ...
```

## Parameters

### `log_exceptions`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `logger` | `PyLogShield` | required | Logger to emit records to |
| `log_calls` | `bool` | `False` | Log function name, args, kwargs at DEBUG on entry |
| `log_returns` | `bool` | `False` | Log return value at DEBUG on success |
| `raise_exception` | `bool` | `True` | Re-raise caught exceptions after logging. Set to `False` to suppress. |
| `mask` | `bool` | `False` | Apply sensitive-data masking to all log messages |

### `trace`

Shorthand for `log_exceptions(logger, log_calls=True, log_returns=True)`.
`raise_exception` is always `True`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `logger` | `PyLogShield` | required | Logger to emit records to |
| `mask` | `bool` | `False` | Apply sensitive-data masking to all log messages |

---

## Examples

### Basic exception logging (sync)

```python
from pylogshield import get_logger, log_exceptions

logger = get_logger("my_app")

@log_exceptions(logger)
def fetch_user(user_id: int) -> dict:
    response = requests.get(f"/users/{user_id}")
    response.raise_for_status()
    return response.json()
```

On an unhandled exception the logger emits a single ERROR record with the
exception message and full traceback attached, then re-raises.

### Basic exception logging (async)

```python
@log_exceptions(logger)
async def fetch_user(user_id: int) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/users/{user_id}")
        response.raise_for_status()
        return response.json()
```

Async functions are detected automatically via `inspect.iscoroutinefunction`
at decoration time.

### Full call/return tracing

```python
@log_exceptions(logger, log_calls=True, log_returns=True)
def calculate_discount(price: float, pct: float) -> float:
    return price * (1 - pct / 100)
```

With `log_level="DEBUG"` on the logger, this emits:

```
DEBUG  Calling calculate_discount(args=(99.99, 20), kwargs={}) from app.py:42
DEBUG  calculate_discount returned: 79.992
```

### `trace` shorthand

```python
@trace(logger)
def calculate_discount(price: float, pct: float) -> float:
    return price * (1 - pct / 100)
```

Identical to the example above — `trace` always enables `log_calls` and `log_returns`.

### Masking sensitive arguments

```python
@log_exceptions(logger, log_calls=True, log_returns=True, mask=True)
def authenticate(username: str, password: str) -> str:
    """Returns an auth token."""
    return auth_service.get_token(username, password)
```

With `mask=True`, masking is applied at three points:

1. **Entry log** — `_mask()` is called on `args` and `kwargs` *before* they
   are serialised to a string. A call like `authenticate("alice", password="s3cr3t")`
   logs `kwargs={'password': '***'}` rather than the raw value.
2. **Return log** — the return value is masked before logging, so a returned
   token string matching `key: value` or `key=value` patterns is redacted.
3. **Exception log** — exception `.args` strings are masked; the traceback
   text (locals) is *not* redacted.

```
# example output with log_level="DEBUG", mask=True
DEBUG  Calling authenticate(args=('alice',), kwargs={'password': '***'}) from ...
DEBUG  authenticate returned: ***
```

!!! note "Pattern matching on return values"
    `mask=True` on return values applies the regex to the *string representation*
    of the result. Objects that do not contain a recognisable `key: value` or
    `key=value` pattern will not be redacted. For structured masking, return a
    dict from the function and let the `_mask_mapping` path handle it.

### Suppressing exceptions

```python
@log_exceptions(logger, raise_exception=False)
def notify_webhook(url: str, payload: dict) -> bool:
    requests.post(url, json=payload).raise_for_status()
    return True

result = notify_webhook("https://hook.example.com", {})
# result is None if an exception occurred; True on success
```

Use `raise_exception=False` when a failed operation should not abort the
calling code — the exception is still logged at ERROR level.

---

## API Reference

::: pylogshield.decorators
    options:
      show_root_heading: true
      show_source: true
      members:
        - log_exceptions
        - trace
