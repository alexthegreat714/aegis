"""
Interactive reasoning pause system.

Allows user to interrupt Aegis during reasoning/action phases.
"""

import time
import msvcrt
import sys
from typing import Optional, Callable
from datetime import datetime

from aegis_logging.logger import AegisLogger


class InteractivePause:
    """
    Non-blocking pause system with timeout.

    Allows user to interrupt during reasoning/action windows.
    """

    def __init__(self, logger: AegisLogger, default_timeout: int = 60):
        """
        Initialize interactive pause system.

        Args:
            logger: Logging system
            default_timeout: Default timeout in seconds
        """
        self.logger = logger
        self.default_timeout = default_timeout
        self.last_command: Optional[str] = None

    def wait_for_input(
        self,
        prompt_message: str = "Press key to interrupt (60s timeout)...",
        timeout: int = None,
        allowed_commands: list = None
    ) -> Optional[str]:
        """
        Wait for user input with timeout (non-blocking on Windows).

        Args:
            prompt_message: Message to display
            timeout: Timeout in seconds (uses default if None)
            allowed_commands: List of allowed commands (None = accept anything)

        Returns:
            User command string or None if timeout
        """
        if timeout is None:
            timeout = self.default_timeout

        if allowed_commands is None:
            allowed_commands = ["pause", "skip", "abort", "approve", "view", "continue"]

        print(f"\n{prompt_message}")
        print(f"Commands: {', '.join(allowed_commands)}")
        print(f"Timeout: {timeout}s")
        print("> ", end="", flush=True)

        start_time = time.time()
        user_input = ""

        while True:
            elapsed = time.time() - start_time

            if elapsed >= timeout:
                print("\n[Interactive] Timeout - continuing automatically")
                self.logger.log_event(
                    event_type="interactive_timeout",
                    data={"timeout": timeout, "elapsed": elapsed},
                    status="info"
                )
                return None

            # Check for keyboard input (Windows-specific)
            if msvcrt.kbhit():
                char = msvcrt.getwch()

                if char == '\r' or char == '\n':  # Enter key
                    print()  # New line
                    command = user_input.strip().lower()

                    if command in allowed_commands:
                        self.last_command = command
                        self.logger.log_event(
                            event_type="interactive_command",
                            data={"command": command, "elapsed": elapsed},
                            status="info"
                        )
                        return command
                    elif command == "":
                        # Empty input = continue
                        self.last_command = "continue"
                        return "continue"
                    else:
                        print(f"[Interactive] Unknown command: {command}")
                        print(f"Allowed: {', '.join(allowed_commands)}")
                        print("> ", end="", flush=True)
                        user_input = ""
                        continue

                elif char == '\x08':  # Backspace
                    if user_input:
                        user_input = user_input[:-1]
                        print('\b \b', end="", flush=True)

                else:
                    user_input += char
                    print(char, end="", flush=True)

            time.sleep(0.1)  # Small delay to avoid busy-waiting

    def pause_for_reasoning(
        self,
        reasoning_text: str,
        risk_level: str = "medium",
        timeout: int = None
    ) -> str:
        """
        Pause after displaying reasoning, allow user to respond.

        Args:
            reasoning_text: The reasoning to display
            risk_level: Risk level (low/medium/high)
            timeout: Custom timeout in seconds

        Returns:
            User command or "continue" if timeout
        """
        # Determine timeout based on risk
        if timeout is None:
            if risk_level == "high":
                timeout = 120  # 2 minutes for high-risk
            elif risk_level == "medium":
                timeout = 60  # 1 minute for medium-risk
            else:
                timeout = 30  # 30 seconds for low-risk

        # Display reasoning
        print("\n" + "=" * 60)
        print("AEGIS REASONING")
        print("=" * 60)
        print(reasoning_text)
        print("=" * 60)
        print(f"Risk Level: {risk_level.upper()}")
        print("=" * 60)

        # Log reasoning
        self.logger.log_event(
            event_type="reasoning_displayed",
            data={
                "reasoning": reasoning_text[:500],  # Truncate for log
                "risk_level": risk_level,
                "timestamp": datetime.now().isoformat()
            },
            status="info"
        )

        # Wait for input
        command = self.wait_for_input(
            prompt_message=f"Review reasoning (Risk: {risk_level}). What should I do?",
            timeout=timeout,
            allowed_commands=["pause", "skip", "abort", "approve", "view", "continue"]
        )

        return command or "continue"

    def pause_before_action(
        self,
        action_description: str,
        action_type: str,
        parameters: dict,
        requires_approval: bool = False,
        timeout: int = None
    ) -> str:
        """
        Pause before executing action, allow user to approve/skip/abort.

        Args:
            action_description: Human-readable action description
            action_type: Intent type
            parameters: Action parameters
            requires_approval: If True, forces approval (no auto-continue)
            timeout: Custom timeout

        Returns:
            User command ("approve", "skip", "abort", or "continue")
        """
        print("\n" + "=" * 60)
        print("PENDING ACTION")
        print("=" * 60)
        print(f"Action: {action_description}")
        print(f"Type: {action_type}")
        print(f"Parameters: {parameters}")
        print("=" * 60)

        if requires_approval:
            print("** APPROVAL REQUIRED - Will not auto-continue **")
            print("=" * 60)

        # Log action pause
        self.logger.log_event(
            event_type="action_pause",
            data={
                "action": action_description,
                "type": action_type,
                "requires_approval": requires_approval
            },
            status="info"
        )

        if requires_approval:
            # Must get explicit approval - no timeout
            while True:
                command = self.wait_for_input(
                    prompt_message="Approval required. Type 'approve' to execute or 'abort' to cancel:",
                    timeout=timeout or 300,  # 5 min max
                    allowed_commands=["approve", "abort", "skip"]
                )

                if command in ["approve", "abort", "skip"]:
                    return command
                elif command is None:
                    print("[Interactive] Timeout reached, but approval required. Please respond.")
                    continue
        else:
            # Auto-continue allowed
            command = self.wait_for_input(
                prompt_message="Action ready. Approve/Skip/Abort or wait for auto-continue:",
                timeout=timeout or 60,
                allowed_commands=["approve", "skip", "abort", "continue"]
            )

            return command or "continue"

    def display_reasoning_history(self, last_n: int = 5) -> None:
        """
        Display last N reasoning steps from logs.

        Args:
            last_n: Number of recent reasoning steps to show
        """
        # TODO: Query SQLite for recent reasoning events
        print(f"\n[Interactive] Displaying last {last_n} reasoning steps...")
        print("[Interactive] (Not implemented - would query aegis.db)")
