"""
Time format conversion utilities.

Provides functions for converting between different time representations.
"""

from datetime import datetime


def to_unix_epoch(ts: str) -> int:
    """
    Convert ISO 8601 timestamp string to Unix epoch integer.

    Args:
        ts: ISO 8601 formatted timestamp string (e.g., "2025-01-08T12:34:56+00:00")

    Returns:
        Integer Unix timestamp (seconds since 1970-01-01 00:00:00 UTC)

    Raises:
        ValueError: If timestamp format is invalid

    Examples:
        >>> to_unix_epoch("1970-01-01T00:00:00+00:00")
        0
        >>> to_unix_epoch("2025-01-08T12:00:00+00:00")
        1736337600
    """
    if not isinstance(ts, str):
        raise ValueError(f"Expected string, got {type(ts).__name__}")

    if not ts:
        raise ValueError("Timestamp string cannot be empty")

    try:
        # Parse ISO 8601 timestamp
        dt = datetime.fromisoformat(ts)

        # Convert to Unix timestamp
        epoch = int(dt.timestamp())

        return epoch

    except ValueError as e:
        raise ValueError(f"Invalid ISO 8601 timestamp format: {ts}") from e
    except Exception as e:
        raise ValueError(f"Error parsing timestamp '{ts}': {e}") from e
