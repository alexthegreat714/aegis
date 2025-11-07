"""
SQLite database schema for Aegis logging.

Stores all events, actions, and LLM interactions for auditing.
"""

import sqlite3
from pathlib import Path
from typing import Optional


def create_database_schema(db_path: str) -> None:
    """
    Create SQLite database schema.

    Args:
        db_path: Path to database file
    """
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Events table - general system events
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Actions table - all executed actions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action_type TEXT NOT NULL,
            category TEXT,
            parameters TEXT,
            status TEXT NOT NULL,
            result TEXT,
            error TEXT,
            execution_time_ms REAL,
            intent_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # LLM interactions table - all calls to OpenWebUI
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS llm_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            model TEXT,
            prompt TEXT,
            response TEXT,
            tokens_used INTEGER,
            duration_ms REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Policy decisions table - policy check results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS policy_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            intent_id TEXT,
            action_type TEXT,
            decision TEXT NOT NULL,
            reason TEXT,
            requires_approval INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indices for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_actions_type ON actions(action_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON actions(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_timestamp ON llm_interactions(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_policy_intent ON policy_decisions(intent_id)")

    conn.commit()
    conn.close()

    print(f"[Database] Schema created at {db_path}")


class DatabaseLogger:
    """SQLite database logger."""

    def __init__(self, db_path: str):
        """
        Initialize database logger.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        create_database_schema(db_path)

    def _connect(self) -> sqlite3.Connection:
        """Create database connection."""
        return sqlite3.connect(self.db_path)

    def log_event(
        self,
        timestamp: str,
        event_type: str,
        status: str,
        data: Optional[str] = None
    ) -> None:
        """
        Log an event.

        Args:
            timestamp: ISO timestamp
            event_type: Event type
            status: Event status
            data: Optional JSON data
        """
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO events (timestamp, event_type, status, data) VALUES (?, ?, ?, ?)",
            (timestamp, event_type, status, data)
        )

        conn.commit()
        conn.close()

    def log_action(
        self,
        timestamp: str,
        action_type: str,
        category: str,
        parameters: str,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        intent_id: Optional[str] = None
    ) -> None:
        """
        Log an action.

        Args:
            timestamp: ISO timestamp
            action_type: Action type
            category: Action category
            parameters: JSON parameters
            status: Action status
            result: Optional result JSON
            error: Optional error message
            execution_time_ms: Execution time in milliseconds
            intent_id: Associated intent ID
        """
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO actions
            (timestamp, action_type, category, parameters, status, result, error, execution_time_ms, intent_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (timestamp, action_type, category, parameters, status, result, error, execution_time_ms, intent_id)
        )

        conn.commit()
        conn.close()

    def log_llm_interaction(
        self,
        timestamp: str,
        model: str,
        prompt: str,
        response: str,
        tokens_used: Optional[int] = None,
        duration_ms: Optional[float] = None
    ) -> None:
        """
        Log LLM interaction.

        Args:
            timestamp: ISO timestamp
            model: Model name
            prompt: Input prompt
            response: LLM response
            tokens_used: Token count
            duration_ms: Request duration
        """
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO llm_interactions
            (timestamp, model, prompt, response, tokens_used, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (timestamp, model, prompt, response, tokens_used, duration_ms)
        )

        conn.commit()
        conn.close()

    def log_policy_decision(
        self,
        timestamp: str,
        intent_id: str,
        action_type: str,
        decision: str,
        reason: str,
        requires_approval: bool
    ) -> None:
        """
        Log policy decision.

        Args:
            timestamp: ISO timestamp
            intent_id: Intent ID
            action_type: Action type
            decision: Decision (allow/block)
            reason: Decision reason
            requires_approval: Whether approval is required
        """
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO policy_decisions
            (timestamp, intent_id, action_type, decision, reason, requires_approval)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (timestamp, intent_id, action_type, decision, reason, 1 if requires_approval else 0)
        )

        conn.commit()
        conn.close()
