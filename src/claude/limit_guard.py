"""
Claude session limit detection and handling.

Detects when Claude hits daily API limits and manages pause/resume logic.
"""

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import re

logger = logging.getLogger(__name__)


class SessionLimitDetector:
    """
    Detects Claude session limits via OCR and manages wait/resume logic.

    Monitors for limit messages, calculates reset times, and persists
    pending work for automatic resumption.
    """

    # Default limit detection patterns
    DEFAULT_LIMIT_PATTERNS = [
        r"session\s+limit\s+reached",
        r"quota\s+exceeded",
        r"try\s+again\s+later",
        r"resets\s+(?:at\s+)?12\s*am",
        r"daily\s+limit",
        r"rate\s+limit",
    ]

    def __init__(
        self,
        state_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize session limit detector.

        Args:
            state_dir: Directory for state persistence
            config: Configuration dictionary with Claude settings
        """
        self.config = config or {}

        # State directory
        if state_dir:
            self.state_dir = Path(state_dir)
        else:
            self.state_dir = Path.cwd() / ".aegis_state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.state_dir / "claude_session_block.json"

        # Configuration
        claude_config = self.config.get("claude", {})
        self.daily_reset_hour = claude_config.get("daily_reset_hour", 0)
        self.resume_buffer_minutes = claude_config.get("resume_buffer_minutes", 2)
        self.limit_patterns = claude_config.get("limiter_match_text", self.DEFAULT_LIMIT_PATTERNS)

        logger.info(f"SessionLimitDetector initialized")
        logger.info(f"  State dir: {self.state_dir}")
        logger.info(f"  Reset hour: {self.daily_reset_hour:02d}:00")
        logger.info(f"  Resume buffer: {self.resume_buffer_minutes} minutes")

    def detect_limit_in_text(self, text: str) -> bool:
        """
        Check if text contains session limit indicators.

        Args:
            text: Text to search (e.g., OCR output or UI text)

        Returns:
            True if limit detected
        """
        if not text:
            return False

        text_lower = text.lower()

        for pattern in self.limit_patterns:
            if isinstance(pattern, str):
                # Treat as regex pattern
                if re.search(pattern, text_lower, re.IGNORECASE):
                    logger.warning(f"Limit pattern matched: {pattern}")
                    return True

        return False

    def detect_limit_in_screenshot(
        self,
        screenshot_path: Path,
        ocr_backend=None
    ) -> Tuple[bool, Optional[str]]:
        """
        Use OCR to detect limit message in screenshot.

        Args:
            screenshot_path: Path to screenshot image
            ocr_backend: OCR backend instance (if None, uses pytesseract)

        Returns:
            Tuple of (limit_detected, extracted_text)
        """
        try:
            if ocr_backend:
                # Use provided OCR backend
                text = ocr_backend.extract_text(str(screenshot_path))
            else:
                # Use pytesseract directly
                import pytesseract
                from PIL import Image

                img = Image.open(screenshot_path)
                text = pytesseract.image_to_string(img)

            detected = self.detect_limit_in_text(text)
            return detected, text

        except Exception as e:
            logger.error(f"OCR error while checking screenshot: {e}")
            return False, None

    def calculate_reset_time(
        self,
        current_time: Optional[datetime] = None
    ) -> datetime:
        """
        Calculate next reset time based on configured reset hour.

        Args:
            current_time: Reference time (defaults to now UTC)

        Returns:
            Next reset datetime (UTC)
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        # Ensure we're working in UTC
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        # Calculate next reset time
        reset_time = current_time.replace(
            hour=self.daily_reset_hour,
            minute=0,
            second=0,
            microsecond=0
        )

        # If reset time has already passed today, use tomorrow
        if reset_time <= current_time:
            reset_time += timedelta(days=1)

        # Add buffer
        reset_time += timedelta(minutes=self.resume_buffer_minutes)

        logger.info(f"Calculated reset time: {reset_time.isoformat()}")
        return reset_time

    def save_blocked_state(
        self,
        revision_id: str,
        prompt: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Save blocked state to disk for later resumption.

        Args:
            revision_id: Current revision ID
            prompt: Pending prompt text
            metadata: Additional metadata to save

        Returns:
            Path to saved state file
        """
        current_time = datetime.now(timezone.utc)
        reset_time = self.calculate_reset_time(current_time)

        state = {
            "blocked_at": current_time.isoformat(),
            "retry_at": reset_time.isoformat(),
            "pending_revision": revision_id,
            "pending_prompt": prompt,
            "metadata": metadata or {}
        }

        self.state_file.write_text(json.dumps(state, indent=2), encoding='utf-8')
        logger.info(f"Blocked state saved: {self.state_file}")
        logger.info(f"  Retry at: {reset_time.isoformat()}")

        return self.state_file

    def load_blocked_state(self) -> Optional[Dict[str, Any]]:
        """
        Load previously saved blocked state.

        Returns:
            State dictionary or None if no saved state
        """
        if not self.state_file.exists():
            return None

        try:
            state = json.loads(self.state_file.read_text(encoding='utf-8'))
            logger.info(f"Loaded blocked state from: {self.state_file}")
            return state

        except Exception as e:
            logger.error(f"Error loading blocked state: {e}")
            return None

    def clear_blocked_state(self):
        """Clear saved blocked state."""
        if self.state_file.exists():
            self.state_file.unlink()
            logger.info("Blocked state cleared")

    def should_resume(self, state: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if enough time has passed to resume.

        Args:
            state: Blocked state dict (loads from file if None)

        Returns:
            True if ready to resume
        """
        if state is None:
            state = self.load_blocked_state()

        if not state:
            return False

        try:
            retry_at = datetime.fromisoformat(state["retry_at"])
            current_time = datetime.now(timezone.utc)

            # Ensure timezone-aware comparison
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)

            can_resume = current_time >= retry_at

            if can_resume:
                logger.info("Resume time reached - ready to continue")
            else:
                wait_seconds = (retry_at - current_time).total_seconds()
                logger.info(f"Still waiting - {wait_seconds:.0f}s until retry")

            return can_resume

        except Exception as e:
            logger.error(f"Error checking resume time: {e}")
            return False

    def wait_for_reset(
        self,
        state: Optional[Dict[str, Any]] = None,
        check_interval: int = 60
    ):
        """
        Block until reset time is reached.

        Args:
            state: Blocked state dict (loads from file if None)
            check_interval: How often to check (seconds)
        """
        if state is None:
            state = self.load_blocked_state()

        if not state:
            logger.warning("No blocked state to wait for")
            return

        try:
            retry_at = datetime.fromisoformat(state["retry_at"])

            # Ensure timezone-aware
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)

            logger.info(f"Waiting for reset at {retry_at.isoformat()}...")

            while True:
                current_time = datetime.now(timezone.utc)

                if current_time >= retry_at:
                    logger.info("Reset time reached!")
                    break

                wait_seconds = (retry_at - current_time).total_seconds()

                # Log progress every check interval
                hours = int(wait_seconds // 3600)
                minutes = int((wait_seconds % 3600) // 60)
                logger.info(f"Waiting... {hours}h {minutes}m remaining")

                # Sleep for check interval or remaining time, whichever is shorter
                sleep_time = min(check_interval, wait_seconds)
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.warning("Wait interrupted by user")
            raise
        except Exception as e:
            logger.error(f"Error during wait: {e}")
            raise


def create_limit_detector(
    state_dir: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None
) -> SessionLimitDetector:
    """
    Create session limit detector instance (convenience function).

    Args:
        state_dir: State directory path
        config: Configuration dictionary

    Returns:
        Configured SessionLimitDetector instance
    """
    return SessionLimitDetector(state_dir=state_dir, config=config)
