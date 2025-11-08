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
        settings: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize night cycle manager.

        Args:
            repo_root: Path to repository root
            settings: Configuration dictionary
        """
        self.repo_root = Path(repo_root)
        self.settings = settings or {}

        # Initialize revision system
        self.rev_system = RevisionSystem(repo_root=self.repo_root)

        # Cycle state
        self.goal = None
        self.current_round = 0
        self.failures = []

        logger.info(f"NightCycle initialized for {self.repo_root}")

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

            # Save reply to revision
            reply_file = (
                self.repo_root / ".aegis_revisions" / rev_id / "reply.txt"
            )
            reply_file.write_text(reply, encoding='utf-8')

            # Step 4: Run tests
            logger.info(f"[4/5] Running tests...")

            # NOTE: This assumes user has manually applied Claude's suggested changes
            # A more advanced version would parse code blocks from reply and apply them
            logger.warning("  Manual step required: Apply Claude's code changes before tests")

            input("\nPress Enter when code changes are applied and ready for testing...")

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
