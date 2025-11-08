"""
Windows UI Automation backend.

Uses UIAutomation COM API to interact with UI elements semantically.
Includes OCR fallback for button detection when UIA fails.
"""

import sys
import logging
import time
from typing import Optional, List, Tuple, Dict, Any
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

# OCR support
try:
    import pytesseract
    from PIL import Image, ImageGrab
    import pyautogui
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR dependencies not available - OCR fallback disabled")


class UIAutomationBackend:
    """
    Windows UI Automation backend using pywinauto.

    Provides semantic UI interaction without coordinates or OCR.
    """

    def __init__(
        self,
        dry_run: bool = False,
        ocr_enabled: bool = True,
        ocr_confidence_threshold: float = 0.80
    ):
        """
        Initialize UI Automation backend.

        Args:
            dry_run: If True, log actions without executing
            ocr_enabled: Enable OCR fallback for button detection
            ocr_confidence_threshold: Minimum confidence for OCR matches (0.0-1.0)
        """
        if not PYWINAUTO_AVAILABLE:
            raise ImportError("pywinauto is required for UI Automation backend")

        self.dry_run = dry_run
        self.app = None
        self.window = None

        # OCR configuration
        self.ocr_enabled = ocr_enabled and OCR_AVAILABLE
        self.ocr_confidence_threshold = ocr_confidence_threshold

        logger.info(f"UIAutomationBackend initialized (dry_run={dry_run})")
        logger.info(f"  OCR fallback: {'enabled' if self.ocr_enabled else 'disabled'}")
        if self.ocr_enabled:
            logger.info(f"  OCR confidence threshold: {ocr_confidence_threshold:.2f}")

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
        Click button by label (tries UIA first, then OCR fallback).

        Args:
            label: Button label text
            timeout: Maximum wait time in seconds

        Returns:
            True if clicked successfully
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Click button: {label}")
            return True

        # Try UIA first
        button = self.find_button(label, timeout=timeout)

        if button:
            try:
                logger.info(f"Clicking button via UIA: {label}")
                button.click()
                time.sleep(0.5)  # Brief pause after click
                return True

            except Exception as e:
                logger.warning(f"UIA click failed for '{label}': {e}")
                # Fall through to OCR

        # Try OCR fallback if enabled
        if self.ocr_enabled:
            logger.info(f"Attempting OCR fallback for button: {label}")
            return self.click_button_ocr(label, timeout=timeout)
        else:
            logger.error(f"Cannot click - button not found and OCR disabled: {label}")
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

    def find_button_ocr(
        self,
        label: str,
        timeout: int = 10,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find button using OCR (fallback when UIA fails).

        Args:
            label: Button text to search for
            timeout: Maximum wait time
            region: Optional (left, top, width, height) region to search

        Returns:
            Dictionary with button info (bbox, confidence) or None
        """
        if not self.ocr_enabled:
            logger.warning("OCR is disabled")
            return None

        if self.dry_run:
            logger.info(f"[DRY-RUN] OCR find button: {label}")
            return {"bbox": (0, 0, 100, 50), "confidence": 1.0}

        logger.debug(f"Using OCR to find button: {label}")

        start_time = time.time()
        poll_interval = 0.5

        while time.time() - start_time < timeout:
            try:
                # Capture screenshot
                if region:
                    screenshot = ImageGrab.grab(bbox=region)
                else:
                    screenshot = ImageGrab.grab()

                # Run OCR with detailed data
                ocr_data = pytesseract.image_to_data(
                    screenshot,
                    output_type=pytesseract.Output.DICT
                )

                # Search for matching text
                for i, text in enumerate(ocr_data['text']):
                    if not text.strip():
                        continue

                    # Check if text matches label (case-insensitive)
                    if label.lower() in text.lower():
                        confidence = float(ocr_data['conf'][i]) / 100.0

                        # Check confidence threshold
                        if confidence >= self.ocr_confidence_threshold:
                            # Extract bounding box
                            left = ocr_data['left'][i]
                            top = ocr_data['top'][i]
                            width = ocr_data['width'][i]
                            height = ocr_data['height'][i]

                            # Adjust for region offset if specified
                            if region:
                                left += region[0]
                                top += region[1]

                            bbox = (left, top, width, height)

                            logger.info(
                                f"OCR found button '{label}': "
                                f"confidence={confidence:.2f}, bbox={bbox}"
                            )

                            return {
                                "text": text,
                                "bbox": bbox,
                                "confidence": confidence,
                                "center": (left + width // 2, top + height // 2)
                            }
                        else:
                            logger.debug(
                                f"OCR match '{text}' below threshold: "
                                f"confidence={confidence:.2f}"
                            )

                time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"OCR error: {e}")
                time.sleep(poll_interval)

        logger.warning(f"OCR timeout finding button: {label}")
        return None

    def click_button_ocr(
        self,
        label: str,
        timeout: int = 10,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> bool:
        """
        Click button using OCR detection.

        Args:
            label: Button text to search for
            timeout: Maximum wait time
            region: Optional search region

        Returns:
            True if clicked successfully
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] OCR click button: {label}")
            return True

        button_info = self.find_button_ocr(label, timeout=timeout, region=region)

        if not button_info:
            logger.error(f"Cannot click - button not found via OCR: {label}")
            return False

        try:
            # Click at center of bounding box
            center_x, center_y = button_info["center"]

            logger.info(
                f"Clicking button '{label}' at ({center_x}, {center_y}) "
                f"[confidence={button_info['confidence']:.2f}]"
            )

            pyautogui.click(center_x, center_y)
            time.sleep(0.5)  # Brief pause after click

            return True

        except Exception as e:
            logger.error(f"Error clicking button via OCR '{label}': {e}")
            return False

    def extract_text_ocr(
        self,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> str:
        """
        Extract all text from screen using OCR.

        Args:
            region: Optional (left, top, width, height) region

        Returns:
            Extracted text
        """
        if not self.ocr_enabled:
            logger.warning("OCR is disabled")
            return ""

        if self.dry_run:
            logger.info("[DRY-RUN] OCR extract text")
            return "Sample OCR text"

        try:
            # Capture screenshot
            if region:
                screenshot = ImageGrab.grab(bbox=region)
            else:
                screenshot = ImageGrab.grab()

            # Extract text
            text = pytesseract.image_to_string(screenshot)
            return text

        except Exception as e:
            logger.error(f"OCR text extraction error: {e}")
            return ""
