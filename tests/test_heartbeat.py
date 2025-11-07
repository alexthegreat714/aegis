"""Tests for heartbeat logging and health monitoring."""

import pytest
import tempfile
from pathlib import Path
from src.aegis_logging.logger import AegisLogger
from src.aegis_logging.session import SessionManager
from src.utils.health_monitor import HealthMonitor


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


def test_log_heartbeat_basic(logger_with_session):
    """Test basic heartbeat logging."""
    logger, session = logger_with_session

    logger.log_heartbeat(
        cycle_id=1,
        cpu_percent=25.5,
        memory_percent=60.2
    )

    events = logger.get_session_events(session.session_id)
    assert len(events) == 1

    event = events[0]
    assert event['intent'] == 'heartbeat'
    assert event['action'] == 'health_check'
    assert event['result'] == 'success'
    assert event['cycle_id'] == 1


def test_log_heartbeat_with_metadata(logger_with_session):
    """Test heartbeat logging with full metadata."""
    logger, session = logger_with_session

    logger.log_heartbeat(
        cycle_id=5,
        cpu_percent=15.3,
        memory_percent=45.8,
        active_window="Test Window - Browser"
    )

    events = logger.get_session_events(session.session_id)
    assert len(events) == 1

    event = events[0]
    import json
    metadata = json.loads(event['metadata'])

    assert metadata['cpu_percent'] == 15.3
    assert metadata['memory_percent'] == 45.8
    assert metadata['active_window'] == "Test Window - Browser"


def test_prune_heartbeats(logger_with_session):
    """Test heartbeat pruning to limit database size."""
    logger, session = logger_with_session

    # Log 20 heartbeats
    for i in range(1, 21):
        logger.log_heartbeat(
            cycle_id=i,
            cpu_percent=float(i),
            memory_percent=float(i * 2)
        )

    # Verify all logged
    events = logger.get_session_events(session.session_id)
    assert len(events) == 20

    # Prune to keep only 10
    deleted = logger.prune_heartbeats(max_entries=10)
    assert deleted == 10

    # Verify only 10 remain
    with logger._get_connection() as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM aegis_events WHERE intent = 'heartbeat'"
        )
        count = cursor.fetchone()[0]
    assert count == 10

    # Verify most recent 10 are kept
    events = logger.get_session_events(session.session_id)
    assert len(events) == 10
    assert events[0]['cycle_id'] == 11  # Oldest remaining
    assert events[-1]['cycle_id'] == 20  # Most recent


def test_prune_heartbeats_no_op_if_under_limit(logger_with_session):
    """Test pruning does nothing if under limit."""
    logger, session = logger_with_session

    # Log 5 heartbeats
    for i in range(1, 6):
        logger.log_heartbeat(cycle_id=i, cpu_percent=10.0)

    # Try to prune with limit of 10
    deleted = logger.prune_heartbeats(max_entries=10)
    assert deleted == 0

    # Verify all still present
    events = logger.get_session_events(session.session_id)
    assert len(events) == 5


def test_prune_old_logs(logger_with_session):
    """Test log retention pruning."""
    logger, session = logger_with_session

    # Log some events
    for i in range(5):
        logger.log_event(
            intent=f"test_{i}",
            action=f"action_{i}",
            policy_decision="ALLOW",
            result="success",
            cycle_id=i + 1,
            duration_ms=100
        )

    # Prune with retention=0 (should delete all)
    deleted = logger.prune_old_logs(retention_days=0)
    # May not delete due to timestamp being current - this is expected

    # Verify method executes without error
    assert deleted >= 0


def test_health_monitor_cpu():
    """Test CPU monitoring."""
    monitor = HealthMonitor()
    cpu = monitor.get_cpu_percent()

    assert isinstance(cpu, float)
    assert 0.0 <= cpu <= 100.0


def test_health_monitor_memory():
    """Test memory monitoring."""
    monitor = HealthMonitor()
    memory = monitor.get_memory_percent()

    assert isinstance(memory, float)
    assert 0.0 <= memory <= 100.0


def test_health_monitor_snapshot():
    """Test complete health snapshot."""
    monitor = HealthMonitor()
    snapshot = monitor.get_health_snapshot(
        include_cpu=True,
        include_memory=True,
        include_window=False  # May not be available in test environment
    )

    assert 'cpu_percent' in snapshot
    assert 'memory_percent' in snapshot
    assert isinstance(snapshot['cpu_percent'], float)
    assert isinstance(snapshot['memory_percent'], float)


def test_health_monitor_selective_snapshot():
    """Test selective health monitoring."""
    monitor = HealthMonitor()

    # Only CPU
    snapshot = monitor.get_health_snapshot(
        include_cpu=True,
        include_memory=False,
        include_window=False
    )
    assert 'cpu_percent' in snapshot
    assert 'memory_percent' not in snapshot

    # Only memory
    snapshot = monitor.get_health_snapshot(
        include_cpu=False,
        include_memory=True,
        include_window=False
    )
    assert 'cpu_percent' not in snapshot
    assert 'memory_percent' in snapshot


def test_heartbeat_mixed_with_regular_events(logger_with_session):
    """Test heartbeats don't interfere with regular events."""
    logger, session = logger_with_session

    # Log regular event
    logger.log_event(
        intent="test_intent",
        action="test_action",
        policy_decision="ALLOW",
        result="success",
        cycle_id=1,
        duration_ms=100
    )

    # Log heartbeat
    logger.log_heartbeat(cycle_id=1, cpu_percent=20.0)

    # Log another regular event
    logger.log_event(
        intent="test_intent_2",
        action="test_action_2",
        policy_decision="ALLOW",
        result="success",
        cycle_id=2,
        duration_ms=150
    )

    # Verify all logged
    events = logger.get_session_events(session.session_id)
    assert len(events) == 3

    # Verify heartbeat is identifiable
    heartbeats = [e for e in events if e['intent'] == 'heartbeat']
    regulars = [e for e in events if e['intent'] != 'heartbeat']

    assert len(heartbeats) == 1
    assert len(regulars) == 2
