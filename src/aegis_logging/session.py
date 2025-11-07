"""
Session tracking for Aegis control loop execution.

Each Aegis run gets a unique session UUID that's used to track
all events, decisions, and actions within that execution.
"""

import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class AegisSession:
    """Represents a single Aegis execution session."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    cycle_count: int = 0
    total_actions: int = 0
    total_errors: int = 0
    replay_mode: bool = False

    def start_cycle(self) -> int:
        """Increment and return the current cycle number."""
        self.cycle_count += 1
        return self.cycle_count

    def record_action(self, success: bool = True):
        """Record an action execution."""
        self.total_actions += 1
        if not success:
            self.total_errors += 1

    def end(self):
        """Mark session as completed."""
        self.ended_at = datetime.utcnow()

    def duration_seconds(self) -> Optional[float]:
        """Calculate session duration in seconds."""
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds()

    def to_dict(self) -> dict:
        """Convert session to dictionary for logging."""
        return {
            'session_id': self.session_id,
            'started_at': self.started_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'cycle_count': self.cycle_count,
            'total_actions': self.total_actions,
            'total_errors': self.total_errors,
            'replay_mode': self.replay_mode,
            'duration_seconds': self.duration_seconds()
        }


class SessionManager:
    """Manages the current active session."""

    _current_session: Optional[AegisSession] = None

    @classmethod
    def create_session(cls, replay_mode: bool = False) -> AegisSession:
        """Create and activate a new session."""
        cls._current_session = AegisSession(replay_mode=replay_mode)
        return cls._current_session

    @classmethod
    def get_current(cls) -> Optional[AegisSession]:
        """Get the currently active session."""
        return cls._current_session

    @classmethod
    def end_session(cls):
        """End the current session."""
        if cls._current_session:
            cls._current_session.end()
        cls._current_session = None

    @classmethod
    def get_session_id(cls) -> Optional[str]:
        """Get current session ID or None."""
        return cls._current_session.session_id if cls._current_session else None
