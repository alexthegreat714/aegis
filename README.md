# Aegis - Intelligent Desktop Automation System

Aegis is an intelligent desktop automation system with a fully auditable control loop. It observes your desktop, generates intents, checks policies, executes actions, and logs everything for replay and analysis.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run Aegis
python aegis.py

# View recent logs
python aegis_inspect.py --last 20

# Replay a past session
python aegis.py --replay <session-uuid>
```

## Features

### ✅ Day 6 - Hardened & Polished (Phase B Complete)

- **Multiple Operation Modes**: Normal, Sandbox, Assist, Replay, Test
- **Heartbeat Logging**: Health monitoring with CPU/RAM/Window tracking
- **Config Hot-Reload**: Changes applied without restart
- **Auto-Pruning**: Prevents log database from growing endlessly
- **Test Connection**: Verify all subsystems operational
- **51 Passing Tests**: Comprehensive test coverage

### ✅ Day 5 - Logging Inspector & Replay System

- **Session Tracking**: Every run gets a unique UUID
- **Normalized Logging**: SQLite + optional JSONL with enforced schema
- **Log Inspector**: CLI tool for querying and analyzing history
- **Replay Mode**: Reconstruct past executions (dry-run only)
- **Multiple Formats**: JSON, table, and markdown output
- **Error Filtering**: Quickly find failures and issues
- **Session Management**: Track cycles, actions, errors per session

## CLI Tools

### aegis.py - Main Control Loop

```bash
# Run normally (creates new session)
python aegis.py

# Run in sandbox mode (mock actions, dry-run)
python aegis.py --sandbox --cycles 20

# Run in assist mode (interactive confirmations)
python aegis.py --assist --cycles 10

# Replay a past session (dry-run)
python aegis.py --replay <session-uuid>

# Test all subsystems
python aegis.py --test-connection

# Custom configuration
python aegis.py --cycles 50 --delay 2.0 --config custom.yaml
```

### aegis_inspect.py - Log Inspector

```bash
# Show last N events
python aegis_inspect.py --last 20

# Show specific session
python aegis_inspect.py --session <uuid>

# Show only errors
python aegis_inspect.py --errors-only

# List all sessions with stats
python aegis_inspect.py --sessions

# Output as JSON
python aegis_inspect.py --last 50 --as json

# Output as markdown (pipe to file)
python aegis_inspect.py --session <uuid> --as md > report.md

# Compact view (fewer columns)
python aegis_inspect.py --last 30 --compact
```

## Architecture

```
Aegis/
├── aegis.py                      # Main CLI
├── aegis_inspect.py              # Inspector CLI
├── requirements.txt
├── README.md
├── PHASE3_IMPLEMENTATION.md      # Detailed documentation
├── data/
│   ├── aegis.db                  # SQLite logs (auto-created)
│   └── aegis_events.jsonl        # Optional JSONL backup
├── src/
│   ├── core/
│   │   └── control_loop.py       # Main loop + replay
│   ├── aegis_logging/
│   │   ├── session.py            # Session tracking
│   │   ├── logger.py             # Normalized logger
│   │   └── log_inspector.py      # Query and format
│   ├── policy/                   # (Future: policy engine)
│   └── observers/                # (Future: desktop observers)
└── tests/
    ├── test_session.py
    ├── test_logger.py
    └── test_log_inspector.py
```

## Logging Schema

Every event logged has these required fields:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO8601 | When event occurred |
| `session_id` | UUID | Unique session identifier |
| `cycle_id` | int | Cycle number within session |
| `intent` | str | What Aegis is trying to do |
| `action` | str | Specific action taken |
| `policy_decision` | str | ALLOW or DENY |
| `result` | str | success/error/blocked |
| `duration_ms` | int | Action duration in milliseconds |
| `error` | str | Error message (nullable) |
| `metadata` | JSON | Additional context (optional) |

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_log_inspector.py -v
```

**Current Test Coverage**: 30 tests, all passing ✅

## Example Session

```bash
$ python aegis.py --cycles 3

🚀 Starting Aegis Control Loop
📋 Session ID: abc123-def456-...
🔄 Max Cycles: 3

🔄 Cycle 1/3
  👁️  Observed: System idle
  🎯 Intent: maintain_idle_state
  🛡️  Policy: ALLOW
  ✅ Result: success (150ms)

🔄 Cycle 2/3
  👁️  Observed: System idle
  🎯 Intent: maintain_idle_state
  🛡️  Policy: ALLOW
  ✅ Result: success (145ms)

🔄 Cycle 3/3
  👁️  Observed: System idle
  🎯 Intent: maintain_idle_state
  🛡️  Policy: ALLOW
  ✅ Result: success (148ms)

✅ Session complete: 3 cycles, 3 actions

$ python aegis_inspect.py --last 3 --compact

📜 Last 3 events:

Cycle  Intent               Action     Result   Duration(ms)  Error
3      maintain_idle_state  no_action  success  148
2      maintain_idle_state  no_action  success  145
1      maintain_idle_state  no_action  success  150

$ python aegis.py --replay abc123-def456-...

🎬 REPLAY MODE - Session abc123-def456-...
⚠️  DRY RUN: No actions will be executed

[Displays all events cycle-by-cycle...]

✅ Replay complete: 3 events replayed

📊 Summary:
   Success: 3
   Errors: 0
   Total: 3
```

## Safety Features

- **Replay is Always Dry-Run**: No actions executed during replay
- **Policy Checks**: All intents checked before execution
- **Error Logging**: Every failure captured with context
- **Session Isolation**: Each run tracked separately
- **Audit Trail**: Complete history in SQLite

## Phase 3 Status

- ✅ **Day 1-4**: Control loop, observation layer, digest generator
- ✅ **Day 5**: Logging inspector + replay system (COMPLETE)
- 🔜 **Day 6**: Policy engine with rules DSL
- 🔜 **Day 7**: Real observers (window detection, processes)
- 🔜 **Day 8**: Action executors (pyautogui/pywinauto)
- 🔜 **Day 9**: Intent generation with LLM
- 🔜 **Day 10**: Full integration test

## Contributing

See [PHASE3_IMPLEMENTATION.md](PHASE3_IMPLEMENTATION.md) for detailed architecture and implementation notes.

## License

Internal project for Sky infrastructure.
