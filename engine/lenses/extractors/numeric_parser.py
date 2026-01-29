"""Numeric parser extractor."""
import re
from typing import Optional, Union


def extract_numeric(text: str) -> Optional[Union[int, float]]:
    """
    Extract first numeric value from text.

    Args:
        text: Input text containing numbers

    Returns:
        First number found (int or float), or None if no number found

    Example:
        >>> extract_numeric("5 courts available")
        5
        >>> extract_numeric("No numbers")
        None
    """
    if not isinstance(text, str):
        text = str(text)

    # Find first number (int or float)
    match = re.search(r'[-+]?\d*\.?\d+', text)

    if not match:
        return None

    number_str = match.group()

    # Convert to int or float
    if '.' in number_str:
        return float(number_str)
    else:
        return int(number_str)
