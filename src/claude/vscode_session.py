"""
Claude VS Code session manager.

Handles high-level interaction with Claude through VS Code extension,
including prompt sending, reply fetching, and I/O persistence.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from vscode.automator import VSCodeAutomator


logger = logging.getLogger(__name__)


class ClaudeVSCodeSession:
    """
    Manages a Claude conversation session via VS Code extension.

    Persists all I/O to revision directory for audit trail.
    """

    def __init__(
        self,
        rev_id: str,
        revisions_root: Path,
        settings: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Claude session.

        Args:
            rev_id: Revision ID for this session
            revisions_root: Root directory for revisions
            settings: Configuration dictionary
        """
        self.rev_id = rev_id
        self.revisions_root = Path(revisions_root)
        self.settings = settings or {}

        # Create I/O directory for this revision
        self.io_dir = (
            self.revisions_root.parent / ".aegis_revisions" /
            rev_id / "claude_io"
        )
        self.io_dir.mkdir(parents=True, exist_ok=True)

        # Initialize automator
        self.automator = VSCodeAutomator(settings=self.settings)

        # Session state
        self.started = False
        self.goal = None
        self.workdir = None
        self.prompt_count = 0

        logger.info(f"ClaudeVSCodeSession initialized for {rev_id}")

    def start(self, goal: str, workdir: Optional[Path] = None):
        """
        Start a new Claude session.

        Args:
            goal: Goal/description for this session
            workdir: Optional working directory to open in VS Code
        """
        self.goal = goal
        self.workdir = workdir

        logger.info(f"Starting Claude session: {goal}")

        # Launch/focus VS Code
        if workdir:
            self.automator.launch(str(workdir))
        else:
            self.automator.focus_window()

        # Start new Claude chat
        self.automator.new_claude_chat()

        self.started = True

        # Write session metadata
        self._write_metadata({
            "rev_id": self.rev_id,
            "goal": goal,
            "workdir": str(workdir) if workdir else None,
            "started_at": datetime.utcnow().isoformat() + 'Z'
        })

    def send_prompt(self, prompt_text: str) -> int:
        """
        Send prompt to Claude.

        Args:
            prompt_text: Prompt to send

        Returns:
            Prompt number (for tracking)
        """
        if not self.started:
            raise RuntimeError("Session not started. Call start() first.")

        self.prompt_count += 1
        prompt_num = self.prompt_count

        logger.info(f"Sending prompt #{prompt_num} ({len(prompt_text)} chars)")

        # Save prompt to file
        prompt_file = self.io_dir / f"prompt_{prompt_num:03d}.txt"
        prompt_file.write_text(prompt_text, encoding='utf-8')

        # Send via automator
        self.automator.send_prompt(prompt_text)

        # Wait for response
        self.automator.wait_for_response()

        return prompt_num

    def fetch_reply(self, prompt_num: Optional[int] = None) -> str:
        """
        Fetch latest reply from Claude.

        Args:
            prompt_num: Optional prompt number for filename

        Returns:
            Reply text
        """
        if not self.started:
            raise RuntimeError("Session not started. Call start() first.")

        if prompt_num is None:
            prompt_num = self.prompt_count

        logger.info(f"Fetching reply for prompt #{prompt_num}")

        # Copy reply from VS Code
        reply_text = self.automator.copy_latest_reply()

        if not reply_text:
            logger.warning("No reply text captured")
            reply_text = "[ERROR: Could not capture reply]"

        # Save reply to file
        reply_file = self.io_dir / f"reply_{prompt_num:03d}.txt"
        reply_file.write_text(reply_text, encoding='utf-8')

        logger.info(f"Reply saved: {reply_file.name} ({len(reply_text)} chars)")

        return reply_text

    def send_and_fetch(self, prompt_text: str) -> tuple[int, str]:
        """
        Send prompt and fetch reply in one call.

        Args:
            prompt_text: Prompt to send

        Returns:
            Tuple of (prompt_num, reply_text)
        """
        prompt_num = self.send_prompt(prompt_text)
        reply = self.fetch_reply(prompt_num)
        return prompt_num, reply

    def _write_metadata(self, data: Dict[str, Any]):
        """
        Write session metadata.

        Args:
            data: Metadata dictionary
        """
        meta_file = self.io_dir / "session_meta.json"

        # Load existing if present
        if meta_file.exists():
            with open(meta_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing.update(data)
            data = existing

        # Write updated metadata
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def close(self):
        """Close session and write final metadata."""
        if self.started:
            self._write_metadata({
                "ended_at": datetime.utcnow().isoformat() + 'Z',
                "total_prompts": self.prompt_count
            })
            self.started = False
            logger.info(f"Session closed: {self.rev_id}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
