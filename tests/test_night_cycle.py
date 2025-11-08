"""
Tests for night cycle functionality.

These tests use mocking and are marked with @pytest.mark.vs
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Skip by default
pytestmark = pytest.mark.vs


class TestNightCycle:
    """Test night cycle with mocked dependencies."""

    @patch('core.night_cycle.RevisionSystem')
    @patch('core.night_cycle.ClaudeVSCodeSession')
    def test_night_cycle_initialization(self, mock_session_class, mock_rev_system_class):
        """Test night cycle initialization."""
        from core.night_cycle import NightCycle

        temp_dir = Path(tempfile.mkdtemp())

        try:
            cycle = NightCycle(repo_root=temp_dir, settings={})

            assert cycle.repo_root == temp_dir
            assert cycle.current_round == 0
            assert cycle.failures == []

        finally:
            shutil.rmtree(temp_dir)

    @patch('core.night_cycle.RevisionSystem')
    @patch('core.night_cycle.ClaudeVSCodeSession')
    @patch('core.night_cycle.build_repo_summary')
    @patch('core.night_cycle.build_night_cycle_prompt')
    @patch('builtins.input', return_value='')  # Mock input for manual step
    def test_run_single_round(
        self,
        mock_input,
        mock_prompt,
        mock_summary,
        mock_session_class,
        mock_rev_system_class
    ):
        """Test running a single round."""
        from core.night_cycle import NightCycle

        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Mock revision system
            mock_rev_system = Mock()
            mock_rev_system.cmd_new.return_value = "rev_0001"
            mock_rev_system.cmd_approve.return_value = 0  # Tests pass
            mock_rev_system_class.return_value = mock_rev_system

            # Mock session
            mock_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_session.send_and_fetch.return_value = (1, "test reply")
            mock_session_class.return_value = mock_session

            # Mock prompts
            mock_summary.return_value = "repo summary"
            mock_prompt.return_value = "test prompt"

            # Create snapshot directory structure
            snapshots_dir = temp_dir / ".aegis_revisions" / "rev_0001"
            snapshots_dir.mkdir(parents=True)

            cycle = NightCycle(repo_root=temp_dir, settings={})

            result = cycle.run_cycle(goal="Test goal", max_rounds=1, confirm_each=False)

            assert result['final_status'] in ['approved', 'pending_review']
            assert len(result['rounds']) == 1

        finally:
            shutil.rmtree(temp_dir)

    @patch('core.night_cycle.RevisionSystem')
    @patch('core.night_cycle.ClaudeVSCodeSession')
    @patch('core.night_cycle.build_repo_summary')
    @patch('core.night_cycle.build_night_cycle_prompt')
    @patch('builtins.input', return_value='')
    def test_run_multiple_rounds_failure(
        self,
        mock_input,
        mock_prompt,
        mock_summary,
        mock_session_class,
        mock_rev_system_class
    ):
        """Test running multiple rounds with failures."""
        from core.night_cycle import NightCycle

        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Mock revision system (all tests fail)
            mock_rev_system = Mock()
            mock_rev_system.cmd_new.side_effect = ["rev_0001", "rev_0002", "rev_0003"]
            mock_rev_system.cmd_approve.return_value = 1  # Tests always fail
            mock_rev_system_class.return_value = mock_rev_system

            # Mock session
            mock_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_session.send_and_fetch.return_value = (1, "test reply")
            mock_session_class.return_value = mock_session

            # Mock prompts
            mock_summary.return_value = "repo summary"
            mock_prompt.return_value = "test prompt"

            # Create snapshot directories
            for i in range(1, 4):
                (temp_dir / ".aegis_revisions" / f"rev_000{i}").mkdir(parents=True)

            cycle = NightCycle(repo_root=temp_dir, settings={})

            result = cycle.run_cycle(goal="Test goal", max_rounds=3, confirm_each=False)

            assert result['final_status'] == 'failed'
            assert len(result['rounds']) == 3
            assert len(cycle.failures) == 3

        finally:
            shutil.rmtree(temp_dir)


def test_night_cycle_function():
    """Test night_cycle convenience function."""
    from core.night_cycle import night_cycle

    # Should not crash when called (will fail due to missing dependencies, but that's OK)
    # Just test import and signature
    assert callable(night_cycle)
