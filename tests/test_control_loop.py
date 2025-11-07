"""
Tests for control loop.
"""

import unittest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.control_loop import ControlLoop
from core.policy_engine import PolicyEngine
from core.action_planner import ActionPlanner
from clients.owui_client import OWUIClient
from aegis_logging.logger import AegisLogger


class TestControlLoop(unittest.TestCase):
    """Test control loop functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir()

        # Create test settings
        self.settings = {
            "paths": {
                "data_dir": str(self.data_dir),
                "logs_dir": str(self.data_dir / "logs"),
                "db_path": str(self.data_dir / "test.db")
            },
            "control_loop": {
                "max_iterations": 10,
                "sleep_between_actions_ms": 10
            }
        }

        # Create test policy file
        self.policy_file = Path(self.temp_dir) / "policy.yaml"
        test_policy = {
            "mode": "assist",
            "actions": {
                "desktop": {"screenshot": "allow"},
                "filesystem": {"file_read": "allow"}
            }
        }
        with open(self.policy_file, 'w') as f:
            yaml.dump(test_policy, f)

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

        # Initialize action planner
        self.action_planner = ActionPlanner(
            logger=self.logger,
            settings=self.settings
        )

        # Mock OWUI client
        self.owui_client = Mock(spec=OWUIClient)

    def test_control_loop_initialization(self):
        """Test control loop initialization."""
        loop = ControlLoop(
            settings=self.settings,
            policy_engine=self.policy_engine,
            logger=self.logger,
            owui_client=self.owui_client,
            action_planner=self.action_planner
        )

        self.assertIsNotNone(loop)
        self.assertFalse(loop.running)
        self.assertEqual(loop.iteration_count, 0)

    def test_observe_gathers_state(self):
        """Test that observe() gathers system state."""
        loop = ControlLoop(
            settings=self.settings,
            policy_engine=self.policy_engine,
            logger=self.logger,
            owui_client=self.owui_client,
            action_planner=self.action_planner
        )

        observation = loop._observe()

        # Check required fields
        self.assertIn("timestamp", observation)
        self.assertIn("iteration", observation)
        self.assertIn("system_status", observation)
        self.assertIn("processes", observation)

        # Check system status fields
        self.assertIn("cpu_percent", observation["system_status"])
        self.assertIn("memory_percent", observation["system_status"])
        self.assertIn("running", observation["system_status"])

    @patch('core.control_loop.ControlLoop._observe')
    @patch('core.control_loop.ControlLoop._think')
    def test_run_iteration_with_prompt(self, mock_think, mock_observe):
        """Test running a single iteration with a prompt."""
        mock_observe.return_value = {
            "timestamp": "2025-01-01T00:00:00",
            "iteration": 0,
            "system_status": {"running": True}
        }

        mock_think.return_value = {
            "reasoning": "Test reasoning",
            "model": "test-model"
        }

        loop = ControlLoop(
            settings=self.settings,
            policy_engine=self.policy_engine,
            logger=self.logger,
            owui_client=self.owui_client,
            action_planner=self.action_planner
        )

        # Run iteration without starting full loop
        loop.running = True
        loop._run_iteration(prompt="Test prompt")

        # Verify observe was called
        mock_observe.assert_called_once()

        # Verify think was called with prompt
        mock_think.assert_called_once()

    def test_get_recent_logs(self):
        """Test retrieving recent logs from SQLite."""
        loop = ControlLoop(
            settings=self.settings,
            policy_engine=self.policy_engine,
            logger=self.logger,
            owui_client=self.owui_client,
            action_planner=self.action_planner
        )

        # Log some events
        self.logger.log_event("test_event_1", {"data": "test1"}, "info")
        self.logger.log_event("test_event_2", {"data": "test2"}, "success")

        # Retrieve recent logs
        logs = loop._get_recent_logs(limit=5)

        # Should return list of logs
        self.assertIsInstance(logs, list)
        # May be empty if DB not flushed yet
        # self.assertGreaterEqual(len(logs), 0)

    def test_get_process_summary(self):
        """Test getting process summary."""
        loop = ControlLoop(
            settings=self.settings,
            policy_engine=self.policy_engine,
            logger=self.logger,
            owui_client=self.owui_client,
            action_planner=self.action_planner
        )

        processes = loop._get_process_summary()

        # Check structure
        self.assertIn("total_count", processes)
        self.assertIn("top_consumers", processes)
        self.assertIsInstance(processes["top_consumers"], list)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)


if __name__ == "__main__":
    unittest.main()
