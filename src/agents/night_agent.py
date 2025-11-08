"""
Autonomous Night Agent for Aegis.

Loads build docs from docs/builds/*.md and executes them autonomously
with desktop automation, Claude interaction, and full revision control.
"""

import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from cli.revision import RevisionSystem
from claude.vscode_session import ClaudeVSCodeSession
from claude.prompts import build_night_cycle_prompt
from claude.limit_guard import SessionLimitDetector
from automation.desktop_executor import DesktopExecutor
from automation.workspace_guard import WorkspaceGuard
from automation.actions import (
    FocusAction,
    AssertWorkspaceAction,
    ClickButtonAction,
    WaitButtonAction,
    ScreenshotAction
)

logger = logging.getLogger(__name__)


class NightAgent:
    """
    Autonomous development agent for overnight cycles.

    Loads build goals, executes Claude sessions with desktop automation,
    handles session limits, and generates comprehensive reports.
    """

    def __init__(
        self,
        repo_root: Path,
        config: Optional[Dict[str, Any]] = None,
        dry_run: bool = False
    ):
        """
        Initialize night agent.

        Args:
            repo_root: Repository root path
            config: Configuration dictionary
            dry_run: If True, simulate actions without execution
        """
        self.repo_root = Path(repo_root)
        self.config = config or {}
        self.dry_run = dry_run

        # Initialize systems
        self.rev_system = RevisionSystem(repo_root=self.repo_root)
        self.limit_detector = SessionLimitDetector(config=self.config)
        self.workspace_guard = WorkspaceGuard(expected_repo=self.repo_root)

        # Desktop automation
        screenshot_dir = self.repo_root / ".aegis_revisions" / "screenshots"
        self.desktop = DesktopExecutor(
            repo_root=self.repo_root,
            dry_run=self.dry_run,
            screenshot_dir=screenshot_dir
        )

        # Agent state
        self.current_goal = None
        self.current_revision = None
        self.goals_completed = []
        self.goals_failed = []

        logger.info(f"NightAgent initialized (dry_run={dry_run})")
        logger.info(f"  Repository: {self.repo_root}")

    def load_build_docs(self, docs_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Load build goal documents from docs/builds/*.md.

        Args:
            docs_dir: Directory containing build docs (defaults to docs/builds)

        Returns:
            List of goal dictionaries with metadata
        """
        if docs_dir is None:
            docs_dir = self.repo_root / "docs" / "builds"

        if not docs_dir.exists():
            logger.warning(f"Build docs directory not found: {docs_dir}")
            return []

        goals = []
        for doc_file in sorted(docs_dir.glob("*.md")):
            try:
                content = doc_file.read_text(encoding='utf-8')

                # Extract metadata from front matter (if present)
                # For now, use simple parsing
                goal = {
                    "file": doc_file,
                    "name": doc_file.stem,
                    "content": content,
                    "priority": 0,  # Could parse from front matter
                    "max_rounds": 3  # Could parse from front matter
                }

                goals.append(goal)
                logger.info(f"Loaded build doc: {doc_file.name}")

            except Exception as e:
                logger.error(f"Error loading build doc {doc_file}: {e}")

        logger.info(f"Loaded {len(goals)} build goals")
        return goals

    def run_autonomous(
        self,
        max_goals: int = 5,
        max_rounds_per_goal: int = 3,
        auto_approve: bool = True
    ) -> Dict[str, Any]:
        """
        Run fully autonomous night cycle.

        Args:
            max_goals: Maximum number of goals to attempt
            max_rounds_per_goal: Maximum rounds per goal
            auto_approve: Auto-approve passing revisions

        Returns:
            Summary dictionary with results
        """
        logger.info("=" * 70)
        logger.info("NIGHT AGENT - AUTONOMOUS MODE")
        logger.info("=" * 70)

        start_time = datetime.now(timezone.utc)

        # Prepare workspace
        logger.info("\n[1/4] Preparing workspace...")
        self._prepare_workspace()

        # Load goals
        logger.info("\n[2/4] Loading build goals...")
        goals = self.load_build_docs()

        if not goals:
            logger.warning("No build goals found - nothing to do")
            return {
                "status": "no_goals",
                "goals_completed": [],
                "goals_failed": [],
                "duration_seconds": 0
            }

        # Limit goals
        goals = goals[:max_goals]
        logger.info(f"Processing {len(goals)} goals (max={max_goals})")

        # Execute goals
        logger.info("\n[3/4] Executing build goals...")

        for i, goal in enumerate(goals, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"GOAL {i}/{len(goals)}: {goal['name']}")
            logger.info(f"{'='*60}\n")

            self.current_goal = goal

            try:
                result = self._execute_goal(
                    goal=goal,
                    max_rounds=max_rounds_per_goal,
                    auto_approve=auto_approve
                )

                if result["approved"]:
                    self.goals_completed.append({
                        "goal": goal['name'],
                        "revision": result["rev_id"],
                        "rounds": result["rounds_used"]
                    })
                    logger.info(f"\n[OK] Goal '{goal['name']}' COMPLETED")
                else:
                    self.goals_failed.append({
                        "goal": goal['name'],
                        "reason": result.get("failure_reason", "Unknown"),
                        "rounds": result["rounds_used"]
                    })
                    logger.warning(f"\n[X] Goal '{goal['name']}' FAILED")

            except Exception as e:
                logger.error(f"Error executing goal '{goal['name']}': {e}", exc_info=True)
                self.goals_failed.append({
                    "goal": goal['name'],
                    "reason": str(e),
                    "rounds": 0
                })

        # Generate report
        logger.info("\n[4/4] Generating report...")
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        summary = {
            "status": "completed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "goals_attempted": len(goals),
            "goals_completed": self.goals_completed,
            "goals_failed": self.goals_failed
        }

        logger.info("\n" + "=" * 70)
        logger.info("NIGHT AGENT - SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Goals attempted: {len(goals)}")
        logger.info(f"Goals completed: {len(self.goals_completed)}")
        logger.info(f"Goals failed: {len(self.goals_failed)}")
        logger.info(f"Duration: {duration:.0f}s ({duration/60:.1f} minutes)")
        logger.info("=" * 70)

        return summary

    def _prepare_workspace(self):
        """Prepare workspace before automation."""
        logger.info("Validating workspace...")

        # Ensure clean working tree
        self.workspace_guard.ensure_clean_tree(stash=True)

        # Ensure on correct branch (master by default)
        target_branch = self.config.get("automation", {}).get("target_branch", "master")
        self.workspace_guard.ensure_branch(target_branch)

        # Focus VS Code window
        logger.info("Focusing VS Code...")
        focus_action = FocusAction(title_hint="Visual Studio Code")
        result = self.desktop.execute(focus_action)

        if not result["success"]:
            logger.warning("Could not focus VS Code - continuing anyway")

        # Assert workspace
        assert_action = AssertWorkspaceAction(expected=str(self.repo_root))
        result = self.desktop.execute(assert_action)

        if not result["success"]:
            raise RuntimeError("Workspace assertion failed")

        logger.info("Workspace ready")

    def _execute_goal(
        self,
        goal: Dict[str, Any],
        max_rounds: int = 3,
        auto_approve: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a single build goal with retries.

        Args:
            goal: Goal dictionary
            max_rounds: Maximum retry rounds
            auto_approve: Auto-approve passing revisions

        Returns:
            Execution result dictionary
        """
        result = {
            "goal": goal["name"],
            "rev_id": None,
            "rounds_used": 0,
            "approved": False,
            "failure_reason": None
        }

        failures = []

        for round_num in range(1, max_rounds + 1):
            logger.info(f"\nRound {round_num}/{max_rounds}")

            try:
                # Create revision
                rev_id = self.rev_system.cmd_new(
                    f"Night Agent: {goal['name']} (Round {round_num})"
                )
                result["rev_id"] = rev_id
                self.current_revision = rev_id
                logger.info(f"  Created revision: {rev_id}")

                # Build prompt
                prompt = self._build_prompt(goal, round_num, failures)

                # Execute Claude session with desktop automation
                session_result = self._execute_claude_session(
                    rev_id=rev_id,
                    prompt=prompt,
                    goal_name=goal["name"]
                )

                if not session_result["success"]:
                    failures.append(session_result.get("error", "Unknown error"))
                    logger.warning(f"  Claude session failed: {session_result.get('error')}")
                    result["rounds_used"] = round_num
                    continue

                # Wait for user to apply changes (in future, could be automated)
                logger.info("\n  Waiting for code changes to be applied...")
                if not self.dry_run:
                    input("  Press Enter when changes are applied...")

                # Run tests via revision approval
                logger.info("  Running tests...")
                approve_result = self.rev_system.cmd_approve(rev_id)

                if approve_result == 0:
                    # Success!
                    result["approved"] = True
                    result["rounds_used"] = round_num
                    logger.info(f"  [OK] Tests passed - revision approved!")
                    return result
                else:
                    # Tests failed
                    failures.append("Tests failed")
                    logger.warning(f"  [X] Tests failed")
                    result["rounds_used"] = round_num

            except Exception as e:
                logger.error(f"  Round {round_num} error: {e}")
                failures.append(str(e))
                result["rounds_used"] = round_num

        # All rounds exhausted
        result["failure_reason"] = f"All {max_rounds} rounds failed"
        return result

    def _build_prompt(
        self,
        goal: Dict[str, Any],
        round_num: int,
        failures: List[str]
    ) -> str:
        """
        Build Claude prompt for goal.

        Args:
            goal: Goal dictionary
            round_num: Current round number
            failures: List of previous failure messages

        Returns:
            Formatted prompt text
        """
        prompt_parts = [
            f"# Night Agent Build Goal - Round {round_num}",
            f"\n## Goal: {goal['name']}",
            f"\n{goal['content']}"
        ]

        if failures and round_num > 1:
            prompt_parts.append("\n## Previous Round Failures")
            for i, failure in enumerate(failures, 1):
                prompt_parts.append(f"{i}. {failure}")

        prompt_parts.append("\n## Instructions")
        prompt_parts.append("- Implement the goal as described")
        prompt_parts.append("- Ensure all tests pass")
        prompt_parts.append("- Follow repository coding standards")
        prompt_parts.append("- Keep changes focused and minimal")

        return '\n'.join(prompt_parts)

    def _execute_claude_session(
        self,
        rev_id: str,
        prompt: str,
        goal_name: str
    ) -> Dict[str, Any]:
        """
        Execute Claude session with desktop automation and limit handling.

        Args:
            rev_id: Revision ID
            prompt: Prompt text
            goal_name: Goal name for logging

        Returns:
            Session result dictionary
        """
        try:
            # Check for blocked state from previous session
            blocked_state = self.limit_detector.load_blocked_state()
            if blocked_state and not self.limit_detector.should_resume(blocked_state):
                logger.warning("Claude session limit still active - waiting...")
                self.limit_detector.wait_for_reset(blocked_state)

            # Take pre-session screenshot
            screenshot_action = ScreenshotAction(
                path=str(self.desktop.screenshot_dir / f"{rev_id}_pre_session.png")
            )
            self.desktop.execute(screenshot_action)

            # Send prompt to Claude
            logger.info("  Sending prompt to Claude...")

            with ClaudeVSCodeSession(
                rev_id=rev_id,
                revisions_root=self.repo_root / "revisions",
                settings=self.config
            ) as session:
                session.start(goal=goal_name, workdir=self.repo_root)
                prompt_num, reply = session.send_and_fetch(prompt)

            logger.info(f"  Received reply ({len(reply)} chars)")

            # Check for limit message in reply
            if self.limit_detector.detect_limit_in_text(reply):
                logger.warning("  Claude session limit detected in reply")

                # Save blocked state
                self.limit_detector.save_blocked_state(
                    revision_id=rev_id,
                    prompt=prompt,
                    metadata={"goal": goal_name}
                )

                return {
                    "success": False,
                    "error": "Claude session limit reached",
                    "limit_detected": True
                }

            # Wait for "Apply Changes" button
            logger.info("  Waiting for Apply Changes button...")
            wait_action = WaitButtonAction(label="Apply Changes", timeout=30)
            wait_result = self.desktop.execute(wait_action)

            if not wait_result["success"]:
                logger.warning("  Apply Changes button not found")

            # Take post-session screenshot
            screenshot_action = ScreenshotAction(
                path=str(self.desktop.screenshot_dir / f"{rev_id}_post_session.png")
            )
            self.desktop.execute(screenshot_action)

            return {
                "success": True,
                "prompt_num": prompt_num,
                "reply_length": len(reply)
            }

        except Exception as e:
            logger.error(f"Claude session error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def clear_backlog(self, docs_dir: Optional[Path] = None):
        """
        Mark all build docs as processed (for testing/reset).

        Args:
            docs_dir: Directory containing build docs
        """
        if docs_dir is None:
            docs_dir = self.repo_root / "docs" / "builds"

        processed_dir = docs_dir / ".processed"
        processed_dir.mkdir(exist_ok=True)

        count = 0
        for doc_file in docs_dir.glob("*.md"):
            # Move to .processed subdirectory
            target = processed_dir / doc_file.name
            doc_file.rename(target)
            count += 1
            logger.info(f"Marked as processed: {doc_file.name}")

        logger.info(f"Cleared {count} build docs")


def run_night_agent(
    repo_root: Optional[Path] = None,
    max_goals: int = 5,
    max_rounds: int = 3,
    auto_approve: bool = True,
    config: Optional[Dict[str, Any]] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Run night agent (convenience function).

    Args:
        repo_root: Repository root path
        max_goals: Maximum goals to attempt
        max_rounds: Maximum rounds per goal
        auto_approve: Auto-approve passing revisions
        config: Configuration dictionary
        dry_run: Dry-run mode

    Returns:
        Summary dictionary
    """
    if repo_root is None:
        # Auto-detect
        current = Path.cwd()
        while current != current.parent:
            if (current / '.git').exists():
                repo_root = current
                break
            current = current.parent
        else:
            repo_root = Path.cwd()

    agent = NightAgent(repo_root=repo_root, config=config, dry_run=dry_run)
    return agent.run_autonomous(
        max_goals=max_goals,
        max_rounds_per_goal=max_rounds,
        auto_approve=auto_approve
    )
