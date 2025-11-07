"""Tests for session tracking."""

import pytest
from datetime import datetime
from src.aegis_logging.session import AegisSession, SessionManager


def test_session_creation():
    """Test basic session creation."""
    session = AegisSession()

    assert session.session_id is not None
    assert len(session.session_id) == 36  # UUID format
    assert session.cycle_count == 0
    assert session.total_actions == 0
    assert session.total_errors == 0
    assert session.replay_mode is False
    assert session.ended_at is None


def test_session_cycle_increment():
    """Test cycle counter increments correctly."""
    session = AegisSession()

    assert session.start_cycle() == 1
    assert session.start_cycle() == 2
    assert session.start_cycle() == 3
    assert session.cycle_count == 3


def test_session_record_action():
    """Test action recording updates stats."""
    session = AegisSession()

    session.record_action(success=True)
    assert session.total_actions == 1
    assert session.total_errors == 0

    session.record_action(success=False)
    assert session.total_actions == 2
    assert session.total_errors == 1


def test_session_end_and_duration():
    """Test session ending and duration calculation."""
    session = AegisSession()
    assert session.duration_seconds() is None

    session.end()
    assert session.ended_at is not None
    assert session.duration_seconds() >= 0


def test_session_to_dict():
    """Test session serialization."""
    session = AegisSession(replay_mode=True)
    session.start_cycle()
    session.record_action(success=True)

    data = session.to_dict()

    assert data['session_id'] == session.session_id
    assert data['cycle_count'] == 1
    assert data['total_actions'] == 1
    assert data['total_errors'] == 0
    assert data['replay_mode'] is True


def test_session_manager_create():
    """Test SessionManager creates and tracks session."""
    SessionManager._current_session = None

    session = SessionManager.create_session()

    assert session is not None
    assert SessionManager.get_current() == session
    assert SessionManager.get_session_id() == session.session_id


def test_session_manager_end():
    """Test SessionManager properly ends session."""
    session = SessionManager.create_session()
    assert session.ended_at is None

    SessionManager.end_session()

    assert session.ended_at is not None
    assert SessionManager.get_current() is None
    assert SessionManager.get_session_id() is None


def test_session_manager_replay_mode():
    """Test SessionManager creates replay session."""
    SessionManager._current_session = None

    session = SessionManager.create_session(replay_mode=True)

    assert session.replay_mode is True
