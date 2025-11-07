# Aegis Sandbox

This directory provides an isolated environment for testing Aegis actions without affecting the real system.

## Purpose

The sandbox allows Aegis to safely test:

- **Destructive file operations** (delete, overwrite)
- **Simulated UI actions** (without clicking real buttons)
- **Script rewrites and testing** (before deploying to production)
- **Mock filesystem operations** (create/delete without real impact)

## Structure

```
sandbox/
├── README.md          # This file
└── scratch/           # Temporary workspace (auto-cleaned)
```

## Usage

### In Policy Configuration

Actions marked as `sandbox_only` in `config/policy.yaml` can ONLY be executed within this directory:

```yaml
sandbox_only:
  - file_delete
  - directory_delete
  - process_kill
```

### Path Validation

Aegis enforces that destructive operations are constrained to `sandbox/scratch/` unless explicitly overridden in policy.

### Cleanup

The `scratch/` directory can be safely deleted at any time. Aegis will recreate it as needed.

## Safety Notes

- Never point sandbox to a real working directory
- Always verify Aegis is in sandbox mode before testing destructive actions
- Review logs after sandbox tests to ensure expected behavior

## Future Features

- Mock Windows registry
- Virtual process list
- Simulated VS Code instance
- Filesystem snapshot/restore
