# Build Request: Add String Padding Utility

## Goal
Implement a string padding utility function that pads a string to a specified width with a configurable padding character. This utility will be useful for formatting console output and aligning text in reports.

## Requirements
- Function signature: `string_pad(s: str, width: int, char=' ') -> str`
- Left-pad the string if it's shorter than the specified width
- If string is already equal to or longer than width, return it unchanged
- Padding character should default to space but be configurable
- Handle edge cases: empty strings, zero/negative width, multi-char padding strings
- Deterministic behavior with no side effects

## Files to Create/Modify
- `src/utils/string_utils.py` - New utility module
- `tests/test_string_utils.py` - Comprehensive test coverage

## Acceptance Criteria
- All tests must pass (STRICT pytest validation)
- Code must follow project style (type hints, docstrings)
- Deterministic behavior required
- Test coverage for edge cases:
  - Empty string
  - Width = 0
  - Width < string length
  - Different padding characters
  - Unicode strings

## Example Usage
```python
from utils.string_utils import string_pad

string_pad("hello", 10)           # "     hello"
string_pad("test", 8, '0')        # "0000test"
string_pad("toolong", 4)          # "toolong"
string_pad("", 5)                 # "     "
```
