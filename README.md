# Aegis - Local AI Security/DevOps Agent

Aegis is a semi-autonomous AI agent designed to run locally on Windows, performing security and development operations with policy-based controls.

## Core Features

- **Local AI Processing**: All LLM calls go through local OpenWebUI instance
- **Policy-Based Control**: YAML-defined policies for allowed/blocked/approval-required actions
- **Comprehensive Logging**: Dual logging system (JSONL + SQLite) for full audit trails
- **Desktop Automation**: Interact with VS Code and Windows UI elements
- **Sandbox Testing**: Isolated environment for testing destructive operations
- **Assist Mode**: Suggest-only mode before autonomous execution

## Architecture

```
LLM (OWUI) → Intent → Policy Check → Action Plan → Automation → Logging
```

## Project Structure

```
aegis/
├── config/          # Policy and settings files
├── data/            # Logs and database
├── sandbox/         # Isolated testing environment
├── src/             # Main source code
│   ├── core/        # Control loop, policy engine, action planner
│   ├── intents/     # Intent type definitions and schemas
│   ├── clients/     # OpenWebUI API client
│   ├── automation/  # Desktop/VS Code automation
│   ├── logging/     # Dual logging system
│   └── utils/       # Common utilities
└── tests/           # Unit tests
```

## Setup

1. **Install Python 3.11+**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure settings**:
   - Edit `config/settings.yaml` with your OWUI endpoint and token path
   - Edit `config/policy.yaml` to define allowed actions

4. **Run Aegis**:
   ```bash
   python src/main.py
   ```

## Operation Modes

- **assist**: Suggest actions only, no execution (default)
- **execute**: Execute with human approval for sensitive actions
- **autonomous**: Full autonomous operation (use with caution)

## Safety Features

- All actions logged before execution
- Policy enforcement on every action
- Sandbox environment for destructive testing
- No cloud API calls (local-only by default)
- No hard-coded credentials

## Development Status

**Current Phase**: Skeleton scaffold - framework only, no implementations yet.

## License

TBD
