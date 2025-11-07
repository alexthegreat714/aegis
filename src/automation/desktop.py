"""
Desktop automation using pyautogui and pywinauto.

Handles mouse, keyboard, and window operations.
"""

from typing import Tuple, Optional, Dict, Any
from pathlib import Path
import time

# Day 3: Uncommented for real execution
try:
    import pyautogui
    # Set safety defaults
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    pyautogui.PAUSE = 0.1  # Small pause between commands
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("[Desktop] WARNING: pyautogui not available, using dry-run mode")

from aegis_logging.logger import AegisLogger
from intents.intent_schema import ActionResult


class DesktopAutomation:
    """
    Desktop UI automation.

    Handles mouse clicks, keyboard input, screenshots, and window management.
    """

    def __init__(self, logger: AegisLogger, settings: Dict[str, Any], dry_run: bool = False):
        """
        Initialize desktop automation.

        Args:
            logger: Logging system
            settings: System settings
            dry_run: If True, simulate actions without executing (Day 3)
        """
        self.logger = logger
        self.settings = settings
        self.dry_run = dry_run or not PYAUTOGUI_AVAILABLE
        self.action_delay_ms = settings.get("automation", {}).get("action_delay_ms", 100)

    def _pre_action_delay(self) -> None:
        """Delay before UI action for stability."""
        time.sleep(self.action_delay_ms / 1000.0)

    def mouse_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> ActionResult:
        """
        Click mouse at coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button ('left', 'right', 'middle')
            clicks: Number of clicks (1 for single, 2 for double)

        Returns:
            ActionResult with execution status
        """
        start_time = time.time()

        self.logger.log_action(
            action_type="mouse_click",
            parameters={"x": x, "y": y, "button": button, "clicks": clicks},
            status="pending"
        )

        self._pre_action_delay()

        try:
            if self.dry_run:
                print(f"[Desktop] DRY RUN: Click at ({x}, {y}) with {button} button, {clicks} click(s)")
            else:
                # Day 3: Real execution
                pyautogui.click(x, y, clicks=clicks, button=button)
                print(f"[Desktop] Clicked at ({x}, {y}) with {button} button, {clicks} click(s)")

            self.logger.log_action(
                action_type="mouse_click",
                parameters={"x": x, "y": y, "button": button},
                status="success"
            )

            execution_time = (time.time() - start_time) * 1000
            return ActionResult(
                success=True,
                details={"x": x, "y": y, "button": button, "clicks": clicks},
                execution_time_ms=execution_time
            )

        except Exception as e:
            self.logger.log_action(
                action_type="mouse_click",
                parameters={"x": x, "y": y, "button": button},
                status="error"
            )

            execution_time = (time.time() - start_time) * 1000
            return ActionResult(
                success=False,
                error=str(e),
                details={"x": x, "y": y, "button": button},
                execution_time_ms=execution_time
            )

    def mouse_move(self, x: int, y: int, duration: float = 0.5) -> None:
        """
        Move mouse to coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            duration: Movement duration in seconds
        """
        self._pre_action_delay()

        # TODO: Implement with pyautogui
        # pyautogui.moveTo(x, y, duration=duration)

        print(f"[Desktop] Move mouse to ({x}, {y})")

    def keyboard_type(self, text: str, interval: float = 0.0) -> ActionResult:
        """
        Type text.

        Args:
            text: Text to type
            interval: Interval between keypresses in seconds

        Returns:
            ActionResult with execution status
        """
        start_time = time.time()

        self.logger.log_action(
            action_type="keyboard_type",
            parameters={"text": text[:100], "length": len(text)},
            status="pending"
        )

        self._pre_action_delay()

        try:
            if self.dry_run:
                print(f"[Desktop] DRY RUN: Type: {text[:50]}...")
            else:
                # Day 3: Real execution
                # Use write() instead of typewrite() for better Unicode support
                pyautogui.write(text, interval=interval)
                print(f"[Desktop] Typed: {text[:50]}...")

            self.logger.log_action(
                action_type="keyboard_type",
                parameters={"text": text[:100]},
                status="success"
            )

            execution_time = (time.time() - start_time) * 1000
            return ActionResult(
                success=True,
                details={"text_length": len(text), "text_preview": text[:100]},
                execution_time_ms=execution_time
            )

        except Exception as e:
            self.logger.log_action(
                action_type="keyboard_type",
                parameters={"text": text[:100]},
                status="error"
            )

            execution_time = (time.time() - start_time) * 1000
            return ActionResult(
                success=False,
                error=str(e),
                details={"text_length": len(text)},
                execution_time_ms=execution_time
            )

    def keyboard_press(self, key: str) -> None:
        """
        Press a special key.

        Args:
            key: Key name (e.g., 'enter', 'ctrl', 'alt', 'tab')
        """
        self._pre_action_delay()

        # TODO: Implement with pyautogui
        # pyautogui.press(key)

        print(f"[Desktop] Press key: {key}")

    def screenshot(self, save_path: Optional[str] = None) -> ActionResult:
        """
        Take a screenshot.

        Args:
            save_path: Optional path to save screenshot

        Returns:
            ActionResult with execution status and file path
        """
        start_time = time.time()

        if not save_path:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            screenshot_dir = Path(self.settings.get("automation", {}).get("screenshot_dir", "data/screenshots"))
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            save_path = str(screenshot_dir / f"screenshot_{timestamp}.png")

        try:
            if self.dry_run:
                print(f"[Desktop] DRY RUN: Screenshot would be saved to {save_path}")
            else:
                # Day 3: Real execution
                screenshot = pyautogui.screenshot()
                screenshot.save(save_path)
                print(f"[Desktop] Screenshot saved to {save_path}")

            self.logger.log_action(
                action_type="screenshot",
                parameters={"path": save_path},
                status="success"
            )

            execution_time = (time.time() - start_time) * 1000
            return ActionResult(
                success=True,
                details={"path": save_path, "exists": Path(save_path).exists() if not self.dry_run else False},
                execution_time_ms=execution_time
            )

        except Exception as e:
            self.logger.log_action(
                action_type="screenshot",
                parameters={"path": save_path},
                status="error"
            )

            execution_time = (time.time() - start_time) * 1000
            return ActionResult(
                success=False,
                error=str(e),
                details={"path": save_path},
                execution_time_ms=execution_time
            )

    def window_focus(self, window_title: str) -> bool:
        """
        Focus a window by title.

        Args:
            window_title: Window title or partial title

        Returns:
            True if window found and focused
        """
        self._pre_action_delay()

        # TODO: Implement with pywinauto
        # from pywinauto import Application
        # app = Application().connect(title_re=f".*{window_title}.*")
        # app.top_window().set_focus()

        print(f"[Desktop] Focus window: {window_title}")

        return True

    def window_close(self, window_title: str) -> bool:
        """
        Close a window by title.

        Args:
            window_title: Window title or partial title

        Returns:
            True if window found and closed
        """
        self.logger.log_action(
            action_type="window_close",
            parameters={"window_title": window_title},
            status="pending"
        )

        # TODO: Implement with pywinauto
        # app = Application().connect(title_re=f".*{window_title}.*")
        # app.top_window().close()

        print(f"[Desktop] Close window: {window_title}")

        self.logger.log_action(
            action_type="window_close",
            parameters={"window_title": window_title},
            status="success"
        )

        return True

    def get_mouse_position(self) -> Tuple[int, int]:
        """
        Get current mouse position.

        Returns:
            (x, y) coordinates
        """
        # TODO: Implement with pyautogui
        # return pyautogui.position()

        return (0, 0)

    def get_screen_size(self) -> Tuple[int, int]:
        """
        Get screen dimensions.

        Returns:
            (width, height) in pixels
        """
        # TODO: Implement with pyautogui
        # return pyautogui.size()

        return (1920, 1080)
