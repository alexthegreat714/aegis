"""
Night Agent CLI commands.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from agents.night_agent import NightAgent
from core.night_report import NightReportGenerator

logger = logging.getLogger(__name__)


def cmd_night_agent_run(
    max_goals: int = 5,
    max_rounds: int = 3,
    auto_approve: bool = False,
    dry_run: bool = False,
    repo_root: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None
):
    """
    Run autonomous night agent.

    Args:
        max_goals: Maximum number of goals to attempt
        max_rounds: Maximum rounds per goal
        auto_approve: Auto-approve passing revisions (use with caution)
        dry_run: Dry-run mode (simulates actions)
        repo_root: Repository root path
        config: Configuration dictionary
    """
    if repo_root is None:
        repo_root = Path.cwd()

    print(f"\n{'='*70}")
    print("AUTONOMOUS NIGHT AGENT")
    print(f"{'='*70}\n")

    print(f"Configuration:")
    print(f"  Max goals: {max_goals}")
    print(f"  Max rounds per goal: {max_rounds}")
    print(f"  Auto-approve: {auto_approve}")
    print(f"  Dry-run: {dry_run}")
    print(f"  Repository: {repo_root}")
    print()

    if not dry_run:
        response = input("This will run autonomous operations. Continue? (y/N): ")
        if response.strip().lower() != 'y':
            print("Cancelled by user.")
            return

    # Initialize and run agent
    agent = NightAgent(
        repo_root=repo_root,
        config=config,
        dry_run=dry_run
    )

    print("\nStarting night agent...\n")

    summary = agent.run_autonomous(
        max_goals=max_goals,
        max_rounds_per_goal=max_rounds,
        auto_approve=auto_approve
    )

    # Generate report
    print("\nGenerating report...")

    report_gen = NightReportGenerator(repo_root=repo_root)
    report_path = report_gen.generate_report(summary)

    print(f"\n{'='*70}")
    print(f"Night agent completed!")
    print(f"Report: {report_path}")
    print(f"{'='*70}\n")

    # Print summary
    print("Summary:")
    print(f"  Goals completed: {len(summary.get('goals_completed', []))}")
    print(f"  Goals failed: {len(summary.get('goals_failed', []))}")
    print(f"  Duration: {summary.get('duration_seconds', 0):.0f}s")
    print()


def cmd_night_agent_report(
    last: bool = True,
    repo_root: Optional[Path] = None
):
    """
    View night agent report.

    Args:
        last: Show last report (True) or list all (False)
        repo_root: Repository root path
    """
    if repo_root is None:
        repo_root = Path.cwd()

    report_gen = NightReportGenerator(repo_root=repo_root)

    if last:
        # Print latest report
        report_gen.print_latest_report()
    else:
        # List all reports
        reports_dir = report_gen.output_dir
        reports = sorted(reports_dir.glob("night_report_*.md"), reverse=True)

        if not reports:
            print("No night reports found.")
            return

        print(f"\n{'='*60}")
        print(f"NIGHT AGENT REPORTS ({len(reports)} total)")
        print(f"{'='*60}\n")

        for i, report_path in enumerate(reports, 1):
            size_kb = report_path.stat().st_size / 1024
            print(f"{i}. {report_path.name} ({size_kb:.1f} KB)")

        print()


def cmd_night_agent_clear_backlog(repo_root: Optional[Path] = None):
    """
    Clear build document backlog (mark all as processed).

    Args:
        repo_root: Repository root path
    """
    if repo_root is None:
        repo_root = Path.cwd()

    print("\n⚠️  WARNING: This will mark all build docs as processed.")

    response = input("Continue? (y/N): ")
    if response.strip().lower() != 'y':
        print("Cancelled.")
        return

    agent = NightAgent(repo_root=repo_root)
    agent.clear_backlog()

    print("\n✓ Backlog cleared.")
