"""
Project queue executor for automated task execution.

Executes tasks from tasklist.yaml in dependency order (read-only for now).
"""

from typing import Dict, Any, Optional, List
from pathlib import Path

from aegis_logging.logger import AegisLogger
from clients.owui_client import OWUIClient
from utils.tasklist_parser import TasklistParser


class QueueExecutor:
    """
    Executes tasks from project queue.

    Reads tasklist.yaml and executes tasks in dependency order.
    """

    def __init__(
        self,
        logger: AegisLogger,
        owui_client: OWUIClient,
        tasklist_path: str = "config/tasklist.yaml"
    ):
        """
        Initialize queue executor.

        Args:
            logger: Logging system
            owui_client: OpenWebUI API client
            tasklist_path: Path to tasklist.yaml
        """
        self.logger = logger
        self.owui_client = owui_client
        self.parser = TasklistParser(tasklist_path)
        self.dry_run = True  # Read-only mode for now

    def load_queue(self) -> bool:
        """
        Load task queue from file.

        Returns:
            True if loaded successfully
        """
        return self.parser.load()

    def display_queue(self) -> None:
        """Display current task queue status."""
        self.parser.display_summary()

        print("\nTask Queue:")
        print("-" * 60)

        tasks = self.parser.get_tasks()
        for task in tasks:
            status_icon = self._get_status_icon(task.get("status", "pending"))
            task_id = task.get("id", "unknown")
            description = task.get("description", "No description")
            priority = task.get("priority", "medium")
            risk = task.get("risk", "low")

            print(f"{status_icon} [{task_id}] {description}")
            print(f"   Priority: {priority} | Risk: {risk}")

            deps = task.get("depends_on", [])
            if deps:
                print(f"   Depends on: {', '.join(deps)}")

            print()

    def _get_status_icon(self, status: str) -> str:
        """Get icon for task status."""
        icons = {
            "pending": "[PENDING]",
            "in_progress": "[WORKING]",
            "completed": "[DONE]",
            "failed": "[FAILED]"
        }
        return icons.get(status, "[?]")

    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """
        Get next executable task.

        Returns:
            Next task or None if no tasks available
        """
        return self.parser.get_next_task()

    def execute_next(self, verbose: bool = True) -> bool:
        """
        Execute next available task (READ-ONLY).

        Args:
            verbose: Print verbose output

        Returns:
            True if task was executed
        """
        if self.dry_run:
            print("[Queue] Running in READ-ONLY mode (dry_run=True)")
            print("[Queue] No actions will be executed, only planning")
            print()

        next_task = self.get_next_task()

        if not next_task:
            if verbose:
                print("[Queue] No tasks available to execute")
                print("[Queue] All pending tasks have unmet dependencies")
            return False

        task_id = next_task.get("id", "unknown")
        description = next_task.get("description", "")
        priority = next_task.get("priority", "medium")
        risk = next_task.get("risk", "low")

        if verbose:
            print(f"\n{'=' * 60}")
            print(f"Next Task: {task_id}")
            print(f"Description: {description}")
            print(f"Priority: {priority} | Risk: {risk}")
            print(f"{'=' * 60}\n")

        if self.dry_run:
            print(f"[Queue] DRY RUN - Would execute task: {task_id}")
            print(f"[Queue] Task will remain in 'pending' status")
            return True

        # TODO: Actual execution when dry_run is disabled
        # This would integrate with control_loop to execute the task

        return True

    def execute_all(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Execute all available tasks in dependency order (READ-ONLY).

        Args:
            verbose: Print verbose output

        Returns:
            Execution summary
        """
        executed_count = 0
        failed_count = 0

        print(f"\n{'=' * 60}")
        print("Starting Queue Execution (READ-ONLY)")
        print(f"{'=' * 60}\n")

        while True:
            next_task = self.get_next_task()

            if not next_task:
                break

            try:
                if self.execute_next(verbose=verbose):
                    executed_count += 1
                else:
                    break
            except Exception as e:
                if verbose:
                    print(f"[Queue] ERROR executing task: {e}")
                failed_count += 1
                break

        summary = {
            "executed": executed_count,
            "failed": failed_count,
            "total": len(self.parser.get_tasks()),
            "pending": len(self.parser.get_tasks(status="pending"))
        }

        if verbose:
            print(f"\n{'=' * 60}")
            print("Queue Execution Complete")
            print(f"{'=' * 60}")
            print(f"Executed: {summary['executed']}")
            print(f"Failed: {summary['failed']}")
            print(f"Remaining: {summary['pending']}")
            print(f"{'=' * 60}\n")

        return summary

    def query_task_reasoning(self, task: Dict[str, Any]) -> Optional[str]:
        """
        Query LLM for reasoning about task execution.

        Args:
            task: Task dictionary

        Returns:
            LLM reasoning response
        """
        description = task.get("description", "")
        notes = task.get("notes", "")
        risk = task.get("risk", "low")

        prompt = (
            f"Task: {description}\n\n"
            f"Notes: {notes}\n\n"
            f"Risk Level: {risk}\n\n"
            f"Please provide:\n"
            f"1. Implementation approach\n"
            f"2. Potential risks\n"
            f"3. Testing strategy\n"
            f"4. Rollback plan"
        )

        try:
            response = self.owui_client.simple_prompt(prompt)
            return response
        except Exception as e:
            print(f"[Queue] Failed to get reasoning: {e}")
            return None
