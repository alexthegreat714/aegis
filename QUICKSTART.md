# Aegis Quick Start Guide

## Installation

1. **Install Python dependencies**:
   ```bash
   cd aegis
   pip install -r requirements.txt
   ```

2. **Get your OpenWebUI token**:
   - Open OpenWebUI in browser: http://127.0.0.1:3000
   - Open browser DevTools (F12)
   - Go to Application → Local Storage
   - Find the `token` key
   - Copy the token value

3. **Create token file**:
   ```bash
   # Create the token file
   echo "YOUR_TOKEN_HERE" > config/.owui_token
   ```

## Test Connection

Before running Aegis, test your OpenWebUI connection:

```bash
python src/main.py --test-connection
```

You should see:
```
[OWUI] Connection test successful: ...
[Test] ✓ Connection successful
```

## First Run

Run Aegis in assist mode (suggestion-only):

```bash
python src/main.py --prompt "Take a screenshot"
```

## Operation Modes

### Assist Mode (Default)
Suggests actions but doesn't execute without approval:
```bash
python src/main.py --mode assist --prompt "Open VS Code"
```

### Execute Mode
Executes allowed actions, asks approval for sensitive operations:
```bash
python src/main.py --mode execute --prompt "List running processes"
```

### Autonomous Mode
Full autonomous operation (use with caution):
```bash
python src/main.py --mode autonomous --prompt "Run tests"
```

## Configuration

### Policy Configuration
Edit `config/policy.yaml` to define:
- Allowed/blocked/approval-required actions
- Restricted paths
- Sandbox-only actions

### Settings Configuration
Edit `config/settings.yaml` to configure:
- OpenWebUI API endpoint
- Logging preferences
- Automation settings

## Logs and Audit Trail

Aegis logs everything to two locations:

1. **JSONL logs**: `data/logs/aegis_YYYYMMDD.jsonl`
   - Human-readable, one JSON per line
   - Easy to grep/tail

2. **SQLite database**: `data/aegis.db`
   - Queryable with SQL
   - Full audit trail

### View recent logs:
```bash
# View today's JSONL log
tail -f data/logs/aegis_*.jsonl

# Query database
sqlite3 data/aegis.db "SELECT * FROM actions ORDER BY timestamp DESC LIMIT 10"
```

## Next Steps

### 1. Enable Desktop Automation
Uncomment in `requirements.txt`:
```
pyautogui>=0.9.54
pywinauto>=0.6.8
```

Then install:
```bash
pip install pyautogui pywinauto
```

### 2. Implement Control Loop
The current scaffold has TODOs marked in:
- `src/core/control_loop.py` - Main agent loop
- `src/automation/desktop.py` - Desktop actions
- `src/automation/vscode.py` - VS Code actions
- `src/automation/windows.py` - Windows system actions

### 3. Customize OWUI Client
Verify the API format in `src/clients/owui_client.py` matches your Chess agent's pattern.

### 4. Write Tests
Implement tests in `tests/` directory:
```bash
pytest tests/
```

## Safety Notes

- Aegis starts in **assist mode** by default (suggest-only)
- All actions are logged before execution
- Destructive actions are sandbox-only by default
- Review `config/policy.yaml` before running in execute/autonomous mode

## Troubleshooting

### Token not loading
- Verify `config/.owui_token` exists
- Check file contains only the token (no newlines/spaces)
- Ensure OpenWebUI is running on port 3000

### Import errors
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check Python version is 3.11+

### Connection failed
- Verify OpenWebUI is running: http://127.0.0.1:3000
- Check base_url in `config/settings.yaml`
- Test with `--test-connection` flag

## Support

For issues or questions, refer to:
- Main README.md
- Policy documentation in config/policy.yaml
- Code comments and TODOs in source files
