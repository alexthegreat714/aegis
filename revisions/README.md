# Aegis Revision System

This directory contains **tracked metadata** for all Aegis revisions. Each revision captures a snapshot of code changes with full file copies for safe restoration.

## Directory Structure

```
/revisions/              ← Tracked in git (metadata only)
  rev_0001.json
  rev_0002.json
  README.md

/.aegis_revisions/       ← Local only (gitignored, full file snapshots)
  rev_0001/
    changed_files/
      src/core/control_loop.py
      src/cli/revision.py
    chat.md
    console.log
  rev_0002/
    ...
```

## Metadata Format

Each `rev_XXXX.json` file contains:

```json
{
  "rev_id": "rev_0001",
  "goal": "Description of what this revision accomplishes",
  "created_utc": "2025-01-07T12:34:56.789Z",
  "head_commit": "5095dc6",
  "status": "draft|approved|applied|discarded",
  "files": [
    "src/core/control_loop.py",
    "src/cli/revision.py"
  ],
  "test_summary": "159 passed in 41.35s" or null
}
```

## Revision Lifecycle

1. **draft** - Created with `aegis revision new "<goal>"`
   - Full file snapshots saved to `.aegis_revisions/rev_XXXX/changed_files/`
   - Metadata written to `revisions/rev_XXXX.json`

2. **approved** - After `aegis revision approve <rev_id>`
   - STRICT: Only approves if `pytest -q` shows all 159 tests passing
   - Updates `test_summary` and sets `status="approved"`
   - Does NOT auto-apply to working tree

3. **applied** - After `aegis revision restore <rev_id>`
   - Copies snapshot files back to working tree
   - User must manually commit changes

4. **discarded** - After `aegis revision discard <rev_id>`
   - Marks revision as abandoned
   - Snapshot files remain for audit trail

## CLI Commands

```bash
# Create new revision
aegis revision new "Add revision system"

# List all revisions
aegis revision list

# Show current/latest revision status
aegis revision status

# Approve revision (runs tests, strict)
aegis revision approve rev_0001

# Restore snapshot to working tree
aegis revision restore rev_0001

# Show diff summary
aegis revision diff rev_0001

# Discard revision
aegis revision discard rev_0001
```

## Safety Rules

- **Never rewrite git history** - All changes are additive
- **STRICT approval** - `approve` command MUST verify all tests pass
- **Manual application** - `restore` requires user confirmation
- **Full file snapshots** - Store complete files, not diffs
- **Snapshot validation** - Approve/restore blocked if `.aegis_revisions/` missing

## Notes

- Revision IDs are sequential: `rev_0001`, `rev_0002`, etc.
- `.aegis_revisions/` is local-only (gitignored) for safety
- Only metadata JSON files are tracked in git
- Chat logs and console output can be saved alongside snapshots
