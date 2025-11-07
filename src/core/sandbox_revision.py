"""
Sandbox revision system for safe file modifications.

Creates isolated revision bundles before applying changes to live files.
"""

import os
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from aegis_logging.logger import AegisLogger


class RevisionBundle:
    """
    Represents a single revision bundle in sandbox.

    Contains all information needed to apply or rollback changes.
    """

    def __init__(
        self,
        revision_id: str,
        task_description: str,
        reasoning: str,
        risk_level: str,
        files_modified: List[Dict[str, Any]]
    ):
        """
        Initialize revision bundle.

        Args:
            revision_id: Unique revision ID (timestamp-based slug)
            task_description: What this revision does
            reasoning: Why these changes are needed
            risk_level: low/medium/high
            files_modified: List of file modification records
        """
        self.revision_id = revision_id
        self.task_description = task_description
        self.reasoning = reasoning
        self.risk_level = risk_level
        self.files_modified = files_modified
        self.created_at = datetime.now().isoformat()
        self.status = "pending"  # pending, approved, rejected, failed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "revision_id": self.revision_id,
            "task_description": self.task_description,
            "reasoning": self.reasoning,
            "risk_level": self.risk_level,
            "files_modified": self.files_modified,
            "created_at": self.created_at,
            "status": self.status
        }


class SandboxRevisionManager:
    """
    Manages sandbox revisions for file modifications.

    All file-modifying operations create a revision bundle first.
    """

    def __init__(self, logger: AegisLogger, sandbox_base: str = "sandbox/revisions"):
        """
        Initialize sandbox revision manager.

        Args:
            logger: Logging system
            sandbox_base: Base path for revisions
        """
        self.logger = logger
        self.sandbox_base = Path(sandbox_base)
        self.sandbox_base.mkdir(parents=True, exist_ok=True)

    def create_revision_id(self, task_slug: str = "mod") -> str:
        """
        Generate unique revision ID.

        Args:
            task_slug: Short task description slug

        Returns:
            Revision ID (YYYYMMDD_HHMMSS_slug)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize slug
        safe_slug = "".join(c if c.isalnum() or c == "_" else "_" for c in task_slug)
        safe_slug = safe_slug[:20]  # Limit length
        return f"{timestamp}_{safe_slug}"

    def create_revision_bundle(
        self,
        task_description: str,
        reasoning: str,
        risk_level: str,
        files_to_modify: List[Dict[str, Any]],
        task_slug: str = "mod"
    ) -> RevisionBundle:
        """
        Create a new revision bundle in sandbox.

        Args:
            task_description: What this revision does
            reasoning: Why changes are needed
            risk_level: low/medium/high
            files_to_modify: List of file modification records
            task_slug: Short task identifier

        Returns:
            RevisionBundle instance
        """
        revision_id = self.create_revision_id(task_slug)
        revision_path = self.sandbox_base / revision_id
        revision_path.mkdir(parents=True, exist_ok=True)

        # Create revision bundle object
        bundle = RevisionBundle(
            revision_id=revision_id,
            task_description=task_description,
            reasoning=reasoning,
            risk_level=risk_level,
            files_modified=files_to_modify
        )

        # Create README.md
        readme_content = self._generate_readme(bundle)
        (revision_path / "README.md").write_text(readme_content, encoding="utf-8")

        # Create manifest.json
        manifest = bundle.to_dict()
        (revision_path / "manifest.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8"
        )

        # Copy original files and create patches
        self._backup_original_files(revision_path, files_to_modify)

        # Create PENDING_APPROVAL marker
        (revision_path / "PENDING_APPROVAL").write_text(
            f"Revision created at: {bundle.created_at}\n"
            f"Requires approval before applying to live files.\n",
            encoding="utf-8"
        )

        # Log creation
        self.logger.log_event(
            event_type="revision_created",
            data={
                "revision_id": revision_id,
                "task": task_description,
                "risk": risk_level,
                "file_count": len(files_to_modify)
            },
            status="info"
        )

        print(f"[Revision] Created: {revision_id}")
        print(f"[Revision] Path: {revision_path}")

        return bundle

    def _generate_readme(self, bundle: RevisionBundle) -> str:
        """Generate README.md for revision bundle."""
        return f"""# Revision: {bundle.revision_id}

## Task Description
{bundle.task_description}

## Reasoning
{bundle.reasoning}

## Risk Level
**{bundle.risk_level.upper()}**

## Files Modified
{self._format_files_list(bundle.files_modified)}

## Test Plan
- [ ] Review diff for each file
- [ ] Verify no unintended changes
- [ ] Run relevant tests
- [ ] Check for security implications
- [ ] Verify rollback procedure

## Rollback Procedure
```bash
# If applied and issues occur:
python aegis.py --rollback-revision {bundle.revision_id}

# Or manually restore from:
# sandbox/revisions/{bundle.revision_id}/backups/
```

## Approval
To apply this revision:
```bash
python aegis.py --approve-revision {bundle.revision_id}
```

To reject:
```bash
python aegis.py --reject-revision {bundle.revision_id}
```

## Status
- Created: {bundle.created_at}
- Status: {bundle.status}
"""

    def _format_files_list(self, files: List[Dict[str, Any]]) -> str:
        """Format file list for README."""
        if not files:
            return "- None"

        result = []
        for f in files:
            action = f.get("action", "modify")
            path = f.get("path", "unknown")
            result.append(f"- [{action.upper()}] {path}")

        return "\n".join(result)

    def _backup_original_files(
        self,
        revision_path: Path,
        files_to_modify: List[Dict[str, Any]]
    ) -> None:
        """
        Backup original files before modification.

        Args:
            revision_path: Path to revision directory
            files_to_modify: List of file modification records
        """
        backup_dir = revision_path / "backups"
        backup_dir.mkdir(exist_ok=True)

        for file_record in files_to_modify:
            src_path = Path(file_record.get("path", ""))

            if src_path.exists() and src_path.is_file():
                # Compute hash
                file_hash = self._compute_file_hash(src_path)
                file_record["original_hash"] = file_hash

                # Copy to backup
                backup_path = backup_dir / src_path.name
                shutil.copy2(src_path, backup_path)

                print(f"[Revision] Backed up: {src_path} -> {backup_path}")

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)

        return sha256.hexdigest()

    def approve_revision(self, revision_id: str) -> bool:
        """
        Approve and apply revision to live files.

        Args:
            revision_id: Revision ID to approve

        Returns:
            True if successful
        """
        revision_path = self.sandbox_base / revision_id

        if not revision_path.exists():
            print(f"[Revision] ERROR: Revision not found: {revision_id}")
            return False

        # Check for PENDING_APPROVAL marker
        if not (revision_path / "PENDING_APPROVAL").exists():
            print(f"[Revision] ERROR: Revision already processed or invalid")
            return False

        # Load manifest
        try:
            with open(revision_path / "manifest.json") as f:
                manifest = json.load(f)
        except Exception as e:
            print(f"[Revision] ERROR: Failed to load manifest: {e}")
            return False

        # Apply changes
        try:
            self._apply_changes(manifest)

            # Remove PENDING_APPROVAL, add APPLIED marker
            (revision_path / "PENDING_APPROVAL").unlink()
            (revision_path / "APPLIED.txt").write_text(
                f"Applied at: {datetime.now().isoformat()}\n",
                encoding="utf-8"
            )

            # Log approval
            self.logger.log_event(
                event_type="revision_approved",
                data={"revision_id": revision_id},
                status="success"
            )

            print(f"[Revision] SUCCESS: Approved and applied {revision_id}")
            return True

        except Exception as e:
            # Mark as failed
            (revision_path / "FAILED_MERGE.txt").write_text(
                f"Failed at: {datetime.now().isoformat()}\n"
                f"Error: {str(e)}\n",
                encoding="utf-8"
            )

            self.logger.log_event(
                event_type="revision_apply_failed",
                data={"revision_id": revision_id, "error": str(e)},
                status="error"
            )

            print(f"[Revision] ERROR: Failed to apply: {e}")
            return False

    def _apply_changes(self, manifest: Dict[str, Any]) -> None:
        """
        Apply changes from manifest to live files.

        Args:
            manifest: Revision manifest

        Raises:
            Exception if apply fails
        """
        files_modified = manifest.get("files_modified", [])

        for file_record in files_modified:
            action = file_record.get("action", "modify")
            target_path = Path(file_record.get("path", ""))
            content = file_record.get("content")

            if action == "write" or action == "modify":
                # Write new content
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                print(f"[Revision] Applied: {target_path}")

            elif action == "delete":
                if target_path.exists():
                    target_path.unlink()
                    print(f"[Revision] Deleted: {target_path}")

    def reject_revision(self, revision_id: str) -> bool:
        """
        Reject revision (do not apply).

        Args:
            revision_id: Revision ID to reject

        Returns:
            True if successful
        """
        revision_path = self.sandbox_base / revision_id

        if not revision_path.exists():
            print(f"[Revision] ERROR: Revision not found: {revision_id}")
            return False

        # Remove PENDING_APPROVAL, add REJECTED marker
        if (revision_path / "PENDING_APPROVAL").exists():
            (revision_path / "PENDING_APPROVAL").unlink()

        (revision_path / "REJECTED.txt").write_text(
            f"Rejected at: {datetime.now().isoformat()}\n",
            encoding="utf-8"
        )

        # Log rejection
        self.logger.log_event(
            event_type="revision_rejected",
            data={"revision_id": revision_id},
            status="info"
        )

        print(f"[Revision] Rejected: {revision_id}")
        return True

    def list_pending_revisions(self) -> List[str]:
        """
        List all pending revisions.

        Returns:
            List of pending revision IDs
        """
        pending = []

        for revision_dir in self.sandbox_base.iterdir():
            if revision_dir.is_dir() and (revision_dir / "PENDING_APPROVAL").exists():
                pending.append(revision_dir.name)

        return sorted(pending)
