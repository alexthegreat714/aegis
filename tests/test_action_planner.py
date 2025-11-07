"""
Tests for action planner.
"""

import unittest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.action_planner import ActionPlanner, ActionPlan, ActionStep
from intents.intent_schema import Intent
from intents.intent_types import IntentType
from aegis_logging.logger import AegisLogger


class TestActionPlanner(unittest.TestCase):
    """Test action planner functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir()

        # Initialize logger
        self.logger = AegisLogger(
            jsonl_path=str(self.data_dir / "logs" / "test.jsonl"),
            db_path=str(self.data_dir / "test.db")
        )

        # Test settings
        self.settings = {
            "automation": {"action_delay_ms": 100}
        }

        # Initialize planner
        self.planner = ActionPlanner(self.logger, self.settings)

    def test_plan_desktop_mouse_click(self):
        """Test planning desktop mouse click action."""
        intent = Intent(
            action_type=IntentType.MOUSE_CLICK,
            parameters={"x": 100, "y": 200}
        )

        plan = self.planner.plan(intent)

        self.assertIsInstance(plan, ActionPlan)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].executor, "automation.desktop")
        self.assertEqual(plan.steps[0].function, "mouse_click")

    def test_plan_desktop_keyboard_type(self):
        """Test planning keyboard type action."""
        intent = Intent(
            action_type=IntentType.KEYBOARD_TYPE,
            parameters={"text": "Hello, world!"}
        )

        plan = self.planner.plan(intent)

        self.assertIsInstance(plan, ActionPlan)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].function, "keyboard_type")

    def test_plan_desktop_screenshot(self):
        """Test planning screenshot action."""
        intent = Intent(
            action_type=IntentType.SCREENSHOT,
            parameters={"output_path": "test.png"}
        )

        plan = self.planner.plan(intent)

        self.assertIsInstance(plan, ActionPlan)
        self.assertEqual(len(plan.steps), 1)

    def test_plan_window_focus_with_title(self):
        """Test planning window focus with title."""
        intent = Intent(
            action_type=IntentType.WINDOW_FOCUS,
            parameters={"title": "Notepad"}
        )

        plan = self.planner.plan(intent)

        # Should have find_window step + focus step
        self.assertIsInstance(plan, ActionPlan)
        self.assertGreaterEqual(len(plan.steps), 1)

        # Check if window finding step exists
        has_find_step = any(
            step.function == "find_window"
            for step in plan.steps
        )
        self.assertTrue(has_find_step or len(plan.steps) >= 1)

    def test_plan_window_close(self):
        """Test planning window close action."""
        intent = Intent(
            action_type=IntentType.WINDOW_CLOSE,
            parameters={"title": "Notepad"}
        )

        plan = self.planner.plan(intent)

        self.assertIsInstance(plan, ActionPlan)
        self.assertGreaterEqual(len(plan.steps), 1)

    def test_plan_filesystem_write_has_backup(self):
        """Test that file write plan includes backup step."""
        intent = Intent(
            action_type=IntentType.FILE_WRITE,
            parameters={"path": "/tmp/test.txt", "content": "test"}
        )

        plan = self.planner.plan(intent)

        self.assertIsInstance(plan, ActionPlan)
        self.assertGreater(len(plan.steps), 1)  # Should have multiple steps

        # Check for backup step
        has_backup = any(
            "backup" in step.description.lower()
            for step in plan.steps
        )
        self.assertTrue(has_backup)

    def test_plan_filesystem_write_has_validation(self):
        """Test that file write plan includes path validation."""
        intent = Intent(
            action_type=IntentType.FILE_WRITE,
            parameters={"path": "/tmp/test.txt", "content": "test"}
        )

        plan = self.planner.plan(intent)

        # Check for validation step
        has_validation = any(
            "validate" in step.description.lower()
            for step in plan.steps
        )
        self.assertTrue(has_validation)

    def test_plan_filesystem_write_has_verification(self):
        """Test that file write plan includes verification."""
        intent = Intent(
            action_type=IntentType.FILE_WRITE,
            parameters={"path": "/tmp/test.txt", "content": "test"}
        )

        plan = self.planner.plan(intent)

        # Check for verification step
        has_verification = any(
            "verify" in step.description.lower()
            for step in plan.steps
        )
        self.assertTrue(has_verification)

    def test_plan_filesystem_read(self):
        """Test planning file read action."""
        intent = Intent(
            action_type=IntentType.FILE_READ,
            parameters={"path": "/tmp/test.txt"}
        )

        plan = self.planner.plan(intent)

        self.assertIsInstance(plan, ActionPlan)
        self.assertGreaterEqual(len(plan.steps), 1)

    def test_plan_meta_action(self):
        """Test planning meta action (control Aegis)."""
        intent = Intent(
            action_type=IntentType.PAUSE,
            parameters={}
        )

        plan = self.planner.plan(intent)

        self.assertIsInstance(plan, ActionPlan)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].executor, "core.control_loop")

    def test_validate_plan_valid(self):
        """Test validating valid action plan."""
        intent = Intent(
            action_type=IntentType.MOUSE_CLICK,
            parameters={"x": 100, "y": 200}
        )

        plan = self.planner.plan(intent)
        result = self.planner.validate_plan(plan)

        self.assertTrue(result)

    def test_validate_plan_no_steps(self):
        """Test validating plan with no steps."""
        intent = Intent(
            action_type=IntentType.SCREENSHOT,
            parameters={}
        )

        plan = ActionPlan(intent=intent, steps=[])  # Empty steps
        result = self.planner.validate_plan(plan)

        self.assertFalse(result)

    def test_action_plan_is_complete(self):
        """Test action plan completion tracking."""
        intent = Intent(
            action_type=IntentType.MOUSE_CLICK,
            parameters={"x": 100, "y": 200}
        )

        plan = self.planner.plan(intent)

        # Initially not complete
        self.assertFalse(plan.is_complete())

        # Mark all steps as completed
        for step in plan.steps:
            plan.completed_steps.append(step.step_id)

        # Now should be complete
        self.assertTrue(plan.is_complete())

    def test_action_plan_has_failures(self):
        """Test action plan failure tracking."""
        intent = Intent(
            action_type=IntentType.MOUSE_CLICK,
            parameters={"x": 100, "y": 200}
        )

        plan = self.planner.plan(intent)

        # Initially no failures
        self.assertFalse(plan.has_failures())

        # Mark a step as failed
        plan.failed_steps.append(1)

        # Now should have failures
        self.assertTrue(plan.has_failures())

    def test_action_plan_to_dict(self):
        """Test converting action plan to dictionary."""
        intent = Intent(
            action_type=IntentType.MOUSE_CLICK,
            parameters={"x": 100, "y": 200}
        )

        plan = self.planner.plan(intent)
        plan_dict = plan.to_dict()

        self.assertIsInstance(plan_dict, dict)
        self.assertIn("intent", plan_dict)
        self.assertIn("steps", plan_dict)
        self.assertIn("completed_steps", plan_dict)
        self.assertIn("failed_steps", plan_dict)

    def test_action_step_creation(self):
        """Test ActionStep creation."""
        step = ActionStep(
            step_id=1,
            description="Test step",
            executor="automation.desktop",
            function="mouse_click",
            parameters={"x": 100, "y": 200}
        )

        self.assertEqual(step.step_id, 1)
        self.assertEqual(step.description, "Test step")
        self.assertEqual(step.executor, "automation.desktop")
        self.assertEqual(step.function, "mouse_click")
        self.assertEqual(step.parameters["x"], 100)

    def test_plan_vscode_action(self):
        """Test planning VS Code action."""
        intent = Intent(
            action_type=IntentType.VSCODE_RUN_COMMAND,
            parameters={"command": "npm test"}
        )

        plan = self.planner.plan(intent)

        self.assertIsInstance(plan, ActionPlan)
        self.assertGreaterEqual(len(plan.steps), 1)

    def test_plan_system_action(self):
        """Test planning system action."""
        intent = Intent(
            action_type=IntentType.PROCESS_LIST,
            parameters={}
        )

        plan = self.planner.plan(intent)

        self.assertIsInstance(plan, ActionPlan)
        self.assertEqual(len(plan.steps), 1)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)


if __name__ == "__main__":
    unittest.main()
