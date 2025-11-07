"""
Digest report generation for Aegis agent.

Day 4: Summarizes multi-cycle execution results.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
import json


@dataclass
class CycleDigest:
    """
    Summary of agent execution cycles.

    Day 4: Tracks intents, successes, failures, policy decisions, and timing.
    """

    start_time: str
    end_time: Optional[str] = None
    total_cycles: int = 0
    intents_executed: int = 0
    intents_succeeded: int = 0
    intents_failed: int = 0
    policy_allows: int = 0
    policy_denies: int = 0
    policy_requires_approval: int = 0
    execution_times_ms: List[float] = field(default_factory=list)
    intent_types_executed: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to JSON-serializable dictionary.

        Returns:
            Dictionary representation
        """
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """
        Convert to JSON string.

        Args:
            indent: Indentation level

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        """
        Generate pretty markdown summary.

        Returns:
            Markdown-formatted digest
        """
        lines = [
            "# Aegis Cycle Digest",
            "",
            f"**Start Time**: {self.start_time}",
            f"**End Time**: {self.end_time or 'Running...'}",
            "",
            "## Execution Summary",
            "",
            f"- **Total Cycles**: {self.total_cycles}",
            f"- **Intents Executed**: {self.intents_executed}",
            f"- **Success Rate**: {self._success_rate():.1f}%",
            "",
            "### Results",
            "",
            f"- ✅ **Succeeded**: {self.intents_succeeded}",
            f"- ❌ **Failed**: {self.intents_failed}",
            "",
            "### Policy Decisions",
            "",
            f"- ✅ **Allowed**: {self.policy_allows}",
            f"- 🚫 **Denied**: {self.policy_denies}",
            f"- ⏸️  **Requires Approval**: {self.policy_requires_approval}",
            "",
            "### Performance",
            "",
            f"- **Total Execution Time**: {self._total_execution_time():.2f}ms",
            f"- **Average Execution Time**: {self._avg_execution_time():.2f}ms",
            f"- **Min Execution Time**: {self._min_execution_time():.2f}ms",
            f"- **Max Execution Time**: {self._max_execution_time():.2f}ms",
            "",
        ]

        # Add intent types breakdown
        if self.intent_types_executed:
            lines.extend([
                "### Intent Types Executed",
                "",
            ])
            for intent_type, count in sorted(
                self.intent_types_executed.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                lines.append(f"- **{intent_type}**: {count}")
            lines.append("")

        # Add errors if any
        if self.errors:
            lines.extend([
                "### Errors",
                "",
            ])
            for error in self.errors[:10]:  # Show first 10 errors
                lines.append(f"- {error}")
            if len(self.errors) > 10:
                lines.append(f"- ... and {len(self.errors) - 10} more")
            lines.append("")

        return "\n".join(lines)

    def _success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.intents_executed == 0:
            return 0.0
        return (self.intents_succeeded / self.intents_executed) * 100

    def _total_execution_time(self) -> float:
        """Calculate total execution time."""
        return sum(self.execution_times_ms)

    def _avg_execution_time(self) -> float:
        """Calculate average execution time."""
        if not self.execution_times_ms:
            return 0.0
        return sum(self.execution_times_ms) / len(self.execution_times_ms)

    def _min_execution_time(self) -> float:
        """Calculate minimum execution time."""
        if not self.execution_times_ms:
            return 0.0
        return min(self.execution_times_ms)

    def _max_execution_time(self) -> float:
        """Calculate maximum execution time."""
        if not self.execution_times_ms:
            return 0.0
        return max(self.execution_times_ms)


class DigestGenerator:
    """
    Generates execution digest reports.

    Day 4: Tracks agent activity across cycles and produces summaries.
    """

    def __init__(self):
        """Initialize digest generator."""
        self.current_digest: Optional[CycleDigest] = None
        self.digest_history: List[CycleDigest] = []

    def start_digest(self) -> CycleDigest:
        """
        Start a new digest tracking session.

        Returns:
            New CycleDigest instance
        """
        self.current_digest = CycleDigest(
            start_time=datetime.now().isoformat()
        )
        return self.current_digest

    def record_cycle(self) -> None:
        """Record completion of one cycle."""
        if self.current_digest:
            self.current_digest.total_cycles += 1

    def record_intent_executed(
        self,
        intent_type: str,
        success: bool,
        execution_time_ms: float,
        error: Optional[str] = None
    ) -> None:
        """
        Record an executed intent.

        Args:
            intent_type: Type of intent executed
            success: Whether execution succeeded
            execution_time_ms: Execution time in milliseconds
            error: Error message if failed
        """
        if not self.current_digest:
            return

        self.current_digest.intents_executed += 1

        if success:
            self.current_digest.intents_succeeded += 1
        else:
            self.current_digest.intents_failed += 1
            if error:
                self.current_digest.errors.append(error)

        self.current_digest.execution_times_ms.append(execution_time_ms)

        # Track intent type counts
        if intent_type not in self.current_digest.intent_types_executed:
            self.current_digest.intent_types_executed[intent_type] = 0
        self.current_digest.intent_types_executed[intent_type] += 1

    def record_policy_decision(
        self,
        allowed: bool,
        requires_approval: bool = False
    ) -> None:
        """
        Record a policy decision.

        Args:
            allowed: Whether intent was allowed
            requires_approval: Whether approval is required
        """
        if not self.current_digest:
            return

        if requires_approval:
            self.current_digest.policy_requires_approval += 1
        elif allowed:
            self.current_digest.policy_allows += 1
        else:
            self.current_digest.policy_denies += 1

    def end_digest(self) -> CycleDigest:
        """
        End current digest session.

        Returns:
            Completed CycleDigest
        """
        if not self.current_digest:
            raise RuntimeError("No active digest to end")

        self.current_digest.end_time = datetime.now().isoformat()
        self.digest_history.append(self.current_digest)

        completed_digest = self.current_digest
        self.current_digest = None

        return completed_digest

    def get_current_digest(self) -> Optional[CycleDigest]:
        """
        Get current digest without ending it.

        Returns:
            Current CycleDigest or None
        """
        return self.current_digest

    def get_digest_history(self) -> List[CycleDigest]:
        """
        Get all completed digests.

        Returns:
            List of completed CycleDigest objects
        """
        return self.digest_history

    def clear_history(self) -> None:
        """Clear digest history."""
        self.digest_history.clear()
