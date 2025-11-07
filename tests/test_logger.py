"""Tests for logging system."""

import pytest
import tempfile
from pathlib import Path
from src.aegis_logging.logger import AegisLogger
from src.aegis_logging.session import SessionManager


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_aegis.db"
        yield str(db_path)


@pytest.fixture
def logger_with_session(temp_db):
    """Create logger with active session."""
    SessionManager._current_session = None
    session = SessionManager.create_session()
    logger = AegisLogger(db_path=temp_db, enable_jsonl=False)
    yield logger, session
    SessionManager.end_session()


def test_logger_initialization(temp_db):
    """Test logger creates database and schema."""
    logger = AegisLogger(db_path=temp_db, enable_jsonl=False)

    assert Path(temp_db).exists()

    # Verify table exists
    with logger._get_connection() as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='aegis_events'"
        )
        assert cursor.fetchone() is not None


def test_log_event_without_session(temp_db):
    """Test logging without active session raises error."""
    logger = AegisLogger(db_path=temp_db, enable_jsonl=False)
    SessionManager._current_session = None

    with pytest.raises(RuntimeError, match="No active session"):
        logger.log_event(
            intent="test",
            action="test_action",
            policy_decision="ALLOW",
            result="success",
            cycle_id=1,
            duration_ms=100
        )


def test_log_event_success(logger_with_session):
    """Test successful event logging."""
    logger, session = logger_with_session

    logger.log_event(
        intent="test_intent",
        action="test_action",
        policy_decision="ALLOW",
        result="success",
        cycle_id=1,
        duration_ms=150,
        error=None,
        metadata={'key': 'value'}
    )

    # Verify event was stored
    events = logger.get_session_events(session.session_id)
    assert len(events) == 1

    event = events[0]
    assert event['intent'] == "test_intent"
    assert event['action'] == "test_action"
    assert event['policy_decision'] == "ALLOW"
    assert event['result'] == "success"
    assert event['cycle_id'] == 1
    assert event['duration_ms'] == 150
    assert event['error'] is None
    assert '"key": "value"' in event['metadata']


def test_log_event_with_error(logger_with_session):
    """Test logging event with error."""
    logger, session = logger_with_session

    logger.log_event(
        intent="failing_intent",
        action="fail_action",
        policy_decision="ALLOW",
        result="error",
        cycle_id=1,
        duration_ms=50,
        error="Something went wrong"
    )

    errors = logger.get_error_events()
    assert len(errors) == 1
    assert errors[0]['error'] == "Something went wrong"


def test_get_recent_events(logger_with_session):
    """Test retrieving recent events."""
    logger, session = logger_with_session

    # Log multiple events
    for i in range(5):
        logger.log_event(
            intent=f"intent_{i}",
            action=f"action_{i}",
            policy_decision="ALLOW",
            result="success",
            cycle_id=i + 1,
            duration_ms=100
        )

    recent = logger.get_recent_events(limit=3)
    assert len(recent) == 3

    # Should be in reverse chronological order
    assert recent[0]['cycle_id'] == 5
    assert recent[1]['cycle_id'] == 4
    assert recent[2]['cycle_id'] == 3


def test_get_sessions(logger_with_session):
    """Test session summary retrieval."""
    logger, session = logger_with_session

    # Log some events
    logger.log_event(
        intent="test1", action="act1", policy_decision="ALLOW",
        result="success", cycle_id=1, duration_ms=100
    )
    logger.log_event(
        intent="test2", action="act2", policy_decision="ALLOW",
        result="error", cycle_id=2, duration_ms=200, error="test error"
    )

    sessions = logger.get_sessions()
    assert len(sessions) == 1

    s = sessions[0]
    assert s['session_id'] == session.session_id
    assert s['cycle_count'] == 2
    assert s['total_events'] == 2
    assert s['error_count'] == 1


def test_required_fields_validation(logger_with_session):
    """Test that missing required fields raise errors."""
    logger, session = logger_with_session

    # duration_ms is required but missing
    with pytest.raises(TypeError):
        logger.log_event(
            intent="test",
            action="test",
            policy_decision="ALLOW",
            result="success",
            cycle_id=1
            # Missing duration_ms
        )


def test_jsonl_writing(temp_db):
    """Test JSONL file is created when enabled."""
    logger = AegisLogger(db_path=temp_db, enable_jsonl=True)
    session = SessionManager.create_session()

    logger.log_event(
        intent="test", action="act", policy_decision="ALLOW",
        result="success", cycle_id=1, duration_ms=100
    )

    jsonl_path = Path(temp_db).parent / "aegis_events.jsonl"
    assert jsonl_path.exists()

    with open(jsonl_path, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 1
        assert "test" in lines[0]

    SessionManager.end_session()
