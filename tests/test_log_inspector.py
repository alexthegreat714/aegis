"""Tests for log inspector."""

import pytest
import tempfile
from pathlib import Path
from src.aegis_logging.logger import AegisLogger
from src.aegis_logging.log_inspector import LogInspector
from src.aegis_logging.session import SessionManager


@pytest.fixture
def populated_db():
    """Create database with test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_aegis.db"

        # Create logger and populate with data
        logger = AegisLogger(db_path=str(db_path), enable_jsonl=False)

        # Session 1: 3 successful events
        session1 = SessionManager.create_session()
        for i in range(3):
            logger.log_event(
                intent=f"intent_s1_{i}",
                action=f"action_s1_{i}",
                policy_decision="ALLOW",
                result="success",
                cycle_id=i + 1,
                duration_ms=100 + i * 10
            )
        SessionManager.end_session()

        # Session 2: 2 events, 1 with error
        session2 = SessionManager.create_session()
        logger.log_event(
            intent="intent_s2_0",
            action="action_s2_0",
            policy_decision="ALLOW",
            result="success",
            cycle_id=1,
            duration_ms=200
        )
        logger.log_event(
            intent="intent_s2_1",
            action="action_s2_1",
            policy_decision="DENY",
            result="error",
            cycle_id=2,
            duration_ms=50,
            error="Test error message"
        )
        SessionManager.end_session()

        yield str(db_path), session1.session_id, session2.session_id


def test_inspector_missing_db():
    """Test inspector raises error for missing database."""
    with pytest.raises(FileNotFoundError, match="not found"):
        LogInspector(db_path="/nonexistent/path/aegis.db")


def test_query_last_n(populated_db):
    """Test --last N returns correct count."""
    db_path, _, _ = populated_db
    inspector = LogInspector(db_path=db_path)

    # Query last 2 events
    events = inspector.query_last(n=2)

    assert len(events) == 2

    # Should be in reverse chronological order (most recent first)
    assert events[0]['intent'] == "intent_s2_1"  # Last event from session 2
    assert events[1]['intent'] == "intent_s2_0"


def test_query_last_more_than_exists(populated_db):
    """Test querying more events than exist."""
    db_path, _, _ = populated_db
    inspector = LogInspector(db_path=db_path)

    events = inspector.query_last(n=100)

    assert len(events) == 5  # Only 5 events total


def test_query_session(populated_db):
    """Test --session returns all events for session."""
    db_path, session1_id, _ = populated_db
    inspector = LogInspector(db_path=db_path)

    events = inspector.query_session(session1_id)

    assert len(events) == 3
    assert all(e['session_id'] == session1_id for e in events)

    # Should be ordered by cycle
    assert events[0]['cycle_id'] == 1
    assert events[1]['cycle_id'] == 2
    assert events[2]['cycle_id'] == 3


def test_query_nonexistent_session(populated_db):
    """Test querying nonexistent session raises error."""
    db_path, _, _ = populated_db
    inspector = LogInspector(db_path=db_path)

    with pytest.raises(ValueError, match="No events found"):
        inspector.query_session("nonexistent-uuid")


def test_query_errors_only(populated_db):
    """Test --errors-only filters correctly."""
    db_path, _, _ = populated_db
    inspector = LogInspector(db_path=db_path)

    errors = inspector.query_errors_only()

    assert len(errors) == 1
    assert errors[0]['error'] == "Test error message"
    assert errors[0]['intent'] == "intent_s2_1"


def test_query_errors_with_limit(populated_db):
    """Test errors query respects limit."""
    db_path, _, _ = populated_db
    inspector = LogInspector(db_path=db_path)

    # Add more errors
    logger = AegisLogger(db_path=db_path, enable_jsonl=False)
    session = SessionManager.create_session()

    for i in range(5):
        logger.log_event(
            intent=f"error_intent_{i}",
            action=f"error_action_{i}",
            policy_decision="ALLOW",
            result="error",
            cycle_id=i + 1,
            duration_ms=100,
            error=f"Error {i}"
        )

    SessionManager.end_session()

    errors = inspector.query_errors_only(limit=3)
    assert len(errors) == 3


def test_list_sessions(populated_db):
    """Test session listing with stats."""
    db_path, session1_id, session2_id = populated_db
    inspector = LogInspector(db_path=db_path)

    sessions = inspector.list_sessions()

    assert len(sessions) == 2

    # Most recent first
    s2 = sessions[0]
    assert s2['session_id'] == session2_id
    assert s2['total_events'] == 2
    assert s2['error_count'] == 1
    assert s2['success_count'] == 1

    s1 = sessions[1]
    assert s1['session_id'] == session1_id
    assert s1['total_events'] == 3
    assert s1['error_count'] == 0
    assert s1['success_count'] == 3


def test_format_events_json(populated_db):
    """Test JSON formatting."""
    db_path, _, _ = populated_db
    inspector = LogInspector(db_path=db_path)

    events = inspector.query_last(n=2)
    output = inspector.format_events(events, format_type='json')

    assert '"intent"' in output
    assert '"action"' in output
    assert 'intent_s2_1' in output


def test_format_events_table(populated_db):
    """Test table formatting."""
    db_path, _, _ = populated_db
    inspector = LogInspector(db_path=db_path)

    events = inspector.query_last(n=2)
    output = inspector.format_events(events, format_type='table')

    assert 'Session' in output
    assert 'Cycle' in output
    assert 'Intent' in output


def test_format_events_markdown(populated_db):
    """Test markdown formatting."""
    db_path, _, _ = populated_db
    inspector = LogInspector(db_path=db_path)

    events = inspector.query_last(n=2)
    output = inspector.format_events(events, format_type='md')

    # Markdown tables have pipes
    assert '|' in output


def test_format_events_compact(populated_db):
    """Test compact formatting has fewer columns."""
    db_path, _, _ = populated_db
    inspector = LogInspector(db_path=db_path)

    events = inspector.query_last(n=2)
    compact = inspector.format_events(events, format_type='table', compact=True)
    full = inspector.format_events(events, format_type='table', compact=False)

    # Compact should be shorter (fewer columns)
    assert 'Session' in full
    assert 'Session' not in compact  # Session column not in compact


def test_get_replay_data(populated_db):
    """Test replay data structure."""
    db_path, session1_id, _ = populated_db
    inspector = LogInspector(db_path=db_path)

    replay_data = inspector.get_replay_data(session1_id)

    assert replay_data['session_id'] == session1_id
    assert replay_data['event_count'] == 3
    assert replay_data['max_cycle'] == 3
    assert replay_data['started_at'] is not None
    assert replay_data['ended_at'] is not None
    assert len(replay_data['events']) == 3


def test_format_empty_events(populated_db):
    """Test formatting empty results."""
    db_path, _, _ = populated_db
    inspector = LogInspector(db_path=db_path)

    output = inspector.format_events([], format_type='table')
    assert output == "No events found."
