"""
Sandbox and safety policies for desktop automation.

Enforces:
- Whitelist of allowed applications
- Maximum action limits per cycle
- No raw coordinate clicking
- All actions logged with screenshots
"""

import logging
from typing import List, Optional, Set
from pathlib import Path

from automation.actions import DesktopAction, ActionType


logger = logging.getLogger(__name__)


class AutomationPolicy:
    """
    Desktop automation safety policy.

    Enforces rules and limits to prevent runaway automation.
    """

    # Default whitelist of allowed applications
    DEFAULT_ALLOWED_APPS = {
        "code",  # VS Code
        "Code.exe",
        "notepad",
        "notepad.exe",
    }

    # Actions that are always safe
    SAFE_ACTIONS = {
        ActionType.SCREENSHOT,
        ActionType.ASSERT_WINDOW,
        ActionType.ASSERT_WORKSPACE,
    }

    # Maximum actions per cycle to prevent runaway
    MAX_ACTIONS_PER_CYCLE = 20

    def __init__(
        self,
        allowed_apps: Optional[Set[str]] = None,
        max_actions: int = MAX_ACTIONS_PER_CYCLE,
        allow_coordinate_clicks: bool = False,
        screenshot_all: bool = True
    ):
        """
        Initialize automation policy.

        Args:
            allowed_apps: Set of allowed application names
            max_actions: Maximum actions per cycle
            allow_coordinate_clicks: If True, allow raw coordinate clicks (unsafe)
            screenshot_all: If True, screenshot before/after each action
        """
        self.allowed_apps = allowed_apps or self.DEFAULT_ALLOWED_APPS.copy()
        self.max_actions = max_actions
        self.allow_coordinate_clicks = allow_coordinate_clicks
        self.screenshot_all = screenshot_all

        self.action_count = 0
        self.blocked_count = 0

        logger.info(f"AutomationPolicy initialized: "
                   f"max_actions={max_actions}, "
                   f"coordinate_clicks={allow_coordinate_clicks}, "
                   f"screenshot_all={screenshot_all}")

    def reset_cycle(self):
        """Reset counters for new cycle."""
        self.action_count = 0
        self.blocked_count = 0
        logger.debug("Policy counters reset for new cycle")

    def check_action(self, action: DesktopAction) -> tuple[bool, Optional[str]]:
        """
        Check if action is allowed by policy.

        Args:
            action: Action to check

        Returns:
            Tuple of (allowed: bool, reason: Optional[str])
        """
        # Check action limit
        if self.action_count >= self.max_actions:
            reason = f"Action limit exceeded ({self.max_actions} per cycle)"
            self.blocked_count += 1
            return False, reason

        # Always allow safe actions
        if action.action in self.SAFE_ACTIONS:
            self.action_count += 1
            return True, None

        # Check application whitelist for launch/focus
        if action.action == ActionType.LAUNCH:
            exe = action.params.get("exe", "")
            exe_name = Path(exe).name
            if exe_name not in self.allowed_apps and exe not in self.allowed_apps:
                reason = f"Application not in whitelist: {exe}"
                self.blocked_count += 1
                return False, reason

        # Block coordinate clicks unless explicitly allowed
        if not self.allow_coordinate_clicks:
            if "x" in action.params and "y" in action.params:
                # Has coordinates - this is a raw click, not semantic
                reason = "Raw coordinate clicking is disabled (use button labels instead)"
                self.blocked_count += 1
                return False, reason

        # Check button click whitelist (could be extended)
        if action.action == ActionType.CLICK_BUTTON:
            label = action.params.get("label", "")
            # Could add label whitelist here
            # For now, allow any labeled button (semantic action)
            pass

        self.action_count += 1
        return True, None

    def validate_action_sequence(self, actions: List[DesktopAction]) -> tuple[bool, List[str]]:
        """
        Validate a sequence of actions.

        Args:
            actions: List of actions to validate

        Returns:
            Tuple of (all_valid: bool, errors: List[str])
        """
        errors = []

        # Check total count
        if len(actions) > self.max_actions:
            errors.append(f"Action sequence exceeds limit: {len(actions)} > {self.max_actions}")

        # Check each action
        for i, action in enumerate(actions):
            try:
                action.validate()
            except ValueError as e:
                errors.append(f"Action {i}: {e}")

            allowed, reason = self.check_action(action)
            if not allowed:
                errors.append(f"Action {i} ({action.action.value}): {reason}")

        return len(errors) == 0, errors

    def add_allowed_app(self, app: str):
        """Add application to whitelist."""
        self.allowed_apps.add(app)
        logger.info(f"Added to whitelist: {app}")

    def remove_allowed_app(self, app: str):
        """Remove application from whitelist."""
        if app in self.allowed_apps:
            self.allowed_apps.remove(app)
            logger.info(f"Removed from whitelist: {app}")


# Global policy instance (can be overridden)
_global_policy: Optional[AutomationPolicy] = None


def get_policy() -> AutomationPolicy:
    """Get global automation policy."""
    global _global_policy
    if _global_policy is None:
        _global_policy = AutomationPolicy()
    return _global_policy


def set_policy(policy: AutomationPolicy):
    """Set global automation policy."""
    global _global_policy
    _global_policy = policy


def reset_policy():
    """Reset global policy to default."""
    global _global_policy
    _global_policy = AutomationPolicy()
