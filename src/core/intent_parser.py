"""
Intent parser for Aegis agent.

Converts LLM output (JSON or natural language) into structured Intent objects.
"""

from typing import Dict, Any, List, Optional, Union
import json
import re
from datetime import datetime

from intents.intent_schema import Intent
from intents.intent_types import IntentType
from aegis_logging.logger import AegisLogger


class IntentParseError(Exception):
    """Raised when intent parsing fails."""
    pass


class IntentParser:
    """
    Parses LLM output into structured Intent objects.

    Supports both JSON format and natural language parsing.

    Example JSON format:
    {
        "intent": "open_app",
        "target": "notepad",
        "args": {}
    }

    Example natural language:
    "open notepad and type hello world"
    """

    def __init__(self, logger: AegisLogger):
        """
        Initialize intent parser.

        Args:
            logger: Logging system
        """
        self.logger = logger
        self._init_patterns()

    def _init_patterns(self) -> None:
        """Initialize regex patterns for natural language parsing."""
        self.patterns = {
            "open_app": [
                re.compile(r"open\s+(\w+)", re.IGNORECASE),
                re.compile(r"launch\s+(\w+)", re.IGNORECASE),
                re.compile(r"start\s+(\w+)", re.IGNORECASE),
            ],
            "type_text": [
                re.compile(r"type\s+['\"](.+?)['\"]", re.IGNORECASE),
                re.compile(r"enter\s+['\"](.+?)['\"]", re.IGNORECASE),
                re.compile(r"write\s+['\"](.+?)['\"]", re.IGNORECASE),
            ],
            "click_on": [
                re.compile(r"click\s+(?:on\s+)?(.+?)(?:\s+button)?$", re.IGNORECASE),
                re.compile(r"press\s+(?:the\s+)?(.+?)(?:\s+button)?$", re.IGNORECASE),
            ],
        }

    def parse(self, llm_output: Union[str, Dict[str, Any]]) -> Intent:
        """
        Parse LLM output into Intent object.

        Args:
            llm_output: Raw LLM output (string or dict)

        Returns:
            Parsed Intent object

        Raises:
            IntentParseError: If parsing fails
        """
        try:
            # If dict, assume it's already structured
            if isinstance(llm_output, dict):
                return self._parse_json(llm_output)

            # If string, try JSON first, then natural language
            if isinstance(llm_output, str):
                # Try to parse as JSON
                try:
                    data = json.loads(llm_output)
                    return self._parse_json(data)
                except json.JSONDecodeError:
                    # Fall back to natural language parsing
                    return self._parse_natural_language(llm_output)

            raise IntentParseError(f"Unsupported LLM output type: {type(llm_output)}")

        except IntentParseError:
            raise
        except Exception as e:
            self.logger.log_event(
                event_type="intent_parse_error",
                data={"error": str(e), "output": str(llm_output)[:200]},
                status="error"
            )
            raise IntentParseError(f"Failed to parse intent: {e}")

    def _parse_json(self, data: Dict[str, Any]) -> Intent:
        """
        Parse JSON-formatted intent.

        Expected formats:

        Format 1 - Simple:
        {
            "intent": "open_app",
            "target": "notepad",
            "args": {}
        }

        Format 2 - Full intent object:
        {
            "action_type": "mouse_click",
            "parameters": {"x": 100, "y": 200},
            "rationale": "Click on button"
        }

        Args:
            data: JSON dictionary

        Returns:
            Intent object

        Raises:
            IntentParseError: If JSON is malformed
        """
        # Format 2: Full intent object
        if "action_type" in data:
            try:
                action_type = IntentType(data["action_type"])
                return Intent(
                    action_type=action_type,
                    parameters=data.get("parameters", {}),
                    rationale=data.get("rationale"),
                    confidence=data.get("confidence", 1.0)
                )
            except ValueError as e:
                raise IntentParseError(f"Invalid action_type: {data['action_type']}")

        # Format 1: Simple intent mapping
        if "intent" not in data:
            raise IntentParseError("Missing 'intent' or 'action_type' field in JSON")

        intent_name = data["intent"]
        target = data.get("target", "")
        args = data.get("args", {})

        # Map simple intent names to IntentType
        intent_mapping = {
            "open_app": self._create_open_app_intent,
            "type_text": self._create_type_text_intent,
            "click_on": self._create_click_on_intent,
            "screenshot": self._create_screenshot_intent,
            "close_window": self._create_close_window_intent,
        }

        creator = intent_mapping.get(intent_name)
        if not creator:
            raise IntentParseError(f"Unknown intent type: {intent_name}")

        return creator(target, args)

    def _parse_natural_language(self, text: str) -> Intent:
        """
        Parse natural language into Intent object.

        Examples:
        - "open notepad" -> Intent(VSCODE_OPEN_FILE, ...)
        - "type hello world" -> Intent(KEYBOARD_TYPE, ...)
        - "click on submit button" -> Intent(MOUSE_CLICK, ...)

        Args:
            text: Natural language text

        Returns:
            Intent object

        Raises:
            IntentParseError: If text cannot be parsed
        """
        text = text.strip()

        # Try each pattern set
        for intent_name, patterns in self.patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    target = match.group(1) if match.groups() else ""

                    # Create intent based on type
                    if intent_name == "open_app":
                        return self._create_open_app_intent(target, {})
                    elif intent_name == "type_text":
                        return self._create_type_text_intent(target, {})
                    elif intent_name == "click_on":
                        return self._create_click_on_intent(target, {})

        # If no pattern matches, log and raise error
        self.logger.log_event(
            event_type="natural_language_parse_failed",
            data={"text": text},
            status="warning"
        )
        raise IntentParseError(f"Could not parse natural language: {text}")

    def _create_open_app_intent(self, target: str, args: Dict[str, Any]) -> Intent:
        """
        Create intent to open an application.

        Args:
            target: Application name (e.g., "notepad", "vscode")
            args: Additional arguments

        Returns:
            Intent object
        """
        # Map common app names to executables
        app_mapping = {
            "notepad": "notepad.exe",
            "vscode": "code",
            "code": "code",
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "terminal": "cmd.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
        }

        executable = app_mapping.get(target.lower(), target)

        return Intent(
            action_type=IntentType.VSCODE_RUN_COMMAND,  # Using run_command as generic execution
            parameters={
                "command": executable,
                "app_name": target,
                **args
            },
            rationale=f"Open application: {target}"
        )

    def _create_type_text_intent(self, target: str, args: Dict[str, Any]) -> Intent:
        """
        Create intent to type text.

        Args:
            target: Text to type
            args: Additional arguments (e.g., delay, special keys)

        Returns:
            Intent object
        """
        return Intent(
            action_type=IntentType.KEYBOARD_TYPE,
            parameters={
                "text": target,
                "delay_ms": args.get("delay_ms", 50),
                **args
            },
            rationale=f"Type text: {target[:50]}..."
        )

    def _create_click_on_intent(self, target: str, args: Dict[str, Any]) -> Intent:
        """
        Create intent to click on element.

        Args:
            target: Element description or coordinates
            args: Additional arguments (x, y, button type)

        Returns:
            Intent object
        """
        # Check if target is coordinates (e.g., "100,200")
        coord_match = re.match(r"(\d+)\s*,\s*(\d+)", target)
        if coord_match:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            return Intent(
                action_type=IntentType.MOUSE_CLICK,
                parameters={
                    "x": x,
                    "y": y,
                    "button": args.get("button", "left"),
                    **args
                },
                rationale=f"Click at ({x}, {y})"
            )

        # Otherwise, click on named element (requires vision/OCR in future)
        return Intent(
            action_type=IntentType.MOUSE_CLICK,
            parameters={
                "target_element": target,
                "button": args.get("button", "left"),
                "requires_screenshot": True,  # Need to find element first
                **args
            },
            rationale=f"Click on: {target}"
        )

    def _create_screenshot_intent(self, target: str, args: Dict[str, Any]) -> Intent:
        """
        Create intent to take screenshot.

        Args:
            target: Output path or empty for default
            args: Additional arguments

        Returns:
            Intent object
        """
        return Intent(
            action_type=IntentType.SCREENSHOT,
            parameters={
                "output_path": target or "screenshot.png",
                **args
            },
            rationale="Capture screenshot"
        )

    def _create_close_window_intent(self, target: str, args: Dict[str, Any]) -> Intent:
        """
        Create intent to close window.

        Args:
            target: Window title or empty for active window
            args: Additional arguments

        Returns:
            Intent object
        """
        return Intent(
            action_type=IntentType.WINDOW_CLOSE,
            parameters={
                "title": target or None,  # None means active window
                **args
            },
            rationale=f"Close window: {target or 'active window'}"
        )

    def parse_batch(self, llm_outputs: List[Union[str, Dict[str, Any]]]) -> List[Intent]:
        """
        Parse multiple LLM outputs into Intent objects.

        Args:
            llm_outputs: List of LLM outputs

        Returns:
            List of Intent objects (skips failed parses)
        """
        intents = []
        for idx, output in enumerate(llm_outputs):
            try:
                intent = self.parse(output)
                intents.append(intent)
            except IntentParseError as e:
                self.logger.log_event(
                    event_type="batch_parse_error",
                    data={"index": idx, "error": str(e)},
                    status="warning"
                )
                # Skip failed parses, continue with rest
                continue

        return intents

    def validate_intent(self, intent: Intent) -> bool:
        """
        Validate that an Intent object is well-formed.

        Args:
            intent: Intent to validate

        Returns:
            True if valid

        Raises:
            IntentParseError: If validation fails
        """
        # Check that action_type is valid
        if not isinstance(intent.action_type, IntentType):
            raise IntentParseError(f"Invalid action_type: {intent.action_type}")

        # Check that parameters is a dict
        if not isinstance(intent.parameters, dict):
            raise IntentParseError("Parameters must be a dictionary")

        # Check confidence is in valid range
        if not (0.0 <= intent.confidence <= 1.0):
            raise IntentParseError(f"Confidence must be 0-1, got {intent.confidence}")

        return True
