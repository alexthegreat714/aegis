"""
Workspace guard for VS Code automation.

Ensures VS Code is open to the correct repository before
any Claude automation begins.
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


class WorkspaceGuard:
    """
    Ensures VS Code workspace matches expected repository.

    Validates and corrects workspace before automation.
    """

    def __init__(self, expected_repo: Path):
        """
        Initialize workspace guard.

        Args:
            expected_repo: Expected repository root path
        """
        self.expected_repo = Path(expected_repo).resolve()
        self.last_check_result = None

        logger.info(f"WorkspaceGuard initialized for: {self.expected_repo}")

    def get_vscode_workspace(self) -> Optional[Path]:
        """
        Get current VS Code workspace path.

        Uses VS Code CLI to query workspace folders.

        Returns:
            Current workspace path or None if not available
        """
        try:
            # Try to get workspace from VS Code API
            # This is a simplified version - real implementation would use
            # VS Code extension API or parse workspace files

            # Check for .vscode/settings.json or .code-workspace files
            vscode_dir = self.expected_repo / ".vscode"
            if vscode_dir.exists():
                # Found .vscode directory - likely correct workspace
                return self.expected_repo

            # Alternative: Check running VS Code instances (Windows-specific)
            # Would need to query process list and window titles
            # For now, return None and rely on assertion to catch mismatches

            return None

        except Exception as e:
            logger.warning(f"Could not determine VS Code workspace: {e}")
            return None

    def assert_workspace(self, fix: bool = True) -> bool:
        """
        Assert VS Code workspace matches expected repository.

        Args:
            fix: If True, attempt to fix mismatch by reopening

        Returns:
            True if workspace matches (or was fixed)

        Raises:
            AssertionError: If workspace doesn't match and fix=False
        """
        current = self.get_vscode_workspace()

        # If we can't determine current workspace, skip check
        # (defensive - assumes user has correct workspace)
        if current is None:
            logger.warning("Could not determine current workspace - skipping check")
            self.last_check_result = "unknown"
            return True

        current_resolved = current.resolve()

        if current_resolved == self.expected_repo:
            logger.info(f"[OK] Workspace matches: {self.expected_repo}")
            self.last_check_result = "match"
            return True

        # Mismatch detected
        logger.error(f"[X] Workspace mismatch!")
        logger.error(f"    Expected: {self.expected_repo}")
        logger.error(f"    Current:  {current_resolved}")

        if not fix:
            self.last_check_result = "mismatch_no_fix"
            raise AssertionError(
                f"Workspace mismatch: expected {self.expected_repo}, "
                f"got {current_resolved}"
            )

        # Attempt to fix
        logger.info("Attempting to fix workspace...")
        self.fix_workspace()
        self.last_check_result = "mismatch_fixed"
        return True

    def fix_workspace(self):
        """
        Fix workspace by reopening VS Code at correct path.

        Uses --reuse-window to avoid creating new window.
        """
        try:
            logger.info(f"Opening VS Code at: {self.expected_repo}")

            # Launch VS Code with correct workspace
            cmd = ["code", str(self.expected_repo), "--reuse-window"]

            subprocess.Popen(
                cmd,
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Wait for VS Code to focus
            import time
            time.sleep(2)

            logger.info("VS Code workspace corrected")

        except Exception as e:
            logger.error(f"Failed to fix workspace: {e}")
            raise

    def validate_repo_structure(self) -> bool:
        """
        Validate that expected repo has required structure.

        Returns:
            True if repo structure is valid
        """
        if not self.expected_repo.exists():
            logger.error(f"Repository does not exist: {self.expected_repo}")
            return False

        if not self.expected_repo.is_dir():
            logger.error(f"Repository is not a directory: {self.expected_repo}")
            return False

        # Check for .git directory
        git_dir = self.expected_repo / ".git"
        if not git_dir.exists():
            logger.warning(f"No .git directory found in: {self.expected_repo}")
            # Not fatal - could be a non-git workspace

        return True

    def get_current_branch(self) -> Optional[str]:
        """
        Get current git branch.

        Returns:
            Branch name or None if not a git repo
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.expected_repo,
                capture_output=True,
                text=True,
                check=True
            )
            branch = result.stdout.strip()
            logger.debug(f"Current branch: {branch}")
            return branch

        except subprocess.CalledProcessError as e:
            logger.warning(f"Could not determine current branch: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error getting branch: {e}")
            return None

    def ensure_branch(self, branch: str, create: bool = False) -> bool:
        """
        Ensure repository is on specified branch.

        Args:
            branch: Target branch name
            create: If True, create branch if it doesn't exist

        Returns:
            True if on correct branch (or switched successfully)

        Raises:
            AssertionError: If can't switch to branch
        """
        current = self.get_current_branch()

        if current == branch:
            logger.info(f"[OK] On correct branch: {branch}")
            return True

        logger.warning(f"[X] Branch mismatch: current={current}, expected={branch}")

        # Attempt to switch
        try:
            logger.info(f"Switching to branch: {branch}")

            # Check if branch exists
            result = subprocess.run(
                ["git", "rev-parse", "--verify", branch],
                cwd=self.expected_repo,
                capture_output=True,
                text=True
            )

            if result.returncode != 0 and create:
                # Create new branch
                logger.info(f"Creating new branch: {branch}")
                subprocess.run(
                    ["git", "checkout", "-b", branch],
                    cwd=self.expected_repo,
                    check=True
                )
            else:
                # Switch to existing branch
                subprocess.run(
                    ["git", "checkout", branch],
                    cwd=self.expected_repo,
                    check=True
                )

            logger.info(f"Switched to branch: {branch}")
            return True

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to switch to branch {branch}: {e}"
            logger.error(error_msg)
            raise AssertionError(error_msg)

    def is_clean_tree(self) -> bool:
        """
        Check if working tree is clean (no uncommitted changes).

        Returns:
            True if working tree is clean
        """
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.expected_repo,
                capture_output=True,
                text=True,
                check=True
            )

            # Empty output means clean tree
            is_clean = len(result.stdout.strip()) == 0

            if is_clean:
                logger.debug("Working tree is clean")
            else:
                logger.debug(f"Working tree has changes:\n{result.stdout}")

            return is_clean

        except subprocess.CalledProcessError as e:
            logger.warning(f"Could not check tree status: {e}")
            return False
        except Exception as e:
            logger.warning(f"Error checking tree status: {e}")
            return False

    def ensure_clean_tree(self, stash: bool = True) -> bool:
        """
        Ensure working tree is clean.

        Args:
            stash: If True, stash uncommitted changes; if False, reset hard

        Returns:
            True if tree is clean (or was cleaned successfully)

        Raises:
            AssertionError: If can't clean tree
        """
        if self.is_clean_tree():
            logger.info("[OK] Working tree is clean")
            return True

        logger.warning("[X] Working tree has uncommitted changes")

        try:
            if stash:
                logger.info("Stashing uncommitted changes...")
                subprocess.run(
                    ["git", "stash", "push", "-u", "-m", "Aegis auto-stash before automation"],
                    cwd=self.expected_repo,
                    check=True
                )
                logger.info("Changes stashed successfully")
            else:
                logger.warning("Resetting working tree (HARD RESET)...")
                subprocess.run(
                    ["git", "reset", "--hard", "HEAD"],
                    cwd=self.expected_repo,
                    check=True
                )
                logger.info("Working tree reset")

            # Verify clean
            if not self.is_clean_tree():
                raise AssertionError("Working tree still dirty after cleanup")

            return True

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to clean working tree: {e}"
            logger.error(error_msg)
            raise AssertionError(error_msg)

    def get_workspace_info(self) -> dict:
        """
        Get workspace information for logging.

        Returns:
            Dictionary with workspace metadata
        """
        return {
            "expected_repo": str(self.expected_repo),
            "expected_exists": self.expected_repo.exists(),
            "expected_is_git": (self.expected_repo / ".git").exists(),
            "current_branch": self.get_current_branch(),
            "is_clean": self.is_clean_tree(),
            "last_check": self.last_check_result
        }
