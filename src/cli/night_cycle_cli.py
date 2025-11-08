"""
Night Cycle CLI for Aegis.

Provides autonomous development cycle orchestration.
"""

from pathlib import Path

from core.night_cycle import night_cycle
from utils.config_loader import ConfigLoader


def main(args):
    """
    Main entry point for night cycle CLI.

    Args:
        args: Parsed command-line arguments
    """
    # Load configuration
    config = ConfigLoader(config_path='config/settings.yaml')
    settings = config._config

    # Run night cycle
    result = night_cycle(
        goal=args.goal,
        max_rounds=args.rounds,
        confirm_each=not args.auto,
        repo_root=Path.cwd(),
        settings=settings
    )

    # Display results
    print("\n" + "="*60)
    print("NIGHT CYCLE RESULTS")
    print("="*60)
    print(f"Goal: {result['goal']}")
    print(f"Total rounds: {len(result['rounds'])}/{result['max_rounds']}")
    print(f"Final status: {result['final_status']}")

    print("\nRound summaries:")
    for r in result['rounds']:
        status_icon = "[OK]" if r['approved'] else ("[~]" if r['tests_passed'] else "[X]")
        print(f"  {status_icon} Round {r['round']}: {r['rev_id']} - "
              f"Tests={'PASS' if r['tests_passed'] else 'FAIL'}, "
              f"Approved={r['approved']}")

    if result['final_status'] == 'approved':
        print("\n[SUCCESS] Night cycle completed with approved revision!")
        return 0
    elif result['final_status'] == 'pending_review':
        print("\n[PENDING] Tests passed but awaiting manual review")
        return 0
    else:
        print(f"\n[FAILED] Night cycle did not complete successfully")
        return 1
