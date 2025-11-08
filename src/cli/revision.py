"""
Aegis Revision System - Full file snapshot management with STRICT approvals.

This module implements a revision tracking system that:
- Stores full file snapshots (not diffs) in .aegis_revisions/
- Tracks metadata in /revisions/ (git-tracked)
- Enforces STRICT test-passing requirement for approval
- Never auto-applies changes without explicit restore command
"""

import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


class RevisionSystem:
    """Manages Aegis revisions with full file snapshots."""

    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize revision system.

        Args:
            repo_root: Path to repository root (default: auto-detect)
        """
        if repo_root is None:
            # Auto-detect repo root (look for .git directory)
            current = Path(__file__).resolve()
            while current != current.parent:
                if (current / '.git').exists():
                    repo_root = current
                    break
                current = current.parent
            else:
                repo_root = Path.cwd()

        self.repo_root = Path(repo_root)
        self.revisions_dir = self.repo_root / "revisions"
        self.snapshots_dir = self.repo_root / ".aegis_revisions"

        # Ensure directories exist
        self.revisions_dir.mkdir(exist_ok=True)
        self.snapshots_dir.mkdir(exist_ok=True)

    def _next_rev_id(self) -> str:
        """
        Generate next sequential revision ID.

        Returns:
            Next revision ID (e.g., "rev_0001", "rev_0002")
        """
        existing = list(self.revisions_dir.glob("rev_*.json"))
        if not existing:
            return "rev_0001"

        # Extract numbers from existing revisions
        numbers = []
        for meta_file in existing:
            try:
                num = int(meta_file.stem.split('_')[1])
                numbers.append(num)
            except (IndexError, ValueError):
                continue

        next_num = max(numbers) + 1 if numbers else 1
        return f"rev_{next_num:04d}"

    def _collect_changed_files(self) -> List[Path]:
        """
        Collect list of changed files in working tree.

        Uses git status --porcelain to detect changes.

        Returns:
            List of Path objects for changed files
        """
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )

            changed_files = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                # Parse git status output
                # Format: XY filename
                # X = index status, Y = working tree status
                status = line[:2]
                filename = line[3:].strip()

                # Skip deleted files (D status)
                if 'D' in status:
                    continue

                # Handle renames (filename -> new_filename)
                if '->' in filename:
                    filename = filename.split('->')[-1].strip()

                file_path = self.repo_root / filename
                if file_path.exists() and file_path.is_file():
                    changed_files.append(file_path)

            return changed_files

        except subprocess.CalledProcessError:
            # Fallback: no git or error
            return []

    def _snapshot_files(self, files: List[Path], dest_dir: Path):
        """
        Copy full file contents to snapshot directory.

        Args:
            files: List of files to snapshot
            dest_dir: Destination directory for snapshots
        """
        dest_dir.mkdir(parents=True, exist_ok=True)

        for file_path in files:
            if not file_path.exists():
                continue

            # Calculate relative path from repo root
            try:
                rel_path = file_path.relative_to(self.repo_root)
            except ValueError:
                # File is outside repo, skip
                continue

            # Create destination with same structure
            dest_file = dest_dir / rel_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy full file
            shutil.copy2(file_path, dest_file)

    def _run_pytest_quiet(self) -> Tuple[bool, str]:
        """
        Run pytest in quiet mode and capture results.

        Returns:
            Tuple of (passed: bool, summary: str)
        """
        try:
            result = subprocess.run(
                ['pytest', '-q'],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # Parse output for summary line
            output = result.stdout + result.stderr
            summary = None

            for line in output.split('\n'):
                if 'passed' in line.lower():
                    summary = line.strip()
                    break

            if summary is None:
                summary = f"Exit code: {result.returncode}"

            passed = result.returncode == 0
            return passed, summary

        except subprocess.TimeoutExpired:
            return False, "Test timeout (300s exceeded)"
        except Exception as e:
            return False, f"Test execution failed: {str(e)}"

    def _get_head_commit(self) -> str:
        """
        Get current git HEAD commit hash.

        Returns:
            Short commit hash (7 chars) or "unknown"
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"

    def _write_meta_json(self, rev_id: str, data: Dict[str, Any]):
        """
        Write revision metadata to JSON file.

        Args:
            rev_id: Revision ID
            data: Metadata dictionary
        """
        meta_path = self.revisions_dir / f"{rev_id}.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_meta(self, rev_id: str) -> Optional[Dict[str, Any]]:
        """
        Load revision metadata from JSON file.

        Args:
            rev_id: Revision ID

        Returns:
            Metadata dictionary or None if not found
        """
        meta_path = self.revisions_dir / f"{rev_id}.json"
        if not meta_path.exists():
            return None

        with open(meta_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _snapshot_exists(self, rev_id: str) -> bool:
        """
        Check if snapshot directory exists for revision.

        Args:
            rev_id: Revision ID

        Returns:
            True if snapshot directory exists
        """
        snapshot_dir = self.snapshots_dir / rev_id
        return snapshot_dir.exists()

    def cmd_new(self, goal: str) -> str:
        """
        Create new revision with current changes.

        Args:
            goal: Description of what this revision accomplishes

        Returns:
            Revision ID
        """
        # Generate revision ID
        rev_id = self._next_rev_id()

        # Get current state
        head_commit = self._get_head_commit()
        created_utc = datetime.utcnow().isoformat() + 'Z'
        changed_files = self._collect_changed_files()

        # Create snapshot directory
        snapshot_dir = self.snapshots_dir / rev_id
        changed_files_dir = snapshot_dir / "changed_files"

        # Snapshot files (even if empty)
        if changed_files:
            self._snapshot_files(changed_files, changed_files_dir)
        else:
            changed_files_dir.mkdir(parents=True, exist_ok=True)

        # Create placeholder files
        (snapshot_dir / "chat.md").touch()
        (snapshot_dir / "console.log").touch()

        # Build metadata
        file_list = [
            str(f.relative_to(self.repo_root))
            for f in changed_files
        ]

        metadata = {
            "rev_id": rev_id,
            "goal": goal,
            "created_utc": created_utc,
            "head_commit": head_commit,
            "status": "draft",
            "files": file_list,
            "test_summary": None
        }

        # Write metadata
        self._write_meta_json(rev_id, metadata)

        print(f"Created revision: {rev_id}")
        print(f"  Goal: {goal}")
        print(f"  Files: {len(file_list)}")
        print(f"  Snapshot: {snapshot_dir}")

        return rev_id

    def cmd_status(self):
        """Show status of most recent revision."""
        # Find most recent revision
        meta_files = sorted(self.revisions_dir.glob("rev_*.json"), reverse=True)

        if not meta_files:
            print("No revisions found")
            return

        latest = meta_files[0]
        rev_id = latest.stem
        meta = self._load_meta(rev_id)

        if not meta:
            print(f"Error: Cannot load metadata for {rev_id}")
            return

        snapshot_exists = self._snapshot_exists(rev_id)

        print(f"Latest Revision: {rev_id}")
        print(f"  Status: {meta['status']}")
        print(f"  Goal: {meta['goal']}")
        print(f"  Created: {meta['created_utc']}")
        print(f"  Commit: {meta['head_commit']}")
        print(f"  Files: {len(meta['files'])}")
        print(f"  Snapshot: {'[OK] exists' if snapshot_exists else '[X] MISSING'}")

        if meta['test_summary']:
            print(f"  Tests: {meta['test_summary']}")

    def cmd_list(self):
        """List all revisions."""
        meta_files = sorted(self.revisions_dir.glob("rev_*.json"))

        if not meta_files:
            print("No revisions found")
            return

        print(f"{'REV_ID':<12} {'STATUS':<10} {'FILES':<6} {'CREATED':<20} {'GOAL':<50}")
        print("-" * 100)

        for meta_file in meta_files:
            rev_id = meta_file.stem
            meta = self._load_meta(rev_id)

            if not meta:
                continue

            goal_short = meta['goal'][:47] + '...' if len(meta['goal']) > 50 else meta['goal']
            created_short = meta['created_utc'][:19]  # Remove milliseconds and Z

            print(f"{rev_id:<12} {meta['status']:<10} {len(meta['files']):<6} {created_short:<20} {goal_short:<50}")

    def cmd_approve(self, rev_id: str) -> int:
        """
        Approve revision after STRICT test validation.

        Args:
            rev_id: Revision ID to approve

        Returns:
            Exit code (0 = success, 1 = failure)
        """
        # Load metadata
        meta = self._load_meta(rev_id)
        if not meta:
            print(f"Error: Revision {rev_id} not found")
            return 1

        # Verify snapshot exists
        if not self._snapshot_exists(rev_id):
            print(f"Error: Snapshot directory missing for {rev_id}")
            print("Cannot approve revision without valid snapshot")
            return 1

        # Warn if no files
        if not meta['files']:
            print(f"Warning: Revision {rev_id} has no changed files")

        # Run tests (STRICT)
        print(f"Running tests for {rev_id}...")
        passed, summary = self._run_pytest_quiet()

        # Update metadata with test results
        meta['test_summary'] = summary

        if not passed:
            print(f"\n[X] APPROVAL DENIED - Tests failed")
            print(f"  Test summary: {summary}")
            print(f"  Status remains: draft")
            meta['status'] = 'draft'
            self._write_meta_json(rev_id, meta)
            return 1

        # Tests passed - approve
        meta['status'] = 'approved'
        self._write_meta_json(rev_id, meta)

        print(f"\n[OK] APPROVAL GRANTED")
        print(f"  Test summary: {summary}")
        print(f"  Status: approved")
        print(f"\nRevision {rev_id} is approved but NOT automatically applied")
        print(f"Use 'aegis revision restore {rev_id}' to apply changes")

        return 0

    def cmd_discard(self, rev_id: str) -> int:
        """
        Discard revision.

        Args:
            rev_id: Revision ID to discard

        Returns:
            Exit code (0 = success, 1 = failure)
        """
        meta = self._load_meta(rev_id)
        if not meta:
            print(f"Error: Revision {rev_id} not found")
            return 1

        meta['status'] = 'discarded'
        self._write_meta_json(rev_id, meta)

        print(f"Revision {rev_id} discarded")
        print("Snapshot files retained for audit trail")

        return 0

    def cmd_restore(self, rev_id: str) -> int:
        """
        Restore snapshot files to working tree.

        Args:
            rev_id: Revision ID to restore

        Returns:
            Exit code (0 = success, 1 = failure)
        """
        # Load metadata
        meta = self._load_meta(rev_id)
        if not meta:
            print(f"Error: Revision {rev_id} not found")
            return 1

        # Verify snapshot exists
        snapshot_dir = self.snapshots_dir / rev_id / "changed_files"
        if not snapshot_dir.exists():
            print(f"Error: Snapshot directory missing for {rev_id}")
            return 1

        # Count files to restore
        snapshot_files = list(snapshot_dir.rglob("*"))
        snapshot_files = [f for f in snapshot_files if f.is_file()]

        if not snapshot_files:
            print(f"Warning: No files to restore in {rev_id}")
            return 0

        # Confirm with user
        print(f"This will overwrite {len(snapshot_files)} working tree files from snapshot of {rev_id}")
        print(f"Goal: {meta['goal']}")
        print(f"\nFiles to restore:")
        for f in snapshot_files[:10]:  # Show first 10
            rel = f.relative_to(snapshot_dir)
            print(f"  {rel}")
        if len(snapshot_files) > 10:
            print(f"  ... and {len(snapshot_files) - 10} more")

        response = input("\nContinue? (y/N): ").strip().lower()
        if response != 'y':
            print("Restore cancelled")
            return 0

        # Restore files
        restored = 0
        for snapshot_file in snapshot_files:
            # Get relative path from snapshot dir
            rel_path = snapshot_file.relative_to(snapshot_dir)
            dest_file = self.repo_root / rel_path

            # Create parent directory
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(snapshot_file, dest_file)
            restored += 1

        # Update metadata
        meta['status'] = 'applied'
        self._write_meta_json(rev_id, meta)

        print(f"\n[OK] Restored {restored} files from {rev_id}")
        print(f"Status updated: applied")
        print(f"\nNext steps:")
        print(f"  git add .")
        print(f"  git commit -m \"{meta['goal']}\"")

        return 0

    def cmd_diff(self, rev_id: str) -> int:
        """
        Show diff summary for revision.

        Args:
            rev_id: Revision ID

        Returns:
            Exit code (0 = success, 1 = failure)
        """
        # Load metadata
        meta = self._load_meta(rev_id)
        if not meta:
            print(f"Error: Revision {rev_id} not found")
            return 1

        # Verify snapshot exists
        snapshot_dir = self.snapshots_dir / rev_id / "changed_files"
        if not snapshot_dir.exists():
            print(f"Error: Snapshot directory missing for {rev_id}")
            return 1

        print(f"Diff summary for {rev_id}")
        print(f"Goal: {meta['goal']}")
        print(f"\nFiles in snapshot:")

        snapshot_files = list(snapshot_dir.rglob("*"))
        snapshot_files = [f for f in snapshot_files if f.is_file()]

        if not snapshot_files:
            print("  (no files)")
            return 0

        for snapshot_file in snapshot_files:
            rel_path = snapshot_file.relative_to(snapshot_dir)
            current_file = self.repo_root / rel_path

            # Check if file exists in working tree
            if not current_file.exists():
                print(f"  {rel_path} (NEW in snapshot)")
                continue

            # Compare file sizes as simple diff metric
            snapshot_size = snapshot_file.stat().st_size
            current_size = current_file.stat().st_size

            if snapshot_size == current_size:
                # Do byte comparison
                with open(snapshot_file, 'rb') as f1, open(current_file, 'rb') as f2:
                    if f1.read() == f2.read():
                        print(f"  {rel_path} (unchanged)")
                        continue

            print(f"  {rel_path} (snapshot: {snapshot_size}B, current: {current_size}B)")

        return 0


def main(args):
    """
    Main entry point for revision CLI.

    Args:
        args: Parsed command-line arguments
    """
    system = RevisionSystem()

    if args.revision_command == 'new':
        system.cmd_new(args.goal)
        return 0

    elif args.revision_command == 'status':
        system.cmd_status()
        return 0

    elif args.revision_command == 'list':
        system.cmd_list()
        return 0

    elif args.revision_command == 'approve':
        return system.cmd_approve(args.rev_id)

    elif args.revision_command == 'discard':
        return system.cmd_discard(args.rev_id)

    elif args.revision_command == 'restore':
        return system.cmd_restore(args.rev_id)

    elif args.revision_command == 'diff':
        return system.cmd_diff(args.rev_id)

    else:
        print(f"Unknown revision command: {args.revision_command}")
        return 1
