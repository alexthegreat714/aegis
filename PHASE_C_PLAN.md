# Phase C: VS Code Claude Automation

Phase C implements VS Code automation for Claude Code extension, enabling Aegis to interact with Claude programmatically for autonomous development cycles.

## Overview

Phase C adds:
- VS Code window automation (Windows-only for now)
- Claude VS Code extension interaction
- Prompt generation and session management
- Autonomous "night cycle" development workflow
- Full CLI integration with revision system

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Aegis CLI                             │
├─────────────────────────────────────────────────────────┤
│  aegis claude plan "<goal>"                              │
│  aegis claude send --rev rev_0001                        │
│  aegis night_cycle --goal "<goal>" --rounds 3            │
└────────┬────────────────────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────────────────────┐
│              Night Cycle Orchestrator                    │
│  - Creates revisions                                     │
│  - Generates prompts                                     │
│  - Manages Claude sessions                               │
│  - Runs pytest validation                                │
│  - Auto-approves on success                              │
└────────┬────────────────────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────────────────────┐
│           Claude VS Code Session                         │
│  - Sends prompts to Claude                               │
│  - Fetches replies                                       │
│  - Persists I/O to .aegis_revisions/                     │
└────────┬────────────────────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────────────────────┐
│            VS Code Automator                             │
│  - pywinauto/pyautogui driver                            │
│  - Window focus, command palette                         │
│  - Text input (paste mode)                               │
│  - Clipboard operations                                  │
│  - Dry-run mode for testing                              │
└─────────────────────────────────────────────────────────┘
```

## New Modules

### `src/vscode/automator.py`
VS Code automation driver using pywinauto and pyautogui.

**Key Features:**
- Window management (launch, focus)
- Command palette interaction
- Text input with paste or typing modes
- Clipboard operations
- Dry-run mode for safe testing
- Configurable delays and timeouts

**Configuration** (in `config/settings.yaml`):
```yaml
vscode:
  exe_path: "code"
  window_title_hint: "Visual Studio Code"
  claude_new_chat_cmd: "Claude: New Chat"
  input_focus_pause_ms: 300
  type_pause_ms: 10
  paste_mode: true
  dry_run: false
```

### `src/claude/vscode_session.py`
High-level Claude session manager.

**Key Features:**
- Session lifecycle management
- Prompt sending and reply fetching
- I/O persistence to `.aegis_revisions/<rev_id>/claude_io/`
- Context manager support
- Metadata tracking

### `src/claude/prompts.py`
Prompt template builders.

**Templates:**
- `build_phase_c_prompt()` - Development task prompts
- `build_code_review_prompt()` - Code review requests
- `build_bug_fix_prompt()` - Bug fix requests
- `build_test_generation_prompt()` - Test generation
- `build_night_cycle_prompt()` - Autonomous cycle prompts
- `build_repo_summary()` - Repository structure summary

### `src/core/night_cycle.py`
Autonomous development cycle orchestrator.

**Workflow:**
1. Create new revision
2. Generate prompt with repo context
3. Send to Claude via VS Code
4. Wait for user to apply code changes
5. Run `pytest -q` for validation
6. Auto-approve if tests pass, discard if fail
7. Repeat up to `max_rounds` times

### CLI Modules

- `src/cli/logs.py` - Log tailing (`aegis logs tail --live`)
- `src/cli/claude_cli.py` - Claude commands
- `src/cli/night_cycle_cli.py` - Night cycle commands

## Usage

### 1. Generate Development Plan

```bash
python aegis.py claude plan "Add VS Code debugging support"
```

Outputs a formatted prompt ready to paste into Claude.

### 2. Send Prompt to Claude (Manual)

```bash
# Create revision first
python aegis.py revision new "Add feature X"

# Generate prompt and save
python aegis.py claude plan "Add feature X" > .aegis_revisions/rev_0003/prompt.txt

# Send via VS Code automation
python aegis.py claude send --rev rev_0003
```

This will:
- Focus VS Code
- Open Claude extension
- Paste prompt
- Wait for response
- Save reply to `.aegis_revisions/rev_0003/claude_io/`

### 3. Run Night Cycle (Autonomous)

```bash
python aegis.py night_cycle --goal "Implement X feature" --rounds 3 --auto
```

This will:
- **Round 1:**
  - Create `rev_0004`
  - Generate prompt with goal and repo context
  - Send to Claude
  - Pause for you to apply code changes
  - Run tests
  - Approve if pass, continue if fail

- **Round 2-3:** (if needed)
  - Include previous failures in prompt
  - Retry with context of what failed

### 4. Monitor Logs

```bash
# Tail logs in real-time
python aegis.py logs tail --live

# Show last 50 lines
python aegis.py logs tail --lines 50
```

### 5. Manual Review Workflow

```bash
# Generate plan
python aegis.py claude plan "Fix bug in X"

# Create revision
python aegis.py revision new "Bug fix for X"

# Apply Claude's suggestions manually

# Test and approve
python aegis.py revision approve rev_0005
```

## Dependencies

### Required

```bash
pip install pywinauto pyautogui pyperclip
```

### Optional (for tests)

```bash
pip install pytest pytest-mock
```

## Testing

### Run All Tests (Excluding VS Code Integration)

```bash
pytest -q
```

Expected: `187 passed, 1 skipped`

### Run VS Code Integration Tests

```bash
pytest -m vs -v
```

These tests are **mocked** and safe to run without VS Code.

### Test Structure

```
tests/
├── test_vscode_automator.py    (7 tests, 1 skip)
├── test_vscode_session.py      (5 tests)
├── test_night_cycle.py         (4 tests)
└── ... (existing 171 tests)
```

All new tests use `@pytest.mark.vs` and are skipped by default.

## File Structure

```
.aegis_revisions/              # Local only (gitignored)
  rev_0001/
    claude_io/                 # Claude I/O
      prompt_001.txt
      reply_001.txt
      session_meta.json
    prompt.txt                 # Master prompt
    reply.txt                  # Master reply
    changed_files/             # File snapshots
      src/...

revisions/                     # Tracked in git
  rev_0001.json                # Metadata only
```

## Configuration

Add to `config/settings.yaml`:

```yaml
vscode:
  exe_path: "code"
  window_title_hint: "Visual Studio Code"
  claude_new_chat_cmd: "Claude: New Chat"
  input_focus_pause_ms: 300
  type_pause_ms: 10
  paste_mode: true
  selection_copy_cmd: "Ctrl+C"
  dry_run: false
```

## Limitations

1. **Windows Only**: Uses pywinauto which is Windows-specific
2. **Manual Code Application**: Night cycle pauses for you to apply Claude's code changes
3. **Simple Wait**: Response wait is time-based, not UI-aware
4. **Clipboard Copy**: Reply fetching uses Ctrl+A → Ctrl+C (may need tuning)

## Future Enhancements

- Cross-platform support (macOS, Linux)
- Automatic code block extraction and application
- Smart wait (monitor for typing indicators)
- Browser automation (for Claude web UI)
- Multi-round conversation memory
- Parallel night cycles with different approaches

## Troubleshooting

### VS Code Not Found

```bash
# Set explicit path
echo "vscode:
  exe_path: 'C:\\Program Files\\Microsoft VS Code\\Code.exe'" >> config/settings.yaml
```

### Claude Extension Not Available

- Install Claude Code extension in VS Code
- Verify command palette shows "Claude: New Chat"
- Update `claude_new_chat_cmd` in settings if command differs

### Clipboard Issues

- Ensure pyperclip is installed
- Try setting `paste_mode: false` to use typing instead
- Check antivirus isn't blocking clipboard access

### Tests Failing

```bash
# Make sure you're not running VS Code tests
pytest -q

# Skip VS Code tests explicitly
pytest -m "not vs" -q
```

## Safety

- **Dry Run Mode**: Set `vscode.dry_run: true` to log actions without executing
- **Revision System**: All changes tracked with full audit trail
- **Test Gating**: Auto-approval requires 100% test pass
- **Manual Confirm**: Night cycle can pause between rounds

## Next Steps

1. Test manual Claude interaction: `python aegis.py claude plan "Test task"`
2. Run a safe night cycle: `python aegis.py night_cycle --goal "Add docstrings" --rounds 1`
3. Monitor logs: `python aegis.py logs tail --live`
4. Review revisions: `python aegis.py revision list`

## Questions?

- Check test files for usage examples
- Review `src/vscode/automator.py` for low-level automation
- See `src/core/night_cycle.py` for orchestration logic
