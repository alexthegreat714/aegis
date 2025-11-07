"""
Tasklist YAML parser for project task queues.

Parses structured task lists from YAML files for execution.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml


class TasklistParser:
    """
    Parser for tasklist.yaml files.

    Tasks are organized in YAML format with metadata and dependencies.
    """

    def __init__(self, tasklist_path: str = "config/tasklist.yaml"):
        """
        Initialize tasklist parser.

        Args:
            tasklist_path: Path to tasklist.yaml file
        """
        self.tasklist_path = Path(tasklist_path)
        self.tasks: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

    def load(self) -> bool:
        """
        Load tasklist from YAML file.

        Returns:
            True if loaded successfully
        """
        if not self.tasklist_path.exists():
            print(f"[Tasklist] File not found: {self.tasklist_path}")
            return False

        try:
            with open(self.tasklist_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                print(f"[Tasklist] Empty file: {self.tasklist_path}")
                return False

            # Parse metadata
            self.metadata = {
                "name": data.get("name", "Unnamed Project"),
                "description": data.get("description", ""),
                "version": data.get("version", "1.0"),
                "created": data.get("created", ""),
                "updated": data.get("updated", "")
            }

            # Parse tasks
            self.tasks = data.get("tasks", [])

            # Validate tasks
            for i, task in enumerate(self.tasks):
                if "id" not in task:
                    task["id"] = f"task_{i}"
                if "description" not in task:
                    print(f"[Tasklist] WARNING: Task {task['id']} has no description")

            print(f"[Tasklist] Loaded {len(self.tasks)} tasks from {self.tasklist_path}")
            return True

        except yaml.YAMLError as e:
            print(f"[Tasklist] YAML parse error: {e}")
            return False
        except Exception as e:
            print(f"[Tasklist] Failed to load tasklist: {e}")
            return False

    def get_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get tasks, optionally filtered by status.

        Args:
            status: Filter by status (pending/in_progress/completed/failed)

        Returns:
            List of task dictionaries
        """
        if status:
            return [t for t in self.tasks if t.get("status") == status]
        return self.tasks

    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """
        Get next pending task that has no unmet dependencies.

        Returns:
            Next task dictionary or None if no tasks available
        """
        pending = self.get_tasks(status="pending")

        for task in pending:
            # Check if all dependencies are completed
            deps = task.get("depends_on", [])

            if not deps:
                # No dependencies, task is ready
                return task

            # Check each dependency
            deps_met = True
            for dep_id in deps:
                dep_task = self.get_task_by_id(dep_id)
                if not dep_task or dep_task.get("status") != "completed":
                    deps_met = False
                    break

            if deps_met:
                return task

        return None

    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task dictionary or None if not found
        """
        for task in self.tasks:
            if task.get("id") == task_id:
                return task
        return None

    def update_task_status(self, task_id: str, status: str) -> bool:
        """
        Update task status.

        Args:
            task_id: Task identifier
            status: New status (pending/in_progress/completed/failed)

        Returns:
            True if updated successfully
        """
        task = self.get_task_by_id(task_id)
        if task:
            task["status"] = status
            return True
        return False

    def get_project_summary(self) -> Dict[str, Any]:
        """
        Get project summary with task statistics.

        Returns:
            Summary dictionary
        """
        total = len(self.tasks)
        pending = len(self.get_tasks(status="pending"))
        in_progress = len(self.get_tasks(status="in_progress"))
        completed = len(self.get_tasks(status="completed"))
        failed = len(self.get_tasks(status="failed"))

        return {
            "metadata": self.metadata,
            "total_tasks": total,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "failed": failed,
            "progress_percent": (completed / total * 100) if total > 0 else 0
        }

    def display_summary(self) -> None:
        """Display project summary to console."""
        summary = self.get_project_summary()

        print(f"\n{'=' * 60}")
        print(f"Project: {summary['metadata']['name']}")
        print(f"Description: {summary['metadata']['description']}")
        print(f"{'=' * 60}")
        print(f"Total Tasks: {summary['total_tasks']}")
        print(f"  Pending:     {summary['pending']}")
        print(f"  In Progress: {summary['in_progress']}")
        print(f"  Completed:   {summary['completed']}")
        print(f"  Failed:      {summary['failed']}")
        print(f"Progress: {summary['progress_percent']:.1f}%")
        print(f"{'=' * 60}\n")
