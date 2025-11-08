# Build Request: Add Unix Epoch Time Converter

## Goal
Implement a time format conversion utility that converts ISO 8601 timestamp strings to Unix epoch integers. This will enable easier time comparisons and storage in the system observer and reporting modules.

## Requirements
- Function signature: `to_unix_epoch(ts: str) -> int`
- Accept ISO 8601 format strings (e.g., "2025-01-08T12:34:56+00:00")
- Return integer Unix timestamp (seconds since 1970-01-01 00:00:00 UTC)
- Handle timezone-aware timestamps correctly
- Raise ValueError for invalid timestamp formats
- Deterministic behavior with no side effects
- Work with the existing `now_iso()` function in `src/utils/time_now.py`

## Files to Create/Modify
- `src/utils/time_format.py` - New conversion utility module
- `tests/test_time_format.py` - Comprehensive test coverage

## Acceptance Criteria
- All tests must pass (STRICT pytest validation)
- Code must follow project style (type hints, docstrings)
- Deterministic behavior required
- Test coverage for:
  - Valid ISO 8601 timestamps
  - Timezone-aware timestamps
  - Invalid format strings
  - Edge cases (epoch zero, far future dates)
  - Round-trip conversion compatibility

## Example Usage
```python
from utils.time_format import to_unix_epoch

to_unix_epoch("1970-01-01T00:00:00+00:00")  # 0
to_unix_epoch("2025-01-08T12:00:00+00:00")  # 1736337600
to_unix_epoch("invalid")                    # raises ValueError
```

## Integration
This utility should work seamlessly with the existing `now_iso()` function:
```python
from utils.time_now import now_iso
from utils.time_format import to_unix_epoch

current_timestamp = now_iso()
epoch = to_unix_epoch(current_timestamp)  # Should work perfectly
```
