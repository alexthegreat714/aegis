"""
Tests for time_now utility.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.time_now import now_iso


def test_now_iso_returns_string():
    """Test that now_iso() returns a string."""
    result = now_iso()
    assert isinstance(result, str)


def test_now_iso_format():
    """Test that now_iso() returns ISO 8601 format."""
    result = now_iso()

    # Should contain ISO format elements
    assert 'T' in result  # Date-time separator
    assert '+' in result or 'Z' in result or '-' in result[-6:]  # Timezone

    # Should be parseable as datetime
    parsed = datetime.fromisoformat(result)
    assert parsed is not None


def test_now_iso_is_current():
    """Test that now_iso() returns current time (within 1 second)."""
    from datetime import timezone

    result = now_iso()
    parsed = datetime.fromisoformat(result)
    current = datetime.now(timezone.utc)

    # Should be within 1 second of current time
    diff = abs((current - parsed).total_seconds())
    assert diff < 1.0
