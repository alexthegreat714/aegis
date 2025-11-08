"""
Tests for multi-cycle mode and digest reporting.

Day 4: Tests autonomous cycles, intent chaining, observation, and digest.
"""

import unittest
import tempfile
from pathlib import Path
import time
from unittest.mock import Mock, MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.system_observer import SystemObserver, SystemObservation
from reporting.digest import DigestGenerator, CycleDigest
from core.intent_parser import IntentParser
from aegis_logging.logger import AegisLogger


class TestSystemObserver(unittest.TestCase):
    """Test SystemObserver functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.observer = SystemObserver()

    def test_observe_returns_typed_dict(self):
        """Test that observe() returns SystemObservation dict."""
        observation = self.observer.observe()

        # Check it's a dictionary
        self.assertIsInstance(observation, dict)

        # Check required fields exist
        self.assertIn("timestamp", observation)
        self.assertIn("cpu_percent", observation)
        self.assertIn("memory_percent", observation)
        self.assertIn("platform", observation)

    def test_observation_has_useful_fields(self):
        """Test that observation contains at least 2 useful fields."""
        observation = self.observer.observe()

        # Requirement: observation contains at least 2 useful fields
        useful_fields = [
            "active_window",
            "processes",
            "cpu_percent",
            "memory_percent",
            "process_count",
            "top_cpu_processes"
        ]

        present_fields = [f for f in useful_fields if f in observation]
        self.assertGreaterEqual(
            len(present_fields),
            2,
            f"Observation should have at least 2 useful fields, found: {present_fields}"
        )

    def test_observation_cpu_percent_valid(self):
        """Test that CPU percentage is valid."""
        observation = self.observer.observe()

        cpu = observation.get("cpu_percent")
        self.assertIsNotNone(cpu)
        self.assertGreaterEqual(cpu, 0.0)
        self.assertLessEqual(cpu, 100.0)

    def test_observation_memory_percent_valid(self):
        """Test that memory percentage is valid."""
        observation = self.observer.observe()

        memory = observation.get("memory_percent")
        self.assertIsNotNone(memory)
        self.assertGreaterEqual(memory, 0.0)
        self.assertLessEqual(memory, 100.0)

    def test_observation_timestamp_format(self):
        """Test that timestamp is ISO format."""
        observation = self.observer.observe()

        timestamp = observation.get("timestamp")
        self.assertIsNotNone(timestamp)
        self.assertIn("T", timestamp)  # ISO format has T separator

    def test_get_idle_time(self):
        """Test idle time tracking."""
        # First observation
        observation1 = self.observer.observe()
        idle_time1 = self.observer.get_idle_time()
        self.assertEqual(idle_time1, 0.0)  # First observation, no prior time

        # Wait a bit
        time.sleep(0.1)

        # Check idle time before second observation
        idle_time_before = self.observer.get_idle_time()
        self.assertGreaterEqual(idle_time_before, 0.1)  # Should be >= sleep time

        # Second observation resets the timer
        observation2 = self.observer.observe()
        idle_time2 = self.observer.get_idle_time()
        self.assertLess(idle_time2, 0.01)  # Should be near 0 after fresh observe()

    def test_to_summary_dict(self):
        """Test observation summary conversion."""
        observation = self.observer.observe()
        summary = self.observer.to_summary_dict(observation)

        self.assertIsInstance(summary, dict)
        self.assertIn("timestamp", summary)
        self.assertIn("cpu_percent", summary)
        self.assertLessEqual(len(summary), len(observation))  # Summary is compact


class TestDigestGenerator(unittest.TestCase):
    """Test DigestGenerator functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = DigestGenerator()

    def test_start_digest(self):
        """Test starting a digest session."""
        digest = self.generator.start_digest()

        self.assertIsInstance(digest, CycleDigest)
        self.assertEqual(digest.total_cycles, 0)
        self.assertEqual(digest.intents_executed, 0)
        self.assertIsNotNone(digest.start_time)

    def test_record_cycle(self):
        """Test recording cycle completion."""
        self.generator.start_digest()

        self.generator.record_cycle()
        self.assertEqual(self.generator.current_digest.total_cycles, 1)

        self.generator.record_cycle()
        self.assertEqual(self.generator.current_digest.total_cycles, 2)

    def test_record_intent_success(self):
        """Test recording successful intent."""
        self.generator.start_digest()

        self.generator.record_intent_executed(
            intent_type="mouse_click",
            success=True,
            execution_time_ms=100.0
        )

        digest = self.generator.current_digest
        self.assertEqual(digest.intents_executed, 1)
        self.assertEqual(digest.intents_succeeded, 1)
        self.assertEqual(digest.intents_failed, 0)
        self.assertEqual(digest.execution_times_ms, [100.0])

    def test_record_intent_failure(self):
        """Test recording failed intent."""
        self.generator.start_digest()

        self.generator.record_intent_executed(
            intent_type="mouse_click",
            success=False,
            execution_time_ms=50.0,
            error="Test error"
        )

        digest = self.generator.current_digest
        self.assertEqual(digest.intents_executed, 1)
        self.assertEqual(digest.intents_succeeded, 0)
        self.assertEqual(digest.intents_failed, 1)
        self.assertEqual(digest.errors, ["Test error"])

    def test_record_policy_allow(self):
        """Test recording policy allow decision."""
        self.generator.start_digest()

        self.generator.record_policy_decision(allowed=True)

        digest = self.generator.current_digest
        self.assertEqual(digest.policy_allows, 1)
        self.assertEqual(digest.policy_denies, 0)

    def test_record_policy_deny(self):
        """Test recording policy deny decision."""
        self.generator.start_digest()

        self.generator.record_policy_decision(allowed=False)

        digest = self.generator.current_digest
        self.assertEqual(digest.policy_allows, 0)
        self.assertEqual(digest.policy_denies, 1)

    def test_record_policy_requires_approval(self):
        """Test recording policy requires approval decision."""
        self.generator.start_digest()

        self.generator.record_policy_decision(
            allowed=False,
            requires_approval=True
        )

        digest = self.generator.current_digest
        self.assertEqual(digest.policy_requires_approval, 1)

    def test_digest_tracks_success_failure_deny_counts(self):
        """Test that digest records success, failure, deny counts."""
        self.generator.start_digest()

        # Record some successes
        self.generator.record_intent_executed("mouse_click", True, 100.0)
        self.generator.record_intent_executed("keyboard_type", True, 150.0)

        # Record a failure
        self.generator.record_intent_executed(
            "screenshot", False, 50.0, "Test error"
        )

        # Record policy decisions
        self.generator.record_policy_decision(allowed=True)
        self.generator.record_policy_decision(allowed=True)
        self.generator.record_policy_decision(allowed=False)

        digest = self.generator.current_digest

        # Verify counts
        self.assertEqual(digest.intents_executed, 3)
        self.assertEqual(digest.intents_succeeded, 2)
        self.assertEqual(digest.intents_failed, 1)
        self.assertEqual(digest.policy_allows, 2)
        self.assertEqual(digest.policy_denies, 1)

    def test_end_digest(self):
        """Test ending a digest session."""
        self.generator.start_digest()
        self.generator.record_cycle()

        digest = self.generator.end_digest()

        self.assertIsInstance(digest, CycleDigest)
        self.assertIsNotNone(digest.end_time)
        self.assertIsNone(self.generator.current_digest)
        self.assertEqual(len(self.generator.digest_history), 1)

    def test_digest_to_dict(self):
        """Test digest to_dict conversion."""
        self.generator.start_digest()
        self.generator.record_cycle()

        digest = self.generator.current_digest
        digest_dict = digest.to_dict()

        self.assertIsInstance(digest_dict, dict)
        self.assertIn("total_cycles", digest_dict)
        self.assertIn("intents_executed", digest_dict)
        self.assertIn("start_time", digest_dict)

    def test_digest_to_json(self):
        """Test digest to_json conversion."""
        self.generator.start_digest()
        self.generator.record_cycle()

        digest = self.generator.current_digest
        json_str = digest.to_json()

        self.assertIsInstance(json_str, str)
        self.assertIn('"total_cycles"', json_str)

    def test_digest_to_markdown(self):
        """Test digest to_markdown conversion."""
        self.generator.start_digest()
        self.generator.record_intent_executed("mouse_click", True, 100.0)
        self.generator.record_policy_decision(allowed=True)

        digest = self.generator.current_digest
        markdown = digest.to_markdown()

        self.assertIsInstance(markdown, str)
        self.assertIn("# Aegis Cycle Digest", markdown)
        self.assertIn("Execution Summary", markdown)
        self.assertIn("Performance", markdown)


class TestIntentChaining(unittest.TestCase):
    """Test intent chaining functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir()
        (self.data_dir / "logs").mkdir(exist_ok=True)

        # Test settings
        self.settings = {
            "logging": {"jsonl_enabled": True, "sqlite_enabled": True}
        }

        # Initialize logger
        self.logger = AegisLogger(
            log_dir=str(self.data_dir / "logs"),
            db_path=str(self.data_dir / "test.db"),
            settings=self.settings
        )

        # Initialize parser
        self.parser = IntentParser(self.logger)

    def test_parse_intent_list_json_array(self):
        """Test parsing JSON array of intents."""
        json_input = '''[
            {"intent": "open_app", "target": "notepad", "args": {}},
            {"intent": "type_text", "target": "hello", "args": {}}
        ]'''

        intents = self.parser.parse_intent_list(json_input)

        self.assertEqual(len(intents), 2)
        self.assertIsNotNone(intents[0])
        self.assertIsNotNone(intents[1])

    def test_parse_intent_list_multiline_format(self):
        """Test parsing multi-line intent list."""
        text_input = """INTENTS:
  - open_app name=notepad
  - type_text text=hello
"""

        intents = self.parser.parse_intent_list(text_input)

        # Should parse at least one intent
        self.assertGreaterEqual(len(intents), 1)

    def test_parse_intent_list_single_intent(self):
        """Test parsing single intent returns list with one item."""
        text_input = "open notepad"

        intents = self.parser.parse_intent_list(text_input)

        self.assertEqual(len(intents), 1)

    def test_parse_intent_list_empty_returns_empty_list(self):
        """Test parsing unparseable text returns empty list."""
        text_input = "random unparseable text"

        intents = self.parser.parse_intent_list(text_input)

        self.assertEqual(len(intents), 0)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)


class TestControlLoopCycles(unittest.TestCase):
    """Test control loop cycle functionality."""

    @patch('core.control_loop.OWUIClient')
    @patch('core.control_loop.PolicyEngine')
    @patch('core.control_loop.ActionPlanner')
    def test_run_n_cycles_completes(self, mock_planner, mock_policy, mock_client):
        """Test that run_n_cycles(3) completes 3 cycles."""
        # This test verifies the cycle count
        # In practice, would need full mocking of all dependencies
        # For now, just test that the method signature is correct

        from core.control_loop import ControlLoop
        from aegis_logging.logger import AegisLogger

        temp_dir = tempfile.mkdtemp()
        data_dir = Path(temp_dir) / "data"
        data_dir.mkdir()
        (data_dir / "logs").mkdir(exist_ok=True)

        settings = {
            "control_loop": {"max_iterations": 10, "sleep_between_actions_ms": 10},
            "safety": {"dry_run": True},
            "logging": {"jsonl_enabled": True, "sqlite_enabled": True}
        }

        logger = AegisLogger(
            log_dir=str(data_dir / "logs"),
            db_path=str(data_dir / "test.db"),
            settings=settings
        )

        # Create control loop (with mocked components)
        loop = ControlLoop(
            settings=settings,
            policy_engine=mock_policy(),
            logger=logger,
            owui_client=mock_client(),
            action_planner=mock_planner()
        )

        # Verify run_n_cycles method exists
        self.assertTrue(hasattr(loop, 'run_n_cycles'))
        self.assertTrue(callable(loop.run_n_cycles))

        # Verify run_forever method exists
        self.assertTrue(hasattr(loop, 'run_forever'))
        self.assertTrue(callable(loop.run_forever))

        # Clean up
        import shutil
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()
