# Aegis Quick Start Guide

## Installation

```bash
cd Aegis
pip install -r requirements.txt
```

## Running Aegis

```bash
# Run normally (creates new session)
python aegis.py

# Run in sandbox mode (safe testing with mock actions)
python aegis.py --sandbox --cycles 20

# Run in assist mode (interactive, asks before each action)
python aegis.py --assist --cycles 10

# Test all subsystems (config, database, health monitoring)
python aegis.py --test-connection

# Run with custom settings
python aegis.py --cycles 50 --delay 2.0 --config config/settings.yaml
```

## Viewing Logs

```bash
# Show last 20 events
python aegis_inspect.py --last 20

# Show specific session
python aegis_inspect.py --session <session-uuid>

# Show only errors
python aegis_inspect.py --errors-only

# List all sessions
python aegis_inspect.py --sessions

# Compact view (fewer columns)
python aegis_inspect.py --last 30 --compact

# JSON output
python aegis_inspect.py --last 10 --as json

# Markdown output (for reports)
python aegis_inspect.py --session <uuid> --as md > report.md
```

## Replaying Sessions

```bash
# Replay a past session (dry-run, no actions executed)
python aegis.py --replay <session-uuid>
```

## Finding Session IDs

```bash
# List all sessions to find UUIDs
python aegis_inspect.py --sessions

# Output:
# Session ID       Started              Ended                Cycles  Events  Errors
# ---------------  -------------------  -------------------  ------  ------  ------
# 031469d0-04a...  2025-11-07T15:22:28  2025-11-07T15:22:29      3       3       0
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_log_inspector.py -v
```

## Common Workflows

### Debug a specific session
```bash
# 1. List sessions to find the one you want
python aegis_inspect.py --sessions

# 2. View all events for that session
python aegis_inspect.py --session abc123-def456-...

# 3. Replay it to see step-by-step execution
python aegis.py --replay abc123-def456-...
```

### Find recent errors
```bash
# Show only events with errors
python aegis_inspect.py --errors-only

# Or limit to last 10 errors
python aegis_inspect.py --errors-only --last 10
```

### Export data for analysis
```bash
# Export as JSON
python aegis_inspect.py --last 100 --as json > events.json

# Export as markdown report
python aegis_inspect.py --session <uuid> --as md > session_report.md
```

## File Locations

- **Database**: `data/aegis.db` (auto-created)
- **JSONL Logs**: `data/aegis_events.jsonl` (optional)
- **Source Code**: `src/`
- **Tests**: `tests/`

## Help

```bash
# Main CLI help
python aegis.py --help

# Inspector help
python aegis_inspect.py --help
```

## Architecture

```
User Input → aegis.py → ControlLoop → AegisLogger → SQLite
                              ↓
                         Observation → Intent → Policy → Action
                              ↓
                          Log Event

aegis_inspect.py → LogInspector → SQLite → Formatted Output
```

## Key Features

- **Session Tracking**: Every run gets unique UUID
- **Normalized Schema**: 8 required fields per event
- **Multiple Formats**: JSON, table, markdown
- **Replay Mode**: DRY RUN reconstruction of past executions
- **Error Filtering**: Quickly find failures
- **Metadata Support**: Store additional context with each event

## Safety

- Replay mode NEVER executes real actions (dry-run only)
- Database is append-only (no destructive operations)
- Each session is isolated with unique UUID
- All policy decisions are logged for audit trail

---

For detailed documentation, see:
- [README.md](README.md) - User guide
- [PHASE3_IMPLEMENTATION.md](PHASE3_IMPLEMENTATION.md) - Technical details
- [DELIVERY_SUMMARY.md](DELIVERY_SUMMARY.md) - Day 5 delivery status
