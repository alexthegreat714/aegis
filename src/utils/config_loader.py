"""
Configuration loader with hot-reload support.

Monitors settings.yaml for changes and reloads without restart.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class ConfigLoader:
    """
    Configuration loader with hot-reload capability.

    Watches config/settings.yaml and automatically reloads when modified.
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        Initialize config loader.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._last_modified: Optional[float] = None
        self._load_count = 0

        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Initial load
        self.reload()

    def _get_mtime(self) -> Optional[float]:
        """Get file modification time."""
        try:
            return os.path.getmtime(self.config_path)
        except FileNotFoundError:
            return None

    def reload(self) -> bool:
        """
        Reload configuration from file.

        Returns:
            True if config was reloaded, False if unchanged
        """
        if not self.config_path.exists():
            # Use defaults if config doesn't exist
            self._config = self._get_defaults()
            self._last_modified = None
            return False

        current_mtime = self._get_mtime()

        # Check if file has changed
        if self._last_modified is not None and current_mtime == self._last_modified:
            return False

        # Load config
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}

            self._last_modified = current_mtime
            self._load_count += 1

            return True
        except Exception as e:
            print(f"Warning: Failed to reload config: {e}")
            return False

    def check_and_reload(self) -> bool:
        """
        Check if config has changed and reload if needed.

        Returns:
            True if config was reloaded
        """
        return self.reload()

    def load(self) -> Dict[str, Any]:
        """
        Deprecated alias for to_dict(), kept for backwards compatibility.

        Returns:
            Configuration dictionary

        Note:
            Use to_dict() instead. This method exists for compatibility
            with external code that may call config_loader.load().
        """
        return self.to_dict()

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get config value using dot notation.

        Args:
            key_path: Dot-separated path (e.g., "control_loop.max_cycles")
            default: Default value if key not found

        Returns:
            Config value or default
        """
        keys = key_path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire config section.

        Args:
            section: Section name (e.g., "control_loop")

        Returns:
            Section dictionary or empty dict
        """
        return self._config.get(section, {})

    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'control_loop': {
                'max_cycles': 100,
                'cycle_delay_seconds': 1.0,
                'enable_heartbeat': True,
                'heartbeat_interval_cycles': 5
            },
            'logging': {
                'db_path': 'data/aegis.db',
                'enable_jsonl': True,
                'log_retention_days': 30,
                'max_heartbeat_entries': 1000
            },
            'health': {
                'monitor_cpu': True,
                'monitor_memory': True,
                'monitor_active_window': True
            },
            'policy': {
                'mode': 'permissive',
                'allowed_intents': ['maintain_idle_state', 'monitor_system', 'check_health']
            },
            'sandbox': {
                'enabled': False,
                'mock_actions': True,
                'dry_run': True
            },
            'assist': {
                'enabled': False,
                'require_confirmation': True,
                'verbose': True
            }
        }

    @property
    def load_count(self) -> int:
        """Number of times config has been loaded."""
        return self._load_count

    @property
    def last_modified(self) -> Optional[datetime]:
        """Last modification time of config file."""
        if self._last_modified:
            return datetime.fromtimestamp(self._last_modified)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Get entire configuration as dictionary."""
        return self._config.copy()


# Global config instance
_global_config: Optional[ConfigLoader] = None


def get_config() -> ConfigLoader:
    """Get global config instance."""
    global _global_config
    if _global_config is None:
        _global_config = ConfigLoader()
    return _global_config


def reload_config() -> bool:
    """Reload global config."""
    return get_config().reload()
