"""
Tests for desktop automation layer.

Covers actions, policy, workspace guard, and executor.
Uses mocking - no real UI automation.
"""

import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from automation.actions import (
    ActionType, DesktopAction, LaunchAction, ClickButtonAction,
    WaitButtonAction, create_action
)
from automation.sandbox import AutomationPolicy
from automation.workspace_guard import WorkspaceGuard


class TestActions:
    """Test typed action objects."""

    def test_launch_action_creation(self):
        """Test creating launch action."""
        action = LaunchAction(exe="code", args=["/path/to/repo"], reuse=True)

        assert action.action == ActionType.LAUNCH
        assert action.params["exe"] == "code"
        assert action.params["args"] == ["/path/to/repo"]
        assert action.params["reuse"] is True

    def test_launch_action_validation(self):
        """Test launch action validation."""
        action = LaunchAction(exe="code")
        assert action.validate() is True

        # Missing exe should fail
        action.params["exe"] = None
        with pytest.raises(ValueError):
            action.validate()

    def test_click_button_action(self):
        """Test click button action."""
        action = ClickButtonAction(label="Apply Changes", timeout=10)

        assert action.action == ActionType.CLICK_BUTTON
        assert action.params["label"] == "Apply Changes"
        assert action.timeout == 10

    def test_wait_button_action(self):
        """Test wait button action."""
        action = WaitButtonAction(label="Authorize", timeout=30)

        assert action.action == ActionType.WAIT_BUTTON
        assert action.params["label"] == "Authorize"
        assert action.timeout == 30

    def test_action_to_dict(self):
        """Test action serialization."""
        action = ClickButtonAction(label="Test")
        action_dict = action.to_dict()

        assert action_dict["action"] == "desktop.click_button"
        assert action_dict["params"]["label"] == "Test"

    def test_action_from_dict(self):
        """Test action deserialization."""
        action_dict = {
            "action": "desktop.click_button",
            "params": {"label": "Test Button"},
            "timeout": 15
        }

        action = DesktopAction.from_dict(action_dict)

        assert action.action == ActionType.CLICK_BUTTON
        assert action.params["label"] == "Test Button"
        assert action.timeout == 15

    def test_create_action_factory(self):
        """Test action factory."""
        action = create_action("desktop.launch", exe="notepad")

        assert isinstance(action, LaunchAction)
        assert action.params["exe"] == "notepad"


class TestAutomationPolicy:
    """Test automation safety policy."""

    def test_policy_initialization(self):
        """Test policy initialization."""
        policy = AutomationPolicy(max_actions=10)

        assert policy.max_actions == 10
        assert policy.action_count == 0
        assert policy.allow_coordinate_clicks is False

    def test_policy_action_limit(self):
        """Test action limit enforcement."""
        policy = AutomationPolicy(max_actions=2)

        # First two actions should pass
        action = ClickButtonAction(label="Test")

        allowed, reason = policy.check_action(action)
        assert allowed is True

        allowed, reason = policy.check_action(action)
        assert allowed is True

        # Third should fail
        allowed, reason = policy.check_action(action)
        assert allowed is False
        assert "limit exceeded" in reason.lower()

    def test_policy_whitelist(self):
        """Test application whitelist."""
        policy = AutomationPolicy(allowed_apps={"code", "notepad"})

        # Allowed app
        action = LaunchAction(exe="code")
        allowed, reason = policy.check_action(action)
        assert allowed is True

        # Blocked app
        action = LaunchAction(exe="chrome")
        allowed, reason = policy.check_action(action)
        assert allowed is False
        assert "whitelist" in reason.lower()

    def test_policy_coordinate_clicks_blocked(self):
        """Test coordinate clicks are blocked by default."""
        policy = AutomationPolicy()

        # Action with coordinates should be blocked
        action = DesktopAction(
            ActionType.CLICK_BUTTON,
            params={"x": 100, "y": 200}  # Has coordinates
        )

        allowed, reason = policy.check_action(action)
        assert allowed is False
        assert "coordinate" in reason.lower()

    def test_policy_reset_cycle(self):
        """Test resetting counters for new cycle."""
        policy = AutomationPolicy(max_actions=2)

        action = ClickButtonAction(label="Test")
        policy.check_action(action)
        policy.check_action(action)

        # Should be at limit
        allowed, _ = policy.check_action(action)
        assert allowed is False

        # Reset and try again
        policy.reset_cycle()
        allowed, _ = policy.check_action(action)
        assert allowed is True

    def test_policy_validate_sequence(self):
        """Test validating action sequence."""
        policy = AutomationPolicy(max_actions=5)

        actions = [
            ClickButtonAction(label="Button 1"),
            ClickButtonAction(label="Button 2"),
            ClickButtonAction(label="Button 3"),
        ]

        valid, errors = policy.validate_action_sequence(actions)
        assert valid is True
        assert len(errors) == 0

    def test_policy_sequence_too_long(self):
        """Test sequence exceeding limit."""
        policy = AutomationPolicy(max_actions=2)

        actions = [
            ClickButtonAction(label="Button 1"),
            ClickButtonAction(label="Button 2"),
            ClickButtonAction(label="Button 3"),
        ]

        valid, errors = policy.validate_action_sequence(actions)
        assert valid is False
        assert len(errors) > 0


class TestWorkspaceGuard:
    """Test workspace validation."""

    def test_workspace_guard_initialization(self):
        """Test workspace guard initialization."""
        temp_repo = Path(tempfile.mkdtemp())

        try:
            guard = WorkspaceGuard(expected_repo=temp_repo)

            assert guard.expected_repo == temp_repo.resolve()

        finally:
            temp_repo.rmdir()

    def test_validate_repo_structure(self):
        """Test repository structure validation."""
        temp_repo = Path(tempfile.mkdtemp())

        try:
            guard = WorkspaceGuard(expected_repo=temp_repo)

            # Valid repo (exists and is directory)
            assert guard.validate_repo_structure() is True

            # Create .git directory
            (temp_repo / ".git").mkdir()
            assert guard.validate_repo_structure() is True

        finally:
            import shutil
            shutil.rmtree(temp_repo)

    def test_workspace_info(self):
        """Test getting workspace info."""
        temp_repo = Path(tempfile.mkdtemp())

        try:
            guard = WorkspaceGuard(expected_repo=temp_repo)
            info = guard.get_workspace_info()

            assert "expected_repo" in info
            assert "expected_exists" in info
            assert info["expected_exists"] is True

        finally:
            temp_repo.rmdir()


# Mark desktop tests to skip by default
pytestmark = pytest.mark.desktop


@pytest.mark.desktop
class TestDesktopIntegration:
    """Integration tests requiring real UI (skip by default)."""

    def test_skip_placeholder(self):
        """Placeholder for desktop integration tests."""
        # These tests would run actual UI automation
        # Only run with: pytest -m desktop
        assert True
