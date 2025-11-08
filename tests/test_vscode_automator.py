"""
Tests for VS Code automator.

These tests use mocking and are marked with @pytest.mark.vs
to skip by default (run with: pytest -m vs)
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Skip tests by default unless -m vs is specified
pytestmark = pytest.mark.vs


@patch('vscode.automator.PYWINAUTO_AVAILABLE', True)
@patch('vscode.automator.PYAUTOGUI_AVAILABLE', True)
class TestVSCodeAutomator:
    """Test VS Code automator with mocked dependencies."""

    def test_initialization(self):
        """Test automator initialization."""
        from vscode.automator import VSCodeAutomator

        settings = {
            'vscode': {
                'exe_path': 'code',
                'dry_run': True
            }
        }

        automator = VSCodeAutomator(settings=settings)

        assert automator.exe_path == 'code'
        assert automator.dry_run is True

    def test_dry_run_mode(self):
        """Test that dry_run prevents actual execution."""
        from vscode.automator import VSCodeAutomator

        settings = {'vscode': {'dry_run': True}}
        automator = VSCodeAutomator(settings=settings)

        # Should not raise errors in dry run mode
        automator.launch()
        automator.focus_window()
        automator.open_command_palette()

    @patch('vscode.automator.subprocess')
    def test_launch(self, mock_subprocess):
        """Test launching VS Code."""
        from vscode.automator import VSCodeAutomator

        settings = {'vscode': {'dry_run': False, 'exe_path': 'code'}}
        automator = VSCodeAutomator(settings=settings)

        automator.launch(code_path='/path/to/project')

        mock_subprocess.Popen.assert_called_once()

    @patch('vscode.automator.pyautogui')
    def test_open_command_palette(self, mock_pyautogui):
        """Test opening command palette."""
        from vscode.automator import VSCodeAutomator

        settings = {'vscode': {'dry_run': False}}
        automator = VSCodeAutomator(settings=settings)

        automator.open_command_palette()

        mock_pyautogui.hotkey.assert_called_with('ctrl', 'shift', 'p')

    @patch('vscode.automator.pyautogui')
    @patch('vscode.automator.pyperclip')
    def test_paste_text(self, mock_pyperclip, mock_pyautogui):
        """Test pasting text."""
        from vscode.automator import VSCodeAutomator

        settings = {'vscode': {'dry_run': False}}
        automator = VSCodeAutomator(settings=settings)

        automator.paste_text("test content")

        mock_pyperclip.copy.assert_called_with("test content")
        mock_pyautogui.hotkey.assert_called_with('ctrl', 'v')

    @patch('vscode.automator.pyautogui')
    def test_submit(self, mock_pyautogui):
        """Test submit action."""
        from vscode.automator import VSCodeAutomator

        settings = {'vscode': {'dry_run': False}}
        automator = VSCodeAutomator(settings=settings)

        automator.submit()

        mock_pyautogui.press.assert_called_with('enter')


def test_import_safety_windows():
    """Test that module imports safely on Windows."""
    if sys.platform != 'win32':
        pytest.skip("Windows-only test")

    # Should import without errors (even if dependencies missing)
    try:
        from vscode import automator
        assert automator is not None
    except ImportError as e:
        # Acceptable if pywinauto/pyautogui not installed
        assert 'pywinauto' in str(e) or 'pyautogui' in str(e)


def test_import_fails_non_windows():
    """Test that module raises on non-Windows platforms."""
    if sys.platform == 'win32':
        pytest.skip("Non-Windows test")

    with pytest.raises(NotImplementedError):
        from vscode import automator
