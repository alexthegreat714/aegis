# Aegis System Specification (Authoritative)

## 1. Change Control Policy

### 1.1 Sandbox Rule
Aegis MAY fully approve and stage Claude-generated patches into the sandbox.

Aegis SHALL NOT modify any production file without explicit human approval from Alex.

### 1.2 Definitions
SANDBOX_APPROVAL = Aegis validation + staging only
FINAL_APPROVAL = Alex merges changes to live environment

shell
Copy code

### 1.3 Enforcement Logic
if action.target == "live":
require_human_approval = true
else if action.target == "sandbox":
aegis_auto_approval = allowed

shell
Copy code

### 1.4 Sandbox Structure
aegis/sandbox/revisions/<YYYYMMDD_HHMMSS_slug>/
README.md
manifest.json
original/
patched/
logs/
PENDING_FINAL_APPROVAL

sql
Copy code

## 2. Execution Modes

| Mode | Description |
|------|-------------|
| interactive | verbose reasoning, user-intervention windows |
| autonomous | no pauses except where policy requires |
| approve-revision | apply staged change to production |
| reject-revision | delete staged change |
| list-revisions | enumerate pending sandboxes |

## 3. Logging Requirements
Aegis MUST log:
- every LLM request and response
- every patch staged
- every file changed checksum-verified
- every human approval event
- every policy decision (allow/block/require)

Logs are dual-written to:
data/logs/*.jsonl
data/aegis.db (SQLite)

pgsql
Copy code

## 4. LLM Integration

### 4.1 Call Pattern
- API: OpenWebUI POST /api/chat/completions
- Model: "aegis"
- Reasoning temperature: 0.2
- Required wrapper: aegis_reasoning_call()

### 4.2 Output Contract
Claude MUST return structured JSON:
```json
{
  "intent": "modify_files",
  "rationale": "...",
  "patches": [
    { "file": "path/to/file.py", "replacement": "..." }
  ]
}
5. Human Safety Guarantees
Aegis SHALL:

isolate all modifications

checksum original files

rollback failures

require Alex for any irreversible change

Aegis SHALL NOT:

run OS-level destructive commands

deploy network-affecting code

execute live patching without final approval

6. Startup Behavior
On launch, Aegis MUST:

Load README_SPEC.md into memory

Load policy.yaml

Verify sandbox path exists

Scan for PENDING_FINAL_APPROVAL and notify user

yaml
Copy code

---

## ✅ Next Step

If approved, I will now:

1. Add both README files to Git-ready text blocks  
2. Write the Claude instruction block so it **obeys the spec**  
3. Provide the `sandbox/` folder layout  
4. Write Phase 4 control-loop TODOs in `PHASE4_NOTES.md`  

---

## ❓ Before I proceed — choose sandbox location

LOCAL = aegis/sandbox/ inside the repo
GLOBAL = C:\Sandbox\Aegis\ shared across agents

csharp
Copy code

Reply with:

SANDBOX = LOCAL

nginx
Copy code
or
SANDBOX = GLOBAL

mathematica
Copy code

Once I have that, I’ll finalize the file contents and the Claude instruction sheet.