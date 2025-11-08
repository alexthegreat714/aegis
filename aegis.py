#!/usr/bin/env python3
"""
Aegis - Intelligent Desktop Automation System

Main entry point with multiple operation modes.

Usage:
    python aegis.py                    # Run normal mode
    python aegis.py --assist           # Interactive mode with confirmations
    python aegis.py --sandbox          # Sandbox mode (mock actions)
    python aegis.py --replay <uuid>    # Replay past session
    python aegis.py --test-connection  # Test subsystems
    python aegis.py --cycles 50        # Run with custom cycle limit
    python aegis.py revision new "goal"  # Create revision snapshot
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.control_loop import ControlLoop
from aegis_logging.logger import AegisLogger
from aegis_logging.session import SessionManager
from utils.config_loader import ConfigLoader


def main():
    parser = argparse.ArgumentParser(
        description="Aegis - Intelligent Desktop Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Operation Modes:
  Normal Mode (default)
    Standard operation with full action execution
    Example: python aegis.py --cycles 100

  Assist Mode (--assist)
    Interactive mode that asks for confirmation before each action
    Example: python aegis.py --assist --cycles 10

  Sandbox Mode (--sandbox)
    Dry-run mode with mock actions for testing
    Example: python aegis.py --sandbox --cycles 20

  Replay Mode (--replay <session-id>)
    Reconstruct past execution from logs (read-only)
    Example: python aegis.py --replay abc123-def456...

  Test Mode (--test-connection)
    Verify all subsystems are operational
    Example: python aegis.py --test-connection

  Revision Mode (revision <subcommand>)
    Manage code revisions with full file snapshots
    Example: python aegis.py revision new "Add feature X"

Configuration:
  Edit config/settings.yaml to customize behavior
  Config supports hot-reload during execution

For log inspection, use: python aegis_inspect.py
        """
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--assist',
        action='store_true',
        help='Interactive mode with confirmations'
    )
    mode_group.add_argument(
        '--sandbox',
        action='store_true',
        help='Sandbox mode (mock actions, dry-run)'
    )
    mode_group.add_argument(
        '--replay',
        type=str,
        metavar='SESSION_ID',
        help='Replay a past session (dry-run mode)'
    )
    mode_group.add_argument(
        '--test-connection',
        action='store_true',
        help='Test database, config, and health monitoring'
    )

    # Configuration
    parser.add_argument(
        '--cycles',
        type=int,
        metavar='N',
        help='Maximum number of cycles to run (overrides config)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        metavar='SECONDS',
        help='Delay between cycles in seconds (overrides config)'
    )
    parser.add_argument(
        '--db',
        type=str,
        metavar='PATH',
        help='Path to database (default: from config)'
    )
    parser.add_argument(
        '--config',
        type=str,
        metavar='PATH',
        default='config/settings.yaml',
        help='Path to config file (default: config/settings.yaml)'
    )

    # Revision subcommands
    revision_parser = subparsers.add_parser('revision', help='Manage code revisions')
    revision_subparsers = revision_parser.add_subparsers(dest='revision_command', help='Revision commands')

    # revision new
    new_parser = revision_subparsers.add_parser('new', help='Create new revision')
    new_parser.add_argument('goal', type=str, help='Description of revision goal')

    # revision status
    revision_subparsers.add_parser('status', help='Show latest revision status')

    # revision list
    revision_subparsers.add_parser('list', help='List all revisions')

    # revision approve
    approve_parser = revision_subparsers.add_parser('approve', help='Approve revision (strict test validation)')
    approve_parser.add_argument('rev_id', type=str, help='Revision ID to approve')

    # revision discard
    discard_parser = revision_subparsers.add_parser('discard', help='Discard revision')
    discard_parser.add_argument('rev_id', type=str, help='Revision ID to discard')

    # revision restore
    restore_parser = revision_subparsers.add_parser('restore', help='Restore revision snapshot to working tree')
    restore_parser.add_argument('rev_id', type=str, help='Revision ID to restore')

    # revision diff
    diff_parser = revision_subparsers.add_parser('diff', help='Show diff summary for revision')
    diff_parser.add_argument('rev_id', type=str, help='Revision ID to diff')

    args = parser.parse_args()

    # Handle revision commands
    if args.command == 'revision':
        from cli.revision import main as revision_main
        return revision_main(args)

    # Initialize config
    config = ConfigLoader(config_path=args.config)

    # Override config from command line
    if args.delay is not None:
        config._config.setdefault('control_loop', {})['cycle_delay_seconds'] = args.delay

    # Determine mode
    if args.assist:
        mode = "assist"
    elif args.sandbox:
        mode = "sandbox"
    elif args.replay:
        mode = "replay"
    elif args.test_connection:
        mode = "test"
    else:
        mode = "normal"

    # Initialize logger
    db_path = args.db or config.get('logging.db_path', 'data/aegis.db')
    logger = AegisLogger(
        db_path=db_path,
        enable_jsonl=config.get('logging.enable_jsonl', True)
    )

    # Initialize control loop
    control_loop = ControlLoop(
        logger=logger,
        config=config,
        mode=mode
    )

    # Execute requested mode
    try:
        if args.test_connection:
            # Test connection mode
            success = control_loop.test_connection()
            return 0 if success else 1

        elif args.replay:
            # Replay mode - dry run only
            control_loop.replay(args.replay)
            return 0

        else:
            # Normal/Assist/Sandbox mode - create new session and run
            session = SessionManager.create_session(replay_mode=False)
            control_loop.run(session, cycles=args.cycles)
            return 0

    except KeyboardInterrupt:
        print("\n Aegis stopped by user")
        return 0
    except Exception as e:
        print(f"\n Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
