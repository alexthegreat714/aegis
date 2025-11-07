#!/usr/bin/env python3
"""
Aegis - Intelligent Desktop Automation System

Main entry point for running Aegis control loop or replaying past sessions.

Usage:
    python aegis.py                    # Run normal mode
    python aegis.py --replay <uuid>    # Replay past session
    python aegis.py --cycles 50        # Run with custom cycle limit
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.control_loop import ControlLoop
from aegis_logging.logger import AegisLogger
from aegis_logging.session import SessionManager


def main():
    parser = argparse.ArgumentParser(
        description="Aegis - Intelligent Desktop Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Run Aegis normally
  %(prog)s --cycles 50                  # Run 50 cycles
  %(prog)s --replay abc123-def456...    # Replay session (dry-run)
  %(prog)s --db data/aegis.db           # Use custom database

For viewing logs, use aegis_inspect.py instead.
        """
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--replay',
        type=str,
        metavar='SESSION_ID',
        help='Replay a past session (dry-run mode, no actions executed)'
    )

    # Configuration
    parser.add_argument(
        '--cycles',
        type=int,
        default=100,
        help='Maximum number of cycles to run (default: 100)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between cycles in seconds (default: 1.0)'
    )
    parser.add_argument(
        '--db',
        type=str,
        default='data/aegis.db',
        help='Path to database (default: data/aegis.db)'
    )

    args = parser.parse_args()

    # Initialize logger
    logger = AegisLogger(db_path=args.db)

    # Initialize control loop
    control_loop = ControlLoop(
        logger=logger,
        max_cycles=args.cycles,
        cycle_delay_seconds=args.delay
    )

    # Execute requested mode
    try:
        if args.replay:
            # Replay mode - dry run only
            control_loop.replay(args.replay)
        else:
            # Normal mode - create new session and run
            session = SessionManager.create_session(replay_mode=False)
            control_loop.run(session)

        return 0

    except KeyboardInterrupt:
        print("\n👋 Aegis stopped by user")
        return 0
    except Exception as e:
        print(f"\n❌ Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
