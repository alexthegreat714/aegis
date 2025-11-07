# Phase 3 Implementation - Complete

## ✅ All Tasks Completed

All three parallel tasks from Phase 3 have been implemented:

### 1. ✅ Windows .BAT Control Console
**File**: [start_aegis.bat](start_aegis.bat)

**Features**:
- Numbered menu system (8 options)
- Interactive and autonomous mode launchers
- Connection testing
- Log viewing (opens in Notepad)
- Sandbox revisions explorer
- Revision approval interface
- Process killing
- Error logging and reporting

**Usage**:
```bash
# From aegis/ directory:
start_aegis.bat
```

### 2. ✅ OWUI Integration (Chess Agent Compatible)
**Files**:
- [src/clients/owui_client.py](src/clients/owui_client.py)

**Features**:
- Chess agent compatible API format
- POST `/api/chat/completions` with Bearer token
- Streaming support (SSE format)
- Standard OpenAI-compatible response parsing
- Aegis-specific reasoning call format
- Default model: `"aegis"`
- Temperature: 0.2 (reasoning-optimized)

**New Methods**:
- `chat_completion()` - Standard completion (stream or non-stream)
- `_stream_completion()` - SSE streaming handler
- `aegis_reasoning_call()` - Structured reasoning format
- `prompt_with_context()` - Context-aware prompts

**API Format**:
```python
payload = {
    "model": "aegis",
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ],
    "temperature": 0.2,
    "stream": False
}

# Response:
{
    "choices": [{
        "message": {"role": "assistant", "content": "..."},
        "finish_reason": "stop"
    }]
}
```

### 3. ✅ Interactive Reasoning Pause System
**Files**:
- [src/core/interactive.py](src/core/interactive.py)
- [src/core/sandbox_revision.py](src/core/sandbox_revision.py)

**Interactive Pause Features**:
- Non-blocking 60s timeout (Windows `msvcrt`)
- Risk-based timeout adjustment:
  - Low risk: 30s
  - Medium risk: 60s
  - High risk: 120s
- Commands: `pause`, `skip`, `abort`, `approve`, `view`, `continue`
- Verbose reasoning display
- Auto-continue on timeout (unless requires_approval)

**Sandbox Revision Features**:
- Revision bundle creation: `sandbox/revisions/YYYYMMDD_HHMMSS_slug/`
- Bundle contents:
  - `README.md` - Task, reasoning, risk, test plan, rollback
  - `manifest.json` - Structured metadata
  - `backups/` - Original file copies with SHA256 hashes
  - `PENDING_APPROVAL` - Marker file
- Approval workflow:
  - `python aegis.py --approve-revision <id>` - Apply changes
  - `python aegis.py --reject-revision <id>` - Reject
  - `python aegis.py --list-revisions` - List pending
- Safety features:
  - No live file changes until approved
  - Original file backup with hash verification
  - Failed merge auto-rollback
  - Audit trail in logs

## 📁 New Files Created

1. **start_aegis.bat** - Windows control console
2. **src/core/interactive.py** - Interactive pause system
3. **src/core/sandbox_revision.py** - Revision management
4. **PHASE3_IMPLEMENTATION.md** - This file

## 🔧 Modified Files

1. **src/clients/owui_client.py** - Chess agent compatible format
2. **src/main.py** - Added CLI modes and revision commands

## 🎯 New CLI Commands

### Execution Modes
```bash
# Interactive mode (verbose + pause windows)
python aegis.py --interactive

# Autonomous mode (auto-continue, pauses for high-risk)
python aegis.py --run --prompt "Your task"

# Default mode (uses policy settings)
python aegis.py --prompt "Your task"
```

### Revision Management
```bash
# List pending revisions
python aegis.py --list-revisions

# Approve and apply revision
python aegis.py --approve-revision 20250106_143052_file_mod

# Reject revision
python aegis.py --reject-revision 20250106_143052_file_mod

# Rollback (not implemented yet)
python aegis.py --rollback-revision 20250106_143052_file_mod
```

### Testing
```bash
# Test OWUI connection
python aegis.py --test-connection
```

## 🎯 Phase B: Control Loop & Policy Engine - COMPLETE

### ✅ Control Loop Implementation

The control loop has been fully implemented with the observe → think → decide → act cycle:

**File**: `src/core/control_loop.py`

#### State Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     AEGIS CONTROL LOOP                       │
└─────────────────────────────────────────────────────────────┘

    [START]
       │
       ▼
   ┌───────────┐
   │  OBSERVE  │ ← Gather system state
   └─────┬─────┘   - CPU/Memory metrics
         │         - Active window
         │         - Recent logs
         │         - Process summary
         ▼
   ┌───────────┐
   │   THINK   │ ← Call LLM for reasoning
   └─────┬─────┘   - owui_client.aegis_reasoning_call()
         │         - Returns verbose reasoning
         │         - Logged to internal channel
         ▼
   ┌───────────┐
   │ SUMMARIZE │ ← Convert to compact intent
   └─────┬─────┘   - reasoning_channel.summarize_to_intent()
         │         - Creates structured intent packet
         │         - Logged to external channel
         ▼
   ┌───────────┐
   │  DECIDE   │ ← Policy + Sandbox + Pause checks
   └─────┬─────┘   - action_router.route_intent()
         │         - Policy engine validation
         │         - Sandbox routing for file ops
         │         - Interactive pause if needed
         ▼
   ┌───────────┐
   │    ACT    │ ← Execute allowed actions
   └─────┬─────┘   - Automation modules (future)
         │         - Logging to SQLite + JSONL
         │
         ▼
   [ITERATION COMPLETE]
       │
       ▼
   ┌───────────┐
   │   STOP?   │ ◄─── Max iterations reached?
   └─────┬─────┘      User interrupt?
         │ No         Task complete?
         │
     Yes │
         ▼
     [END]
```

#### Control Loop Flow Details

**OBSERVE Phase** (`_observe()`):
- Gathers CPU, memory, disk usage via `psutil`
- Detects active window (Windows-specific)
- Queries recent logs from SQLite
- Summarizes top CPU-consuming processes
- Returns structured observation dictionary

**THINK Phase** (`_think()`):
- Calls `owui_client.aegis_reasoning_call()` with task + observations
- LLM returns verbose reasoning (internal channel)
- Reasoning logged via `reasoning_channel.log_internal_reasoning()`
- **Never exposed to Claude** - only visible to Alex in logs

**SUMMARIZE Phase**:
- Converts verbose reasoning → compact intent packet
- Uses `reasoning_channel.summarize_to_intent()`
- Intent includes: intent_type, risk_level, actions, test_plan, rollback
- Logged to external channel (what Claude sees)

**DECIDE Phase**:
- Routes intent through `action_router.route_intent()`
- **Policy Check**: Validates against policy.yaml rules
- **Sandbox Check**: File modifications → sandbox revision bundle
- **Interactive Pause**: High-risk intents pause for approval
- Returns routing result (allowed/blocked/sandboxed)

**ACT Phase**:
- Executes allowed intents via automation modules (Phase 5)
- Logs all actions to SQLite + JSONL
- Updates iteration counter and sleeps

### ✅ Policy Engine Implementation

**File**: `src/core/policy_engine.py`

#### Features Implemented:

1. **Mode-Based Control**:
   - `assist`: All actions require approval
   - `execute`: Actions follow policy rules
   - `autonomous`: Maximum autonomy (use with caution)

2. **Action Permission Checking**:
   - `allow`: Action executes immediately
   - `block`: Action denied completely
   - `require_approval`: Human approval required

3. **Path Validation**:
   - `restricted_paths`: Never allowed (e.g., `/etc`, `/System`)
   - `allowed_paths`: Whitelist for file operations
   - Sandbox directory always allowed

4. **Sandbox-Only Actions**:
   - Destructive actions (delete, kill) restricted to sandbox
   - Enforced before policy check
   - Prevents accidental system damage

5. **Meta Actions**:
   - Control Aegis itself (pause, stop, reload_policy)
   - Always allowed regardless of mode

#### Policy Check Flow:

```
Intent arrives
    ↓
┌──────────────────────────────┐
│ 1. Sandbox-Only Check        │
│    - Is action sandbox-only? │
│    - Is target in sandbox?   │
└──────┬───────────────────────┘
       │ PASS
       ▼
┌──────────────────────────────┐
│ 2. Path Validation           │
│    - Check restricted_paths  │
│    - Check allowed_paths     │
└──────┬───────────────────────┘
       │ PASS
       ▼
┌──────────────────────────────┐
│ 3. Mode Check                │
│    - assist → require_approval│
│    - execute → check rules   │
│    - autonomous → check rules│
└──────┬───────────────────────┘
       │ PASS
       ▼
┌──────────────────────────────┐
│ 4. Action Permission Check   │
│    - Lookup in policy.yaml   │
│    - Return decision         │
└──────┬───────────────────────┘
       │
       ▼
PolicyDecision(allowed, reason, requires_approval)
```

### ✅ Action Planner Implementation

**File**: `src/core/action_planner.py`

#### Features Implemented:

1. **Intent Routing by Category**:
   - Desktop actions → `_plan_desktop_action()`
   - VS Code actions → `_plan_vscode_action()`
   - Filesystem actions → `_plan_filesystem_action()`
   - System actions → `_plan_system_action()`
   - Meta actions → `_plan_meta_action()`

2. **Multi-Step Planning**:
   - Desktop: Window finding → Screenshot → Action
   - Filesystem: Backup → Validate → Execute → Verify
   - VS Code: Focus window → Open terminal → Execute command

3. **Action Plan Validation**:
   - Checks all steps have executor + function
   - Validates parameters are dictionaries
   - Logs validation results

4. **Execution Tracking**:
   - Tracks completed_steps
   - Tracks failed_steps
   - Reports plan status (complete, has_failures)

### ✅ Test Suite Implementation

#### Test Files Created/Updated:

1. **`tests/test_control_loop.py`** (NEW):
   - Test initialization
   - Test observe() gathers state
   - Test iteration with prompt
   - Test recent log retrieval
   - Test process summary

2. **`tests/test_policy.py`** (ENHANCED):
   - Test policy loading from YAML
   - Test allow/block/require_approval decisions
   - Test path validation (allowed/restricted/sandbox)
   - Test sandbox-only action enforcement
   - Test policy hot-reload
   - Test mode switching (assist/execute/autonomous)
   - Test meta action handling

Run tests:
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_policy.py -v

# Run with coverage
python -m pytest tests/ --cov=src/core
```

---

## 🎯 Day 2: Intent Parsing & Automation Dispatch - COMPLETE

### ✅ Intent Parser Implementation

**File**: `src/core/intent_parser.py` (NEW)

The intent parser converts LLM output (JSON or natural language) into structured Intent objects.

#### Features:

1. **Dual Format Support**:
   - **JSON Format**: Structured intent objects
   - **Natural Language**: Plain text commands (e.g., "open notepad", "type hello")

2. **Example Intents**:
   - `open_app`: Launch applications (notepad, vscode, chrome, etc.)
   - `type_text`: Type text with keyboard
   - `click_on`: Click on elements or coordinates

3. **JSON Format Examples**:
```json
// Simple format
{
    "intent": "open_app",
    "target": "notepad",
    "args": {}
}

// Full format
{
    "action_type": "mouse_click",
    "parameters": {"x": 100, "y": 200},
    "rationale": "Click on button",
    "confidence": 0.95
}
```

4. **Natural Language Examples**:
   - "open notepad" → `Intent(VSCODE_RUN_COMMAND, {command: "notepad.exe"})`
   - "type 'hello world'" → `Intent(KEYBOARD_TYPE, {text: "hello world"})`
   - "click on submit button" → `Intent(MOUSE_CLICK, {target_element: "submit button"})`
   - "click on 100,200" → `Intent(MOUSE_CLICK, {x: 100, y: 200})`

5. **Error Handling**:
   - Raises `IntentParseError` for malformed input
   - Validates intent structure
   - Logs all parse attempts

6. **Batch Processing**:
   - `parse_batch()` method for multiple intents
   - Continues on failures, skips invalid intents

### ✅ Action Executor (Stubbed)

**File**: `src/automation/executor.py` (NEW)

Routes action plans to automation modules for execution.

**Day 2 Status**: All execution is stubbed with `# EXEC_HOOK` comments and logging only.
**Day 3**: Will implement actual `pyautogui`/`pywinauto` calls.

#### Features:

1. **Execution Routing**:
   - Desktop actions → `DesktopAutomation`
   - VS Code actions → `VSCodeAutomation`
   - Windows actions → `WindowsAutomation`
   - Filesystem actions → Filesystem handlers

2. **Dry Run Mode**:
   - `dry_run_plan()` simulates execution without actually performing actions
   - Shows what would be executed

3. **Stubbed Execution**:
```python
# Day 2: Logs only
print(f"[Desktop] Would click at ({x}, {y})")

# Day 3: Will actually execute
# self.desktop.mouse_click(x, y)
```

### ✅ Control Loop Integration

**File**: `src/core/control_loop.py` (UPDATED)

Integrated intent parsing and action planning into the control loop.

#### New Flow:

```
OBSERVE → THINK → PARSE → PLAN → POLICY CHECK → EXECUTE (stubbed)
```

**Updated `_run_iteration()` Method**:
1. **OBSERVE**: Gather system state (Phase B)
2. **THINK**: Call LLM for reasoning (Phase B)
3. **PARSE**: Convert reasoning to Intent object (NEW - Day 2)
4. **PLAN**: Create ActionPlan from Intent (NEW - Day 2)
5. **POLICY CHECK**: Validate against policy (Phase B)
6. **EXECUTE**: Dry run only (NEW - Day 2, stubbed for Day 3)

**New Method**: `_parse_intent(llm_output, prompt)` - Parses LLM output with fallback handling

#### Execution Output:

```
============================================================
INTENT PARSING:
============================================================

[Parser] Intent: mouse_click
[Parser] Parameters: {'x': 100, 'y': 200}
[Parser] Rationale: Click on button

============================================================
ACTION PLANNING:
============================================================

[Planner] Created plan with 1 steps
  1. Execute mouse_click

============================================================
POLICY CHECK:
============================================================

[Policy] Decision: PolicyDecision(ALLOW: Action 'mouse_click' is allowed by policy)

============================================================
EXECUTION (STUBBED - Day 3):
============================================================

DRY RUN: mouse_click
Intent: Click on button
Steps: 1

  1. Execute mouse_click
     → automation.desktop.mouse_click({'x': 100, 'y': 200})
```

### ✅ Intent Schema Expansion

**File**: `src/intents/intent_schema.py` (UPDATED)

Added comprehensive docstring with 6 example intent payloads covering all supported intent types.

### ✅ Test Suite (Day 2)

#### New Test Files:

**1. `tests/test_intents.py`** (NEW - 20+ tests):
- Parse JSON simple intents (open_app, type_text, click_on)
- Parse JSON full format intents
- Parse JSON strings
- Parse natural language commands
- Parse click with coordinates
- Test error handling (invalid JSON, missing fields, unknown intents)
- Test batch parsing
- Test intent validation

**2. `tests/test_action_planner.py`** (NEW - 15+ tests):
- Plan desktop actions (mouse, keyboard, screenshot)
- Plan window operations (focus, close)
- Plan filesystem actions (read, write with backup/validation)
- Plan VS Code actions
- Plan system actions
- Plan meta actions
- Validate action plans
- Test completion/failure tracking

Run Day 2 tests:
```bash
# Run all Day 2 tests
python -m pytest tests/test_intents.py tests/test_action_planner.py -v

# Run intent parser tests only
python -m pytest tests/test_intents.py -v

# Run action planner tests only
python -m pytest tests/test_action_planner.py -v
```

### Day 2 Summary

**Files Created**:
- `src/core/intent_parser.py` (NEW, 400+ lines)
- `src/automation/executor.py` (NEW, 250+ lines)
- `tests/test_intents.py` (NEW, 270+ lines)
- `tests/test_action_planner.py` (NEW, 230+ lines)

**Files Modified**:
- `src/core/control_loop.py` (added parsing + execution steps)
- `src/intents/intent_schema.py` (added example payloads)

**Total Day 2**: ~1,150 lines of new code + comprehensive tests

---

## 🎯 Day 3: Real Executable Automation - COMPLETE

### ✅ ActionResult Dataclass

**File**: `src/intents/intent_schema.py` (UPDATED)

Added `ActionResult` dataclass for individual action execution results:

```python
@dataclass
class ActionResult:
    success: bool
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
```

**Usage**: Every automation method now returns `ActionResult` to track execution status, errors, and timing.

### ✅ Desktop Automation (Real Execution)

**File**: `src/automation/desktop.py` (UPDATED)

**Uncommented pyautogui**: Real automation now enabled with safety defaults:
```python
import pyautogui
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.1  # Small pause between commands
```

**dry_run Support**: All methods support `dry_run` parameter:
- `dry_run=True`: Simulate actions, log only (safe for testing)
- `dry_run=False`: Execute real automation (requires pyautogui)

**Updated Methods**:

1. **`mouse_click(x, y, button, clicks)`** → `ActionResult`:
   - Real execution: `pyautogui.click(x, y, clicks=clicks, button=button)`
   - Dry run: Logs what would be clicked
   - Returns execution time and details

2. **`keyboard_type(text, interval)`** → `ActionResult`:
   - Real execution: `pyautogui.write(text, interval=interval)`
   - Dry run: Logs what would be typed
   - Unicode support via `write()` instead of `typewrite()`

3. **`screenshot(save_path)`** → `ActionResult`:
   - Real execution: `pyautogui.screenshot()` + save to file
   - Dry run: Logs where screenshot would be saved
   - Auto-generates timestamped filenames

**Error Handling**: Try/except blocks catch all automation errors and return ActionResult with error details.

### ✅ Action Executor (Real Execution)

**File**: `src/automation/executor.py` (UPDATED)

**Key Changes**:

1. **`dry_run` Support**: Constructor accepts `dry_run` parameter, propagates to automation modules
2. **Real Method Calls**: Removed `# EXEC_HOOK` stubs, now calls actual automation methods
3. **ActionResult Returns**: All `_execute_*` methods return `ActionResult` objects

**Updated `_execute_desktop_action()`**:
```python
def _execute_desktop_action(self, step: ActionStep) -> ActionResult:
    if function == "mouse_click":
        return self.desktop.mouse_click(
            params.get('x', 0),
            params.get('y', 0),
            params.get('button', 'left'),
            params.get('clicks', 1)
        )
    # ... similar for keyboard_type, screenshot, etc.
```

**Execution Flow**:
```
ActionPlan → execute_plan() → _execute_step() → _execute_desktop_action()
                                                    ↓
                                            desktop.mouse_click()
                                                    ↓
                                            ActionResult(success=True)
```

### ✅ Control Loop Integration

**File**: `src/core/control_loop.py` (UPDATED)

**Dry Run Mode from Settings**:
```python
dry_run = settings.get("safety", {}).get("dry_run", False)
self.executor = ActionExecutor(logger, settings, dry_run=dry_run)
```

**Real Execution**: Replaced `dry_run_plan()` with `execute_plan()`:

**Old (Day 2)**:
```python
dry_run = self.executor.dry_run_plan(action_plan)
print(dry_run)
```

**New (Day 3)**:
```python
result = self.executor.execute_plan(action_plan)
print(f"Result: {'SUCCESS' if result.success else 'FAILED'}")
print(f"Time: {result.execution_time_ms:.2f}ms")
```

**Execution Output**:
```
============================================================
DRY RUN:  (or EXECUTING: if dry_run=False)
============================================================

[Executor] Step 1: Execute mouse_click
[Executor] → Executor: automation.desktop
[Executor] → Function: mouse_click
[Executor] → Parameters: {'x': 100, 'y': 200}
[Desktop] DRY RUN: Click at (100, 200) with left button, 1 click(s)

[Execution] DRY RUN Result: SUCCESS
[Execution] Output: Completed 1 steps
[Execution] Time: 12.45ms
```

### ✅ Safety Guards

1. **PyAutoGUI Failsafe**: Move mouse to corner to abort (built-in)
2. **Dry Run Mode**: Test without system changes (`dry_run=True`)
3. **Error Handling**: All automation methods wrapped in try/except
4. **Execution Timeout**: Configurable via settings (default: 30s)
5. **Action Delay**: Configurable delay before actions (default: 100ms)
6. **Logging**: All actions logged before/during/after execution

**Settings Configuration**:
```yaml
safety:
  dry_run: true  # Day 3: Enable dry run mode
  max_consecutive_failures: 5
  emergency_stop_keyword: "AEGIS_STOP"

automation:
  action_delay_ms: 100  # Delay before UI actions
  screenshot_dir: "data/screenshots"
```

### ✅ Test Suite (Day 3)

**File**: `tests/test_execution.py` (NEW - 15+ tests)

**Test Coverage**:
- `test_desktop_automation_dry_run_mode()`: Verify dry run doesn't change state
- `test_desktop_automation_mouse_click()`: Test mouse click execution
- `test_desktop_automation_keyboard_type()`: Test keyboard typing
- `test_desktop_automation_screenshot()`: Test screenshot capture
- `test_action_result_structure()`: Validate ActionResult format
- `test_action_result_to_dict()`: Test serialization
- `test_executor_dry_run_mode()`: Test executor dry run
- `test_executor_dispatches_to_correct_function()`: Test routing
- `test_executor_completes_multi_step_plan()`: Test multi-step execution
- `test_execution_time_tracked()`: Verify timing
- `test_dry_run_flag_propagates()`: Verify dry_run propagation
- `test_error_handling_in_action_result()`: Test error handling

**Run Day 3 Tests**:
```bash
# All execution tests
python -m pytest tests/test_execution.py -v

# With coverage
python -m pytest tests/test_execution.py --cov=src/automation -v
```

### Day 3 Summary

**Files Created**:
- `tests/test_execution.py` (NEW, 230+ lines, 15+ tests)

**Files Modified**:
- `src/intents/intent_schema.py` (added ActionResult dataclass)
- `src/automation/desktop.py` (uncommented pyautogui, added dry_run support)
- `src/automation/executor.py` (real execution, ActionResult returns)
- `src/core/control_loop.py` (real execution integration)

**Total Day 3**: ~300 lines of updates + 15+ new tests

**Key Achievement**: **Real executable automation with safety guards!**

---

## 🔄 Next Steps for Full Implementation

### Phase C: Sky Integration (Future)

The framework is ready for Sky agent handoff. Look for `// SKY_HOOK` markers:
- `src/core/reasoning.py` - Dual-channel reasoning handoff
- `src/core/action_router.py` - Intent delegation to Claude

### Phase D: Automation Implementation

Uncomment and implement automation modules:

1. **Observation Gathering** (`_observe()`):
   ```python
   - Screenshot capture
   - Active window detection
   - Recent log events
   - System resource status
   ```

2. **LLM Reasoning** (`_think()`):
   ```python
   # Use the new aegis_reasoning_call method
   response = self.owui_client.aegis_reasoning_call(
       task=prompt,
       observations=observation,
       conversation_history=self.conversation_history
   )
   ```

3. **Intent Parsing**:
   ```python
   # Parse LLM response into Intent objects
   # Extract actions, risks, tests from reasoning
   ```

4. **Interactive Pause Integration**:
   ```python
   from core.interactive import InteractivePause

   pause = InteractivePause(self.logger)
   command = pause.pause_for_reasoning(
       reasoning_text=response["reasoning"],
       risk_level="medium"
   )
   ```

5. **Sandbox Integration**:
   ```python
   from core.sandbox_revision import SandboxRevisionManager

   # For file-modifying intents:
   if intent.action_type in [WRITE, DELETE, MODIFY]:
       bundle = sandbox_manager.create_revision_bundle(
           task_description=task,
           reasoning=reasoning,
           risk_level=risk,
           files_to_modify=files
       )
   ```

### Phase 5: Automation Implementation

Uncomment the TODO sections in:
- `src/automation/desktop.py`
- `src/automation/vscode.py`
- `src/automation/windows.py`

Libraries are already installed:
- `pyautogui` (mouse, keyboard)
- `pywinauto` (Windows UI)

### Phase 6: OWUI Model Setup

1. **Create "aegis" model profile in OWUI**:
   - Go to http://127.0.0.1:3000
   - Settings → Models → Add Model
   - Name: `aegis`
   - Backend: Your preferred local model (e.g., Gemma-3 12B, Llama 3.2)

2. **System Prompt**:
   ```
   You are Aegis, a local security/devops AI agent.

   Your responses should follow this structure:
   1. **Reasoning**: Explain your thought process
   2. **Risk Assessment**: Low/Medium/High + justification
   3. **Proposed Actions**: List of intents with parameters
   4. **Tests**: How to verify success
   5. **Rollback**: How to undo if needed

   Be verbose in reasoning, concise in action specs.
   ```

3. **Get token**:
   - Browser DevTools (F12) → Application → Local Storage
   - Copy `token` value
   - Paste into `config/.owui_token`

## 🧪 Testing Checklist

### Connection Test
```bash
python aegis.py --test-connection
```
Should output: `[Test] OK Connection successful`

### Interactive Mode Test
```bash
# Start BAT console
start_aegis.bat

# Select option 1 (Interactive mode)
# Enter simple task: "Say hello"
```

Expected behavior:
- Displays reasoning from LLM
- Shows 60s timeout countdown
- Accepts commands: pause, skip, abort, approve, continue

### Revision Workflow Test
```bash
# Create a test revision (placeholder)
# List revisions
python aegis.py --list-revisions

# Approve revision
python aegis.py --approve-revision <id>
```

### Autonomous Mode Test
```bash
python aegis.py --run --prompt "List files in current directory"
```

## 📊 Architecture Summary

```
User Input
    ↓
[BAT Console / CLI]
    ↓
[main.py] → Parse args, init systems
    ↓
[control_loop.py] → Observe → Think → Decide → Act
    ↓
┌─────────────────────────────────────────┐
│ THINK Phase                             │
│ ├─ owui_client.aegis_reasoning_call()  │
│ └─ Parse reasoning → Intents            │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ INTERACTIVE PAUSE                       │
│ ├─ Display reasoning                    │
│ ├─ Wait for user (60s timeout)          │
│ └─ Command: pause/skip/abort/continue   │
└─────────────────────────────────────────┘
    ↓
[policy_engine.py] → Check intent against policy
    ↓
┌─────────────────────────────────────────┐
│ FILE MODIFICATION?                      │
│ YES → Create revision bundle            │
│       ├─ Backup originals               │
│       ├─ Generate README                │
│       └─ Mark PENDING_APPROVAL          │
└─────────────────────────────────────────┘
    ↓
[action_planner.py] → Intent → Action plan
    ↓
[automation/*] → Execute actions
    ↓
[logger] → Log to JSONL + SQLite
```

## 🎓 Key Concepts

### Interactive Pause Workflow
```python
# 1. Display reasoning
print(reasoning_text)

# 2. Wait for input (non-blocking)
command = pause.wait_for_input(timeout=60)

# 3. Handle commands
if command == "pause":
    # Freeze execution, await resume
elif command == "skip":
    # Skip current action, continue plan
elif command == "abort":
    # Abort entire task chain
elif command == "approve":
    # Execute immediately
elif command is None:
    # Timeout → auto-continue
```

### Sandbox Revision Workflow
```python
# 1. Detect file-modifying intent
if intent.action_type in [WRITE, DELETE, MODIFY]:

    # 2. Create revision bundle
    bundle = sandbox_manager.create_revision_bundle(
        task_description="Update config file",
        reasoning="Need to enable feature X",
        risk_level="medium",
        files_to_modify=[{
            "path": "config/settings.yaml",
            "action": "write",
            "content": new_content
        }]
    )

    # 3. User reviews bundle
    # sandbox/revisions/20250106_143052_config/
    #   ├── README.md
    #   ├── manifest.json
    #   ├── backups/settings.yaml
    #   └── PENDING_APPROVAL

    # 4. Approval
    python aegis.py --approve-revision 20250106_143052_config

    # 5. Changes applied
    # PENDING_APPROVAL removed, APPLIED.txt created
```

## 🔒 Security Features

1. **No live file changes without approval**
2. **All reasoning logged and displayed**
3. **Risk-based timeout adjustment**
4. **Original file backups with hash verification**
5. **Policy enforcement on every action**
6. **Audit trail in SQLite + JSONL**
7. **Restricted path enforcement**
8. **Sandbox-only destructive operations**

## 📝 Configuration Files

### config/settings.yaml
Update for Aegis model:
```yaml
owui:
  base_url: "http://127.0.0.1:3000"
  endpoint: "/api/chat/completions"
  token_file: "config/.owui_token"
  timeout_seconds: 30
  model: "aegis"  # ← Default model
```

### config/policy.yaml
Add interactive settings:
```yaml
mode: assist  # assist | execute | autonomous

# Interactive pause settings
interactive:
  default_timeout: 60
  risk_based_timeout: true
  auto_continue_low_risk: true
  require_approval_high_risk: true
```

## 🚀 Quick Start After Setup

1. **Add OWUI token**: Put your token in `config/.owui_token`
2. **Test connection**: `python aegis.py --test-connection`
3. **Launch console**: `start_aegis.bat`
4. **Try interactive mode**: Select option 1, enter a simple task
5. **Review reasoning**: Read the verbose output
6. **Test commands**: Try `pause`, `approve`, `continue`

## 📚 Documentation

- [SETUP_COMPLETE.md](SETUP_COMPLETE.md) - Phase 1 & 2 setup
- [QUICKSTART.md](QUICKSTART.md) - Usage guide
- [README.md](README.md) - Project overview
- [sandbox/README.md](sandbox/README.md) - Sandbox usage

## ✅ Status

**Phase 3: COMPLETE**

All frameworks are in place. Next step is implementing the control loop TODOs to connect everything together.

---

**Ready for Phase 4: Control Loop Implementation** 🎉
