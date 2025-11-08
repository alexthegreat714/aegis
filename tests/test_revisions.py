"""
Tests for Aegis Revision System.

Tests the revision management system including:
- Creating revisions
- Snapshotting files
- Strict approval with test validation
- Restoring snapshots
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli.revision import RevisionSystem


class TestRevisionSystem(unittest.TestCase):
    """Test revision system functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary repository
        self.temp_repo = Path(tempfile.mkdtemp())

        # Create minimal git structure
        (self.temp_repo / '.git').mkdir()

        # Initialize revision system
        self.rev_system = RevisionSystem(repo_root=self.temp_repo)

    def tearDown(self):
        """Clean up test fixtures."""
        import time
        if self.temp_repo.exists():
            # On Windows, git may lock files - give time and handle gracefully
            time.sleep(0.1)
            try:
                shutil.rmtree(self.temp_repo)
            except PermissionError:
                # Windows may still have file handles open, skip cleanup
                pass

    def test_create_revision_minimal(self):
        """Test creating a revision with no changes."""
        # Create revision with no changed files
        rev_id = self.rev_system.cmd_new("Test revision with no changes")

        # Verify revision ID format
        self.assertEqual(rev_id, "rev_0001")

        # Verify metadata file exists
        meta_path = self.temp_repo / "revisions" / f"{rev_id}.json"
        self.assertTrue(meta_path.exists())

        # Verify metadata content
        with open(meta_path, 'r') as f:
            meta = json.load(f)

        self.assertEqual(meta['rev_id'], rev_id)
        self.assertEqual(meta['goal'], "Test revision with no changes")
        self.assertEqual(meta['status'], "draft")
        self.assertIsInstance(meta['files'], list)
        self.assertEqual(len(meta['files']), 0)

        # Verify snapshot directory exists
        snapshot_dir = self.temp_repo / ".aegis_revisions" / rev_id
        self.assertTrue(snapshot_dir.exists())

        # Verify placeholder files
        self.assertTrue((snapshot_dir / "chat.md").exists())
        self.assertTrue((snapshot_dir / "console.log").exists())

    def test_revision_snapshot_contains_files(self):
        """Test that revision snapshot contains full file copies."""
        # Create a test file
        test_file = self.temp_repo / "test_file.txt"
        test_content = "This is test content\nLine 2\nLine 3\n"
        test_file.write_text(test_content)

        # Initialize git (so git status works)
        import subprocess
        subprocess.run(['git', 'init'], cwd=self.temp_repo, capture_output=True)
        subprocess.run(['git', 'add', 'test_file.txt'], cwd=self.temp_repo, capture_output=True)

        # Create revision
        rev_id = self.rev_system.cmd_new("Test with file changes")

        # Verify snapshot contains the file
        snapshot_file = (
            self.temp_repo / ".aegis_revisions" / rev_id /
            "changed_files" / "test_file.txt"
        )
        self.assertTrue(snapshot_file.exists())

        # Verify content matches
        snapshot_content = snapshot_file.read_text()
        self.assertEqual(snapshot_content, test_content)

    def test_next_rev_id_increments(self):
        """Test that revision IDs increment correctly."""
        rev_id_1 = self.rev_system.cmd_new("First revision")
        self.assertEqual(rev_id_1, "rev_0001")

        rev_id_2 = self.rev_system.cmd_new("Second revision")
        self.assertEqual(rev_id_2, "rev_0002")

        rev_id_3 = self.rev_system.cmd_new("Third revision")
        self.assertEqual(rev_id_3, "rev_0003")

    def test_snapshot_exists_validation(self):
        """Test snapshot existence validation."""
        rev_id = self.rev_system.cmd_new("Test revision")
        self.assertTrue(self.rev_system._snapshot_exists(rev_id))

        # Remove snapshot directory
        snapshot_dir = self.temp_repo / ".aegis_revisions" / rev_id
        shutil.rmtree(snapshot_dir)

        self.assertFalse(self.rev_system._snapshot_exists(rev_id))

    def test_load_meta(self):
        """Test loading revision metadata."""
        rev_id = self.rev_system.cmd_new("Test load meta")

        meta = self.rev_system._load_meta(rev_id)
        self.assertIsNotNone(meta)
        self.assertEqual(meta['rev_id'], rev_id)
        self.assertEqual(meta['goal'], "Test load meta")

        # Test loading non-existent revision
        meta_missing = self.rev_system._load_meta("rev_9999")
        self.assertIsNone(meta_missing)

    def test_discard_revision(self):
        """Test discarding a revision."""
        rev_id = self.rev_system.cmd_new("Test discard")

        # Discard the revision
        result = self.rev_system.cmd_discard(rev_id)
        self.assertEqual(result, 0)

        # Verify status updated
        meta = self.rev_system._load_meta(rev_id)
        self.assertEqual(meta['status'], 'discarded')

    def test_revision_diff_empty(self):
        """Test diff command with no files."""
        rev_id = self.rev_system.cmd_new("Empty revision")

        # Run diff command
        result = self.rev_system.cmd_diff(rev_id)
        self.assertEqual(result, 0)

    def test_cmd_list_empty(self):
        """Test list command with no revisions."""
        # Should not crash with empty revisions
        self.rev_system.cmd_list()

    def test_cmd_status_no_revisions(self):
        """Test status command with no revisions."""
        # Should not crash with no revisions
        self.rev_system.cmd_status()

    def test_approve_missing_snapshot_fails(self):
        """Test that approve fails if snapshot is missing."""
        rev_id = self.rev_system.cmd_new("Test approve fail")

        # Remove snapshot
        snapshot_dir = self.temp_repo / ".aegis_revisions" / rev_id
        shutil.rmtree(snapshot_dir)

        # Try to approve
        result = self.rev_system.cmd_approve(rev_id)
        self.assertEqual(result, 1)  # Should fail

        # Verify status still draft
        meta = self.rev_system._load_meta(rev_id)
        self.assertEqual(meta['status'], 'draft')


class TestRevisionRestoreFlow(unittest.TestCase):
    """Test revision restore functionality (interactive, so limited testing)."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_repo = Path(tempfile.mkdtemp())
        (self.temp_repo / '.git').mkdir()
        self.rev_system = RevisionSystem(repo_root=self.temp_repo)

    def tearDown(self):
        """Clean up test fixtures."""
        import time
        if self.temp_repo.exists():
            # On Windows, git may lock files - give time and handle gracefully
            time.sleep(0.1)
            try:
                shutil.rmtree(self.temp_repo)
            except PermissionError:
                # Windows may still have file handles open, skip cleanup
                pass

    def test_restore_nonexistent_fails(self):
        """Test that restoring non-existent revision fails."""
        result = self.rev_system.cmd_restore("rev_9999")
        self.assertEqual(result, 1)

    def test_restore_missing_snapshot_fails(self):
        """Test that restore fails if snapshot missing."""
        rev_id = self.rev_system.cmd_new("Test restore fail")

        # Remove snapshot
        snapshot_dir = self.temp_repo / ".aegis_revisions" / rev_id
        shutil.rmtree(snapshot_dir)

        # Try to restore
        result = self.rev_system.cmd_restore(rev_id)
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
