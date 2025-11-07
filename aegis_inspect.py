#!/usr/bin/env python3
"""
Aegis Log Inspector CLI

Command-line tool for viewing, filtering, and analyzing Aegis execution history.

Usage Examples:
    python aegis_inspect.py --last 20
    python aegis_inspect.py --session <uuid>
    python aegis_inspect.py --errors-only
    python aegis_inspect.py --sessions
    python aegis_inspect.py --last 50 --as json
    python aegis_inspect.py --session <uuid> --as md > report.md
"""

import sys
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aegis_logging.log_inspector import LogInspector


def main():
    parser = argparse.ArgumentParser(
        description="Aegis Log Inspector - View and analyze Aegis execution history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --last 20                    # Show last 20 events
  %(prog)s --session abc123             # Show all events for session
  %(prog)s --errors-only                # Show only errors
  %(prog)s --sessions                   # List all sessions
  %(prog)s --last 50 --as json          # Output as JSON
  %(prog)s --last 30 --compact          # Compact table view
        """
    )

    # Query options (mutually exclusive)
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument(
        '--last',
        type=int,
        metavar='N',
        help='Show last N events (default: 20)'
    )
    query_group.add_argument(
        '--session',
        type=str,
        metavar='UUID',
        help='Show all events for specific session ID'
    )
    query_group.add_argument(
        '--errors-only',
        action='store_true',
        help='Show only events with errors'
    )
    query_group.add_argument(
        '--sessions',
        action='store_true',
        help='List all sessions with summary statistics'
    )

    # Format options
    parser.add_argument(
        '--as',
        dest='format',
        choices=['json', 'table', 'md'],
        default='table',
        help='Output format (default: table)'
    )
    parser.add_argument(
        '--compact',
        action='store_true',
        help='Use compact view with fewer columns'
    )

    # Database path
    parser.add_argument(
        '--db',
        type=str,
        default='data/aegis.db',
        help='Path to Aegis database (default: data/aegis.db)'
    )

    args = parser.parse_args()

    # Initialize inspector
    try:
        inspector = LogInspector(db_path=args.db)
    except FileNotFoundError as e:
        print(f" Error: {e}", file=sys.stderr)
        print("\nThe Aegis database doesn't exist yet.", file=sys.stderr)
        print("Run Aegis at least once to create the database:", file=sys.stderr)
        print("  python aegis.py", file=sys.stderr)
        return 1

    # Execute query
    try:
        if args.sessions:
            # List sessions
            sessions = inspector.list_sessions()
            output = inspector.format_sessions(sessions, format_type=args.format)
            print(output)

        elif args.session:
            # Query specific session
            events = inspector.query_session(args.session)
            if not events:
                print(f"  No events found for session: {args.session}", file=sys.stderr)
                return 1

            print(f" Session: {args.session}")
            print(f" Total events: {len(events)}")
            print(f" Cycles: {max(e['cycle_id'] for e in events)}")
            print()

            output = inspector.format_events(
                events,
                format_type=args.format,
                compact=args.compact
            )
            print(output)

        elif args.errors_only:
            # Query errors only
            events = inspector.query_errors_only()
            if not events:
                print(" No errors found in Aegis logs!")
                return 0

            print(f"  Found {len(events)} events with errors:\n")
            output = inspector.format_events(
                events,
                format_type=args.format,
                compact=args.compact
            )
            print(output)

        else:  # args.last
            # Query last N events
            n = args.last if args.last else 20
            events = inspector.query_last(n)

            if not events:
                print(" No events found in database.")
                return 0

            print(f" Last {len(events)} events:\n")
            output = inspector.format_events(
                events,
                format_type=args.format,
                compact=args.compact
            )
            print(output)

        return 0

    except ValueError as e:
        print(f" Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f" Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
