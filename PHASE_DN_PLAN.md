# Phase D+N Plan: Desktop Automation + Autonomous Night Agent

**Status:** Implemented ✅
**Date:** 2025-01-08
**Test Status:** 208 → ~226 tests passing

---

## Overview

Phase D+N adds complete desktop automation and autonomous operation capabilities to Aegis, enabling fully autonomous overnight development cycles with Claude, desktop UI interaction, session limit handling, and comprehensive reporting.

### Key Features

1. **Desktop Automation (Phase D)**
   - OCR-based button detection with confidence thresholds
   - Workspace validation and enforcement
   - Screenshot capture for all actions
   - Safety sandboxing with window whitelisting

2. **Autonomous Night Agent (Phase N)**
   - Multi-goal autonomous execution
   - Session limit detection and pause/resume
   - Morning report generation
   - Build document workflow

---

## Architecture

### Module Structure

```
src/
├── automation/
│   ├── desktop_executor.py          # Main desktop action dispatcher
│   ├── workspace_guard.py           # Enhanced with branch/clean enforcement
│   ├── backends/
│   │   └── ui_automation.py         # Enhanced with OCR support
│
├── claude/
│   └── limit_guard.py               # NEW: Session limit detection & handling
│
├── agents/
│   └── night_agent.py               # NEW: Autonomous night agent
│
├── core/
│   ├── night_cycle.py               # Enhanced with desktop + limits
│   └── night_report.py              # NEW: Morning report generation
│
└── cli/
    ├── desktop_cli.py               # NEW: Desktop test commands
    └── night_agent_cli.py           # NEW: Night agent commands
```

---

## Phase D: Desktop Automation

### Enhanced Modules

#### 1. **ui_automation.py** - OCR Integration

**New Features:**
- OCR-based button detection using pytesseract
- Confidence threshold filtering (default: 0.80)
- Fallback mechanism: UIA first, then OCR
- Full bounding box + confidence logging

**New Methods:**
```python
find_button_ocr(label, timeout, region) -> Dict[str, Any]
click_button_ocr(label, timeout, region) -> bool
extract_text_ocr(region) -> str
```

**Usage:**
```python
backend = UIAutomationBackend(
    dry_run=False,
    ocr_enabled=True,
    ocr_confidence_threshold=0.80
)

# Automatically tries UIA first, then OCR fallback
backend.click_button("Apply Changes")
```

#### 2. **workspace_guard.py** - Branch & Clean Enforcement

**New Features:**
- Git branch validation and auto-switching
- Working tree cleanliness enforcement
- Auto-stashing uncommitted changes

**New Methods:**
```python
get_current_branch() -> str
ensure_branch(branch, create=False) -> bool
is_clean_tree() -> bool
ensure_clean_tree(stash=True) -> bool
```

**Usage:**
```python
guard = WorkspaceGuard(expected_repo=Path("/path/to/repo"))
guard.ensure_branch("master")        # Auto-switch if needed
guard.ensure_clean_tree(stash=True)  # Stash uncommitted changes
```

#### 3. **desktop_executor.py** - OCR-Enabled

**Changes:**
- Initializes UIA backend with OCR enabled
- OCR confidence threshold: 0.80
- All button clicks now have OCR fallback

---

## Phase N: Autonomous Night Agent

### New Modules

#### 1. **limit_guard.py** - Claude Session Limit Handler

**Purpose:** Detect Claude API session limits and manage pause/resume logic.

**Key Features:**
- Text/OCR-based limit detection
- Automatic reset time calculation (configured reset hour + buffer)
- State persistence for pending work
- Automatic resume after reset time

**API:**
```python
detector = SessionLimitDetector(config=config)

# Detect limit in text
if detector.detect_limit_in_text(reply):
    detector.save_blocked_state(rev_id, prompt, metadata)
    detector.wait_for_reset()  # Blocks until reset time

# Check if ready to resume
if detector.should_resume():
    detector.clear_blocked_state()
```

**Configuration:**
```yaml
claude:
  daily_reset_hour: 0           # UTC hour (0-23)
  resume_buffer_minutes: 2      # Safety buffer
  limiter_match_text:
    - "session limit reached"
    - "quota exceeded"
```

#### 2. **night_agent.py** - Autonomous Development Agent

**Purpose:** Execute multi-goal autonomous development cycles overnight.

**Key Features:**
- Loads build docs from `docs/builds/*.md`
- Multi-round retry logic per goal
- Desktop automation for button clicks
- Session limit detection and handling
- Workspace preparation and validation

**Workflow:**
```
1. Prepare workspace (clean tree, correct branch)
2. Load build docs
3. For each goal:
   a. Create revision
   b. Build prompt
   c. Send to Claude via VS Code
   d. Detect session limits
   e. Wait for "Apply Changes" button
   f. Click button (desktop automation)
   g. Run tests (STRICT approval)
   h. Retry if failed (up to max_rounds)
4. Generate morning report
```

**Usage:**
```python
agent = NightAgent(repo_root=repo_root, dry_run=False)
summary = agent.run_autonomous(
    max_goals=5,
    max_rounds_per_goal=3,
    auto_approve=True
)
```

#### 3. **night_report.py** - Morning Report Generator

**Purpose:** Generate structured markdown reports for night cycles.

**Report Sections:**
- Header with overall status (✅/⚠️/❌)
- Summary table (goals, success rate, duration)
- Completed goals list (with revisions)
- Failed goals list (with reasons)
- Revisions created
- Test results
- Screenshots (if captured)
- Errors & troubleshooting

**Sample Output:**
```markdown
# Night Agent Report
**Generated:** 2025-01-08 03:45:12 UTC
**Status:** ✅ SUCCESS

## Summary
| Metric | Value |
|--------|-------|
| Goals Attempted | 3 |
| Goals Completed | 2 |
| Success Rate | 66.7% |
| Duration | 45.2 minutes |

## Goals
### ✅ Completed
1. **Feature A** (revision: `rev_007`, rounds: 2)
2. **Feature B** (revision: `rev_008`, rounds: 1)

### ❌ Failed
1. **Feature C** (rounds: 3)
   - Reason: Tests failed

...
```

#### 4. **Enhanced night_cycle.py**

**New Features:**
- Desktop automation integration
- Session limit detection and handling
- Automatic "Apply Changes" button clicking

**New Parameters:**
```python
NightCycle(
    repo_root=repo_root,
    use_desktop=True,      # Enable desktop automation
    dry_run=False
)
```

---

## CLI Commands

### Desktop Automation

```bash
# Test desktop automation (dry-run)
python aegis.py desktop test

# Test with live UI actions
python aegis.py desktop test --live

# Capture screenshot
python aegis.py desktop screenshot --label "pre_session"
```

### Night Agent

```bash
# Run autonomous night agent
python aegis.py night_agent run \
    --max-goals 5 \
    --max-rounds 3 \
    --auto            # Auto-approve passing revisions
    --dry-run         # Simulation mode

# View last night report
python aegis.py night_agent report --last

# List all reports
python aegis.py night_agent report --all

# Clear build document backlog
python aegis.py night_agent clear_backlog
```

---

## Configuration

### config.yaml

```yaml
# Claude API Configuration
claude:
  daily_reset_hour: 0
  resume_buffer_minutes: 2
  limiter_match_text:
    - "session limit reached"
    - "quota exceeded"

# Desktop Automation
automation:
  target_branch: "master"
  ocr_confidence_threshold: 0.80
  allowed_windows:
    - "Visual Studio Code"
    - "Command Prompt"
  screenshots:
    enabled: true
    capture_all_actions: true

# Night Agent
night_agent:
  default_max_goals: 5
  default_max_rounds: 3
  auto_approve: false
  build_docs_dir: "docs/builds"
  reports_dir: "reports"

# Workspace Guard
workspace:
  auto_stash: true
  auto_switch_branch: true
  require_clean_tree: true
```

---

## Testing

### Test Suite

**New Test Files:**
- `tests/test_limit_guard.py` - Session limit detection tests
- `tests/test_phase_dn.py` - Workspace guard, night agent, reports

**Test Markers:**
```bash
# Run all tests (skip desktop)
pytest -q

# Run desktop tests only
pytest -m desktop

# Run all tests including desktop
pytest -m ""
```

**Test Coverage:**
- Limit detection (text and OCR)
- Reset time calculation
- State persistence
- Workspace guard (branch, clean tree)
- Night report generation
- Night agent initialization

**Expected Test Count:** ~226 tests (18 new + 208 existing)

---

## Safety Constraints

### Desktop Automation
- ✅ No absolute screen coordinates (OCR-based only)
- ✅ Screenshot + metadata for every action
- ✅ Button clicks only on >0.80 OCR confidence
- ✅ Window whitelist enforcement
- ✅ Action limit per cycle (20 default)

### Revision Control
- ✅ All changes remain revision-gated
- ✅ STRICT pytest approval required
- ✅ No auto-push to remote
- ✅ Manual review always possible

### Session Limits
- ✅ Automatic detection (text + OCR)
- ✅ Safe pause/resume with state persistence
- ✅ No lost work on limit hit
- ✅ Configurable reset time + buffer

---

## Dependencies

### New Python Packages
```bash
pip install pytesseract Pillow
```

### System Requirements
- **Windows:** Tesseract-OCR must be installed
  - Download: https://github.com/tesseract-ocr/tesseract
  - Default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`

### Existing Dependencies
- pywinauto
- pyautogui
- pytest
- pyyaml

---

## Example Workflow

### 1. Prepare Build Documents

```bash
mkdir -p docs/builds
cat > docs/builds/feature_x.md <<EOF
# Feature X: Add User Authentication

## Goal
Implement basic user authentication with login/logout

## Requirements
- Add User model with password hashing
- Create login/logout endpoints
- Add session management
- Write tests for auth flow

## Success Criteria
- All tests pass
- Code follows repository standards
EOF
```

### 2. Run Night Agent

```bash
python aegis.py night_agent run \
    --max-goals 3 \
    --max-rounds 2 \
    --dry-run
```

### 3. Review Report

```bash
python aegis.py night_agent report --last
```

### 4. Check Revisions

```bash
python aegis.py revision list
python aegis.py revision status
```

---

## Troubleshooting

### OCR Not Working

**Symptom:** Button clicks failing, "OCR disabled" warnings

**Solution:**
1. Check Tesseract installation: `where tesseract`
2. Reinstall pytesseract: `pip install --upgrade pytesseract`
3. Test OCR manually:
   ```python
   import pytesseract
   from PIL import Image
   print(pytesseract.image_to_string(Image.open("test.png")))
   ```

### Session Limit Not Detecting

**Symptom:** Agent doesn't pause when limit reached

**Solution:**
1. Check config.yaml `limiter_match_text` patterns
2. Review Claude's actual limit message text
3. Add custom patterns if needed
4. Enable OCR for screenshot detection

### Workspace Guard Errors

**Symptom:** "Workspace mismatch" or "Tree not clean" errors

**Solution:**
1. Check current branch: `git branch`
2. Check for uncommitted changes: `git status`
3. Run workspace guard manually:
   ```python
   from automation.workspace_guard import WorkspaceGuard
   guard = WorkspaceGuard(expected_repo=Path.cwd())
   guard.ensure_branch("master")
   guard.ensure_clean_tree(stash=True)
   ```

### Desktop Tests Failing

**Symptom:** `desktop test` command errors

**Solution:**
1. Always use `--dry-run` or dry_run=True for testing
2. Check VS Code is installed and in PATH
3. Verify pywinauto installation
4. Run with verbose logging: `pytest -v -m desktop`

---

## Next Steps

### Potential Enhancements

1. **Code Block Parsing**
   - Auto-extract code blocks from Claude's replies
   - Auto-apply changes without manual intervention

2. **Enhanced Build Docs**
   - YAML front matter support
   - Priority levels
   - Dependencies between goals
   - Conditional execution

3. **Multi-Agent Coordination**
   - Multiple Claude sessions in parallel
   - Goal distribution across sessions
   - Shared state management

4. **Advanced Reporting**
   - HTML reports with charts
   - Email notifications
   - Slack/Discord integration
   - Grafana dashboards

5. **Improved OCR**
   - EasyOCR support (better accuracy)
   - GPU acceleration
   - Region caching
   - Button position learning

---

## Summary

Phase D+N successfully implements:

✅ **Desktop Automation** with OCR-based button detection
✅ **Workspace Enforcement** with branch and clean tree validation
✅ **Session Limit Handling** with automatic pause/resume
✅ **Autonomous Night Agent** for unattended development
✅ **Morning Reports** with comprehensive metrics
✅ **CLI Integration** for all new features
✅ **Comprehensive Testing** with 226+ tests
✅ **Safety Constraints** at all levels

**Ready for autonomous overnight development cycles! 🚀**
