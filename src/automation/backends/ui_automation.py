"""
Windows UI Automation backend.

Uses UIAutomation COM API to interact with UI elements semantically
(no coordinate clicking, no OCR).
"""

import sys
import logging
import time
from typing import Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Platform check
if sys.platform != 'win32':
    raise NotImplementedError("UI Automation backend requires Windows")

try:
    import pywinauto
    from pywinauto import Application
    from pywinauto.findwindows import ElementNotFoundError
    from pywinauto.controls.uiawrapper import UIAWrapper
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    logger.warning("pywinauto not available - UI Automation backend disabled")


class UIAutomationBackend:
    """
    Windows UI Automation backend using pywinauto.

    Provides semantic UI interaction without coordinates or OCR.
    """

    def __init__(self, dry_run: bool = False):
        """
        Initialize UI Automation backend.

        Args:
            dry_run: If True, log actions without executing
        """
        if not PYWINAUTO_AVAILABLE:
            raise ImportError("pywinauto is required for UI Automation backend")

        self.dry_run = dry_run
        self.app = None
        self.window = None

        logger.info(f"UIAutomationBackend initialized (dry_run={dry_run})")

    def connect_window(self, title_hint: str, timeout: int = 10) -> bool:
        """
        Connect to window by title hint.

        Args:
            title_hint: Window title substring
            timeout: Maximum wait time in seconds

        Returns:
            True if connected
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Connect to window: {title_hint}")
            return True

        try:
            logger.info(f"Connecting to window: {title_hint}")

            # Connect to application
            self.app = Application(backend='uia').connect(
                title_re=f".*{title_hint}.*",
                timeout=timeout
            )

            # Get main window
            windows = self.app.windows()
            if not windows:
                logger.error(f"No windows found matching: {title_hint}")
                return False

            self.window = windows[0]
            logger.info(f"Connected to window: {self.window.window_text()}")
            return True

        except ElementNotFoundError:
            logger.error(f"Window not found: {title_hint}")
            return False
        except Exception as e:
            logger.error(f"Error connecting to window: {e}")
            return False

    def find_button(
        self,
        label: str,
        timeout: int = 10,
        parent: Optional[UIAWrapper] = None
    ) -> Optional[UIAWrapper]:
        """
        Find button by label text.

        Args:
            label: Button label text
            timeout: Maximum wait time in seconds
            parent: Optional parent element to search within

        Returns:
            Button element or None if not found
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Find button: {label}")
            return None

        if not self.window and not parent:
            logger.error("No window connected")
            return None

        search_root = parent if parent else self.window

        try:
            logger.debug(f"Searching for button: {label}")

            # Try multiple search strategies
            strategies = [
                # Exact match
                lambda: search_root.child_window(title=label, control_type="Button"),
                # Case-insensitive
                lambda: search_root.child_window(title_re=f"(?i){label}", control_type="Button"),
                # Partial match
                lambda: search_root.child_window(title_re=f".*{label}.*", control_type="Button"),
            ]

            for strategy in strategies:
                try:
                    button = strategy()
                    if button.exists(timeout=timeout/len(strategies)):
                        logger.info(f"Found button: {label}")
                        return button
                except Exception:
                    continue

            logger.warning(f"Button not found: {label}")
            return None

        except Exception as e:
            logger.error(f"Error finding button '{label}': {e}")
            return None

    def click_button(self, label: str, timeout: int = 10) -> bool:
        """
        Click button by label.

        Args:
            label: Button label text
            timeout: Maximum wait time in seconds

        Returns:
            True if clicked successfully
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Click button: {label}")
            return True

        button = self.find_button(label, timeout=timeout)

        if not button:
            logger.error(f"Cannot click - button not found: {label}")
            return False

        try:
            logger.info(f"Clicking button: {label}")
            button.click()
            time.sleep(0.5)  # Brief pause after click
            return True

        except Exception as e:
            logger.error(f"Error clicking button '{label}': {e}")
            return False

    def wait_button(self, label: str, timeout: int = 30) -> bool:
        """
        Wait for button to appear.

        Args:
            label: Button label text
            timeout: Maximum wait time in seconds

        Returns:
            True if button appears within timeout
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Wait for button: {label}")
            return True

        logger.info(f"Waiting for button: {label} (timeout={timeout}s)")

        start_time = time.time()
        poll_interval = 0.5

        while time.time() - start_time < timeout:
            button = self.find_button(label, timeout=poll_interval)
            if button:
                logger.info(f"Button appeared: {label}")
                return True

            time.sleep(poll_interval)

        logger.error(f"Timeout waiting for button: {label}")
        return False

    def get_all_buttons(self) -> List[str]:
        """
        Get all button labels in current window.

        Useful for debugging and discovering available actions.

        Returns:
            List of button label texts
        """
        if self.dry_run or not self.window:
            return []

        try:
            buttons = self.window.descendants(control_type="Button")
            labels = [btn.window_text() for btn in buttons if btn.window_text()]
            return labels

        except Exception as e:
            logger.error(f"Error getting buttons: {e}")
            return []

    def focus_window(self) -> bool:
        """
        Bring window to foreground.

        Returns:
            True if focused successfully
        """
        if self.dry_run:
            logger.info("[DRY-RUN] Focus window")
            return True

        if not self.window:
            logger.error("No window connected")
            return False

        try:
            self.window.set_focus()
            time.sleep(0.3)
            return True

        except Exception as e:
            logger.error(f"Error focusing window: {e}")
            return False

    def assert_window_exists(self, title_hint: str, timeout: int = 5) -> bool:
        """
        Assert window exists.

        Args:
            title_hint: Window title substring
            timeout: Maximum wait time

        Returns:
            True if window exists

        Raises:
            AssertionError: If window not found
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Assert window exists: {title_hint}")
            return True

        try:
            app = Application(backend='uia').connect(
                title_re=f".*{title_hint}.*",
                timeout=timeout
            )
            logger.info(f"Window exists: {title_hint}")
            return True

        except ElementNotFoundError:
            raise AssertionError(f"Window not found: {title_hint}")
        except Exception as e:
            raise AssertionError(f"Error checking window: {e}")
