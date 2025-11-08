"""
Desktop automation CLI commands.
"""

import logging
from pathlib import Path
from typing import Optional

from automation.desktop_executor import DesktopExecutor
from automation.actions import (
    FocusAction,
    AssertWorkspaceAction,
    ClickButtonAction,
    WaitButtonAction,
    ScreenshotAction
)

logger = logging.getLogger(__name__)


def cmd_desktop_test(repo_root: Optional[Path] = None, dry_run: bool = True):
    """
    Run desktop automation tests (dry-run mode).

    Args:
        repo_root: Repository root path
        dry_run: Run in dry-run mode (default: True for safety)
    """
    if repo_root is None:
        repo_root = Path.cwd()

    print(f"\n{'='*60}")
    print("DESKTOP AUTOMATION TEST")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY-RUN MODE] No actual UI actions will be performed\n")
    else:
        print("[LIVE MODE] Real UI actions will be executed\n")

    # Initialize desktop executor
    executor = DesktopExecutor(
        repo_root=repo_root,
        dry_run=dry_run
    )

    print("[1/5] Testing window focus...")
    focus_action = FocusAction(title_hint="Visual Studio Code")
    result = executor.execute(focus_action)
    print(f"  Result: {'SUCCESS' if result['success'] else 'FAILED'}")

    print("\n[2/5] Testing workspace assertion...")
    assert_action = AssertWorkspaceAction(expected=str(repo_root))
    result = executor.execute(assert_action)
    print(f"  Result: {'SUCCESS' if result['success'] else 'FAILED'}")

    print("\n[3/5] Testing screenshot capture...")
    screenshot_path = executor.screenshot_dir / "test_screenshot.png"
    screenshot_action = ScreenshotAction(path=str(screenshot_path))
    result = executor.execute(screenshot_action)
    print(f"  Result: {'SUCCESS' if result['success'] else 'FAILED'}")
    if result['success'] and not dry_run:
        print(f"  Saved to: {screenshot_path}")

    print("\n[4/5] Testing button wait...")
    wait_action = WaitButtonAction(label="Apply Changes", timeout=5)
    result = executor.execute(wait_action)
    print(f"  Result: {'SUCCESS' if result['success'] else 'FAILED'}")

    print("\n[5/5] Testing button click (dry-run only)...")
    # Always dry-run button clicks in test mode
    original_dry_run = executor.dry_run
    executor.dry_run = True
    click_action = ClickButtonAction(label="Apply Changes")
    result = executor.execute(click_action)
    executor.dry_run = original_dry_run
    print(f"  Result: {'SUCCESS' if result['success'] else 'FAILED'}")

    print(f"\n{'='*60}")
    print(f"Test completed - Action count: {executor.action_count}")
    print(f"{'='*60}\n")


def cmd_desktop_screenshot(
    label: str = "manual",
    repo_root: Optional[Path] = None
):
    """
    Capture a desktop screenshot.

    Args:
        label: Screenshot label
        repo_root: Repository root path
    """
    if repo_root is None:
        repo_root = Path.cwd()

    executor = DesktopExecutor(repo_root=repo_root, dry_run=False)

    screenshot_path = executor.screenshot_dir / f"{label}_screenshot.png"

    print(f"Capturing screenshot: {screenshot_path}")

    screenshot_action = ScreenshotAction(path=str(screenshot_path))
    result = executor.execute(screenshot_action)

    if result["success"]:
        print(f"✓ Screenshot saved: {screenshot_path}")
    else:
        print(f"✗ Screenshot failed: {result.get('error')}")
