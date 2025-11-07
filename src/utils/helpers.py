"""
Common utility functions.
"""

from typing import Dict, Any
from pathlib import Path
import yaml


def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    Load YAML file.

    Args:
        file_path: Path to YAML file

    Returns:
        Parsed YAML as dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_token(token_file: str) -> str:
    """
    Load token from file.

    Args:
        token_file: Path to token file

    Returns:
        Token string

    Raises:
        FileNotFoundError: If token file doesn't exist
    """
    path = Path(token_file)

    if not path.exists():
        raise FileNotFoundError(
            f"Token file not found: {token_file}\n"
            f"Create this file with your OpenWebUI Bearer token."
        )

    with open(path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def ensure_directory(dir_path: str) -> Path:
    """
    Ensure directory exists, create if needed.

    Args:
        dir_path: Directory path

    Returns:
        Path object for directory
    """
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe filesystem use.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    sanitized = filename

    for char in unsafe_chars:
        sanitized = sanitized.replace(char, '_')

    return sanitized


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to maximum length.

    Args:
        s: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s

    return s[:max_length - len(suffix)] + suffix
