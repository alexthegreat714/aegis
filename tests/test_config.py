"""Tests for config loader and hot-reload."""

import pytest
import tempfile
import time
from pathlib import Path
from src.utils.config_loader import ConfigLoader


@pytest.fixture
def temp_config():
    """Create temporary config file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_settings.yaml"
        # Write initial config
        config_path.write_text("""
control_loop:
  max_cycles: 50
  cycle_delay_seconds: 0.5

logging:
  db_path: "test.db"
  enable_jsonl: false
        """)
        yield str(config_path)


def test_config_loader_initialization(temp_config):
    """Test config loads on initialization."""
    loader = ConfigLoader(config_path=temp_config)

    assert loader.get('control_loop.max_cycles') == 50
    assert loader.get('control_loop.cycle_delay_seconds') == 0.5
    assert loader.get('logging.db_path') == "test.db"
    assert loader.get('logging.enable_jsonl') is False


def test_config_loader_get_with_default(temp_config):
    """Test getting non-existent keys returns default."""
    loader = ConfigLoader(config_path=temp_config)

    assert loader.get('nonexistent.key', 'default_value') == 'default_value'
    assert loader.get('control_loop.nonexistent', 99) == 99


def test_config_loader_get_section(temp_config):
    """Test getting entire config section."""
    loader = ConfigLoader(config_path=temp_config)

    section = loader.get_section('control_loop')

    assert isinstance(section, dict)
    assert section['max_cycles'] == 50
    assert section['cycle_delay_seconds'] == 0.5


def test_config_loader_hot_reload(temp_config):
    """Test hot-reload detects file changes."""
    loader = ConfigLoader(config_path=temp_config)

    # Initial value
    assert loader.get('control_loop.max_cycles') == 50

    # Modify config file
    time.sleep(0.1)  # Ensure different mtime
    Path(temp_config).write_text("""
control_loop:
  max_cycles: 100
  cycle_delay_seconds: 1.0

logging:
  db_path: "test.db"
  enable_jsonl: true
    """)

    # Reload
    reloaded = loader.reload()
    assert reloaded is True

    # Verify new value
    assert loader.get('control_loop.max_cycles') == 100
    assert loader.get('control_loop.cycle_delay_seconds') == 1.0
    assert loader.get('logging.enable_jsonl') is True


def test_config_loader_no_reload_if_unchanged(temp_config):
    """Test reload returns False if file unchanged."""
    loader = ConfigLoader(config_path=temp_config)

    # First reload after initialization
    reloaded = loader.reload()
    assert reloaded is False  # File hasn't changed


def test_config_loader_check_and_reload(temp_config):
    """Test check_and_reload method."""
    loader = ConfigLoader(config_path=temp_config)

    # No change
    assert loader.check_and_reload() is False

    # Make change
    time.sleep(0.1)
    Path(temp_config).write_text("""
control_loop:
  max_cycles: 200
    """)

    # Should detect change
    assert loader.check_and_reload() is True
    assert loader.get('control_loop.max_cycles') == 200


def test_config_loader_load_count(temp_config):
    """Test load count tracking."""
    loader = ConfigLoader(config_path=temp_config)

    initial_count = loader.load_count
    assert initial_count >= 1

    # Trigger reload
    time.sleep(0.1)
    Path(temp_config).write_text("control_loop:\n  max_cycles: 300")
    loader.reload()

    assert loader.load_count == initial_count + 1


def test_config_loader_to_dict(temp_config):
    """Test converting config to dictionary."""
    loader = ConfigLoader(config_path=temp_config)

    config_dict = loader.to_dict()

    assert isinstance(config_dict, dict)
    assert 'control_loop' in config_dict
    assert 'logging' in config_dict


def test_config_loader_defaults_if_file_missing():
    """Test loader uses defaults if config file doesn't exist."""
    loader = ConfigLoader(config_path="/nonexistent/path/config.yaml")

    # Should use defaults
    assert loader.get('control_loop.max_cycles') == 100
    assert loader.get('logging.db_path') == 'data/aegis.db'


def test_config_loader_invalid_yaml_handling(temp_config):
    """Test handling of invalid YAML."""
    loader = ConfigLoader(config_path=temp_config)

    # Write invalid YAML
    time.sleep(0.1)
    Path(temp_config).write_text("invalid: yaml: syntax: error:")

    # Reload should handle error gracefully
    reloaded = loader.reload()
    # Should return False and keep old config
    assert reloaded is False


def test_config_loader_last_modified(temp_config):
    """Test last modified timestamp tracking."""
    loader = ConfigLoader(config_path=temp_config)

    assert loader.last_modified is not None
    first_modified = loader.last_modified

    # Modify file
    time.sleep(0.1)
    Path(temp_config).write_text("control_loop:\n  max_cycles: 400")
    loader.reload()

    # Timestamp should update
    assert loader.last_modified != first_modified
