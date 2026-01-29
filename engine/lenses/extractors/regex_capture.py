"""Regex capture extractor."""
import re
from typing import Optional


def extract_regex_capture(text: str, pattern: str) -> Optional[str]:
    """
    Extract value using regex pattern with capture group.

    Returns first captured group (group 1).

    Args:
        text: Input text to search
        pattern: Regex pattern with at least one capture group

    Returns:
        Captured value (as string) or None if no match

    Example:
        >>> extract_regex_capture("5 padel courts", r"(\\d+)\\s*padel")
        "5"
    """
    if not isinstance(text, str):
        text = str(text)

    match = re.search(pattern, text)

    if not match:
        return None

    # Return first captured group
    if match.groups():
        return match.group(1)

    return None
