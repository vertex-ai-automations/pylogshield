# Configuration

Sensitive field configuration for automatic log masking. This module manages the registry of field names that are automatically masked in log output.

## Quick Reference

```python
from pylogshield import (
    add_sensitive_fields,
    remove_sensitive_fields,
    get_sensitive_fields,
)
from pylogshield.config import get_sensitive_pattern

# Add custom sensitive fields
add_sensitive_fields(["ssn", "credit_card", "bank_account"])

# Remove fields from the registry
remove_sensitive_fields(["auth"])

# Get all registered fields
fields = get_sensitive_fields()
print(fields)  # frozenset({'password', 'token', 'api_key', ...})

# Get the compiled regex pattern for matching
pattern = get_sensitive_pattern()
```

## Default Sensitive Fields

The following fields are masked by default:

| Field | Description |
|-------|-------------|
| `password`, `passwd`, `pwd` | Password fields |
| `token`, `access_token`, `refresh_token` | Authentication tokens |
| `secret`, `secret_key`, `client_secret` | Secret values |
| `api_key`, `apikey` | API keys |
| `authorization`, `auth`, `bearer` | Authorization headers |
| `private_key`, `encryption_key` | Cryptographic keys |
| `session_token`, `session_id`, `sessionid` | Session identifiers |
| `credit_card`, `creditcard`, `card_number` | Payment card data |
| `ssn`, `social_security` | Social security numbers |
| `cvv`, `pin` | Card verification values |
| `jwt`, `cookie` | JWT tokens and cookies |

## Examples

### Adding Custom Fields

```python
from pylogshield import add_sensitive_fields, get_logger

# Add custom fields before creating loggers
add_sensitive_fields(["employee_id", "salary", "dob"])

logger = get_logger("hr_app")

# These fields will now be masked
logger.info({
    "employee_id": "EMP123",
    "name": "John Doe",
    "salary": 75000
}, mask=True)
# Output: {"employee_id": "***", "name": "John Doe", "salary": "***"}
```

### Checking Registered Fields

```python
from pylogshield import get_sensitive_fields

fields = get_sensitive_fields()
print(f"Total sensitive fields: {len(fields)}")
print(f"Password protected: {'password' in fields}")
```

### Removing Fields

```python
from pylogshield import remove_sensitive_fields

# If you need to log auth tokens for debugging
remove_sensitive_fields(["auth"])

# Note: This affects all loggers globally
```

### Thread Safety

All functions in this module are thread-safe. The pattern cache is automatically invalidated when fields are added or removed:

```python
from pylogshield import add_sensitive_fields, get_sensitive_pattern

# Thread-safe operations
pattern1 = get_sensitive_pattern()  # Cached
add_sensitive_fields(["new_field"])  # Invalidates cache
pattern2 = get_sensitive_pattern()  # New pattern compiled
```

---

## API Reference

::: pylogshield.config
    options:
      show_root_heading: true
      show_source: true
      members:
        - SENSITIVE_FIELDS
        - add_sensitive_fields
        - remove_sensitive_fields
        - get_sensitive_fields
        - get_sensitive_pattern
        - invalidate_sensitive_pattern_cache
