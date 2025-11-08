"""
String utility functions.

Provides helper functions for string manipulation and formatting.
"""


def string_pad(s: str, width: int, char: str = ' ') -> str:
    """
    Left-pad a string to the specified width.

    Args:
        s: String to pad
        width: Target width
        char: Padding character (default: space)

    Returns:
        Padded string. If string is already >= width, returns unchanged.

    Examples:
        >>> string_pad("hello", 10)
        '     hello'
        >>> string_pad("test", 8, '0')
        '0000test'
        >>> string_pad("toolong", 4)
        'toolong'
    """
    if width <= 0:
        return s

    current_len = len(s)

    if current_len >= width:
        return s

    # Calculate padding needed
    padding_needed = width - current_len

    # Use first character of padding string if multi-char
    pad_char = char[0] if char else ' '

    return (pad_char * padding_needed) + s
