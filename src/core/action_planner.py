"""
Action planning system.

Translates validated intents into executable action plans.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from intents.intent_schema import Intent
from aegis_logging.logger import AegisLogger


@dataclass
class ActionStep:
    """Single executable step in an action plan."""

    step_id: int
    description: str
    executor: str  # Module that will execute this (e.g., "automation.desktop")
    function: str  # Function to call
    parameters: Dict[str, Any]
    requires_screenshot: bool = False


class ActionPlan:
    """Executable action plan."""

    def __init__(self, intent: Intent, steps: List[ActionStep]):
        """
        Initialize action plan.

        Args:
            intent: Original intent
            steps: List of executable steps
        """
        self.intent = intent
        self.steps = steps
        self.completed_steps: List[int] = []
        self.failed_steps: List[int] = []

    def is_complete(self) -> bool:
        """Check if all steps are completed."""
        return len(self.completed_steps) == len(self.steps)

    def has_failures(self) -> bool:
        """Check if any steps failed."""
        return len(self.failed_steps) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "intent": self.intent.to_dict(),
            "steps": [
                {
                    "step_id": step.step_id,
                    "description": step.description,
                    "executor": step.executor,
                    "function": step.function,
                    "parameters": step.parameters
                }
                for step in self.steps
            ],
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps
        }


class ActionPlanner:
    """
    Translates intents into executable action plans.

    Layer between policy-validated intents and automation execution.
    """

    def __init__(self, logger: AegisLogger, settings: Dict[str, Any]):
        """
        Initialize action planner.

        Args:
            logger: Logging system
            settings: System settings
        """
        self.logger = logger
        self.settings = settings

    def plan(self, intent: Intent) -> ActionPlan:
        """
        Create an executable action plan from an intent.

        Args:
            intent: Validated intent

        Returns:
            ActionPlan with concrete steps
        """
        self.logger.log_event(
            event_type="action_plan_created",
            data={"intent": intent.to_dict()},
            status="info"
        )

        # Route to appropriate planner based on intent category
        if intent.category == "desktop":
            return self._plan_desktop_action(intent)
        elif intent.category == "vscode":
            return self._plan_vscode_action(intent)
        elif intent.category == "filesystem":
            return self._plan_filesystem_action(intent)
        elif intent.category == "system":
            return self._plan_system_action(intent)
        elif intent.category == "meta":
            return self._plan_meta_action(intent)
        else:
            # Default: create simple single-step plan
            return self._create_simple_plan(intent)

    def _plan_desktop_action(self, intent: Intent) -> ActionPlan:
        """
        Plan desktop automation action.

        Args:
            intent: Desktop intent

        Returns:
            ActionPlan
        """
        from intents.intent_types import IntentType

        steps = []
        action_type = intent.action_type

        # Special handling for window operations
        if action_type in [IntentType.WINDOW_FOCUS, IntentType.WINDOW_CLOSE,
                          IntentType.WINDOW_MINIMIZE, IntentType.WINDOW_MAXIMIZE]:
            # Add window finding step if title provided
            if "title" in intent.parameters:
                steps.append(ActionStep(
                    step_id=len(steps) + 1,
                    description=f"Find window: {intent.parameters['title']}",
                    executor="automation.windows",
                    function="find_window",
                    parameters={"title": intent.parameters["title"]}
                ))

        # Special handling for mouse click - may need screenshot first
        if action_type == IntentType.MOUSE_CLICK and intent.parameters.get("requires_screenshot"):
            steps.append(ActionStep(
                step_id=len(steps) + 1,
                description="Capture screenshot for target verification",
                executor="automation.desktop",
                function="screenshot",
                parameters={},
                requires_screenshot=True
            ))

        # Add main action step
        steps.append(ActionStep(
            step_id=len(steps) + 1,
            description=f"Execute {intent.action_type.value}",
            executor="automation.desktop",
            function=intent.action_type.value,
            parameters=intent.parameters
        ))

        return ActionPlan(intent=intent, steps=steps)

    def _plan_vscode_action(self, intent: Intent) -> ActionPlan:
        """
        Plan VS Code action.

        Args:
            intent: VS Code intent

        Returns:
            ActionPlan
        """
        # TODO: Implement VS Code action planning
        # Example: run_command -> focus vscode, open terminal, type command, press enter

        steps = [
            ActionStep(
                step_id=1,
                description=f"Execute VS Code action: {intent.action_type.value}",
                executor="automation.vscode",
                function=intent.action_type.value,
                parameters=intent.parameters
            )
        ]

        return ActionPlan(intent=intent, steps=steps)

    def _plan_filesystem_action(self, intent: Intent) -> ActionPlan:
        """
        Plan filesystem action.

        Args:
            intent: Filesystem intent

        Returns:
            ActionPlan
        """
        from intents.intent_types import IntentType

        steps = []
        action_type = intent.action_type

        # For write/delete/modify operations, add backup step
        if action_type in [IntentType.FILE_WRITE, IntentType.FILE_DELETE,
                          IntentType.DIRECTORY_DELETE]:
            target_path = intent.parameters.get("path") or intent.parameters.get("target")
            if target_path:
                steps.append(ActionStep(
                    step_id=len(steps) + 1,
                    description=f"Create backup of: {target_path}",
                    executor="automation.filesystem",
                    function="create_backup",
                    parameters={"path": target_path}
                ))

        # Add path validation step
        target_path = intent.parameters.get("path") or intent.parameters.get("target")
        if target_path:
            steps.append(ActionStep(
                step_id=len(steps) + 1,
                description=f"Validate path: {target_path}",
                executor="automation.filesystem",
                function="validate_path",
                parameters={"path": target_path}
            ))

        # Add main filesystem operation
        steps.append(ActionStep(
            step_id=len(steps) + 1,
            description=f"Execute filesystem action: {intent.action_type.value}",
            executor="automation.filesystem",
            function=intent.action_type.value,
            parameters=intent.parameters
        ))

        # For write operations, add verification step
        if action_type in [IntentType.FILE_WRITE, IntentType.DIRECTORY_CREATE]:
            steps.append(ActionStep(
                step_id=len(steps) + 1,
                description="Verify operation success",
                executor="automation.filesystem",
                function="verify_operation",
                parameters={"operation": intent.action_type.value, **intent.parameters}
            ))

        return ActionPlan(intent=intent, steps=steps)

    def _plan_system_action(self, intent: Intent) -> ActionPlan:
        """
        Plan system action.

        Args:
            intent: System intent

        Returns:
            ActionPlan
        """
        # TODO: Implement system action planning
        # Example: process_kill -> verify process, log, terminate, verify termination

        steps = [
            ActionStep(
                step_id=1,
                description=f"Execute system action: {intent.action_type.value}",
                executor="automation.windows",
                function=intent.action_type.value,
                parameters=intent.parameters
            )
        ]

        return ActionPlan(intent=intent, steps=steps)

    def _plan_meta_action(self, intent: Intent) -> ActionPlan:
        """
        Plan meta action (control Aegis itself).

        Args:
            intent: Meta intent

        Returns:
            ActionPlan
        """
        steps = [
            ActionStep(
                step_id=1,
                description=f"Execute meta action: {intent.action_type.value}",
                executor="core.control_loop",
                function=intent.action_type.value,
                parameters=intent.parameters
            )
        ]

        return ActionPlan(intent=intent, steps=steps)

    def _create_simple_plan(self, intent: Intent) -> ActionPlan:
        """
        Create a simple single-step action plan.

        Args:
            intent: Intent to plan

        Returns:
            ActionPlan
        """
        steps = [
            ActionStep(
                step_id=1,
                description=f"Execute {intent.action_type.value}",
                executor="automation.generic",
                function=intent.action_type.value,
                parameters=intent.parameters
            )
        ]

        return ActionPlan(intent=intent, steps=steps)

    def validate_plan(self, plan: ActionPlan) -> bool:
        """
        Validate that a plan is executable.

        Args:
            plan: ActionPlan to validate

        Returns:
            True if plan is valid
        """
        # Check that plan has at least one step
        if not plan.steps:
            self.logger.log_event(
                event_type="plan_validation_failed",
                data={"reason": "Plan has no steps"},
                status="error"
            )
            return False

        # Check that all steps have required fields
        for step in plan.steps:
            if not step.executor or not step.function:
                self.logger.log_event(
                    event_type="plan_validation_failed",
                    data={
                        "reason": f"Step {step.step_id} missing executor or function",
                        "step": step.description
                    },
                    status="error"
                )
                return False

            # Check that required parameters are present
            if not isinstance(step.parameters, dict):
                self.logger.log_event(
                    event_type="plan_validation_failed",
                    data={
                        "reason": f"Step {step.step_id} has invalid parameters",
                        "step": step.description
                    },
                    status="error"
                )
                return False

        self.logger.log_event(
            event_type="plan_validated",
            data={"steps_count": len(plan.steps)},
            status="success"
        )

        return True
