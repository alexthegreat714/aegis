"""
Aegis entry point.

Initializes all systems and starts the control loop.
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.helpers import load_yaml
from aegis_logging.logger import AegisLogger
from core.policy_engine import PolicyEngine
from core.action_planner import ActionPlanner
from core.control_loop import ControlLoop
from core.sandbox_revision import SandboxRevisionManager
from core.queue_executor import QueueExecutor
from clients.owui_client import OWUIClient
from automation.desktop import DesktopAutomation
from automation.vscode import VSCodeAutomation
from automation.windows import WindowsAutomation


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Aegis - Local AI Security/DevOps Agent")

    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to settings.yaml"
    )

    parser.add_argument(
        "--policy",
        default="config/policy.yaml",
        help="Path to policy.yaml"
    )

    parser.add_argument(
        "--prompt",
        help="Initial prompt for the agent"
    )

    parser.add_argument(
        "--mode",
        choices=["assist", "execute", "autonomous"],
        help="Override operation mode from policy"
    )

    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test OpenWebUI connection and exit"
    )

    # Interactive mode
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode with verbose reasoning and pause windows"
    )

    # Autonomous run mode
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run in autonomous mode (auto-continue, still pauses for high-risk)"
    )

    # Talk mode (conversational)
    parser.add_argument(
        "--talk",
        action="store_true",
        help="Start interactive talk mode for conversations with Aegis"
    )

    # Queue execution
    parser.add_argument(
        "--queue",
        action="store_true",
        help="Display project task queue and execute next task (read-only)"
    )

    parser.add_argument(
        "--queue-all",
        action="store_true",
        help="Execute all available tasks in queue (read-only)"
    )

    # Revision management
    parser.add_argument(
        "--approve-revision",
        metavar="REVISION_ID",
        help="Approve and apply a pending revision"
    )

    parser.add_argument(
        "--reject-revision",
        metavar="REVISION_ID",
        help="Reject a pending revision"
    )

    parser.add_argument(
        "--list-revisions",
        action="store_true",
        help="List all pending revisions"
    )

    parser.add_argument(
        "--rollback-revision",
        metavar="REVISION_ID",
        help="Rollback an applied revision (not implemented yet)"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    print("=" * 60)
    print("AEGIS - Local AI Security/DevOps Agent")
    print("=" * 60)
    print()

    args = parse_args()

    # Load settings
    try:
        settings = load_yaml(args.config)
        print(f"[Config] Loaded settings from {args.config}")
    except Exception as e:
        print(f"[Error] Failed to load settings: {e}")
        sys.exit(1)

    # Load README_SPEC.md (binding system policy)
    readme_spec_path = Path("README_SPEC.md")
    readme_spec_content = None
    try:
        if readme_spec_path.exists():
            readme_spec_content = readme_spec_path.read_text(encoding="utf-8")
            settings["readme_spec"] = readme_spec_content
            print(f"[Config] Loaded README_SPEC.md ({len(readme_spec_content)} bytes)")
        else:
            print(f"[Config] WARNING: README_SPEC.md not found - no binding policy loaded")
    except Exception as e:
        print(f"[Config] WARNING: Failed to load README_SPEC.md: {e}")

    # Initialize logger
    log_dir = settings.get("paths", {}).get("logs_dir", "data/logs")
    db_path = settings.get("paths", {}).get("db_path", "data/aegis.db")

    logger = AegisLogger(
        log_dir=log_dir,
        db_path=db_path,
        settings=settings
    )

    logger.log_event(
        event_type="aegis_startup",
        data={"args": vars(args)},
        status="info"
    )

    # Initialize OWUI client
    owui_config = settings.get("owui", {})
    try:
        owui_client = OWUIClient(
            base_url=owui_config.get("base_url", "http://127.0.0.1:3000"),
            endpoint=owui_config.get("endpoint", "/api/chat/completions"),
            token_file=owui_config.get("token_file", "config/.owui_token"),
            timeout=owui_config.get("timeout_seconds", 30),
            default_model=owui_config.get("model", "agentica-org_DeepCoder-14B-Preview-Q8_0:latest")
        )

        if args.test_connection:
            print("\n[Test] Testing OpenWebUI connection...")
            if owui_client.test_connection():
                print("[Test] OK Connection successful")
                sys.exit(0)
            else:
                print("[Test] FAILED Connection failed")
                sys.exit(1)

    except Exception as e:
        print(f"[Error] Failed to initialize OWUI client: {e}")
        logger.log_event(
            event_type="owui_init_failed",
            data={"error": str(e)},
            status="error"
        )
        sys.exit(1)

    # Initialize policy engine
    try:
        policy_engine = PolicyEngine(
            policy_path=args.policy,
            logger=logger
        )

        # Override mode if specified
        if args.mode:
            policy_engine.policy["mode"] = args.mode
            print(f"[Policy] Mode overridden to: {args.mode}")

    except Exception as e:
        print(f"[Error] Failed to load policy: {e}")
        sys.exit(1)

    # Initialize automation systems
    desktop_automation = DesktopAutomation(logger=logger, settings=settings)
    vscode_automation = VSCodeAutomation(
        logger=logger,
        settings=settings,
        desktop=desktop_automation
    )
    windows_automation = WindowsAutomation(logger=logger, settings=settings)

    print("[Automation] Desktop, VS Code, and Windows automation initialized")

    # Initialize action planner
    action_planner = ActionPlanner(logger=logger, settings=settings)

    # Initialize control loop
    control_loop = ControlLoop(
        settings=settings,
        policy_engine=policy_engine,
        logger=logger,
        owui_client=owui_client,
        action_planner=action_planner
    )

    # Initialize sandbox revision manager
    sandbox_manager = SandboxRevisionManager(logger=logger)

    # Handle revision management commands
    if args.list_revisions:
        pending = sandbox_manager.list_pending_revisions()
        if pending:
            print("\n[Revisions] Pending revisions:")
            for rev_id in pending:
                print(f"  - {rev_id}")
        else:
            print("\n[Revisions] No pending revisions")
        sys.exit(0)

    if args.approve_revision:
        success = sandbox_manager.approve_revision(args.approve_revision)
        sys.exit(0 if success else 1)

    if args.reject_revision:
        success = sandbox_manager.reject_revision(args.reject_revision)
        sys.exit(0 if success else 1)

    if args.rollback_revision:
        print(f"[Revisions] Rollback not implemented yet for: {args.rollback_revision}")
        sys.exit(1)

    # Handle queue execution commands
    if args.queue or args.queue_all:
        queue_executor = QueueExecutor(
            logger=logger,
            owui_client=owui_client
        )

        if not queue_executor.load_queue():
            print("[Queue] Failed to load task queue")
            sys.exit(1)

        queue_executor.display_queue()

        if args.queue:
            # Execute next task
            queue_executor.execute_next(verbose=True)
        elif args.queue_all:
            # Execute all available tasks
            queue_executor.execute_all(verbose=True)

        sys.exit(0)

    # Display startup info
    print()
    print("Aegis is ready.")
    print(f"Mode: {policy_engine.get_mode()}")
    print(f"Policy: {args.policy}")
    print()

    # Handle different execution modes
    if args.talk:
        print("[Mode] TALK MODE - Interactive conversation with Aegis")
        print("[Mode] Type 'exit' or 'quit' to end conversation")
        print()

        conversation_history = []

        while True:
            try:
                user_input = input("You: ")

                if user_input.lower() in ["exit", "quit", "bye"]:
                    print("\n[Aegis] Goodbye!")
                    break

                if not user_input.strip():
                    continue

                # Build messages for conversation
                messages = [
                    {"role": "system", "content": "You are Aegis, a helpful local AI security/devops assistant. Be concise and friendly."}
                ] + conversation_history + [
                    {"role": "user", "content": user_input}
                ]

                # Call OWUI
                response = owui_client.chat_completion(messages=messages, temperature=0.7)
                assistant_reply = response["choices"][0]["message"]["content"]

                print(f"\nAegis: {assistant_reply}\n")

                # Update conversation history
                conversation_history.append({"role": "user", "content": user_input})
                conversation_history.append({"role": "assistant", "content": assistant_reply})

                # Log conversation
                logger.log_llm_call(
                    model=owui_client.default_model,
                    prompt=user_input,
                    response=assistant_reply,
                    tokens_used=0
                )

            except KeyboardInterrupt:
                print("\n\n[Aegis] Conversation interrupted")
                break
            except Exception as e:
                print(f"\n[Error] {e}\n")

        sys.exit(0)

    elif args.interactive:
        print("[Mode] INTERACTIVE - Verbose reasoning with pause windows")
        print("[Mode] You can interrupt at any time with commands:")
        print("[Mode]   pause, skip, abort, approve, view, continue")
        print()

        if not args.prompt:
            args.prompt = input("Enter task: ")

        if args.prompt:
            # TODO: Start interactive control loop with pause windows
            control_loop.start(initial_prompt=args.prompt)
        else:
            print("[Error] No task provided")
            sys.exit(1)

    elif args.run:
        print("[Mode] AUTONOMOUS - Auto-continue (pauses for high-risk only)")
        print()

        if not args.prompt:
            print("[Error] --run requires --prompt")
            sys.exit(1)

        # TODO: Start autonomous control loop
        control_loop.start(initial_prompt=args.prompt)

    elif args.prompt:
        print(f"[Mode] Starting with prompt: {args.prompt}")
        print()
        control_loop.start(initial_prompt=args.prompt)

    else:
        print("No action specified. Available options:")
        print()
        print("  --talk                     Start conversational talk mode")
        print("  --interactive              Run with interactive reasoning")
        print("  --run --prompt 'task'      Run autonomously")
        print("  --prompt 'task'            Run with default settings")
        print("  --queue                    Display queue and execute next task")
        print("  --queue-all                Execute all available tasks")
        print("  --test-connection          Test OWUI connection")
        print("  --list-revisions           List pending revisions")
        print("  --approve-revision ID      Approve revision")
        print("  --reject-revision ID       Reject revision")
        print()
        print("Example:")
        print("  python aegis.py --talk")
        print("  python aegis.py --queue")
        print("  python aegis.py --interactive")
        print("  python aegis.py --run --prompt 'List running processes'")
        print("  python aegis.py --test-connection")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[Aegis] Shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[Error] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
