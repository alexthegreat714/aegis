"""
Typed desktop action objects for Aegis automation.

Provides strongly-typed action definitions with validation
and serialization support.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from enum import Enum


class ActionType(Enum):
    """Supported desktop action types."""
    LAUNCH = "desktop.launch"
    FOCUS = "desktop.focus"
    ASSERT_WORKSPACE = "desktop.assert_workspace"
    CLICK_BUTTON = "desktop.click_button"
    WAIT_BUTTON = "desktop.wait_button"
    TYPE_TEXT = "desktop.type"
    HOTKEY = "desktop.hotkey"
    SCREENSHOT = "desktop.screenshot"
    ASSERT_WINDOW = "desktop.assert_window"


@dataclass
class DesktopAction:
    """
    Base class for desktop actions.

    All desktop actions must:
    - Be serializable to dict/YAML
    - Include timeout and retry parameters
    - Support dry-run mode
    - Log all executions
    """
    action: ActionType
    params: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 10  # seconds
    retry: int = 0
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "action": self.action.value,
            "params": self.params,
            "timeout": self.timeout,
            "retry": self.retry,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DesktopAction':
        """Create action from dictionary."""
        action_str = data.get("action", "")
        action_type = ActionType(action_str)

        return cls(
            action=action_type,
            params=data.get("params", {}),
            timeout=data.get("timeout", 10),
            retry=data.get("retry", 0),
            description=data.get("description")
        )

    def validate(self) -> bool:
        """
        Validate action parameters.

        Returns:
            True if valid, raises ValueError if invalid
        """
        # Subclasses should override for specific validation
        return True


@dataclass
class LaunchAction(DesktopAction):
    """Launch an application."""

    def __init__(
        self,
        exe: str,
        args: Optional[List[str]] = None,
        reuse: bool = True,
        **kwargs
    ):
        params = {
            "exe": exe,
            "args": args or [],
            "reuse": reuse
        }
        super().__init__(ActionType.LAUNCH, params=params, **kwargs)

    def validate(self) -> bool:
        if not self.params.get("exe"):
            raise ValueError("LaunchAction requires 'exe' parameter")
        return True


@dataclass
class FocusAction(DesktopAction):
    """Focus an application window."""

    def __init__(self, title_hint: str, **kwargs):
        params = {"title_hint": title_hint}
        super().__init__(ActionType.FOCUS, params=params, **kwargs)

    def validate(self) -> bool:
        if not self.params.get("title_hint"):
            raise ValueError("FocusAction requires 'title_hint' parameter")
        return True


@dataclass
class AssertWorkspaceAction(DesktopAction):
    """Assert VS Code workspace matches expected path."""

    def __init__(self, expected: str, **kwargs):
        params = {"expected": expected}
        super().__init__(ActionType.ASSERT_WORKSPACE, params=params, **kwargs)

    def validate(self) -> bool:
        if not self.params.get("expected"):
            raise ValueError("AssertWorkspaceAction requires 'expected' parameter")
        return True


@dataclass
class ClickButtonAction(DesktopAction):
    """Click a UI button by label."""

    def __init__(self, label: str, **kwargs):
        params = {"label": label}
        super().__init__(ActionType.CLICK_BUTTON, params=params, **kwargs)

    def validate(self) -> bool:
        if not self.params.get("label"):
            raise ValueError("ClickButtonAction requires 'label' parameter")
        return True


@dataclass
class WaitButtonAction(DesktopAction):
    """Wait for a UI button to appear."""

    def __init__(self, label: str, **kwargs):
        params = {"label": label}
        super().__init__(ActionType.WAIT_BUTTON, params=params, **kwargs)

    def validate(self) -> bool:
        if not self.params.get("label"):
            raise ValueError("WaitButtonAction requires 'label' parameter")
        return True


@dataclass
class TypeTextAction(DesktopAction):
    """Type text in focused field."""

    def __init__(self, text: str, interval: float = 0.01, **kwargs):
        params = {"text": text, "interval": interval}
        super().__init__(ActionType.TYPE_TEXT, params=params, **kwargs)

    def validate(self) -> bool:
        if "text" not in self.params:
            raise ValueError("TypeTextAction requires 'text' parameter")
        return True


@dataclass
class HotkeyAction(DesktopAction):
    """Send keyboard hotkey."""

    def __init__(self, keys: List[str], **kwargs):
        params = {"keys": keys}
        super().__init__(ActionType.HOTKEY, params=params, **kwargs)

    def validate(self) -> bool:
        if not self.params.get("keys"):
            raise ValueError("HotkeyAction requires 'keys' parameter")
        return True


@dataclass
class ScreenshotAction(DesktopAction):
    """Take a screenshot."""

    def __init__(self, path: str, region: Optional[Dict[str, int]] = None, **kwargs):
        params = {"path": path, "region": region}
        super().__init__(ActionType.SCREENSHOT, params=params, **kwargs)

    def validate(self) -> bool:
        if not self.params.get("path"):
            raise ValueError("ScreenshotAction requires 'path' parameter")
        return True


@dataclass
class AssertWindowAction(DesktopAction):
    """Assert a window exists."""

    def __init__(self, title_hint: str, **kwargs):
        params = {"title_hint": title_hint}
        super().__init__(ActionType.ASSERT_WINDOW, params=params, **kwargs)

    def validate(self) -> bool:
        if not self.params.get("title_hint"):
            raise ValueError("AssertWindowAction requires 'title_hint' parameter")
        return True


# Action factory
def create_action(action_type: str, **params) -> DesktopAction:
    """
    Create action from type string and parameters.

    Args:
        action_type: Action type string (e.g., "desktop.launch")
        **params: Action parameters

    Returns:
        Typed DesktopAction instance
    """
    action_map = {
        ActionType.LAUNCH: LaunchAction,
        ActionType.FOCUS: FocusAction,
        ActionType.ASSERT_WORKSPACE: AssertWorkspaceAction,
        ActionType.CLICK_BUTTON: ClickButtonAction,
        ActionType.WAIT_BUTTON: WaitButtonAction,
        ActionType.TYPE_TEXT: TypeTextAction,
        ActionType.HOTKEY: HotkeyAction,
        ActionType.SCREENSHOT: ScreenshotAction,
        ActionType.ASSERT_WINDOW: AssertWindowAction,
    }

    action_enum = ActionType(action_type)
    action_class = action_map.get(action_enum)

    if not action_class:
        raise ValueError(f"Unknown action type: {action_type}")

    return action_class(**params)
