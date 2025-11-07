"""
Intent schema definitions.

Structured representation of agent intents.

Example Intent Payloads:

1. Open Application:
{
    "intent": "open_app",
    "target": "notepad",
    "args": {}
}

2. Type Text:
{
    "intent": "type_text",
    "target": "Hello, world!",
    "args": {"delay_ms": 50}
}

3. Click On Element:
{
    "intent": "click_on",
    "target": "submit button",
    "args": {"button": "left"}
}

4. Full Intent Format:
{
    "action_type": "mouse_click",
    "parameters": {"x": 100, "y": 200},
    "rationale": "Click on button",
    "confidence": 0.95
}

5. Screenshot:
{
    "intent": "screenshot",
    "target": "output.png",
    "args": {}
}

6. Close Window:
{
    "intent": "close_window",
    "target": "Notepad",
    "args": {}
}
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from intents.intent_types import IntentType, IntentCategory


@dataclass
class Intent:
    """
    Structured representation of an agent intent.

    Intents are the formalized actions that Aegis proposes,
    which are then validated against policy before execution.
    """

    action_type: IntentType
    parameters: Dict[str, Any] = field(default_factory=dict)
    rationale: Optional[str] = None  # Why is this action being taken?
    confidence: float = 1.0  # LLM confidence in this action (0-1)
    intent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def category(self) -> str:
        """Get the category of this intent."""
        return IntentType.get_category(self.action_type).value

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert intent to dictionary for logging.

        Returns:
            Dictionary representation
        """
        return {
            "intent_id": self.intent_id,
            "timestamp": self.timestamp,
            "action_type": self.action_type.value,
            "category": self.category,
            "parameters": self.parameters,
            "rationale": self.rationale,
            "confidence": self.confidence
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Intent":
        """
        Create Intent from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Intent instance
        """
        return cls(
            action_type=IntentType(data["action_type"]),
            parameters=data.get("parameters", {}),
            rationale=data.get("rationale"),
            confidence=data.get("confidence", 1.0),
            intent_id=data.get("intent_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", datetime.now().isoformat())
        )

    def __repr__(self) -> str:
        """String representation."""
        return f"Intent({self.action_type.value}, params={self.parameters})"


@dataclass
class IntentResult:
    """
    Result of an executed intent.

    Captures success/failure and any output.
    """

    intent: Intent
    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for logging.

        Returns:
            Dictionary representation
        """
        return {
            "intent": self.intent.to_dict(),
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp
        }
