"""
Normalized logging system for Aegis with SQLite and JSONL support.

Enforces schema with required fields for auditable history.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager

from .session import SessionManager


class AegisLogger:
    """
    Structured logger for Aegis control loop events.

    Enforces normalized schema:
    - timestamp: ISO8601 format
    - session_id: UUID of current session
    - cycle_id: Cycle number within session
    - intent: What Aegis is trying to do
    - action: Specific action taken
    - policy_decision: Policy evaluation result
    - result: Outcome of action
    - error: Error message if any (nullable)
    - duration_ms: Action duration in milliseconds
    """

    REQUIRED_FIELDS = [
        'timestamp', 'session_id', 'cycle_id', 'intent',
        'action', 'policy_decision', 'result', 'duration_ms'
    ]

    SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS aegis_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        session_id TEXT NOT NULL,
        cycle_id INTEGER NOT NULL,
        intent TEXT NOT NULL,
        action TEXT NOT NULL,
        policy_decision TEXT NOT NULL,
        result TEXT NOT NULL,
        error TEXT,
        duration_ms INTEGER NOT NULL,
        metadata TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_session_id ON aegis_events(session_id);
    CREATE INDEX IF NOT EXISTS idx_timestamp ON aegis_events(timestamp);
    CREATE INDEX IF NOT EXISTS idx_error ON aegis_events(error);
    """

    def __init__(
        self,
        db_path: str = "data/aegis.db",
        enable_jsonl: bool = True,
        log_dir: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize logger with database path.

        Args:
            db_path: Path to SQLite database
            enable_jsonl: Also write JSONL logs alongside SQLite
            log_dir: Legacy parameter - directory for JSONL logs (optional)
            settings: Legacy parameter - settings dict (optional, absorbed safely)
            **kwargs: Additional legacy parameters (absorbed safely)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.enable_jsonl = enable_jsonl

        # Safely absorb legacy settings dict without changing behavior
        self._settings = settings or {}

        # Determine JSONL log directory
        if enable_jsonl:
            if log_dir is not None:
                # Use legacy log_dir if provided
                log_root = Path(log_dir)
                log_root.mkdir(parents=True, exist_ok=True)
                self.jsonl_path = log_root / "aegis.jsonl"
            else:
                # Use default location alongside database
                self.jsonl_path = self.db_path.parent / "aegis_events.jsonl"

        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.executescript(self.SCHEMA_SQL)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def log_event(
        self,
        intent: Optional[str] = None,
        action: Optional[str] = None,
        policy_decision: Optional[str] = None,
        result: Optional[str] = None,
        cycle_id: Optional[int] = None,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        # Legacy parameters
        event_type: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        **kwargs
    ):
        """
        Log a single Aegis event with enforced schema.

        Args:
            intent: What Aegis is trying to accomplish
            action: Specific action being taken
            policy_decision: Result of policy evaluation
            result: Outcome (success/failure/skipped)
            cycle_id: Current cycle number
            duration_ms: How long the action took
            error: Error message if action failed
            metadata: Additional context (stored as JSON)
            event_type: Legacy parameter - event type (maps to action)
            data: Legacy parameter - event data (maps to metadata)
            status: Legacy parameter - status (maps to result)
            **kwargs: Additional legacy parameters (absorbed safely)
        """
        # Handle legacy API - map old parameters to new schema
        if event_type is not None:
            # Legacy call detected
            action = action or event_type
            intent = intent or "legacy_event"
            policy_decision = policy_decision or "ALLOW"
            result = result or status or "info"
            cycle_id = cycle_id or 0
            duration_ms = duration_ms or 0
            metadata = metadata or data

        # Validate we have required data
        if any(x is None for x in [intent, action, policy_decision, result, cycle_id, duration_ms]):
            # This is a legacy call without session - log to JSONL only if enabled
            if self.enable_jsonl and event_type:
                legacy_event = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'event_type': event_type,
                    'data': data,
                    'status': status
                }
                with open(self.jsonl_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(legacy_event) + '\n')
            return

        session = SessionManager.get_current()
        if not session:
            # No active session - legacy mode, log to JSONL only
            if self.enable_jsonl:
                legacy_event = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'intent': intent,
                    'action': action,
                    'result': result,
                    'metadata': metadata
                }
                with open(self.jsonl_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(legacy_event) + '\n')
            return

        timestamp = datetime.utcnow().isoformat()
        session_id = session.session_id

        event = {
            'timestamp': timestamp,
            'session_id': session_id,
            'cycle_id': cycle_id,
            'intent': intent,
            'action': action,
            'policy_decision': policy_decision,
            'result': result,
            'error': error,
            'duration_ms': duration_ms,
            'metadata': json.dumps(metadata) if metadata else None
        }

        # Validate required fields
        for field in self.REQUIRED_FIELDS:
            if field not in event or event[field] is None:
                raise ValueError(f"Required field '{field}' is missing or None")

        # Write to SQLite
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO aegis_events
                (timestamp, session_id, cycle_id, intent, action, policy_decision,
                 result, error, duration_ms, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event['timestamp'], event['session_id'], event['cycle_id'],
                event['intent'], event['action'], event['policy_decision'],
                event['result'], event['error'], event['duration_ms'],
                event['metadata']
            ))
            conn.commit()

        # Write to JSONL if enabled
        if self.enable_jsonl:
            with open(self.jsonl_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event) + '\n')

        # Update session stats
        session.record_action(success=(result == 'success'))

    def log_action(
        self,
        action_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        status: str = "pending",
        **kwargs
    ):
        """
        Legacy method - log an action (alias for log_event).

        Args:
            action_type: Type of action being performed
            parameters: Action parameters
            status: Action status
            **kwargs: Additional legacy parameters
        """
        self.log_event(
            event_type=action_type,
            data=parameters,
            status=status,
            **kwargs
        )

    def get_session_events(self, session_id: str) -> list:
        """Retrieve all events for a specific session."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM aegis_events WHERE session_id = ? ORDER BY cycle_id, id",
                (session_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_events(self, limit: int = 20) -> list:
        """Retrieve most recent events across all sessions."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM aegis_events ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_error_events(self, limit: Optional[int] = None) -> list:
        """Retrieve all events with errors."""
        query = "SELECT * FROM aegis_events WHERE error IS NOT NULL ORDER BY timestamp DESC"
        if limit:
            query += f" LIMIT {limit}"

        with self._get_connection() as conn:
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def get_sessions(self) -> list:
        """Get list of all unique sessions with summary stats."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT
                    session_id,
                    MIN(timestamp) as started_at,
                    MAX(timestamp) as ended_at,
                    MAX(cycle_id) as cycle_count,
                    COUNT(*) as total_events,
                    SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as error_count
                FROM aegis_events
                GROUP BY session_id
                ORDER BY started_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def log_heartbeat(
        self,
        cycle_id: int,
        cpu_percent: Optional[float] = None,
        memory_percent: Optional[float] = None,
        active_window: Optional[str] = None
    ):
        """
        Log a heartbeat event with system health metrics.

        Args:
            cycle_id: Current cycle number
            cpu_percent: CPU usage percentage
            memory_percent: Memory usage percentage
            active_window: Active window title
        """
        metadata = {}
        if cpu_percent is not None:
            metadata['cpu_percent'] = cpu_percent
        if memory_percent is not None:
            metadata['memory_percent'] = memory_percent
        if active_window is not None:
            metadata['active_window'] = active_window

        self.log_event(
            intent="heartbeat",
            action="health_check",
            policy_decision="ALLOW",
            result="success",
            cycle_id=cycle_id,
            duration_ms=0,
            metadata=metadata
        )

    def prune_old_logs(self, retention_days: int = 30):
        """
        Remove logs older than retention period.

        Args:
            retention_days: Keep logs from last N days
        """
        cutoff_date = datetime.utcnow().timestamp() - (retention_days * 86400)
        cutoff_iso = datetime.fromtimestamp(cutoff_date).isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM aegis_events WHERE timestamp < ?",
                (cutoff_iso,)
            )
            deleted = cursor.rowcount
            conn.commit()

        return deleted

    def prune_heartbeats(self, max_entries: int = 1000):
        """
        Keep only the most recent N heartbeat entries.

        Args:
            max_entries: Maximum heartbeat entries to retain
        """
        with self._get_connection() as conn:
            # Count current heartbeats
            cursor = conn.execute(
                "SELECT COUNT(*) FROM aegis_events WHERE intent = 'heartbeat'"
            )
            count = cursor.fetchone()[0]

            if count <= max_entries:
                return 0

            # Delete oldest heartbeats beyond limit
            cursor = conn.execute("""
                DELETE FROM aegis_events
                WHERE intent = 'heartbeat'
                AND id NOT IN (
                    SELECT id FROM aegis_events
                    WHERE intent = 'heartbeat'
                    ORDER BY timestamp DESC
                    LIMIT ?
                )
            """, (max_entries,))
            deleted = cursor.rowcount
            conn.commit()

        return deleted

    def log_llm_call(
        self,
        model: str,
        prompt: str,
        response: str,
        tokens_used: int = 0,
        **kwargs
    ):
        """
        Log LLM interaction.

        Args:
            model: Model name/identifier
            prompt: Input prompt
            response: Model response
            tokens_used: Token count
            **kwargs: Additional parameters (absorbed safely)
        """
        # Log as a special event type
        self.log_event(
            intent="llm_interaction",
            action=f"call_{model}",
            policy_decision="ALLOW",
            result="success",
            cycle_id=kwargs.get("cycle_id", 0),
            duration_ms=kwargs.get("duration_ms", 0),
            metadata={
                "model": model,
                "prompt": prompt[:500],  # Truncate for storage
                "response": response[:500],  # Truncate for storage
                "tokens_used": tokens_used
            }
        )
