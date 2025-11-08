"""
VS Code automation driver using pywinauto and pyautogui.

This module provides controlled interaction with VS Code windows,
particularly for Claude VS Code extension automation.

Windows-only for now; raises NotImplementedError on other platforms.
"""

import sys
import time
import logging
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import subprocess
import pyperclip

# Platform check
if sys.platform != 'win32':
    raise NotImplementedError("VS Code automator currently supports Windows only")

try:
    import pywinauto
    from pywinauto import Application
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


logger = logging.getLogger(__name__)


class VSCodeAutomator:
    """
    Automates VS Code interactions with safety guards and logging.

    Reads configuration from settings dict with keys:
    - exe_path: Path to code executable
    - window_title_hint: Window title substring to match
    - claude_new_chat_cmd: Command palette command for new Claude chat
    - input_focus_pause_ms: Delay after focusing input
    - type_pause_ms: Delay between keystrokes
    - paste_mode: Use clipboard paste instead of typing
    - selection_copy_cmd: Keyboard shortcut for copy
    - dry_run: If True, log actions without executing
    """

    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        """
        Initialize VS Code automator.

        Args:
            settings: Configuration dictionary (from config/settings.yaml)
        """
        if not PYWINAUTO_AVAILABLE:
            raise ImportError("pywinauto is required for VS Code automation")
        if not PYAUTOGUI_AVAILABLE:
            raise ImportError("pyautogui is required for VS Code automation")

        self.settings = settings or {}
        self.vscode_config = self.settings.get('vscode', {})

        # Configuration
        self.exe_path = self.vscode_config.get('exe_path', 'code')
        self.window_title_hint = self.vscode_config.get('window_title_hint', 'Visual Studio Code')
        self.claude_new_chat_cmd = self.vscode_config.get('claude_new_chat_cmd', 'Claude: New Chat')
        self.input_focus_pause_ms = self.vscode_config.get('input_focus_pause_ms', 300)
        self.type_pause_ms = self.vscode_config.get('type_pause_ms', 10)
        self.paste_mode = self.vscode_config.get('paste_mode', True)
        self.selection_copy_cmd = self.vscode_config.get('selection_copy_cmd', 'Ctrl+C')
        self.dry_run = self.vscode_config.get('dry_run', False)

        self.app = None
        self.window = None

        logger.info(f"VSCodeAutomator initialized (dry_run={self.dry_run})")

    def _sleep(self, ms: int):
        """Sleep for specified milliseconds."""
        time.sleep(ms / 1000.0)

    def _execute(self, action: str, func, *args, **kwargs):
        """
        Execute action with dry-run guard and logging.

        Args:
            action: Description of action
            func: Function to execute
            *args, **kwargs: Arguments for function

        Returns:
            Result of function or None if dry-run
        """
        logger.info(f"[{'DRY-RUN' if self.dry_run else 'EXEC'}] {action}")

        if self.dry_run:
            return None

        try:
            result = func(*args, **kwargs)
            logger.debug(f"  ✓ {action}")
            return result
        except Exception as e:
            logger.error(f"  ✗ {action}: {e}")
            raise

    def _resolve_vscode_cmd(self) -> str:
        """
        Resolve VS Code executable path in OS-aware manner.

        On Windows, subprocess.Popen with shell=False cannot launch .cmd files,
        so we need to explicitly check for code.cmd first.

        Returns:
            Full path to VS Code executable

        Raises:
            RuntimeError: If VS Code executable not found
        """
        # If exe_path is already a full path that exists, use it
        if os.path.isfile(self.exe_path):
            logger.debug(f"Using configured exe_path: {self.exe_path}")
            return self.exe_path

        # Windows-specific resolution
        if sys.platform == 'win32':
            # Try code.cmd first (preferred on Windows)
            code_cmd = shutil.which('code.cmd')
            if code_cmd:
                logger.debug(f"Resolved VS Code to: {code_cmd}")
                return code_cmd

            # Fall back to code.exe
            code_exe = shutil.which('code.exe')
            if code_exe:
                logger.debug(f"Resolved VS Code to: {code_exe}")
                return code_exe

            # Try the configured exe_path as last resort
            code_generic = shutil.which(self.exe_path)
            if code_generic:
                logger.debug(f"Resolved VS Code to: {code_generic}")
                return code_generic

        else:
            # Linux/macOS: normal code lookup
            code_path = shutil.which(self.exe_path)
            if code_path:
                logger.debug(f"Resolved VS Code to: {code_path}")
                return code_path

        # Not found
        raise RuntimeError(
            f"VS Code executable not found. Tried: {self.exe_path}\n"
            f"Ensure VS Code is installed and 'code' command is on PATH.\n"
            f"On Windows, check that code.cmd exists in PATH."
        )

    def launch(self, code_path: Optional[str] = None):
        """
        Launch VS Code.

        Args:
            code_path: Optional path to open in VS Code
        """
        # Resolve VS Code executable (Windows-safe)
        vscode_exe = self._resolve_vscode_cmd()

        cmd = [vscode_exe]
        if code_path:
            cmd.append(str(code_path))

        def _launch():
            subprocess.Popen(cmd, shell=False)
            self._sleep(2000)  # Wait for VS Code to start

        self._execute(f"Launch VS Code: {' '.join(cmd)}", _launch)

    def focus_window(self, title_hint: Optional[str] = None) -> bool:
        """
        Focus VS Code window.

        Args:
            title_hint: Optional window title substring to match

        Returns:
            True if window found and focused
        """
        title = title_hint or self.window_title_hint

        def _focus():
            try:
                # Find VS Code window
                app = Application(backend='uia').connect(title_re=f".*{title}.*", timeout=10)
                self.app = app

                # Get main window
                windows = app.windows()
                if not windows:
                    raise ElementNotFoundError(f"No windows found matching '{title}'")

                self.window = windows[0]
                self.window.set_focus()
                self._sleep(500)
                return True

            except ElementNotFoundError as e:
                logger.warning(f"Could not find VS Code window: {e}")
                return False

        return self._execute(f"Focus window: {title}", _focus) or False

    def open_command_palette(self):
        """Open VS Code command palette (Ctrl+Shift+P)."""
        def _open():
            pyautogui.hotkey('ctrl', 'shift', 'p')
            self._sleep(500)

        self._execute("Open command palette", _open)

    def run_command(self, command: str):
        """
        Run VS Code command via command palette.

        Args:
            command: Command name to execute
        """
        def _run():
            self.open_command_palette()
            self._sleep(300)

            # Type command
            if self.paste_mode:
                pyperclip.copy(command)
                pyautogui.hotkey('ctrl', 'v')
            else:
                pyautogui.write(command, interval=self.type_pause_ms / 1000.0)

            self._sleep(500)
            pyautogui.press('enter')
            self._sleep(1000)

        self._execute(f"Run command: {command}", _run)

    def focus_claude_input(self):
        """
        Focus Claude extension input field.

        Assumes Claude panel is already open. Uses Tab navigation to reach input.
        """
        def _focus():
            # Click in the Claude panel area (approximate center of screen)
            screen_width, screen_height = pyautogui.size()
            pyautogui.click(screen_width // 2, screen_height - 100)
            self._sleep(300)

            # Tab to input field (may need adjustment per extension version)
            pyautogui.press('tab')
            self._sleep(self.input_focus_pause_ms)

        self._execute("Focus Claude input", _focus)

    def paste_text(self, text: str):
        """
        Paste text into focused field.

        Args:
            text: Text to paste
        """
        def _paste():
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            self._sleep(100)

        self._execute(f"Paste text ({len(text)} chars)", _paste)

    def type_text(self, text: str):
        """
        Type text character by character.

        Args:
            text: Text to type
        """
        def _type():
            pyautogui.write(text, interval=self.type_pause_ms / 1000.0)

        self._execute(f"Type text ({len(text)} chars)", _type)

    def submit(self):
        """Submit current input (press Enter)."""
        def _submit():
            pyautogui.press('enter')
            self._sleep(500)

        self._execute("Submit (Enter)", _submit)

    def copy_latest_reply(self) -> Optional[str]:
        """
        Copy latest Claude reply to clipboard.

        This is a fallback method that uses selection + copy.
        May need adjustment based on Claude extension UI.

        Returns:
            Copied text or None if failed
        """
        def _copy():
            # Clear clipboard
            pyperclip.copy('')

            # Try to select all in conversation (Ctrl+A)
            pyautogui.hotkey('ctrl', 'a')
            self._sleep(300)

            # Copy selection
            pyautogui.hotkey('ctrl', 'c')
            self._sleep(500)

            # Get clipboard content
            result = pyperclip.paste()
            return result if result else None

        return self._execute("Copy latest reply", _copy)

    def new_claude_chat(self):
        """Start a new Claude chat via command palette."""
        self.run_command(self.claude_new_chat_cmd)

    def send_prompt(self, prompt: str):
        """
        Send prompt to Claude.

        Args:
            prompt: Prompt text to send
        """
        self.focus_claude_input()

        if self.paste_mode:
            self.paste_text(prompt)
        else:
            self.type_text(prompt)

        self.submit()

    def wait_for_response(self, timeout_seconds: int = 120) -> bool:
        """
        Wait for Claude to finish responding.

        This is a simple polling implementation. A production version
        would monitor the UI for typing indicators.

        Args:
            timeout_seconds: Maximum wait time

        Returns:
            True if response likely complete
        """
        def _wait():
            logger.info(f"Waiting up to {timeout_seconds}s for Claude response...")
            time.sleep(timeout_seconds)  # Simple wait for now
            return True

        return self._execute(f"Wait for response ({timeout_seconds}s)", _wait) or False
