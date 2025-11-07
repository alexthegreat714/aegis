"""
Enumeration of all allowed intent types.

Defines the vocabulary of actions Aegis can perform.
"""

from enum import Enum


class IntentCategory(str, Enum):
    """High-level categories of intents."""

    DESKTOP = "desktop"
    VSCODE = "vscode"
    FILESYSTEM = "filesystem"
    SYSTEM = "system"
    META = "meta"  # Control Aegis itself (pause, stop, etc.)


class IntentType(str, Enum):
    """
    Specific intent types.

    Each value corresponds to an action that can be policy-checked and executed.
    """

    # Desktop actions
    MOUSE_CLICK = "mouse_click"
    MOUSE_MOVE = "mouse_move"
    MOUSE_DRAG = "mouse_drag"
    KEYBOARD_TYPE = "keyboard_type"
    KEYBOARD_PRESS = "keyboard_press"
    SCREENSHOT = "screenshot"
    WINDOW_FOCUS = "window_focus"
    WINDOW_CLOSE = "window_close"
    WINDOW_MINIMIZE = "window_minimize"
    WINDOW_MAXIMIZE = "window_maximize"

    # VS Code actions
    VSCODE_OPEN_FILE = "open_file"
    VSCODE_CLOSE_TAB = "close_tab"
    VSCODE_SAVE_FILE = "save_file"
    VSCODE_OPEN_TERMINAL = "open_terminal"
    VSCODE_RUN_COMMAND = "run_command"
    VSCODE_SEARCH = "search"

    # Filesystem actions
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    FILE_COPY = "file_copy"
    FILE_MOVE = "file_move"
    DIRECTORY_CREATE = "directory_create"
    DIRECTORY_DELETE = "directory_delete"
    DIRECTORY_LIST = "directory_list"

    # System actions
    PROCESS_LIST = "process_list"
    PROCESS_KILL = "process_kill"
    SERVICE_START = "service_start"
    SERVICE_STOP = "service_stop"
    REGISTRY_READ = "registry_read"
    REGISTRY_WRITE = "registry_write"

    # Meta actions (control Aegis itself)
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    RELOAD_POLICY = "reload_policy"

    @classmethod
    def get_category(cls, intent_type: "IntentType") -> IntentCategory:
        """
        Get the category for a given intent type.

        Args:
            intent_type: The intent type

        Returns:
            IntentCategory
        """
        # Desktop actions
        if intent_type.value in [
            "mouse_click", "mouse_move", "mouse_drag",
            "keyboard_type", "keyboard_press", "screenshot",
            "window_focus", "window_close", "window_minimize", "window_maximize"
        ]:
            return IntentCategory.DESKTOP

        # VS Code actions
        elif intent_type.value.startswith("open_") or intent_type.value.startswith("close_") \
                or intent_type.value.startswith("save_") or "command" in intent_type.value \
                or intent_type.value == "search":
            return IntentCategory.VSCODE

        # Filesystem actions
        elif intent_type.value.startswith("file_") or intent_type.value.startswith("directory_"):
            return IntentCategory.FILESYSTEM

        # System actions
        elif intent_type.value.startswith("process_") or intent_type.value.startswith("service_") \
                or intent_type.value.startswith("registry_"):
            return IntentCategory.SYSTEM

        # Meta actions
        elif intent_type.value in ["pause", "resume", "stop", "reload_policy"]:
            return IntentCategory.META

        else:
            return IntentCategory.DESKTOP  # Default
