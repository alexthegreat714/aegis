"""
Claude CLI for Aegis.

Provides commands for interacting with Claude via VS Code.
"""

from pathlib import Path

from claude.prompts import build_phase_c_prompt, build_repo_summary
from claude.vscode_session import ClaudeVSCodeSession
from cli.revision import RevisionSystem
from utils.config_loader import ConfigLoader


def main(args):
    """
    Main entry point for Claude CLI.

    Args:
        args: Parsed command-line arguments
    """
    repo_root = Path.cwd()

    # Load configuration
    config = ConfigLoader(config_path='config/settings.yaml')
    settings = config._config

    if args.claude_command == 'plan':
        # Generate and display development plan prompt
        repo_summary = build_repo_summary(repo_root)
        prompt = build_phase_c_prompt(
            goal=args.goal,
            repo_summary=repo_summary
        )

        print(prompt)
        print("\n[Prompt generated - copy/paste to Claude]")
        return 0

    elif args.claude_command == 'send':
        # Send prompt to Claude via VS Code
        rev_id = args.rev
        prompt_text = args.prompt if args.prompt else None

        # Load prompt from revision if not provided
        if not prompt_text:
            prompt_file = repo_root / ".aegis_revisions" / rev_id / "prompt.txt"
            if prompt_file.exists():
                prompt_text = prompt_file.read_text(encoding='utf-8')
            else:
                print(f"Error: No prompt provided and no prompt.txt found in revision {rev_id}")
                return 1

        # Send via Claude session
        with ClaudeVSCodeSession(
            rev_id=rev_id,
            revisions_root=repo_root / "revisions",
            settings=settings
        ) as session:
            session.start(goal=f"Send prompt for {rev_id}", workdir=repo_root)
            prompt_num, reply = session.send_and_fetch(prompt_text)

            print(f"\n[Prompt sent and reply received]")
            print(f"Reply saved to: .aegis_revisions/{rev_id}/claude_io/reply_{prompt_num:03d}.txt")

        return 0

    elif args.claude_command == 'apply':
        # Apply revision and run tests
        rev_id = args.rev
        auto_approve = args.auto

        rev_system = RevisionSystem(repo_root=repo_root)

        print(f"Applying revision {rev_id}...")
        print("Manual step: Apply code changes from Claude's reply")

        if auto_approve:
            input("\nPress Enter when changes are applied and ready for testing...")

            # Run tests and auto-approve
            result = rev_system.cmd_approve(rev_id)

            if result == 0:
                print(f"\n[OK] Revision {rev_id} automatically approved!")
            else:
                print(f"\n[X] Revision {rev_id} failed tests - not approved")

            return result
        else:
            print(f"\nUse 'aegis revision approve {rev_id}' when ready")
            return 0

    else:
        print(f"Unknown claude command: {args.claude_command}")
        return 1
