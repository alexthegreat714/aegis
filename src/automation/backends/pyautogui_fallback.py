"""
PyAutoGUI fallback backend.

Used only when UI Automation fails or is unavailable.
Provides keyboard/mouse control but should be secondary to UIA.
"""

import sys
import logging
import time
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    import pyautogui
    import pyperclip
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui not available - fallback backend disabled")


class PyAutoGUIFallback:
    """
    PyAutoGUI fallback for actions that UIA cannot handle.

    Limited to keyboard and screenshot operations.
    """

    def __init__(self, dry_run: bool = False):
        """
        Initialize PyAutoGUI fallback.

        Args:
            dry_run: If True, log actions without executing
        """
        if not PYAUTOGUI_AVAILABLE:
            raise ImportError("pyautogui is required for fallback backend")

        self.dry_run = dry_run

        # Safety settings
        if not dry_run:
            pyautogui.FAILSAFE = True  # Move to corner to abort
            pyautogui.PAUSE = 0.1  # Pause between actions

        logger.info(f"PyAutoGUIFallback initialized (dry_run={dry_run})")

    def type_text(self, text: str, interval: float = 0.01) -> bool:
        """
        Type text character by character.

        Args:
            text: Text to type
            interval: Delay between keystrokes

        Returns:
            True if successful
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Type text: {text[:50]}...")
            return True

        try:
            logger.info(f"Typing text ({len(text)} chars)")
            pyautogui.write(text, interval=interval)
            return True

        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return False

    def paste_text(self, text: str) -> bool:
        """
        Paste text using clipboard.

        Args:
            text: Text to paste

        Returns:
            True if successful
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Paste text: {text[:50]}...")
            return True

        try:
            logger.info(f"Pasting text ({len(text)} chars)")
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.2)
            return True

        except Exception as e:
            logger.error(f"Error pasting text: {e}")
            return False

    def hotkey(self, *keys: str) -> bool:
        """
        Send hotkey combination.

        Args:
            *keys: Keys to press (e.g., 'ctrl', 'shift', 'p')

        Returns:
            True if successful
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Hotkey: {'+'.join(keys)}")
            return True

        try:
            logger.info(f"Sending hotkey: {'+'.join(keys)}")
            pyautogui.hotkey(*keys)
            time.sleep(0.3)
            return True

        except Exception as e:
            logger.error(f"Error sending hotkey: {e}")
            return False

    def press_key(self, key: str) -> bool:
        """
        Press single key.

        Args:
            key: Key to press

        Returns:
            True if successful
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Press key: {key}")
            return True

        try:
            logger.info(f"Pressing key: {key}")
            pyautogui.press(key)
            time.sleep(0.2)
            return True

        except Exception as e:
            logger.error(f"Error pressing key: {e}")
            return False

    def screenshot(self, path: str, region: Optional[tuple] = None) -> bool:
        """
        Take screenshot.

        Args:
            path: Path to save screenshot
            region: Optional (x, y, width, height) tuple

        Returns:
            True if successful
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Screenshot: {path}")
            return True

        try:
            logger.info(f"Taking screenshot: {path}")

            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()

            screenshot.save(path)
            return True

        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return False

    def get_screen_size(self) -> tuple[int, int]:
        """
        Get screen dimensions.

        Returns:
            Tuple of (width, height)
        """
        if self.dry_run:
            return (1920, 1080)  # Default for dry run

        return pyautogui.size()
