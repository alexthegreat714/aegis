"""
Action executor for Aegis.

Routes action plans to automation modules for execution.
"""

from typing import Dict, Any, Optional
from pathlib import Path

from core.action_planner import ActionPlan, ActionStep
from intents.intent_schema import IntentResult
from automation.desktop import DesktopAutomation
from automation.vscode import VSCodeAutomation
from automation.windows import WindowsAutomation
from aegis_logging.logger import AegisLogger


class ExecutionError(Exception):
    """Raised when action execution fails."""
    pass


class ActionExecutor:
    """
    Executes action plans by dispatching to automation modules.

    Day 2: All execution is stubbed with logging only.
    Day 3: Will implement actual pyautogui/pywinauto calls.
    """

    def __init__(self, logger: AegisLogger, settings: Dict[str, Any]):
        """
        Initialize action executor.

        Args:
            logger: Logging system
            settings: System settings
        """
        self.logger = logger
        self.settings = settings

        # Initialize automation modules
        self.desktop = DesktopAutomation(logger, settings)
        self.vscode = VSCodeAutomation(logger, settings, self.desktop)
        self.windows = WindowsAutomation(logger, settings)

    def execute_plan(self, plan: ActionPlan) -> IntentResult:
        """
        Execute an action plan.

        Args:
            plan: ActionPlan to execute

        Returns:
            IntentResult with execution status

        Raises:
            ExecutionError: If execution fails
        """
        self.logger.log_event(
            event_type="plan_execution_start",
            data={
                "intent": plan.intent.to_dict(),
                "steps_count": len(plan.steps)
            },
            status="info"
        )

        import time
        start_time = time.time()

        try:
            # Execute each step in order
            for step in plan.steps:
                self._execute_step(step)
                plan.completed_steps.append(step.step_id)

            # All steps completed successfully
            execution_time = (time.time() - start_time) * 1000  # ms

            result = IntentResult(
                intent=plan.intent,
                success=True,
                output=f"Completed {len(plan.steps)} steps",
                execution_time_ms=execution_time
            )

            self.logger.log_event(
                event_type="plan_execution_complete",
                data={
                    "intent_id": plan.intent.intent_id,
                    "steps_completed": len(plan.completed_steps),
                    "execution_time_ms": execution_time
                },
                status="success"
            )

            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000

            result = IntentResult(
                intent=plan.intent,
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )

            self.logger.log_event(
                event_type="plan_execution_failed",
                data={
                    "intent_id": plan.intent.intent_id,
                    "error": str(e),
                    "steps_completed": len(plan.completed_steps),
                    "steps_failed": len(plan.failed_steps)
                },
                status="error"
            )

            raise ExecutionError(f"Plan execution failed: {e}")

    def _execute_step(self, step: ActionStep) -> None:
        """
        Execute a single action step.

        Args:
            step: ActionStep to execute

        Raises:
            ExecutionError: If step execution fails
        """
        self.logger.log_event(
            event_type="step_execution_start",
            data={
                "step_id": step.step_id,
                "description": step.description,
                "executor": step.executor,
                "function": step.function
            },
            status="info"
        )

        # # EXEC_HOOK: This is where actual execution will happen on Day 3
        # Day 2: Just log what would be executed
        print(f"\n[Executor] Step {step.step_id}: {step.description}")
        print(f"[Executor] → Executor: {step.executor}")
        print(f"[Executor] → Function: {step.function}")
        print(f"[Executor] → Parameters: {step.parameters}")

        # Route to appropriate automation module
        try:
            if step.executor == "automation.desktop":
                self._execute_desktop_action(step)
            elif step.executor == "automation.vscode":
                self._execute_vscode_action(step)
            elif step.executor == "automation.windows":
                self._execute_windows_action(step)
            elif step.executor == "automation.filesystem":
                self._execute_filesystem_action(step)
            elif step.executor == "automation.generic":
                self._execute_generic_action(step)
            else:
                # Unknown executor - log warning but don't fail
                self.logger.log_event(
                    event_type="unknown_executor",
                    data={"executor": step.executor, "function": step.function},
                    status="warning"
                )
                print(f"[Executor] ⚠ Unknown executor: {step.executor}, skipping...")

            self.logger.log_event(
                event_type="step_execution_complete",
                data={"step_id": step.step_id},
                status="success"
            )

        except Exception as e:
            self.logger.log_event(
                event_type="step_execution_failed",
                data={"step_id": step.step_id, "error": str(e)},
                status="error"
            )
            raise ExecutionError(f"Step {step.step_id} failed: {e}")

    def _execute_desktop_action(self, step: ActionStep) -> None:
        """Execute desktop automation action."""
        # # EXEC_HOOK: Day 3 will call actual methods
        function = step.function
        params = step.parameters

        if function == "mouse_click":
            # self.desktop.mouse_click(params['x'], params['y'], params.get('button', 'left'))
            print(f"[Desktop] Would click at ({params.get('x')}, {params.get('y')})")

        elif function == "keyboard_type":
            # self.desktop.keyboard_type(params['text'])
            print(f"[Desktop] Would type: {params.get('text', '')[:50]}...")

        elif function == "screenshot":
            # path = self.desktop.screenshot(params.get('output_path'))
            print(f"[Desktop] Would take screenshot → {params.get('output_path', 'auto')}")

        else:
            print(f"[Desktop] Would execute: {function}({params})")

    def _execute_vscode_action(self, step: ActionStep) -> None:
        """Execute VS Code automation action."""
        # # EXEC_HOOK: Day 3 will call actual methods
        function = step.function
        params = step.parameters

        if function == "run_command":
            # self.vscode.run_command(params['command'])
            print(f"[VSCode] Would run command: {params.get('command')}")

        elif function == "open_file":
            # self.vscode.open_file(params['path'])
            print(f"[VSCode] Would open file: {params.get('path')}")

        else:
            print(f"[VSCode] Would execute: {function}({params})")

    def _execute_windows_action(self, step: ActionStep) -> None:
        """Execute Windows automation action."""
        # # EXEC_HOOK: Day 3 will call actual methods
        function = step.function
        params = step.parameters

        if function == "find_window":
            # window = self.windows.find_window(params['title'])
            print(f"[Windows] Would find window: {params.get('title')}")

        else:
            print(f"[Windows] Would execute: {function}({params})")

    def _execute_filesystem_action(self, step: ActionStep) -> None:
        """Execute filesystem action."""
        # # EXEC_HOOK: Day 3 will call actual methods
        function = step.function
        params = step.parameters

        if function == "create_backup":
            print(f"[Filesystem] Would create backup of: {params.get('path')}")

        elif function == "validate_path":
            print(f"[Filesystem] Would validate path: {params.get('path')}")

        elif function == "file_write":
            print(f"[Filesystem] Would write file: {params.get('path')}")

        elif function == "file_read":
            print(f"[Filesystem] Would read file: {params.get('path')}")

        else:
            print(f"[Filesystem] Would execute: {function}({params})")

    def _execute_generic_action(self, step: ActionStep) -> None:
        """Execute generic action."""
        # # EXEC_HOOK: Day 3 will call actual methods
        print(f"[Generic] Would execute: {step.function}({step.parameters})")

    def dry_run_plan(self, plan: ActionPlan) -> str:
        """
        Simulate plan execution without actually executing.

        Args:
            plan: ActionPlan to simulate

        Returns:
            Summary of what would be executed
        """
        lines = [
            f"DRY RUN: {plan.intent.action_type.value}",
            f"Intent: {plan.intent.rationale}",
            f"Steps: {len(plan.steps)}",
            ""
        ]

        for step in plan.steps:
            lines.append(f"  {step.step_id}. {step.description}")
            lines.append(f"     → {step.executor}.{step.function}({step.parameters})")

        return "\n".join(lines)
