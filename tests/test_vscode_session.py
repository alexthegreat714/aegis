"""
Tests for Claude VS Code session.

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


class TestClaudeVSCodeSession:
    """Test Claude VS Code session with mocked automator."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.revisions_dir = self.temp_dir / "revisions"
        self.revisions_dir.mkdir()

    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch('claude.vscode_session.VSCodeAutomator')
    def test_session_initialization(self, mock_automator_class):
        """Test session initialization."""
        from claude.vscode_session import ClaudeVSCodeSession

        temp_dir = Path(tempfile.mkdtemp())
        revisions_dir = temp_dir / "revisions"
        revisions_dir.mkdir()

        try:
            session = ClaudeVSCodeSession(
                rev_id="rev_0001",
                revisions_root=revisions_dir,
                settings={}
            )

            assert session.rev_id == "rev_0001"
            assert not session.started
            assert session.prompt_count == 0

            # Check I/O directory created
            io_dir = temp_dir / ".aegis_revisions" / "rev_0001" / "claude_io"
            assert io_dir.exists()

        finally:
            shutil.rmtree(temp_dir)

    @patch('claude.vscode_session.VSCodeAutomator')
    def test_start_session(self, mock_automator_class):
        """Test starting a session."""
        from claude.vscode_session import ClaudeVSCodeSession

        temp_dir = Path(tempfile.mkdtemp())
        revisions_dir = temp_dir / "revisions"
        revisions_dir.mkdir()

        try:
            mock_automator = Mock()
            mock_automator_class.return_value = mock_automator

            session = ClaudeVSCodeSession(
                rev_id="rev_0001",
                revisions_root=revisions_dir,
                settings={}
            )

            session.start(goal="Test goal", workdir=temp_dir)

            assert session.started
            assert session.goal == "Test goal"

            # Verify automator methods called
            mock_automator.launch.assert_called_once()
            mock_automator.new_claude_chat.assert_called_once()

        finally:
            shutil.rmtree(temp_dir)

    @patch('claude.vscode_session.VSCodeAutomator')
    def test_send_prompt(self, mock_automator_class):
        """Test sending a prompt."""
        from claude.vscode_session import ClaudeVSCodeSession

        temp_dir = Path(tempfile.mkdtemp())
        revisions_dir = temp_dir / "revisions"
        revisions_dir.mkdir()

        try:
            mock_automator = Mock()
            mock_automator_class.return_value = mock_automator

            session = ClaudeVSCodeSession(
                rev_id="rev_0001",
                revisions_root=revisions_dir,
                settings={}
            )

            session.start(goal="Test", workdir=None)

            prompt_num = session.send_prompt("test prompt")

            assert prompt_num == 1
            assert session.prompt_count == 1

            # Verify prompt file created
            io_dir = temp_dir / ".aegis_revisions" / "rev_0001" / "claude_io"
            prompt_file = io_dir / "prompt_001.txt"
            assert prompt_file.exists()
            assert prompt_file.read_text() == "test prompt"

            # Verify automator called
            mock_automator.send_prompt.assert_called_with("test prompt")

        finally:
            shutil.rmtree(temp_dir)

    @patch('claude.vscode_session.VSCodeAutomator')
    def test_fetch_reply(self, mock_automator_class):
        """Test fetching a reply."""
        from claude.vscode_session import ClaudeVSCodeSession

        temp_dir = Path(tempfile.mkdtemp())
        revisions_dir = temp_dir / "revisions"
        revisions_dir.mkdir()

        try:
            mock_automator = Mock()
            mock_automator.copy_latest_reply.return_value = "test reply"
            mock_automator_class.return_value = mock_automator

            session = ClaudeVSCodeSession(
                rev_id="rev_0001",
                revisions_root=revisions_dir,
                settings={}
            )

            session.start(goal="Test", workdir=None)
            session.send_prompt("test")

            reply = session.fetch_reply()

            assert reply == "test reply"

            # Verify reply file created
            io_dir = temp_dir / ".aegis_revisions" / "rev_0001" / "claude_io"
            reply_file = io_dir / "reply_001.txt"
            assert reply_file.exists()
            assert reply_file.read_text() == "test reply"

        finally:
            shutil.rmtree(temp_dir)

    @patch('claude.vscode_session.VSCodeAutomator')
    def test_context_manager(self, mock_automator_class):
        """Test session as context manager."""
        from claude.vscode_session import ClaudeVSCodeSession

        temp_dir = Path(tempfile.mkdtemp())
        revisions_dir = temp_dir / "revisions"
        revisions_dir.mkdir()

        try:
            mock_automator = Mock()
            mock_automator_class.return_value = mock_automator

            with ClaudeVSCodeSession(
                rev_id="rev_0001",
                revisions_root=revisions_dir,
                settings={}
            ) as session:
                session.start(goal="Test", workdir=None)
                assert session.started

            # After context exit, session should be closed
            assert not session.started

        finally:
            shutil.rmtree(temp_dir)
