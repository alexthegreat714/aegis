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
from desktop.focus_guard import FocusGuard
from utils.config_loader import ConfigLoader

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


def cmd_desktop_focus_test(repo_root: Optional[Path] = None) -> int:
    """
    Test OCR focus verification for VS Code Claude input.

    Brings VS Code to foreground and runs OCR scan to verify
    Claude input is ready. Prints result with confidence and
    exits with appropriate exit code.

    Args:
        repo_root: Repository root path

    Returns:
        Exit code: 0 on success, 1 on failure
    """
    if repo_root is None:
        repo_root = Path.cwd()

    print(f"\n{'='*60}")
    print("OCR FOCUS VERIFICATION TEST")
    print(f"{'='*60}\n")

    # Load configuration
    config_loader = ConfigLoader(repo_root / "config" / "settings.yaml")
    settings = config_loader.load()

    # Initialize focus guard
    print("[1/2] Bringing VS Code to foreground...")
    focus_guard = FocusGuard(logger_instance=logger, settings=settings)

    try:
        # Bring VS Code to foreground
        focus_guard.require_vscode_foreground()
        print("  [OK] VS Code is in foreground\n")

        # Run OCR scan
        print("[2/2] Running OCR scan for Claude input...")
        meta = focus_guard.require_claude_input_ready()

        # Success!
        print(f"  [OK] Claude input confirmed via OCR")
        print(f"\n  Matched phrase: '{meta.get('matched_phrase', 'unknown')}'")
        print(f"  Confidence: {meta.get('confidence', 0.0):.2f}")
        print(f"  OCR text preview: {meta.get('ocr_text', '')[:100]}...")

        print(f"\n{'='*60}")
        print("[SUCCESS] Focus verification passed")
        print(f"{'='*60}\n")

        return 0

    except RuntimeError as e:
        # Focus verification failed
        print(f"  [FAIL] {e}\n")

        # Check for failure screenshot
        ocr_debug_dir = repo_root / ".aegis_debug" / "ocr"
        if ocr_debug_dir.exists():
            screenshots = sorted(ocr_debug_dir.glob("fail_*.png"))
            if screenshots:
                latest_screenshot = screenshots[-1]
                print(f"  Screenshot saved: {latest_screenshot}")

        print(f"\n{'='*60}")
        print("[FAILURE] Focus verification failed")
        print(f"{'='*60}\n")

        return 1
