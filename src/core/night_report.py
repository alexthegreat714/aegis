"""
Night cycle report generation.

Creates structured markdown reports summarizing autonomous night agent runs.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class NightReportGenerator:
    """
    Generates structured markdown reports for night agent runs.

    Reports include goals, revisions, test results, screenshots, and errors.
    """

    def __init__(self, repo_root: Path, output_dir: Optional[Path] = None):
        """
        Initialize report generator.

        Args:
            repo_root: Repository root path
            output_dir: Output directory for reports (defaults to reports/)
        """
        self.repo_root = Path(repo_root)

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.repo_root / "reports"

        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"NightReportGenerator initialized")
        logger.info(f"  Output directory: {self.output_dir}")

    def generate_report(
        self,
        summary: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> Path:
        """
        Generate night report from summary data.

        Args:
            summary: Summary dictionary from night agent
            timestamp: Report timestamp (defaults to now)

        Returns:
            Path to generated report file
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Generate filename
        date_str = timestamp.strftime("%Y-%m-%d")
        time_str = timestamp.strftime("%H%M%S")
        filename = f"night_report_{date_str}_{time_str}.md"
        output_path = self.output_dir / filename

        logger.info(f"Generating night report: {output_path}")

        # Build report content
        content = self._build_report_content(summary, timestamp)

        # Write report
        output_path.write_text(content, encoding='utf-8')

        logger.info(f"Night report generated: {output_path}")
        return output_path

    def _build_report_content(
        self,
        summary: Dict[str, Any],
        timestamp: datetime
    ) -> str:
        """
        Build report markdown content.

        Args:
            summary: Summary dictionary
            timestamp: Report timestamp

        Returns:
            Formatted markdown content
        """
        parts = []

        # Header
        parts.append(self._build_header(summary, timestamp))
        parts.append("")

        # Summary section
        parts.append(self._build_summary_section(summary))
        parts.append("")

        # Goals section
        parts.append(self._build_goals_section(summary))
        parts.append("")

        # Revisions section
        parts.append(self._build_revisions_section(summary))
        parts.append("")

        # Test results section
        parts.append(self._build_test_section(summary))
        parts.append("")

        # Screenshots section (if available)
        if summary.get("screenshots"):
            parts.append(self._build_screenshots_section(summary))
            parts.append("")

        # Errors section (if any)
        if summary.get("goals_failed"):
            parts.append(self._build_errors_section(summary))
            parts.append("")

        # Footer
        parts.append(self._build_footer(summary))

        return '\n'.join(parts)

    def _build_header(self, summary: Dict[str, Any], timestamp: datetime) -> str:
        """Build report header."""
        date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

        overall_status = self._determine_overall_status(summary)
        status_emoji = {
            "success": "✅",
            "partial": "⚠️",
            "failed": "❌",
            "no_goals": "ℹ️"
        }.get(overall_status, "❓")

        return f"""# Night Agent Report
**Generated:** {date_str}
**Status:** {status_emoji} {overall_status.upper()}"""

    def _build_summary_section(self, summary: Dict[str, Any]) -> str:
        """Build summary section."""
        goals_completed = len(summary.get("goals_completed", []))
        goals_failed = len(summary.get("goals_failed", []))
        goals_total = summary.get("goals_attempted", goals_completed + goals_failed)

        duration_sec = summary.get("duration_seconds", 0)
        duration_min = duration_sec / 60.0

        start_time = summary.get("start_time", "Unknown")
        end_time = summary.get("end_time", "Unknown")

        return f"""## Summary

| Metric | Value |
|--------|-------|
| Goals Attempted | {goals_total} |
| Goals Completed | {goals_completed} |
| Goals Failed | {goals_failed} |
| Success Rate | {self._calc_success_rate(goals_completed, goals_total)}% |
| Duration | {duration_min:.1f} minutes ({duration_sec:.0f}s) |
| Start Time | {start_time} |
| End Time | {end_time} |"""

    def _build_goals_section(self, summary: Dict[str, Any]) -> str:
        """Build goals section."""
        parts = ["## Goals"]

        # Completed goals
        completed = summary.get("goals_completed", [])
        if completed:
            parts.append("\n### ✅ Completed")
            for i, goal_info in enumerate(completed, 1):
                goal_name = goal_info.get("goal", "Unknown")
                rev_id = goal_info.get("revision", "N/A")
                rounds = goal_info.get("rounds", 0)
                parts.append(f"{i}. **{goal_name}** (revision: `{rev_id}`, rounds: {rounds})")

        # Failed goals
        failed = summary.get("goals_failed", [])
        if failed:
            parts.append("\n### ❌ Failed")
            for i, goal_info in enumerate(failed, 1):
                goal_name = goal_info.get("goal", "Unknown")
                reason = goal_info.get("reason", "Unknown error")
                rounds = goal_info.get("rounds", 0)
                parts.append(f"{i}. **{goal_name}** (rounds: {rounds})")
                parts.append(f"   - Reason: {reason}")

        if not completed and not failed:
            parts.append("\n*No goals were attempted.*")

        return '\n'.join(parts)

    def _build_revisions_section(self, summary: Dict[str, Any]) -> str:
        """Build revisions section."""
        parts = ["## Revisions"]

        completed = summary.get("goals_completed", [])
        revisions = [g.get("revision") for g in completed if g.get("revision")]

        if revisions:
            parts.append(f"\nTotal revisions created: {len(revisions)}")
            parts.append("\n### Approved Revisions")
            for rev_id in revisions:
                parts.append(f"- `{rev_id}`")
        else:
            parts.append("\n*No revisions were approved.*")

        return '\n'.join(parts)

    def _build_test_section(self, summary: Dict[str, Any]) -> str:
        """Build test results section."""
        parts = ["## Test Results"]

        # Extract test info from completed goals
        completed = summary.get("goals_completed", [])

        if completed:
            parts.append("\nAll completed goals passed their test suites (STRICT approval).")
            parts.append(f"\nRevisions with passing tests: {len(completed)}")
        else:
            parts.append("\n*No tests passed during this night cycle.*")

        return '\n'.join(parts)

    def _build_screenshots_section(self, summary: Dict[str, Any]) -> str:
        """Build screenshots section."""
        parts = ["## Screenshots"]

        screenshots = summary.get("screenshots", [])

        if screenshots:
            parts.append(f"\nTotal screenshots captured: {len(screenshots)}")
            parts.append("\n### Screenshot List")
            for screenshot in screenshots:
                parts.append(f"- `{screenshot}`")
        else:
            parts.append("\n*No screenshots were captured.*")

        return '\n'.join(parts)

    def _build_errors_section(self, summary: Dict[str, Any]) -> str:
        """Build errors section."""
        parts = ["## Errors & Troubleshooting"]

        failed = summary.get("goals_failed", [])

        if failed:
            for i, goal_info in enumerate(failed, 1):
                goal_name = goal_info.get("goal", "Unknown")
                reason = goal_info.get("reason", "Unknown error")

                parts.append(f"\n### Error {i}: {goal_name}")
                parts.append(f"**Reason:** {reason}")
                parts.append(f"**Rounds attempted:** {goal_info.get('rounds', 0)}")

                # Add suggestions based on error type
                if "test" in reason.lower():
                    parts.append("\n**Suggestion:** Review test failures and fix code issues.")
                elif "limit" in reason.lower():
                    parts.append("\n**Suggestion:** Session limit reached - will resume after reset time.")
                else:
                    parts.append("\n**Suggestion:** Review logs for detailed error information.")

        return '\n'.join(parts)

    def _build_footer(self, summary: Dict[str, Any]) -> str:
        """Build report footer."""
        overall_status = self._determine_overall_status(summary)

        status_messages = {
            "success": "All goals completed successfully! 🎉",
            "partial": "Some goals completed. Review failures for next iteration.",
            "failed": "No goals completed. Review errors and retry.",
            "no_goals": "No goals were available to process."
        }

        message = status_messages.get(overall_status, "Status unknown.")

        return f"""---

## Overall Night Status

**{overall_status.upper()}**

{message}

*Report generated by Aegis Night Agent*"""

    def _determine_overall_status(self, summary: Dict[str, Any]) -> str:
        """
        Determine overall status from summary.

        Returns:
            Status string: success, partial, failed, or no_goals
        """
        completed = len(summary.get("goals_completed", []))
        failed = len(summary.get("goals_failed", []))
        total = summary.get("goals_attempted", completed + failed)

        if total == 0:
            return "no_goals"
        elif completed == total:
            return "success"
        elif completed > 0:
            return "partial"
        else:
            return "failed"

    def _calc_success_rate(self, completed: int, total: int) -> float:
        """Calculate success rate percentage."""
        if total == 0:
            return 0.0
        return round((completed / total) * 100, 1)

    def get_latest_report(self) -> Optional[Path]:
        """
        Get path to most recent night report.

        Returns:
            Path to latest report or None if no reports exist
        """
        reports = sorted(self.output_dir.glob("night_report_*.md"), reverse=True)

        if reports:
            return reports[0]
        else:
            return None

    def print_latest_report(self):
        """Print latest report to console."""
        latest = self.get_latest_report()

        if not latest:
            logger.warning("No night reports found")
            print("No night reports available.")
            return

        print(f"\n{'='*70}")
        print(f"LATEST NIGHT REPORT: {latest.name}")
        print(f"{'='*70}\n")

        content = latest.read_text(encoding='utf-8')
        print(content)


def generate_night_report(
    summary: Dict[str, Any],
    repo_root: Optional[Path] = None,
    output_dir: Optional[Path] = None
) -> Path:
    """
    Generate night report (convenience function).

    Args:
        summary: Summary dictionary from night agent
        repo_root: Repository root path
        output_dir: Output directory

    Returns:
        Path to generated report
    """
    if repo_root is None:
        repo_root = Path.cwd()

    generator = NightReportGenerator(repo_root=repo_root, output_dir=output_dir)
    return generator.generate_report(summary)
