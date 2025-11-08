"""
Tests for intent parser.
"""

import unittest
import tempfile
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.intent_parser import IntentParser, IntentParseError
from intents.intent_schema import Intent
from intents.intent_types import IntentType
from aegis_logging.logger import AegisLogger


class TestIntentParser(unittest.TestCase):
    """Test intent parser functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir()
        (self.data_dir / "logs").mkdir(exist_ok=True)

        # Test settings
        self.settings = {
            "logging": {"jsonl_enabled": True, "sqlite_enabled": True}
        }

        # Initialize logger
        self.logger = AegisLogger(
            log_dir=str(self.data_dir / "logs"),
            db_path=str(self.data_dir / "test.db"),
            settings=self.settings
        )

        # Initialize parser
        self.parser = IntentParser(self.logger)

    def test_parse_json_simple_open_app(self):
        """Test parsing simple JSON open_app intent."""
        json_input = {
            "intent": "open_app",
            "target": "notepad",
            "args": {}
        }

        intent = self.parser.parse(json_input)

        self.assertIsInstance(intent, Intent)
        self.assertEqual(intent.action_type, IntentType.VSCODE_RUN_COMMAND)
        self.assertIn("notepad", str(intent.parameters))

    def test_parse_json_simple_type_text(self):
        """Test parsing simple JSON type_text intent."""
        json_input = {
            "intent": "type_text",
            "target": "Hello, world!",
            "args": {"delay_ms": 50}
        }

        intent = self.parser.parse(json_input)

        self.assertIsInstance(intent, Intent)
        self.assertEqual(intent.action_type, IntentType.KEYBOARD_TYPE)
        self.assertEqual(intent.parameters["text"], "Hello, world!")
        self.assertEqual(intent.parameters["delay_ms"], 50)

    def test_parse_json_simple_click_on(self):
        """Test parsing simple JSON click_on intent."""
        json_input = {
            "intent": "click_on",
            "target": "submit button",
            "args": {"button": "left"}
        }

        intent = self.parser.parse(json_input)

        self.assertIsInstance(intent, Intent)
        self.assertEqual(intent.action_type, IntentType.MOUSE_CLICK)
        self.assertEqual(intent.parameters["target_element"], "submit button")
        self.assertEqual(intent.parameters["button"], "left")

    def test_parse_json_full_format(self):
        """Test parsing full intent JSON format."""
        json_input = {
            "action_type": "mouse_click",
            "parameters": {"x": 100, "y": 200},
            "rationale": "Click on button",
            "confidence": 0.95
        }

        intent = self.parser.parse(json_input)

        self.assertIsInstance(intent, Intent)
        self.assertEqual(intent.action_type, IntentType.MOUSE_CLICK)
        self.assertEqual(intent.parameters["x"], 100)
        self.assertEqual(intent.parameters["y"], 200)
        self.assertEqual(intent.rationale, "Click on button")
        self.assertEqual(intent.confidence, 0.95)

    def test_parse_json_string(self):
        """Test parsing JSON string."""
        json_string = json.dumps({
            "intent": "screenshot",
            "target": "output.png",
            "args": {}
        })

        intent = self.parser.parse(json_string)

        self.assertIsInstance(intent, Intent)
        self.assertEqual(intent.action_type, IntentType.SCREENSHOT)
        self.assertEqual(intent.parameters["output_path"], "output.png")

    def test_parse_natural_language_open(self):
        """Test parsing natural language 'open' command."""
        inputs = [
            "open notepad",
            "launch chrome",
            "start vscode"
        ]

        for text in inputs:
            intent = self.parser.parse(text)
            self.assertIsInstance(intent, Intent)
            self.assertEqual(intent.action_type, IntentType.VSCODE_RUN_COMMAND)

    def test_parse_natural_language_type(self):
        """Test parsing natural language 'type' command."""
        inputs = [
            'type "hello world"',
            'enter "test message"',
            'write "some text"'
        ]

        for text in inputs:
            intent = self.parser.parse(text)
            self.assertIsInstance(intent, Intent)
            self.assertEqual(intent.action_type, IntentType.KEYBOARD_TYPE)
            self.assertIn("text", intent.parameters)

    def test_parse_natural_language_click(self):
        """Test parsing natural language 'click' command."""
        inputs = [
            "click on submit button",
            "press the ok button",
            "click cancel"
        ]

        for text in inputs:
            intent = self.parser.parse(text)
            self.assertIsInstance(intent, Intent)
            self.assertEqual(intent.action_type, IntentType.MOUSE_CLICK)

    def test_parse_natural_language_click_coordinates(self):
        """Test parsing click with coordinates."""
        intent = self.parser.parse("click on 100,200")

        self.assertIsInstance(intent, Intent)
        self.assertEqual(intent.action_type, IntentType.MOUSE_CLICK)
        self.assertEqual(intent.parameters["x"], 100)
        self.assertEqual(intent.parameters["y"], 200)

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON raises error."""
        invalid_json = '{"invalid": json}'

        with self.assertRaises(IntentParseError):
            self.parser.parse(invalid_json)

    def test_parse_missing_intent_field(self):
        """Test parsing JSON without 'intent' or 'action_type' field."""
        invalid_input = {"some_other_field": "value"}

        with self.assertRaises(IntentParseError):
            self.parser.parse(invalid_input)

    def test_parse_unknown_intent_type(self):
        """Test parsing unknown intent type."""
        invalid_input = {
            "intent": "unknown_action",
            "target": "something",
            "args": {}
        }

        with self.assertRaises(IntentParseError):
            self.parser.parse(invalid_input)

    def test_parse_unparseable_natural_language(self):
        """Test parsing unparseable natural language."""
        unparseable = "this is just random text with no clear intent"

        with self.assertRaises(IntentParseError):
            self.parser.parse(unparseable)

    def test_parse_batch(self):
        """Test batch parsing multiple intents."""
        inputs = [
            {"intent": "open_app", "target": "notepad", "args": {}},
            'type "hello"',
            {"intent": "screenshot", "target": "out.png", "args": {}},
        ]

        intents = self.parser.parse_batch(inputs)

        self.assertEqual(len(intents), 3)
        self.assertIsInstance(intents[0], Intent)
        self.assertIsInstance(intents[1], Intent)
        self.assertIsInstance(intents[2], Intent)

    def test_parse_batch_with_failures(self):
        """Test batch parsing skips failed parses."""
        inputs = [
            {"intent": "open_app", "target": "notepad", "args": {}},
            "unparseable garbage text",  # This should fail
            {"intent": "screenshot", "target": "out.png", "args": {}},
        ]

        intents = self.parser.parse_batch(inputs)

        # Should get 2 intents (1 failed)
        self.assertEqual(len(intents), 2)

    def test_validate_intent_valid(self):
        """Test validating valid intent."""
        intent = Intent(
            action_type=IntentType.MOUSE_CLICK,
            parameters={"x": 100, "y": 200},
            rationale="Test click",
            confidence=0.8
        )

        result = self.parser.validate_intent(intent)
        self.assertTrue(result)

    def test_validate_intent_invalid_confidence(self):
        """Test validating intent with invalid confidence."""
        intent = Intent(
            action_type=IntentType.MOUSE_CLICK,
            parameters={"x": 100, "y": 200},
            confidence=1.5  # Invalid: > 1.0
        )

        with self.assertRaises(IntentParseError):
            self.parser.validate_intent(intent)

    def test_create_open_app_intent_mapping(self):
        """Test app name to executable mapping."""
        # Test common app mappings
        mappings = {
            "notepad": "notepad.exe",
            "vscode": "code",
            "chrome": "chrome.exe",
        }

        for app_name in mappings.keys():
            intent = self.parser._create_open_app_intent(app_name, {})
            self.assertIsInstance(intent, Intent)
            self.assertIn("command", intent.parameters)

    def test_create_screenshot_intent(self):
        """Test screenshot intent creation."""
        intent = self.parser._create_screenshot_intent("test.png", {})

        self.assertEqual(intent.action_type, IntentType.SCREENSHOT)
        self.assertEqual(intent.parameters["output_path"], "test.png")

    def test_create_close_window_intent(self):
        """Test close window intent creation."""
        intent = self.parser._create_close_window_intent("Notepad", {})

        self.assertEqual(intent.action_type, IntentType.WINDOW_CLOSE)
        self.assertEqual(intent.parameters["title"], "Notepad")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)


if __name__ == "__main__":
    unittest.main()
