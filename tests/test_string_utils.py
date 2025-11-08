"""
Tests for string utility functions.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from utils.string_utils import string_pad


def test_string_pad_basic():
    """Test basic string padding."""
    result = string_pad("hello", 10)
    assert result == "     hello"
    assert len(result) == 10


def test_string_pad_custom_char():
    """Test padding with custom character."""
    result = string_pad("test", 8, '0')
    assert result == "0000test"
    assert len(result) == 8


def test_string_pad_already_long():
    """Test string that's already longer than width."""
    result = string_pad("toolongstring", 4)
    assert result == "toolongstring"
    assert len(result) == 13


def test_string_pad_exact_width():
    """Test string that's exactly the target width."""
    result = string_pad("exact", 5)
    assert result == "exact"
    assert len(result) == 5


def test_string_pad_empty_string():
    """Test padding empty string."""
    result = string_pad("", 5)
    assert result == "     "
    assert len(result) == 5


def test_string_pad_zero_width():
    """Test with zero width."""
    result = string_pad("hello", 0)
    assert result == "hello"


def test_string_pad_negative_width():
    """Test with negative width."""
    result = string_pad("hello", -5)
    assert result == "hello"


def test_string_pad_unicode():
    """Test with unicode characters."""
    result = string_pad("你好", 6)
    assert result == "    你好"
    assert len(result) == 6


def test_string_pad_multichar_padding():
    """Test with multi-character padding string (uses first char)."""
    result = string_pad("test", 8, "xyz")
    assert result == "xxxxtest"
    assert len(result) == 8


def test_string_pad_empty_padding_char():
    """Test with empty padding character (defaults to space)."""
    result = string_pad("test", 8, "")
    assert result == "    test"
    assert len(result) == 8


def test_string_pad_single_char():
    """Test padding single character."""
    result = string_pad("a", 5, '*')
    assert result == "****a"


def test_string_pad_deterministic():
    """Test that function is deterministic."""
    s = "test"
    width = 10
    char = '-'

    result1 = string_pad(s, width, char)
    result2 = string_pad(s, width, char)

    assert result1 == result2
    assert result1 == "------test"
