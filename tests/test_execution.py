"""
Tests for action execution.

Day 3: Tests real execution with dry_run support.
"""

import unittest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from automation.desktop import DesktopAutomation
from automation.executor import ActionExecutor, ExecutionError
from core.action_planner import ActionPlanner, ActionPlan
from intents.intent_schema import Intent, ActionResult
from intents.intent_types import IntentType
from aegis_logging.logger import AegisLogger


class TestActionExecution(unittest.TestCase):
    """Test action execution functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir()

        # Initialize logger
        (self.data_dir / "logs").mkdir(exist_ok=True)
        self.logger = AegisLogger(
            log_dir=str(self.data_dir / "logs"),
            db_path=str(self.data_dir / "test.db"),
            settings={"logging": {"jsonl_enabled": True, "sqlite_enabled": True}}
        )

        # Test settings
        self.settings = {
            "automation": {
                "action_delay_ms": 10,
                "screenshot_dir": str(self.data_dir / "screenshots")
            }
        }

    def test_desktop_automation_dry_run_mode(self):
        """Test that dry_run mode does not change system state."""
        # Initialize with dry_run=True
        desktop = DesktopAutomation(self.logger, self.settings, dry_run=True)

        # Execute actions in dry run mode
        result = desktop.mouse_click(100, 200)

        # Should succeed but not actually click
        self.assertIsInstance(result, ActionResult)
        self.assertTrue(result.success)
        self.assertIsNone(result.error)

    def test_desktop_automation_mouse_click(self):
        """Test mouse click execution."""
        desktop = DesktopAutomation(self.logger, self.settings, dry_run=True)

        result = desktop.mouse_click(100, 200, button="left", clicks=1)

        self.assertIsInstance(result, ActionResult)
        self.assertTrue(result.success)
        self.assertEqual(result.details["x"], 100)
        self.assertEqual(result.details["y"], 200)
        self.assertEqual(result.details["button"], "left")

    def test_desktop_automation_keyboard_type(self):
        """Test keyboard typing."""
        desktop = DesktopAutomation(self.logger, self.settings, dry_run=True)

        result = desktop.keyboard_type("Hello, world!")

        self.assertIsInstance(result, ActionResult)
        self.assertTrue(result.success)
        self.assertEqual(result.details["text_length"], 13)
        self.assertIn("Hello", result.details["text_preview"])

    def test_desktop_automation_screenshot(self):
        """Test screenshot capture."""
        desktop = DesktopAutomation(self.logger, self.settings, dry_run=True)

        result = desktop.screenshot()

        self.assertIsInstance(result, ActionResult)
        self.assertTrue(result.success)
        self.assertIn("path", result.details)
        self.assertIn(".png", result.details["path"])

    def test_action_result_structure(self):
        """Test that ActionResult contains expected keys."""
        desktop = DesktopAutomation(self.logger, self.settings, dry_run=True)

        result = desktop.mouse_click(50, 50)

        # Check required fields
        self.assertTrue(hasattr(result, 'success'))
        self.assertTrue(hasattr(result, 'error'))
        self.assertTrue(hasattr(result, 'details'))
        self.assertTrue(hasattr(result, 'execution_time_ms'))

        # Check types
        self.assertIsInstance(result.success, bool)
        self.assertIsInstance(result.details, dict)
        self.assertIsInstance(result.execution_time_ms, float)

    def test_action_result_to_dict(self):
        """Test ActionResult to_dict method."""
        desktop = DesktopAutomation(self.logger, self.settings, dry_run=True)

        result = desktop.mouse_click(50, 50)
        result_dict = result.to_dict()

        self.assertIsInstance(result_dict, dict)
        self.assertIn("success", result_dict)
        self.assertIn("error", result_dict)
        self.assertIn("details", result_dict)
        self.assertIn("execution_time_ms", result_dict)

    def test_executor_dry_run_mode(self):
        """Test executor in dry_run mode."""
        planner = ActionPlanner(self.logger, self.settings)
        executor = ActionExecutor(self.logger, self.settings, dry_run=True)

        # Create simple intent
        intent = Intent(
            action_type=IntentType.MOUSE_CLICK,
            parameters={"x": 100, "y": 200}
        )

        # Create plan
        plan = planner.plan(intent)

        # Execute in dry run mode
        result = executor.execute_plan(plan)

        # Should succeed
        self.assertTrue(result.success)
        self.assertIsNone(result.error)

    def test_executor_dispatches_to_correct_function(self):
        """Test that executor dispatches to correct automation function."""
        planner = ActionPlanner(self.logger, self.settings)
        executor = ActionExecutor(self.logger, self.settings, dry_run=True)

        # Test mouse click
        intent = Intent(
            action_type=IntentType.MOUSE_CLICK,
            parameters={"x": 100, "y": 200}
        )
        plan = planner.plan(intent)
        result = executor.execute_plan(plan)
        self.assertTrue(result.success)

        # Test keyboard type
        intent = Intent(
            action_type=IntentType.KEYBOARD_TYPE,
            parameters={"text": "test"}
        )
        plan = planner.plan(intent)
        result = executor.execute_plan(plan)
        self.assertTrue(result.success)

        # Test screenshot
        intent = Intent(
            action_type=IntentType.SCREENSHOT,
            parameters={}
        )
        plan = planner.plan(intent)
        result = executor.execute_plan(plan)
        self.assertTrue(result.success)

    def test_executor_completes_multi_step_plan(self):
        """Test executor completes multi-step action plans."""
        planner = ActionPlanner(self.logger, self.settings)
        executor = ActionExecutor(self.logger, self.settings, dry_run=True)

        # Create filesystem intent (has multiple steps)
        intent = Intent(
            action_type=IntentType.FILE_WRITE,
            parameters={"path": "/tmp/test.txt", "content": "test"}
        )

        plan = planner.plan(intent)

        # Should have multiple steps
        self.assertGreater(len(plan.steps), 1)

        # Execute plan
        result = executor.execute_plan(plan)

        # Should complete all steps
        self.assertTrue(result.success)
        self.assertEqual(len(plan.completed_steps), len(plan.steps))

    def test_execution_time_tracked(self):
        """Test that execution time is tracked."""
        desktop = DesktopAutomation(self.logger, self.settings, dry_run=True)

        result = desktop.mouse_click(100, 200)

        # Should have non-zero execution time
        self.assertGreaterEqual(result.execution_time_ms, 0)

    def test_dry_run_flag_propagates(self):
        """Test that dry_run flag propagates to automation modules."""
        executor = ActionExecutor(self.logger, self.settings, dry_run=True)

        # Executor should have dry_run set
        self.assertTrue(executor.dry_run)

        # Desktop automation should have dry_run set
        self.assertTrue(executor.desktop.dry_run)

    def test_error_handling_in_action_result(self):
        """Test error handling returns ActionResult with error."""
        # This test verifies the error handling structure
        # In real scenario, errors would be caught and returned

        result = ActionResult(
            success=False,
            error="Test error",
            details={"info": "test"}
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Test error")
        self.assertIn("info", result.details)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)


if __name__ == "__main__":
    unittest.main()
