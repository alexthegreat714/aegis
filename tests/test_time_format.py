"""
Tests for time format conversion utilities.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from datetime import datetime, timezone
from utils.time_format import to_unix_epoch
from utils.time_now import now_iso


def test_to_unix_epoch_zero():
    """Test converting Unix epoch zero."""
    result = to_unix_epoch("1970-01-01T00:00:00+00:00")
    assert result == 0


def test_to_unix_epoch_known_timestamp():
    """Test converting a known timestamp."""
    # 2025-01-08 12:00:00 UTC = 1736337600
    result = to_unix_epoch("2025-01-08T12:00:00+00:00")
    assert result == 1736337600


def test_to_unix_epoch_with_timezone():
    """Test converting timestamp with different timezone."""
    # These should be equivalent
    utc_time = to_unix_epoch("2025-01-08T12:00:00+00:00")
    est_time = to_unix_epoch("2025-01-08T07:00:00-05:00")

    assert utc_time == est_time


def test_to_unix_epoch_invalid_format():
    """Test with invalid timestamp format."""
    with pytest.raises(ValueError, match="Invalid ISO 8601"):
        to_unix_epoch("not a timestamp")


def test_to_unix_epoch_empty_string():
    """Test with empty string."""
    with pytest.raises(ValueError, match="cannot be empty"):
        to_unix_epoch("")


def test_to_unix_epoch_non_string():
    """Test with non-string input."""
    with pytest.raises(ValueError, match="Expected string"):
        to_unix_epoch(12345)


def test_to_unix_epoch_partial_format():
    """Test with incomplete ISO format (date-only format is actually valid)."""
    # Date-only format is valid ISO 8601 and supported by fromisoformat
    result = to_unix_epoch("2025-01-08")
    assert isinstance(result, int)
    assert result > 0


def test_to_unix_epoch_future_date():
    """Test with far future date."""
    # 2100-01-01
    result = to_unix_epoch("2100-01-01T00:00:00+00:00")
    assert result > 0
    assert result >= 4102444800  # Should be at or after 2100


def test_to_unix_epoch_integration_with_now_iso():
    """Test round-trip conversion with now_iso()."""
    # Get current time as ISO string
    current_iso = now_iso()

    # Convert to epoch
    epoch = to_unix_epoch(current_iso)

    # Should be a reasonable current timestamp (after 2020)
    assert epoch > 1577836800  # 2020-01-01

    # Should be close to current time
    current_epoch = int(datetime.now(timezone.utc).timestamp())
    assert abs(epoch - current_epoch) < 2  # Within 2 seconds


def test_to_unix_epoch_deterministic():
    """Test that function is deterministic."""
    ts = "2025-01-08T15:30:45+00:00"

    result1 = to_unix_epoch(ts)
    result2 = to_unix_epoch(ts)

    assert result1 == result2


def test_to_unix_epoch_microseconds():
    """Test timestamp with microseconds."""
    result = to_unix_epoch("2025-01-08T12:00:00.123456+00:00")
    # Should truncate to seconds
    assert isinstance(result, int)
    assert result == 1736337600


def test_to_unix_epoch_z_notation():
    """Test timestamp with Z timezone notation."""
    result = to_unix_epoch("2025-01-08T12:00:00Z")
    assert result == 1736337600


def test_to_unix_epoch_no_timezone():
    """Test timestamp without explicit timezone (naive datetime)."""
    # This should still work as fromisoformat handles it
    result = to_unix_epoch("2025-01-08T12:00:00")
    assert isinstance(result, int)
    assert result > 0
