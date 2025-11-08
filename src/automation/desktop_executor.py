"""
Desktop action executor.

Dispatches desktop actions to appropriate backends with
safety checks, logging, and screenshot capture.
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from automation.actions import DesktopAction, ActionType
from automation.sandbox import AutomationPolicy, get_policy
from automation.workspace_guard import WorkspaceGuard
from automation.backends.ui_automation import UIAutomationBackend
from automation.backends.pyautogui_fallback import PyAutoGUIFallback


logger = logging.getLogger(__name__)


class DesktopExecutor:
    """
    Executes desktop actions with safety guards and logging.

    Coordinates between UIA backend, pyautogui fallback, and workspace validation.
    """

    def __init__(
        self,
        repo_root: Path,
        policy: Optional[AutomationPolicy] = None,
        dry_run: bool = False,
        screenshot_dir: Optional[Path] = None
    ):
        """
        Initialize desktop executor.

        Args:
            repo_root: Repository root path
            policy: Automation safety policy
            dry_run: If True, log actions without executing
            screenshot_dir: Directory for screenshots
        """
        self.repo_root = Path(repo_root)
        self.policy = policy or get_policy()
        self.dry_run = dry_run

        # Screenshot directory
        if screenshot_dir:
            self.screenshot_dir = Path(screenshot_dir)
        else:
            self.screenshot_dir = self.repo_root / "logs" / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Initialize backends
        try:
            # Enable OCR for button detection
            self.uia_backend = UIAutomationBackend(
                dry_run=dry_run,
                ocr_enabled=True,
                ocr_confidence_threshold=0.80
            )
        except Exception as e:
            logger.warning(f"UIA backend not available: {e}")
            self.uia_backend = None

        try:
            self.fallback_backend = PyAutoGUIFallback(dry_run=dry_run)
        except Exception as e:
            logger.warning(f"Fallback backend not available: {e}")
            self.fallback_backend = None

        # Initialize workspace guard
        self.workspace_guard = WorkspaceGuard(expected_repo=self.repo_root)

        # Execution state
        self.action_count = 0
        self.screenshot_count = 0

        logger.info(f"DesktopExecutor initialized (dry_run={dry_run})")
        logger.info(f"  Repository: {self.repo_root}")
        logger.info(f"  UIA backend: {'available' if self.uia_backend else 'unavailable'}")
        logger.info(f"  Fallback backend: {'available' if self.fallback_backend else 'unavailable'}")

    def execute(self, action: DesktopAction) -> Dict[str, Any]:
        """
        Execute a single desktop action.

        Args:
            action: Action to execute

        Returns:
            Execution result dictionary
        """
        # Check policy
        allowed, reason = self.policy.check_action(action)
        if not allowed:
            logger.error(f"Action blocked by policy: {reason}")
            return {
                "success": False,
                "error": f"Policy violation: {reason}",
                "action": action.to_dict()
            }

        # Validate action
        try:
            action.validate()
        except ValueError as e:
            logger.error(f"Action validation failed: {e}")
            return {
                "success": False,
                "error": f"Validation error: {e}",
                "action": action.to_dict()
            }

        # Take pre-action screenshot if enabled
        pre_screenshot = None
        if self.policy.screenshot_all and not self.dry_run:
            pre_screenshot = self._take_screenshot(f"pre_{action.action.value}")

        # Execute action
        start_time = time.time()
        result = self._dispatch_action(action)
        duration = time.time() - start_time

        # Take post-action screenshot if enabled
        post_screenshot = None
        if self.policy.screenshot_all and result.get("success") and not self.dry_run:
            post_screenshot = self._take_screenshot(f"post_{action.action.value}")

        # Build result
        execution_result = {
            "success": result.get("success", False),
            "action": action.to_dict(),
            "duration": duration,
            "pre_screenshot": pre_screenshot,
            "post_screenshot": post_screenshot,
            "error": result.get("error"),
            "details": result.get("details", {})
        }

        self.action_count += 1
        logger.info(f"Action #{self.action_count} completed: "
                   f"{action.action.value} - "
                   f"{'SUCCESS' if result.get('success') else 'FAILED'}")

        return execution_result

    def execute_sequence(self, actions: List[DesktopAction]) -> List[Dict[str, Any]]:
        """
        Execute a sequence of actions.

        Args:
            actions: List of actions to execute

        Returns:
            List of execution results
        """
        # Validate sequence
        valid, errors = self.policy.validate_action_sequence(actions)
        if not valid:
            logger.error(f"Action sequence validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            raise ValueError(f"Invalid action sequence: {errors}")

        logger.info(f"Executing action sequence ({len(actions)} actions)")

        results = []
        for i, action in enumerate(actions):
            logger.info(f"Action {i+1}/{len(actions)}: {action.action.value}")

            result = self.execute(action)
            results.append(result)

            # Stop on failure (unless retry logic added)
            if not result["success"]:
                logger.error(f"Action failed - stopping sequence")
                break

        return results

    def _dispatch_action(self, action: DesktopAction) -> Dict[str, Any]:
        """
        Dispatch action to appropriate backend.

        Args:
            action: Action to dispatch

        Returns:
            Execution result
        """
        action_type = action.action

        try:
            if action_type == ActionType.LAUNCH:
                return self._exec_launch(action)

            elif action_type == ActionType.FOCUS:
                return self._exec_focus(action)

            elif action_type == ActionType.ASSERT_WORKSPACE:
                return self._exec_assert_workspace(action)

            elif action_type == ActionType.CLICK_BUTTON:
                return self._exec_click_button(action)

            elif action_type == ActionType.WAIT_BUTTON:
                return self._exec_wait_button(action)

            elif action_type == ActionType.TYPE_TEXT:
                return self._exec_type_text(action)

            elif action_type == ActionType.HOTKEY:
                return self._exec_hotkey(action)

            elif action_type == ActionType.SCREENSHOT:
                return self._exec_screenshot(action)

            elif action_type == ActionType.ASSERT_WINDOW:
                return self._exec_assert_window(action)

            else:
                return {"success": False, "error": f"Unknown action type: {action_type}"}

        except Exception as e:
            logger.error(f"Action execution error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _exec_launch(self, action: DesktopAction) -> Dict[str, Any]:
        """Execute launch action."""
        exe = action.params["exe"]
        args = action.params.get("args", [])
        reuse = action.params.get("reuse", True)

        cmd = [exe] + args
        if reuse:
            cmd.append("--reuse-window")

        if self.dry_run:
            logger.info(f"[DRY-RUN] Launch: {' '.join(cmd)}")
            return {"success": True}

        try:
            subprocess.Popen(cmd, shell=False)
            time.sleep(2)  # Wait for launch
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _exec_focus(self, action: DesktopAction) -> Dict[str, Any]:
        """Execute focus action."""
        title_hint = action.params["title_hint"]

        if not self.uia_backend:
            return {"success": False, "error": "UIA backend not available"}

        if self.uia_backend.connect_window(title_hint, timeout=action.timeout):
            self.uia_backend.focus_window()
            return {"success": True}
        else:
            return {"success": False, "error": "Window not found"}

    def _exec_assert_workspace(self, action: DesktopAction) -> Dict[str, Any]:
        """Execute workspace assertion."""
        expected = Path(action.params["expected"])

        try:
            self.workspace_guard.expected_repo = expected
            self.workspace_guard.assert_workspace(fix=True)
            return {"success": True, "details": self.workspace_guard.get_workspace_info()}
        except AssertionError as e:
            return {"success": False, "error": str(e)}

    def _exec_click_button(self, action: DesktopAction) -> Dict[str, Any]:
        """Execute button click."""
        label = action.params["label"]

        if not self.uia_backend:
            return {"success": False, "error": "UIA backend not available"}

        success = self.uia_backend.click_button(label, timeout=action.timeout)
        return {"success": success}

    def _exec_wait_button(self, action: DesktopAction) -> Dict[str, Any]:
        """Execute wait for button."""
        label = action.params["label"]

        if not self.uia_backend:
            return {"success": False, "error": "UIA backend not available"}

        success = self.uia_backend.wait_button(label, timeout=action.timeout)
        return {"success": success}

    def _exec_type_text(self, action: DesktopAction) -> Dict[str, Any]:
        """Execute type text."""
        text = action.params["text"]
        interval = action.params.get("interval", 0.01)

        if not self.fallback_backend:
            return {"success": False, "error": "Fallback backend not available"}

        success = self.fallback_backend.type_text(text, interval=interval)
        return {"success": success}

    def _exec_hotkey(self, action: DesktopAction) -> Dict[str, Any]:
        """Execute hotkey."""
        keys = action.params["keys"]

        if not self.fallback_backend:
            return {"success": False, "error": "Fallback backend not available"}

        success = self.fallback_backend.hotkey(*keys)
        return {"success": success}

    def _exec_screenshot(self, action: DesktopAction) -> Dict[str, Any]:
        """Execute screenshot."""
        path = action.params["path"]
        region = action.params.get("region")

        if not self.fallback_backend:
            return {"success": False, "error": "Fallback backend not available"}

        success = self.fallback_backend.screenshot(path, region=region)
        return {"success": success, "details": {"path": path}}

    def _exec_assert_window(self, action: DesktopAction) -> Dict[str, Any]:
        """Execute window assertion."""
        title_hint = action.params["title_hint"]

        if not self.uia_backend:
            return {"success": False, "error": "UIA backend not available"}

        try:
            self.uia_backend.assert_window_exists(title_hint, timeout=action.timeout)
            return {"success": True}
        except AssertionError as e:
            return {"success": False, "error": str(e)}

    def _take_screenshot(self, prefix: str) -> Optional[str]:
        """
        Take timestamped screenshot.

        Args:
            prefix: Filename prefix

        Returns:
            Screenshot filename or None if failed
        """
        if not self.fallback_backend:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}_{self.screenshot_count:03d}.png"
        path = self.screenshot_dir / filename

        self.screenshot_count += 1

        if self.fallback_backend.screenshot(str(path)):
            return str(path)
        else:
            return None
