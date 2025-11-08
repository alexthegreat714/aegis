"""
Utility for getting current time as ISO 8601 timestamp.
"""

from datetime import datetime, timezone


def now_iso() -> str:
    """
    Get current UTC time as ISO 8601 string.

    Returns:
        ISO 8601 formatted timestamp (e.g., "2025-01-07T12:34:56.789012+00:00")
    """
    return datetime.now(timezone.utc).isoformat()
