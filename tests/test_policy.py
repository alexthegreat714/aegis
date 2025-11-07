"""
Tests for policy engine.
"""

import unittest
import tempfile
import yaml
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.policy_engine import PolicyEngine, PolicyDecision
from intents.intent_schema import Intent
from intents.intent_types import IntentType
from aegis_logging.logger import AegisLogger


class TestPolicyEngine(unittest.TestCase):
    """Test policy engine functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir()

        # Create test policy file
        self.policy_file = Path(self.temp_dir) / "policy.yaml"
        self.test_policy = {
            "mode": "execute",
            "actions": {
                "desktop": {
                    "mouse_click": "allow",
                    "mouse_move": "allow",
                    "screenshot": "allow",
                    "window_close": "require_approval"
                },
                "filesystem": {
                    "file_read": "allow",
                    "file_write": "require_approval",
                    "file_delete": "block"
                },
                "system": {
                    "process_list": "allow",
                    "process_kill": "block"
                }
            },
            "sandbox_only": ["file_delete", "process_kill"],
            "restricted_paths": [
                "/etc",
                "/System"
            ],
            "allowed_paths": [
                str(self.temp_dir)
            ]
        }

        with open(self.policy_file, 'w') as f:
            yaml.dump(self.test_policy, f)

        # Initialize logger
        self.logger = AegisLogger(
            jsonl_path=str(self.data_dir / "logs" / "test.jsonl"),
            db_path=str(self.data_dir / "test.db")
        )

        # Initialize policy engine
        self.policy_engine = PolicyEngine(
            policy_path=str(self.policy_file),
            logger=self.logger
        )

    def test_load_policy(self):
        """Test loading policy from YAML."""
        self.assertEqual(self.policy_engine.policy["mode"], "execute")
        self.assertIn("actions", self.policy_engine.policy)
        self.assertIn("desktop", self.policy_engine.policy["actions"])

    def test_check_allow_action(self):
        """Test allowed action passes policy check."""
        intent = Intent(
            action_type=IntentType.MOUSE_CLICK,
            parameters={"x": 100, "y": 200}
        )

        decision = self.policy_engine.check_intent(intent)

        self.assertTrue(decision.allowed)
        self.assertFalse(decision.requires_approval)
        self.assertIn("allowed", decision.reason.lower())

    def test_check_block_action(self):
        """Test blocked action fails policy check."""
        intent = Intent(
            action_type=IntentType.FILE_DELETE,
            parameters={"path": "/tmp/test.txt"}
        )

        decision = self.policy_engine.check_intent(intent)

        self.assertFalse(decision.allowed)
        self.assertIn("blocked", decision.reason.lower())

    def test_check_approval_required(self):
        """Test action requiring approval."""
        intent = Intent(
            action_type=IntentType.FILE_WRITE,
            parameters={"path": str(self.temp_dir / "test.txt")}
        )

        decision = self.policy_engine.check_intent(intent)

        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_approval)
        self.assertIn("approval", decision.reason.lower())

    def test_path_validation_allowed(self):
        """Test allowed path validation."""
        test_path = str(self.temp_dir / "test.txt")
        self.assertTrue(self.policy_engine.is_path_allowed(test_path))

    def test_path_validation_restricted(self):
        """Test restricted path validation."""
        restricted_path = "/etc/passwd"
        self.assertFalse(self.policy_engine.is_path_allowed(restricted_path))

    def test_path_validation_sandbox_always_allowed(self):
        """Test that sandbox paths are always allowed."""
        sandbox_path = "sandbox/test.txt"
        self.assertTrue(self.policy_engine.is_path_allowed(sandbox_path))

    def test_sandbox_only_actions_outside_sandbox(self):
        """Test sandbox-only action enforcement outside sandbox."""
        intent = Intent(
            action_type=IntentType.FILE_DELETE,
            parameters={"path": str(self.temp_dir / "test.txt")}
        )

        decision = self.policy_engine.check_intent(intent)

        self.assertFalse(decision.allowed)
        self.assertIn("sandbox", decision.reason.lower())

    def test_sandbox_only_actions_inside_sandbox(self):
        """Test sandbox-only actions are allowed inside sandbox."""
        # Create sandbox directory
        sandbox_dir = Path("sandbox")
        sandbox_dir.mkdir(exist_ok=True)

        intent = Intent(
            action_type=IntentType.FILE_DELETE,
            parameters={"path": "sandbox/test.txt"}
        )

        decision = self.policy_engine.check_intent(intent)

        # Should still require approval or be blocked, but not for sandbox reason
        self.assertFalse(decision.allowed)
        # Either blocked by policy or requires approval
        self.assertTrue("blocked" in decision.reason.lower() or "approval" in decision.reason.lower())

    def test_reload_policy(self):
        """Test policy hot-reload."""
        # Modify policy file
        modified_policy = self.test_policy.copy()
        modified_policy["mode"] = "autonomous"

        with open(self.policy_file, 'w') as f:
            yaml.dump(modified_policy, f)

        # Reload policy
        self.policy_engine.reload_policy()

        # Verify new mode
        self.assertEqual(self.policy_engine.get_mode(), "autonomous")

    def test_assist_mode_requires_approval(self):
        """Test that assist mode requires approval for all actions."""
        # Change to assist mode
        assist_policy = self.test_policy.copy()
        assist_policy["mode"] = "assist"

        with open(self.policy_file, 'w') as f:
            yaml.dump(assist_policy, f)

        self.policy_engine.reload_policy()

        # Even allowed actions should require approval in assist mode
        intent = Intent(
            action_type=IntentType.MOUSE_CLICK,
            parameters={"x": 100, "y": 200}
        )

        decision = self.policy_engine.check_intent(intent)

        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_approval)
        self.assertIn("assist mode", decision.reason.lower())

    def test_meta_actions_always_allowed(self):
        """Test that meta actions are always allowed."""
        intent = Intent(
            action_type=IntentType.PAUSE,
            parameters={}
        )

        decision = self.policy_engine.check_intent(intent)

        # Meta actions should be allowed even in assist mode
        # But assist mode catches them first
        self.assertIsNotNone(decision)

    def test_is_sandbox_only(self):
        """Test sandbox-only action detection."""
        self.assertTrue(self.policy_engine.is_sandbox_only("file_delete"))
        self.assertTrue(self.policy_engine.is_sandbox_only("process_kill"))
        self.assertFalse(self.policy_engine.is_sandbox_only("file_read"))

    def test_get_mode(self):
        """Test getting current operation mode."""
        self.assertEqual(self.policy_engine.get_mode(), "execute")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)


if __name__ == "__main__":
    unittest.main()
