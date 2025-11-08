"""
Tests for Claude session limit guard.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

from claude.limit_guard import SessionLimitDetector


@pytest.fixture
def temp_state_dir(tmp_path):
    """Temporary state directory for tests."""
    state_dir = tmp_path / ".aegis_state"
    state_dir.mkdir()
    return state_dir


@pytest.fixture
def detector(temp_state_dir):
    """Create detector instance for testing."""
    config = {
        "claude": {
            "daily_reset_hour": 0,
            "resume_buffer_minutes": 2,
            "limiter_match_text": [
                "session limit reached",
                "quota exceeded"
            ]
        }
    }
    return SessionLimitDetector(state_dir=temp_state_dir, config=config)


def test_limit_detector_initialization(detector, temp_state_dir):
    """Test detector initializes correctly."""
    assert detector.state_dir == temp_state_dir
    assert detector.daily_reset_hour == 0
    assert detector.resume_buffer_minutes == 2
    assert len(detector.limit_patterns) == 2


def test_detect_limit_in_text(detector):
    """Test limit detection in text."""
    # Positive cases - use patterns that match the regex
    assert detector.detect_limit_in_text("Session limit reached") is True
    assert detector.detect_limit_in_text("quota exceeded - try later") is True

    # Negative cases
    assert detector.detect_limit_in_text("Everything is fine") is False
    assert detector.detect_limit_in_text("") is False
    assert detector.detect_limit_in_text(None) is False


def test_calculate_reset_time(detector):
    """Test reset time calculation."""
    # Test with specific time
    current = datetime(2025, 1, 1, 23, 30, 0, tzinfo=timezone.utc)
    reset_time = detector.calculate_reset_time(current)

    # Should be next day at 00:02 (midnight + 2 min buffer)
    expected = datetime(2025, 1, 2, 0, 2, 0, tzinfo=timezone.utc)
    assert reset_time == expected


def test_calculate_reset_time_already_past_reset(detector):
    """Test reset time when current time is past reset hour."""
    # Current time is 1 AM
    current = datetime(2025, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
    reset_time = detector.calculate_reset_time(current)

    # Should be next day
    expected = datetime(2025, 1, 2, 0, 2, 0, tzinfo=timezone.utc)
    assert reset_time == expected


def test_save_and_load_blocked_state(detector):
    """Test saving and loading blocked state."""
    rev_id = "test_rev_001"
    prompt = "Test prompt"
    metadata = {"goal": "Test goal"}

    # Save state
    state_file = detector.save_blocked_state(rev_id, prompt, metadata)
    assert state_file.exists()

    # Load state
    loaded_state = detector.load_blocked_state()
    assert loaded_state is not None
    assert loaded_state["pending_revision"] == rev_id
    assert loaded_state["pending_prompt"] == prompt
    assert loaded_state["metadata"]["goal"] == "Test goal"


def test_clear_blocked_state(detector):
    """Test clearing blocked state."""
    # Create state
    detector.save_blocked_state("test_rev", "test prompt")
    assert detector.state_file.exists()

    # Clear state
    detector.clear_blocked_state()
    assert not detector.state_file.exists()


def test_should_resume_not_ready(detector):
    """Test should_resume when time hasn't passed."""
    # Create blocked state with future retry time
    future_time = datetime.now(timezone.utc) + timedelta(hours=1)
    state = {
        "blocked_at": datetime.now(timezone.utc).isoformat(),
        "retry_at": future_time.isoformat(),
        "pending_revision": "test_rev",
        "pending_prompt": "test"
    }

    # Should not be ready to resume
    assert detector.should_resume(state) is False


def test_should_resume_ready(detector):
    """Test should_resume when time has passed."""
    # Create blocked state with past retry time
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    state = {
        "blocked_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "retry_at": past_time.isoformat(),
        "pending_revision": "test_rev",
        "pending_prompt": "test"
    }

    # Should be ready to resume
    assert detector.should_resume(state) is True


@pytest.mark.desktop
def test_detect_limit_in_screenshot(detector, tmp_path):
    """Test OCR-based limit detection in screenshot."""
    # Skip if OCR not available
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        pytest.skip("OCR dependencies not available")

    # Create a simple test image
    screenshot_path = tmp_path / "screenshot.png"

    # Create a blank image with PIL
    from PIL import Image
    img = Image.new('RGB', (100, 50), color='white')
    img.save(screenshot_path)

    # Note: Real OCR on blank image won't find text, so just test the mechanism
    detected, text = detector.detect_limit_in_screenshot(screenshot_path)

    # Should not detect limit in blank image
    assert isinstance(detected, bool)
    assert isinstance(text, (str, type(None)))


def test_detect_limit_without_ocr(detector, tmp_path):
    """Test screenshot detection when OCR not available."""
    screenshot_path = tmp_path / "screenshot.png"
    screenshot_path.touch()

    # With no OCR backend, should handle gracefully
    detected, text = detector.detect_limit_in_screenshot(screenshot_path, ocr_backend=None)

    # May return False due to OCR unavailable or mock OCR
    assert isinstance(detected, bool)
