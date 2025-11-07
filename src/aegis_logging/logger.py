"""
Aegis dual logging system.

Logs to both JSONL files and SQLite database for maximum flexibility.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json

from .schema import DatabaseLogger


class JSONLLogger:
    """JSONL file logger."""

    def __init__(self, log_dir: str):
        """
        Initialize JSONL logger.

        Args:
            log_dir: Directory for log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create daily log file
        today = datetime.now().strftime("%Y%m%d")
        self.log_file = self.log_dir / f"aegis_{today}.jsonl"

    def write(self, entry: Dict[str, Any]) -> None:
        """
        Write entry to JSONL file.

        Args:
            entry: Log entry dictionary
        """
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')


class AegisLogger:
    """
    Dual logging system for Aegis.

    Logs all events to both JSONL and SQLite for auditing.
    """

    def __init__(self, log_dir: str, db_path: str, settings: Dict[str, Any]):
        """
        Initialize logger.

        Args:
            log_dir: Directory for JSONL logs
            db_path: Path to SQLite database
            settings: Logging settings
        """
        self.settings = settings
        self.jsonl_enabled = settings.get("logging", {}).get("jsonl_enabled", True)
        self.sqlite_enabled = settings.get("logging", {}).get("sqlite_enabled", True)

        if self.jsonl_enabled:
            self.jsonl_logger = JSONLLogger(log_dir)

        if self.sqlite_enabled:
            self.db_logger = DatabaseLogger(db_path)

        print(f"[Logger] Initialized (JSONL: {self.jsonl_enabled}, SQLite: {self.sqlite_enabled})")

    def log_event(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        status: str = "info"
    ) -> None:
        """
        Log a general event.

        Args:
            event_type: Type of event
            data: Event data dictionary
            status: Event status (info, success, error, warning)
        """
        timestamp = datetime.now().isoformat()

        entry = {
            "timestamp": timestamp,
            "type": "event",
            "event_type": event_type,
            "status": status,
            "data": data or {}
        }

        if self.jsonl_enabled:
            self.jsonl_logger.write(entry)

        if self.sqlite_enabled:
            self.db_logger.log_event(
                timestamp=timestamp,
                event_type=event_type,
                status=status,
                data=json.dumps(data) if data else None
            )

    def log_action(
        self,
        action_type: str,
        parameters: Dict[str, Any],
        status: str,
        category: str = "unknown",
        result: Optional[Any] = None,
        error: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        intent_id: Optional[str] = None
    ) -> None:
        """
        Log an action execution.

        Args:
            action_type: Type of action
            parameters: Action parameters
            status: Action status (pending, success, failed)
            category: Action category
            result: Action result
            error: Error message if failed
            execution_time_ms: Execution time
            intent_id: Associated intent ID
        """
        timestamp = datetime.now().isoformat()

        entry = {
            "timestamp": timestamp,
            "type": "action",
            "action_type": action_type,
            "category": category,
            "parameters": parameters,
            "status": status,
            "result": result,
            "error": error,
            "execution_time_ms": execution_time_ms,
            "intent_id": intent_id
        }

        if self.jsonl_enabled:
            self.jsonl_logger.write(entry)

        if self.sqlite_enabled:
            self.db_logger.log_action(
                timestamp=timestamp,
                action_type=action_type,
                category=category,
                parameters=json.dumps(parameters),
                status=status,
                result=json.dumps(result) if result else None,
                error=error,
                execution_time_ms=execution_time_ms,
                intent_id=intent_id
            )

    def log_llm_call(
        self,
        model: str,
        prompt: str,
        response: str,
        tokens_used: Optional[int] = None,
        duration_ms: Optional[float] = None
    ) -> None:
        """
        Log LLM interaction.

        Args:
            model: Model name
            prompt: Input prompt
            response: LLM response
            tokens_used: Token count
            duration_ms: Request duration
        """
        timestamp = datetime.now().isoformat()

        entry = {
            "timestamp": timestamp,
            "type": "llm_call",
            "model": model,
            "prompt": prompt,
            "response": response,
            "tokens_used": tokens_used,
            "duration_ms": duration_ms
        }

        if self.jsonl_enabled:
            self.jsonl_logger.write(entry)

        if self.sqlite_enabled:
            self.db_logger.log_llm_interaction(
                timestamp=timestamp,
                model=model,
                prompt=prompt,
                response=response,
                tokens_used=tokens_used,
                duration_ms=duration_ms
            )

    def log_policy_decision(
        self,
        intent_id: str,
        action_type: str,
        decision: str,
        reason: str,
        requires_approval: bool = False
    ) -> None:
        """
        Log policy decision.

        Args:
            intent_id: Intent ID
            action_type: Action type
            decision: Decision result
            reason: Decision reason
            requires_approval: Whether approval required
        """
        timestamp = datetime.now().isoformat()

        entry = {
            "timestamp": timestamp,
            "type": "policy_decision",
            "intent_id": intent_id,
            "action_type": action_type,
            "decision": decision,
            "reason": reason,
            "requires_approval": requires_approval
        }

        if self.jsonl_enabled:
            self.jsonl_logger.write(entry)

        if self.sqlite_enabled:
            self.db_logger.log_policy_decision(
                timestamp=timestamp,
                intent_id=intent_id,
                action_type=action_type,
                decision=decision,
                reason=reason,
                requires_approval=requires_approval
            )
