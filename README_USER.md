# Aegis — How You Use It (Human-Readable Version)

## What Aegis Is
Aegis is your local security + automation agent.  
It can call Claude, patch code, stage revisions, and run tools — but nothing goes live without you.

Think of it as:
> “Claude can build it, Aegis can stage it, only Alex can deploy it.”

## How Changes Flow

Claude → proposes fix or tool
Aegis → sandboxes it (auto-approve OK)
Alex → reviews / merges / rejects

vbnet
Copy code

✅ Aegis is allowed to **auto-approve Claude’s work into the sandbox**  
❌ Aegis is **not allowed to change live code** without you

Sandboxed changes live here:

aegis/sandbox/revisions/<timestamp_slug>/

markdown
Copy code

Each revision contains:
- a README summarizing the change
- a manifest of every modified file
- before/after versions
- logs of reasoning + validation
- `PENDING_FINAL_APPROVAL` marker

## How You Interact

### Start Aegis
start_aegis.bat

pgsql
Copy code

### Modes
| Option | What Happens |
|--------|--------------|
| 1 | Full interactive CLI (Aegis thinks aloud, waits for you) |
| 2 | Autonomous mode (no pausing unless approval required) |
| 3 | Test OWUI API connection |
| 4 | View logs |
| 5 | Open sandbox revisions directory |
| 6 | Approve/reject pending revision(s) |
| 7 | Kill all Aegis-related processes |
| 8 | Exit |

### Approving/Reverting Revisions
python aegis.py --list-revisions
python aegis.py --approve-revision <id>
python aegis.py --reject-revision <id>

markdown
Copy code

## Important Rules
1. **Claude can never touch live code.**
2. **Aegis can never merge to live without you.**
3. **All changes are logged, versioned, and reversible.**
4. **If you disappear, Aegis continues—but only in sandbox.**

## Coming Later
- RAG memory
- VS Code automation
- nightly task runner
- Hack-The-Box simulation mode
- GPU fine-tune agent