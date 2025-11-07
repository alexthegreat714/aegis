"""
Log inspector module for querying and analyzing Aegis execution history.

Supports filtering, formatting, and session-based queries.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from tabulate import tabulate


FormatType = Literal['json', 'table', 'md']


class LogInspector:
    """Inspector for Aegis event logs with multiple output formats."""

    def __init__(self, db_path: str = "data/aegis.db"):
        """
        Initialize inspector with database path.

        Args:
            db_path: Path to SQLite database

        Raises:
            FileNotFoundError: If database doesn't exist
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Aegis database not found at {self.db_path}. "
                "Run Aegis at least once to create the database."
            )

    def _get_connection(self):
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def query_last(self, n: int = 20) -> List[Dict[str, Any]]:
        """
        Get last N events across all sessions.

        Args:
            n: Number of events to retrieve

        Returns:
            List of event dictionaries
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM aegis_events
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (n,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def query_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all events for a specific session.

        Args:
            session_id: UUID of session to retrieve

        Returns:
            List of event dictionaries ordered by cycle
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM aegis_events
                WHERE session_id = ?
                ORDER BY cycle_id, id
                """,
                (session_id,)
            )
            events = [dict(row) for row in cursor.fetchall()]
            if not events:
                raise ValueError(f"No events found for session: {session_id}")
            return events
        finally:
            conn.close()

    def query_errors_only(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get only events with errors.

        Args:
            limit: Optional limit on number of results

        Returns:
            List of event dictionaries with errors
        """
        conn = self._get_connection()
        try:
            query = """
                SELECT * FROM aegis_events
                WHERE error IS NOT NULL
                ORDER BY timestamp DESC
            """
            if limit:
                query += f" LIMIT {limit}"

            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        Get summary of all sessions.

        Returns:
            List of session summaries with stats
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT
                    session_id,
                    MIN(timestamp) as started_at,
                    MAX(timestamp) as ended_at,
                    MAX(cycle_id) as max_cycle,
                    COUNT(*) as total_events,
                    SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as error_count,
                    SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as success_count
                FROM aegis_events
                GROUP BY session_id
                ORDER BY started_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def format_events(
        self,
        events: List[Dict[str, Any]],
        format_type: FormatType = 'table',
        compact: bool = False
    ) -> str:
        """
        Format events for display.

        Args:
            events: List of event dictionaries
            format_type: Output format (json, table, md)
            compact: Use compact view (fewer columns)

        Returns:
            Formatted string
        """
        if not events:
            return "No events found."

        if format_type == 'json':
            return json.dumps(events, indent=2)

        # Table formats
        if compact:
            headers = ['Cycle', 'Intent', 'Action', 'Result', 'Duration(ms)', 'Error']
            rows = [
                [
                    e.get('cycle_id'),
                    e.get('intent', '')[:30],
                    e.get('action', '')[:30],
                    e.get('result', ''),
                    e.get('duration_ms'),
                    (e.get('error', '') or '')[:40]
                ]
                for e in events
            ]
        else:
            headers = [
                'Session', 'Cycle', 'Timestamp', 'Intent', 'Action',
                'Policy', 'Result', 'Duration(ms)', 'Error'
            ]
            rows = [
                [
                    e.get('session_id', '')[:8],
                    e.get('cycle_id'),
                    e.get('timestamp', '')[:19],  # Trim to datetime portion
                    e.get('intent', '')[:25],
                    e.get('action', '')[:25],
                    e.get('policy_decision', '')[:15],
                    e.get('result', ''),
                    e.get('duration_ms'),
                    (e.get('error', '') or '')[:40]
                ]
                for e in events
            ]

        tablefmt = 'github' if format_type == 'md' else 'simple'
        return tabulate(rows, headers=headers, tablefmt=tablefmt)

    def format_sessions(self, sessions: List[Dict[str, Any]], format_type: FormatType = 'table') -> str:
        """
        Format session summaries for display.

        Args:
            sessions: List of session dictionaries
            format_type: Output format (json, table, md)

        Returns:
            Formatted string
        """
        if not sessions:
            return "No sessions found."

        if format_type == 'json':
            return json.dumps(sessions, indent=2)

        headers = [
            'Session ID', 'Started', 'Ended', 'Cycles', 'Events',
            'Errors', 'Success', 'Error Rate'
        ]

        rows = []
        for s in sessions:
            total = s.get('total_events', 0)
            errors = s.get('error_count', 0)
            error_rate = f"{(errors / total * 100):.1f}%" if total > 0 else "0%"

            rows.append([
                s.get('session_id', '')[:12] + '...',
                s.get('started_at', '')[:19],
                s.get('ended_at', '')[:19] if s.get('ended_at') else 'ongoing',
                s.get('max_cycle'),
                total,
                errors,
                s.get('success_count', 0),
                error_rate
            ])

        tablefmt = 'github' if format_type == 'md' else 'simple'
        return tabulate(rows, headers=headers, tablefmt=tablefmt)

    def get_replay_data(self, session_id: str) -> Dict[str, Any]:
        """
        Get structured data for replay mode.

        Args:
            session_id: Session to replay

        Returns:
            Dictionary with session info and ordered events
        """
        events = self.query_session(session_id)

        return {
            'session_id': session_id,
            'event_count': len(events),
            'started_at': events[0]['timestamp'] if events else None,
            'ended_at': events[-1]['timestamp'] if events else None,
            'max_cycle': max(e['cycle_id'] for e in events) if events else 0,
            'events': events
        }
