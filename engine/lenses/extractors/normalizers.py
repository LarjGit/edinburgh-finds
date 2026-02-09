"""Normalizer functions for field value normalization."""
from typing import Any, List


def normalize_trim(value: Any) -> str:
    """
    Trim leading and trailing whitespace.

    Args:
        value: Input value (converted to string)

    Returns:
        Trimmed string
    """
    return str(value).strip()


def normalize_round_integer(value: Any) -> int:
    """
    Convert value to integer, rounding if float.

    Args:
        value: Input value (numeric or string)

    Returns:
        Integer value (rounded down)
    """
    if isinstance(value, str):
        value = float(value)

    return int(value)


def normalize_lowercase(value: Any) -> str:
    """
    Convert value to lowercase string.

    Args:
        value: Input value

    Returns:
        Lowercase string
    """
    return str(value).lower()


# Normalizer registry
NORMALIZERS = {
    "trim": normalize_trim,
    "round_integer": normalize_round_integer,
    "lowercase": normalize_lowercase,
}


def apply_normalizers(value: Any, normalizers: List[str]) -> Any:
    """
    Apply normalizer pipeline left-to-right.

    Per docs/target-architecture.md 7.5: Normalizers execute in order.

    Args:
        value: Input value
        normalizers: List of normalizer names (e.g., ["trim", "round_integer"])

    Returns:
        Normalized value

    Example:
        >>> apply_normalizers("  5.7  ", ["trim", "round_integer"])
        5
    """
    result = value

    for normalizer_name in normalizers:
        normalizer_fn = NORMALIZERS.get(normalizer_name)

        if normalizer_fn:
            result = normalizer_fn(result)

    return result
