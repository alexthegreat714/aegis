"""
Tests for Phase D+N: Desktop automation and Night Agent.

Consolidates tests for new Phase D+N modules.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from automation.workspace_guard import WorkspaceGuard
from core.night_report import NightReportGenerator


# Workspace Guard Tests

@pytest.fixture
def workspace_guard(tmp_path):
    """Create workspace guard for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    return WorkspaceGuard(expected_repo=repo_dir)


def test_workspace_guard_get_current_branch(workspace_guard):
    """Test getting current git branch."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout="master\n",
            returncode=0
        )

        branch = workspace_guard.get_current_branch()
        assert branch == "master"


def test_workspace_guard_is_clean_tree_clean(workspace_guard):
    """Test checking if working tree is clean."""
    with patch('subprocess.run') as mock_run:
        # Empty output means clean
        mock_run.return_value = Mock(
            stdout="",
            returncode=0
        )

        assert workspace_guard.is_clean_tree() is True


def test_workspace_guard_is_clean_tree_dirty(workspace_guard):
    """Test checking if working tree has changes."""
    with patch('subprocess.run') as mock_run:
        # Non-empty output means dirty
        mock_run.return_value = Mock(
            stdout=" M file.py\n",
            returncode=0
        )

        assert workspace_guard.is_clean_tree() is False


def test_workspace_guard_ensure_branch_already_correct(workspace_guard):
    """Test ensure_branch when already on correct branch."""
    with patch.object(workspace_guard, 'get_current_branch', return_value='master'):
        result = workspace_guard.ensure_branch('master')
        assert result is True


def test_workspace_guard_ensure_branch_switch(workspace_guard):
    """Test ensure_branch switches branches."""
    with patch.object(workspace_guard, 'get_current_branch', return_value='feature'):
        with patch('subprocess.run') as mock_run:
            # First call: branch exists check (returncode 0 = exists)
            # Second call: checkout
            mock_run.side_effect = [
                Mock(returncode=0),  # branch exists
                Mock(returncode=0)   # checkout success
            ]

            result = workspace_guard.ensure_branch('master')
            assert result is True


def test_workspace_guard_ensure_clean_tree_stash(workspace_guard):
    """Test ensure_clean_tree stashes changes."""
    with patch.object(workspace_guard, 'is_clean_tree', side_effect=[False, True]):
        with patch('subprocess.run') as mock_run:
            result = workspace_guard.ensure_clean_tree(stash=True)
            assert result is True
            # Should have called git stash
            assert any('stash' in str(call) for call in mock_run.call_args_list)


# Night Report Tests

@pytest.fixture
def report_gen(tmp_path):
    """Create report generator for testing."""
    return NightReportGenerator(repo_root=tmp_path)


@pytest.fixture
def sample_summary():
    """Sample summary data for testing."""
    return {
        "status": "completed",
        "start_time": "2025-01-01T00:00:00+00:00",
        "end_time": "2025-01-01T01:00:00+00:00",
        "duration_seconds": 3600,
        "goals_attempted": 3,
        "goals_completed": [
            {"goal": "Feature A", "revision": "rev_001", "rounds": 2},
            {"goal": "Feature B", "revision": "rev_002", "rounds": 1}
        ],
        "goals_failed": [
            {"goal": "Feature C", "reason": "Tests failed", "rounds": 3}
        ]
    }


def test_night_report_generate(report_gen, sample_summary):
    """Test report generation."""
    report_path = report_gen.generate_report(sample_summary)

    assert report_path.exists()
    assert report_path.suffix == ".md"

    content = report_path.read_text(encoding='utf-8')
    assert "# Night Agent Report" in content
    assert "Feature A" in content
    assert "Feature B" in content
    assert "Feature C" in content


def test_night_report_summary_section(report_gen, sample_summary):
    """Test summary section generation."""
    content = report_gen._build_summary_section(sample_summary)

    assert "Goals Attempted" in content
    assert "Goals Completed" in content
    assert "66.7%" in content  # 2/3 success rate


def test_night_report_goals_section(report_gen, sample_summary):
    """Test goals section generation."""
    content = report_gen._build_goals_section(sample_summary)

    assert "Feature A" in content
    assert "Feature B" in content
    assert "Feature C" in content
    assert "rev_001" in content
    assert "Tests failed" in content


def test_night_report_determine_overall_status_success(report_gen):
    """Test overall status determination - all success."""
    summary = {
        "goals_attempted": 2,
        "goals_completed": [{"goal": "A"}, {"goal": "B"}],
        "goals_failed": []
    }

    status = report_gen._determine_overall_status(summary)
    assert status == "success"


def test_night_report_determine_overall_status_partial(report_gen):
    """Test overall status determination - partial success."""
    summary = {
        "goals_attempted": 3,
        "goals_completed": [{"goal": "A"}],
        "goals_failed": [{"goal": "B"}, {"goal": "C"}]
    }

    status = report_gen._determine_overall_status(summary)
    assert status == "partial"


def test_night_report_determine_overall_status_failed(report_gen):
    """Test overall status determination - all failed."""
    summary = {
        "goals_attempted": 2,
        "goals_completed": [],
        "goals_failed": [{"goal": "A"}, {"goal": "B"}]
    }

    status = report_gen._determine_overall_status(summary)
    assert status == "failed"


def test_night_report_get_latest_report(report_gen, sample_summary):
    """Test getting latest report."""
    # Generate multiple reports
    report1 = report_gen.generate_report(sample_summary)
    report2 = report_gen.generate_report(sample_summary)

    latest = report_gen.get_latest_report()
    assert latest == report2  # Most recent


def test_night_report_calc_success_rate(report_gen):
    """Test success rate calculation."""
    assert report_gen._calc_success_rate(2, 3) == 66.7
    assert report_gen._calc_success_rate(3, 3) == 100.0
    assert report_gen._calc_success_rate(0, 3) == 0.0
    assert report_gen._calc_success_rate(0, 0) == 0.0


# Integration Tests

@pytest.mark.desktop
def test_night_agent_initialization(tmp_path):
    """Test night agent initializes correctly."""
    from agents.night_agent import NightAgent

    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    agent = NightAgent(repo_root=repo_dir, dry_run=True)

    assert agent.repo_root == repo_dir
    assert agent.dry_run is True
    assert agent.desktop is not None
    assert len(agent.goals_completed) == 0


@pytest.mark.desktop
def test_night_agent_load_build_docs(tmp_path):
    """Test loading build docs."""
    from agents.night_agent import NightAgent

    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Create docs directory
    docs_dir = repo_dir / "docs" / "builds"
    docs_dir.mkdir(parents=True)

    # Create test build docs
    (docs_dir / "feature_a.md").write_text("Implement feature A")
    (docs_dir / "feature_b.md").write_text("Implement feature B")

    agent = NightAgent(repo_root=repo_dir, dry_run=True)
    goals = agent.load_build_docs()

    assert len(goals) == 2
    assert goals[0]["name"] == "feature_a"
    assert goals[1]["name"] == "feature_b"


@pytest.mark.desktop
def test_night_agent_build_prompt(tmp_path):
    """Test prompt building."""
    from agents.night_agent import NightAgent

    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    agent = NightAgent(repo_root=repo_dir, dry_run=True)

    goal = {"name": "test_goal", "content": "Test content"}
    prompt = agent._build_prompt(goal, round_num=1, failures=[])

    assert "Round 1" in prompt
    assert "test_goal" in prompt
    assert "Test content" in prompt


@pytest.mark.desktop
def test_night_agent_build_prompt_with_failures(tmp_path):
    """Test prompt building with previous failures."""
    from agents.night_agent import NightAgent

    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    agent = NightAgent(repo_root=repo_dir, dry_run=True)

    goal = {"name": "test_goal", "content": "Test content"}
    failures = ["Tests failed", "Syntax error"]
    prompt = agent._build_prompt(goal, round_num=2, failures=failures)

    assert "Round 2" in prompt
    assert "Previous Round Failures" in prompt
    assert "Tests failed" in prompt
    assert "Syntax error" in prompt


def test_night_cycle_initialization_with_desktop(tmp_path):
    """Test night cycle with desktop automation enabled."""
    from core.night_cycle import NightCycle

    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    cycle = NightCycle(repo_root=repo_dir, use_desktop=True, dry_run=True)

    assert cycle.use_desktop is True
    assert cycle.desktop is not None
    assert cycle.workspace_guard is not None


def test_night_cycle_initialization_without_desktop(tmp_path):
    """Test night cycle without desktop automation."""
    from core.night_cycle import NightCycle

    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    cycle = NightCycle(repo_root=repo_dir, use_desktop=False)

    assert cycle.use_desktop is False
    assert cycle.desktop is None
    assert cycle.workspace_guard is None
