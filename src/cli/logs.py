"""
Log viewing CLI for Aegis.

Provides tail functionality for live log monitoring.
"""

import time
from pathlib import Path


def tail_file(file_path: Path, lines: int = 20, follow: bool = False):
    """
    Tail a file (like tail -f).

    Args:
        file_path: Path to log file
        lines: Number of lines to show initially
        follow: If True, keep following file for new lines
    """
    if not file_path.exists():
        print(f"Log file not found: {file_path}")
        print("Waiting for log file to be created...")

        # Wait for file to exist
        while not file_path.exists():
            time.sleep(1)

    # Read initial lines
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        all_lines = f.readlines()
        initial_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        for line in initial_lines:
            print(line, end='')

    if not follow:
        return

    # Follow mode
    print("\n[Following log file... Press Ctrl+C to stop]")

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        # Seek to end
        f.seek(0, 2)

        try:
            while True:
                line = f.readline()
                if line:
                    print(line, end='')
                else:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[Stopped tailing]")


def main(args):
    """
    Main entry point for logs CLI.

    Args:
        args: Parsed command-line arguments
    """
    if args.logs_command == 'tail':
        # Find log file
        log_file = Path('logs/aegis_live.log')

        tail_file(log_file, lines=args.lines, follow=args.live)
        return 0

    else:
        print(f"Unknown logs command: {args.logs_command}")
        return 1
