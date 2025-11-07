# bootstrap_repo.py
# One-shot bootstrap: prep ignores, init git, first commit, push to GitHub.
# Run from the project root (C:\Users\blyth\aegis).

import os
import sys
import subprocess
from pathlib import Path
from textwrap import dedent

# ---- CONFIG ----
REPO_URL = "https://github.com/alexthegreat714/aegis.git"
PROJECT_DIR = Path(__file__).resolve().parent
BRANCH = "main"
COMMIT_MSG = "Bootstrap commit: Aegis core structure, ready for Claude Phase B build-out"

# Files/dirs to make sure exist (tracked as structure only)
STRUCTURE_DIRS = [
    PROJECT_DIR / "data",
    PROJECT_DIR / "sandbox",
    PROJECT_DIR / "RAG",
    PROJECT_DIR / "src",
    PROJECT_DIR / "tests",
    PROJECT_DIR / "config",
]

# These files will be added if present (safe to commit)
SAFE_TOP_FILES = [
    "aegis.py",
    "README.md",
    "QUICKSTART.md",
    "SETUP_COMPLETE.md",
    "IMPLEMENTATION_STATUS.md",
    "PHASE3_IMPLEMENTATION.md",
    "README_USER.md",
    "README_SPEC.md",
    "requirements.txt",
    "start_aegis.bat",
]

# Paths that must NEVER be committed
NEVER_COMMIT = [
    "config/.owui_token",
]

GITIGNORE_CONTENT = dedent(
    r"""
    # Python caches
    __pycache__/
    *.pyc
    *.pyo
    *.pyd

    # Virtual envs
    venv/
    env/
    .env
    .envrc

    # IDE
    .vscode/
    .idea/

    # Logs & runtime db
    *.db
    *.log
    data/**
    !data/.gitkeep

    # Config secrets
    config/.owui_token

    # Sandbox scratch
    sandbox/output/**
    sandbox/tmp/**
    """
).strip() + "\n"


def run(cmd, cwd=None, check=True):
    print(f"> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, text=True)
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result.returncode


def ensure_git_available():
    try:
        subprocess.run("git --version", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        print("ERROR: git is not available on PATH.")
        sys.exit(1)


def write_gitignore():
    gi = PROJECT_DIR / ".gitignore"
    if gi.exists():
        # Backup existing
        backup = PROJECT_DIR / ".gitignore.bak"
        print("Found existing .gitignore — backing up to .gitignore.bak and replacing.")
        backup.write_text(gi.read_text(encoding="utf-8"), encoding="utf-8")
    gi.write_text(GITIGNORE_CONTENT, encoding="utf-8")
    print("Wrote .gitignore")


def ensure_structure():
    for d in STRUCTURE_DIRS:
        d.mkdir(parents=True, exist_ok=True)
    # ensure .gitkeep placeholders
    for keeper in [PROJECT_DIR / "data/.gitkeep", PROJECT_DIR / "sandbox/.gitkeep", PROJECT_DIR / "RAG/.gitkeep"]:
        if not keeper.exists():
            keeper.parent.mkdir(parents=True, exist_ok=True)
            keeper.write_text("", encoding="utf-8")
    print("Ensured structure and .gitkeep placeholders")


def init_git():
    # if already a repo, skip init
    if (PROJECT_DIR / ".git").exists():
        print("Git repo already initialized.")
        return
    run("git init", cwd=PROJECT_DIR)
    run(f"git branch -M {BRANCH}", cwd=PROJECT_DIR)
    print("Initialized git")


def stage_files():
    # Prevent accidental staging of forbidden files
    for path in NEVER_COMMIT:
        p = PROJECT_DIR / path
        if p.exists():
            print(f"Removing forbidden file from worktree: {path}")
            # Leave file on disk but make sure it's not staged
            run(f'git rm --cached -f "{path}"', cwd=PROJECT_DIR, check=False)

    # Add safe roots if present
    add_list = []
    for rel in SAFE_TOP_FILES:
        if (PROJECT_DIR / rel).exists():
            add_list.append(rel)

    # Always add these folders (git will respect .gitignore for internals)
    must_add_dirs = ["src", "tests", "sandbox", "RAG", "config", "data"]
    for rel in must_add_dirs:
        if (PROJECT_DIR / rel).exists():
            add_list.append(rel)

    if not add_list:
        print("Nothing to add. Exiting.")
        sys.exit(0)

    quoted = " ".join(f'"{a}"' for a in add_list)
    run(f"git add {quoted} .gitignore", cwd=PROJECT_DIR)

    # Double insurance: unstage forbidden file if git tried to include it
    for path in NEVER_COMMIT:
        run(f'git restore --staged "{path}"', cwd=PROJECT_DIR, check=False)

    print("Staged files.")


def commit_if_needed():
    # Check if anything staged
    rc = subprocess.run("git diff --cached --quiet", shell=True, cwd=PROJECT_DIR)
    if rc.returncode == 0:
        print("No changes staged. Skipping commit.")
        return
    run(f'git commit -m "{COMMIT_MSG}"', cwd=PROJECT_DIR)
    print("Committed.")


def set_remote_and_push():
    # Set/replace origin
    got_remote = subprocess.run("git remote get-url origin", shell=True, cwd=PROJECT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if got_remote.returncode != 0:
        run(f'git remote add origin "{REPO_URL}"', cwd=PROJECT_DIR)
    else:
        current = got_remote.stdout.strip()
        if current != REPO_URL:
            print(f"Updating origin from {current} -> {REPO_URL}")
            run(f'git remote set-url origin "{REPO_URL}"', cwd=PROJECT_DIR)

    run(f"git push -u origin {BRANCH}", cwd=PROJECT_DIR)
    print("Pushed to GitHub.")


def main():
    os.environ["PYTHONUTF8"] = "1"
    print("Aegis Git bootstrap starting…")
    ensure_git_available()
    write_gitignore()
    ensure_structure()
    init_git()
    stage_files()
    commit_if_needed()
    set_remote_and_push()
    print("Done.")

if __name__ == "__main__":
    main()
