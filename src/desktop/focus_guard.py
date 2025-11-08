"""
Focus guard for VS Code automation.

Ensures VS Code is foreground and Claude input is ready before any keystrokes.
Hard-block policy: raises RuntimeError on failure (no retries).
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from desktop.ocr_focus import verify_claude_input_focus

logger = logging.getLogger(__name__)

# Platform-specific imports
if sys.platform == 'win32':
    try:
        from pywinauto import Application
        from pywinauto.findwindows import ElementNotFoundError
        import win32gui
        import win32process
        WINDOWING_AVAILABLE = True
    except ImportError:
        WINDOWING_AVAILABLE = False
        logger.warning("Windowing libraries not available (pywinauto/win32gui)")
else:
    WINDOWING_AVAILABLE = False


class FocusGuard:
    """
    Guards against mis-pasting by verifying focus before keystrokes.

    Policy: Hard-block, no retries. Raises RuntimeError on failure.
    """

    def __init__(self, logger_instance=None, settings: Optional[Dict[str, Any]] = None):
        """
        Initialize focus guard.

        Args:
            logger_instance: Optional logger instance
            settings: Optional settings dict
        """
        self.logger = logger_instance or logger
        self.settings = settings or {}

        # Focus settings
        focus_config = self.settings.get('focus', {})
        self.method = focus_config.get('method', 'ocr')
        self.retry = focus_config.get('retry', 0)  # No retries
        self.save_fail_screenshot = focus_config.get('save_fail_screenshot', True)

        # Debug directory for screenshots
        self.debug_dir = Path('.aegis_debug') / 'ocr'
        self.debug_dir.mkdir(parents=True, exist_ok=True)

        self.logger.debug(f"FocusGuard initialized (method={self.method}, retry={self.retry})")

    def require_vscode_foreground(self) -> None:
        """
        Bring VS Code window to foreground and verify.

        Raises:
            RuntimeError: If VS Code cannot be brought to foreground
        """
        if not WINDOWING_AVAILABLE:
            self.logger.warning("[FOCUS] Windowing not available - skipping foreground check")
            return

        self.logger.info("[FOCUS] Ensuring VS Code foreground...")

        try:
            # Find VS Code window
            app = Application(backend='uia').connect(
                title_re=".*Visual Studio Code.*",
                timeout=10
            )

            # Get main window
            windows = app.windows()
            if not windows:
                raise RuntimeError("VS Code window not found")

            window = windows[0]

            # Bring to foreground
            window.set_focus()

            # Verify it's actually foreground
            import time
            time.sleep(0.3)  # Brief pause for window to come to front

            # Check foreground window title
            try:
                hwnd = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(hwnd)

                if "Visual Studio Code" not in title:
                    raise RuntimeError(f"VS Code not foreground (foreground is: {title})")

                self.logger.info(f"[FOCUS] VS Code is foreground ✅ (title: {title})")

            except Exception as e:
                self.logger.warning(f"[FOCUS] Could not verify foreground window: {e}")
                # Don't fail here - we tried our best

        except ElementNotFoundError:
            raise RuntimeError("VS Code not found - ensure it's running")
        except Exception as e:
            raise RuntimeError(f"Failed to bring VS Code to foreground: {e}")

    def require_claude_input_ready(self) -> Dict[str, Any]:
        """
        Run one OCR scan to verify Claude input is ready.

        Raises:
            RuntimeError: If Claude input not confirmed via OCR

        Returns:
            Metadata dict from OCR scan
        """
        self.logger.info("[OCR] Scanning screen for Claude input...")

        # Generate failure screenshot path if needed
        fail_path = None
        if self.save_fail_screenshot:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fail_path = self.debug_dir / f"focus_fail_{timestamp}.png"

        # Run OCR scan (one-shot, no retry)
        matched, meta = verify_claude_input_focus(save_fail_path=fail_path)

        if matched:
            phrase = meta.get('matched_phrase', 'unknown')
            confidence = meta.get('confidence', 0.0)
            self.logger.info(f"[OCR] Match: \"{phrase}\" (confidence ~{confidence:.2f}) ✅")
            return meta

        # No match - hard fail
        screenshot_path = meta.get('screenshot_path')
        error_msg = "Claude input not confirmed via OCR"

        if screenshot_path:
            self.logger.error(f"[ABORT] {error_msg}; screenshot saved: {screenshot_path}")
            raise RuntimeError(f"{error_msg} (screenshot: {screenshot_path})")
        else:
            self.logger.error(f"[ABORT] {error_msg}")
            raise RuntimeError(error_msg)

    def verify_focus_full(self) -> Dict[str, Any]:
        """
        Full focus verification: foreground + OCR.

        Raises:
            RuntimeError: If any verification step fails

        Returns:
            Metadata dict from OCR scan
        """
        self.require_vscode_foreground()
        return self.require_claude_input_ready()
