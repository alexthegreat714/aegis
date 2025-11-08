"""
Aegis Night Cycle - Autonomous development with Claude.

Manages iterative development cycles:
1. Create revision
2. Generate and send prompt to Claude
3. Save Claude's response
4. Run pytest validation
5. Approve/discard based on test results

Each cycle is a self-contained revision with full audit trail.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from cli.revision import RevisionSystem
from claude.vscode_session import ClaudeVSCodeSession
from claude.prompts import build_night_cycle_prompt, build_repo_summary
from claude.limit_guard import SessionLimitDetector
from automation.desktop_executor import DesktopExecutor
from automation.workspace_guard import WorkspaceGuard
from automation.actions import WaitButtonAction, ClickButtonAction


logger = logging.getLogger(__name__)


class NightCycle:
    """
    Manages autonomous development cycles with Claude.

    Each cycle creates a revision, sends a prompt to Claude,
    validates the result, and approves/discards based on tests.
    """

    def __init__(
        self,
        repo_root: Path,
        settings: Optional[Dict[str, Any]] = None,
        use_desktop: bool = False,
        dry_run: bool = False
    ):
        """
        Initialize night cycle manager.

        Args:
            repo_root: Path to repository root
            settings: Configuration dictionary
            use_desktop: Enable desktop automation for button clicking
            dry_run: Dry-run mode for desktop actions
        """
        self.repo_root = Path(repo_root)
        self.settings = settings or {}
        self.use_desktop = use_desktop
        self.dry_run = dry_run

        # Initialize revision system
        self.rev_system = RevisionSystem(repo_root=self.repo_root)

        # Initialize session limit detector
        self.limit_detector = SessionLimitDetector(config=self.settings)

        # Initialize desktop automation (if enabled)
        self.desktop = None
        self.workspace_guard = None
        if use_desktop:
            screenshot_dir = self.repo_root / ".aegis_revisions" / "screenshots"
            self.desktop = DesktopExecutor(
                repo_root=self.repo_root,
                dry_run=dry_run,
                screenshot_dir=screenshot_dir
            )
            self.workspace_guard = WorkspaceGuard(expected_repo=self.repo_root)

        # Cycle state
        self.goal = None
        self.current_round = 0
        self.failures = []

        logger.info(f"NightCycle initialized for {self.repo_root}")
        logger.info(f"  Desktop automation: {'enabled' if use_desktop else 'disabled'}")

    def run_cycle(
        self,
        goal: str,
        max_rounds: int = 3,
        confirm_each: bool = False
    ) -> Dict[str, Any]:
        """
        Run night cycle with specified goal.

        Args:
            goal: Development goal
            max_rounds: Maximum number of rounds to attempt
            confirm_each: If True, pause for confirmation between rounds

        Returns:
            Summary dictionary with cycle results
        """
        self.goal = goal
        self.failures = []

        logger.info(f"Starting night cycle: {goal}")
        logger.info(f"Max rounds: {max_rounds}, Confirm each: {confirm_each}")

        results = {
            "goal": goal,
            "max_rounds": max_rounds,
            "rounds": [],
            "final_status": "incomplete"
        }

        for round_num in range(1, max_rounds + 1):
            self.current_round = round_num

            logger.info(f"\n{'='*60}")
            logger.info(f"ROUND {round_num}/{max_rounds}")
            logger.info(f"{'='*60}\n")

            # Run round
            round_result = self._run_round(round_num)
            results["rounds"].append(round_result)

            # Check result
            if round_result["approved"]:
                logger.info(f"\n[OK] Round {round_num} APPROVED!")
                results["final_status"] = "approved"
                break

            elif round_result["tests_passed"]:
                logger.info(f"\n[OK] Round {round_num} tests passed (awaiting manual review)")
                results["final_status"] = "pending_review"
                break

            else:
                logger.warning(f"\n[X] Round {round_num} FAILED - Tests did not pass")
                self.failures.append(round_result.get("failure_reason", "Unknown failure"))

                # Continue to next round if available
                if round_num < max_rounds:
                    if confirm_each:
                        response = input("\nContinue to next round? (y/N): ").strip().lower()
                        if response != 'y':
                            logger.info("User cancelled cycle")
                            results["final_status"] = "cancelled"
                            break
                else:
                    logger.error("\n[X] All rounds exhausted - Cycle FAILED")
                    results["final_status"] = "failed"

        return results

    def _run_round(self, round_num: int) -> Dict[str, Any]:
        """
        Run a single development round.

        Args:
            round_num: Round number

        Returns:
            Round result dictionary
        """
        result = {
            "round": round_num,
            "rev_id": None,
            "prompt_sent": False,
            "reply_received": False,
            "tests_passed": False,
            "approved": False,
            "failure_reason": None
        }

        try:
            # Step 1: Create revision
            logger.info(f"[1/5] Creating revision for round {round_num}...")
            rev_id = self.rev_system.cmd_new(f"{self.goal} (Night Cycle Round {round_num})")
            result["rev_id"] = rev_id
            logger.info(f"  Created: {rev_id}")

            # Step 2: Generate prompt
            logger.info(f"[2/5] Generating prompt...")
            repo_summary = build_repo_summary(self.repo_root)
            prompt = build_night_cycle_prompt(
                goal=self.goal,
                round_num=round_num,
                prev_failures=self.failures if round_num > 1 else None
            )

            prompt_file = (
                self.repo_root / ".aegis_revisions" / rev_id / "prompt.txt"
            )
            prompt_file.write_text(prompt, encoding='utf-8')
            logger.info(f"  Prompt saved: {prompt_file}")

            # Step 3: Send to Claude and get response
            logger.info(f"[3/5] Sending to Claude via VS Code...")

            # Check for session limit block
            blocked_state = self.limit_detector.load_blocked_state()
            if blocked_state and not self.limit_detector.should_resume(blocked_state):
                logger.warning("  Claude session limit active - waiting for reset...")
                self.limit_detector.wait_for_reset(blocked_state)
                self.limit_detector.clear_blocked_state()

            with ClaudeVSCodeSession(
                rev_id=rev_id,
                revisions_root=self.repo_root / "revisions",
                settings=self.settings
            ) as session:
                session.start(goal=self.goal, workdir=self.repo_root)
                result["prompt_sent"] = True

                prompt_num, reply = session.send_and_fetch(prompt)
                result["reply_received"] = True

                logger.info(f"  Reply received ({len(reply)} chars)")

                # Check for session limit in reply
                if self.limit_detector.detect_limit_in_text(reply):
                    logger.warning("  Session limit detected in Claude's reply")
                    self.limit_detector.save_blocked_state(
                        revision_id=rev_id,
                        prompt=prompt,
                        metadata={"goal": self.goal, "round": round_num}
                    )
                    result["failure_reason"] = "Claude session limit reached"
                    return result

            # Save reply to revision
            reply_file = (
                self.repo_root / ".aegis_revisions" / rev_id / "reply.txt"
            )
            reply_file.write_text(reply, encoding='utf-8')

            # Step 3.5: Apply changes with desktop automation (if enabled)
            if self.use_desktop and self.desktop:
                logger.info(f"[3.5/5] Waiting for Apply Changes button...")

                # Wait for button to appear
                wait_action = WaitButtonAction(label="Apply Changes", timeout=30)
                wait_result = self.desktop.execute(wait_action)

                if wait_result["success"]:
                    logger.info("  Clicking Apply Changes button...")
                    click_action = ClickButtonAction(label="Apply Changes")
                    click_result = self.desktop.execute(click_action)

                    if click_result["success"]:
                        logger.info("  Changes applied automatically")
                        import time
                        time.sleep(2)  # Wait for changes to be written
                    else:
                        logger.warning("  Failed to click Apply Changes - continuing manually")
                        input("\nPress Enter when code changes are applied...")
                else:
                    logger.warning("  Apply Changes button not found - continuing manually")
                    input("\nPress Enter when code changes are applied...")
            else:
                # Manual mode
                logger.warning("  Manual step required: Apply Claude's code changes before tests")
                input("\nPress Enter when code changes are applied and ready for testing...")

            # Step 4: Run tests
            logger.info(f"[4/5] Running tests...")

            # Run tests via revision system
            approve_result = self.rev_system.cmd_approve(rev_id)

            if approve_result == 0:
                result["tests_passed"] = True
                result["approved"] = True
                logger.info(f"  [OK] Tests passed and revision approved!")
            else:
                result["tests_passed"] = False
                result["approved"] = False
                result["failure_reason"] = "Tests failed"
                logger.warning(f"  [X] Tests failed - revision remains draft")

        except Exception as e:
            logger.error(f"Round {round_num} error: {e}", exc_info=True)
            result["failure_reason"] = str(e)

        return result


def night_cycle(
    goal: str,
    max_rounds: int = 3,
    confirm_each: bool = False,
    repo_root: Optional[Path] = None,
    settings: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run night cycle (convenience function).

    Args:
        goal: Development goal
        max_rounds: Maximum number of rounds
        confirm_each: Pause for confirmation between rounds
        repo_root: Repository root (auto-detected if None)
        settings: Configuration dictionary

    Returns:
        Cycle results dictionary
    """
    if repo_root is None:
        # Auto-detect repo root
        current = Path.cwd()
        while current != current.parent:
            if (current / '.git').exists():
                repo_root = current
                break
            current = current.parent
        else:
            repo_root = Path.cwd()

    cycle = NightCycle(repo_root=repo_root, settings=settings)
    return cycle.run_cycle(goal=goal, max_rounds=max_rounds, confirm_each=confirm_each)
