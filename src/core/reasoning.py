"""
Dual-channel reasoning system for Aegis.

Separates internal reasoning (verbose, logged) from external intents (compact, structured).
"""

from typing import Dict, Any, List, Optional
import yaml
from datetime import datetime

from aegis_logging.logger import AegisLogger


class ReasoningChannel:
    """
    Manages dual-channel reasoning:
    - Internal channel: Full verbose reasoning (logged for Alex, never exposed to Claude)
    - External channel: Compact YAML intent packets (sent to Claude for execution)
    """

    def __init__(self, logger: AegisLogger):
        """
        Initialize reasoning channel.

        Args:
            logger: Logging system
        """
        self.logger = logger
        self.internal_reasoning_history: List[Dict[str, Any]] = []
        self.external_intent_history: List[Dict[str, Any]] = []

    def log_internal_reasoning(
        self,
        task: str,
        reasoning: str,
        model: str,
        observation: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log full internal reasoning (NEVER exposed to Claude).

        This is DeepCoder's verbose chain-of-thought.
        Only Alex can read this via logs.

        Args:
            task: Task description
            reasoning: Full verbose reasoning text
            model: Model used for reasoning
            observation: System observation data
            metadata: Additional metadata

        Returns:
            Reasoning ID for reference
        """
        reasoning_id = f"reasoning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        entry = {
            "reasoning_id": reasoning_id,
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "reasoning": reasoning,
            "model": model,
            "observation": observation,
            "metadata": metadata or {},
            "channel": "internal",
            "visibility": "alex_only"
        }

        # Store in internal history
        self.internal_reasoning_history.append(entry)

        # Log to JSONL/SQLite (Alex can query these)
        self.logger.log_event(
            event_type="internal_reasoning",
            data={
                "reasoning_id": reasoning_id,
                "task": task,
                "reasoning_length": len(reasoning),
                "model": model
            },
            status="info"
        )

        # Log full reasoning to LLM interaction table
        self.logger.log_llm_call(
            model=model,
            prompt=task,
            response=reasoning,
            tokens_used=0  # TODO: Parse from response
        )

        return reasoning_id

    def summarize_to_intent(self, reasoning: str, task: str) -> Optional[Dict[str, Any]]:
        """
        Convert verbose reasoning into compact YAML intent packet.

        This is what Claude receives - NOT the full reasoning.

        Args:
            reasoning: Full reasoning text
            task: Original task

        Returns:
            Intent packet dictionary or None if no action needed
        """
        # TODO: Use LLM to extract structured intent from reasoning
        # For now, create a basic intent structure

        intent = {
            "intent_id": f"intent_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "task": task,
            "intent_type": "query",  # query | modify_file | execute_command | approve_revision
            "risk_level": "low",  # low | medium | high
            "requires_approval": False,
            "requires_sandbox": False,
            "actions": [],
            "reasoning_summary": self._extract_summary(reasoning),
            "test_plan": [],
            "rollback_plan": None
        }

        return intent

    def _extract_summary(self, reasoning: str, max_length: int = 200) -> str:
        """
        Extract brief summary from verbose reasoning.

        Args:
            reasoning: Full reasoning text
            max_length: Maximum summary length

        Returns:
            Brief summary
        """
        # Simple extraction - take first paragraph or truncate
        lines = reasoning.split('\n')
        summary_lines = []
        total_length = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if total_length + len(line) > max_length:
                break

            summary_lines.append(line)
            total_length += len(line)

        summary = ' '.join(summary_lines)

        if len(summary) > max_length:
            summary = summary[:max_length - 3] + "..."

        return summary

    def log_external_intent(self, intent: Dict[str, Any]) -> str:
        """
        Log external intent packet (sent to Claude).

        Args:
            intent: Intent packet dictionary

        Returns:
            Intent ID
        """
        intent_id = intent.get("intent_id", f"intent_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        entry = {
            "intent_id": intent_id,
            "timestamp": datetime.now().isoformat(),
            "intent": intent,
            "channel": "external",
            "visibility": "claude_visible"
        }

        # Store in external history
        self.external_intent_history.append(entry)

        # Log to database
        self.logger.log_event(
            event_type="external_intent",
            data={
                "intent_id": intent_id,
                "intent_type": intent.get("intent_type"),
                "risk_level": intent.get("risk_level"),
                "requires_approval": intent.get("requires_approval"),
                "requires_sandbox": intent.get("requires_sandbox")
            },
            status="info"
        )

        return intent_id

    def format_intent_as_yaml(self, intent: Dict[str, Any]) -> str:
        """
        Format intent packet as YAML for Claude.

        Args:
            intent: Intent dictionary

        Returns:
            YAML string
        """
        return yaml.dump(intent, default_flow_style=False, sort_keys=False)

    def get_internal_reasoning(self, reasoning_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve internal reasoning by ID (Alex only).

        Args:
            reasoning_id: Reasoning ID

        Returns:
            Reasoning entry or None
        """
        for entry in self.internal_reasoning_history:
            if entry.get("reasoning_id") == reasoning_id:
                return entry
        return None

    def get_external_intent(self, intent_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve external intent by ID.

        Args:
            intent_id: Intent ID

        Returns:
            Intent entry or None
        """
        for entry in self.external_intent_history:
            if entry.get("intent_id") == intent_id:
                return entry
        return None

    def clear_history(self, channel: str = "both") -> None:
        """
        Clear reasoning history.

        Args:
            channel: Which channel to clear (internal | external | both)
        """
        if channel in ["internal", "both"]:
            self.internal_reasoning_history.clear()

        if channel in ["external", "both"]:
            self.external_intent_history.clear()

        self.logger.log_event(
            event_type="reasoning_history_cleared",
            data={"channel": channel},
            status="info"
        )

    def get_reasoning_stats(self) -> Dict[str, Any]:
        """
        Get statistics about reasoning channels.

        Returns:
            Statistics dictionary
        """
        return {
            "internal_count": len(self.internal_reasoning_history),
            "external_count": len(self.external_intent_history),
            "latest_internal": self.internal_reasoning_history[-1] if self.internal_reasoning_history else None,
            "latest_external": self.external_intent_history[-1] if self.external_intent_history else None
        }
