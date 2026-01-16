"""
Opening Hours Extraction Utility

Parses and normalizes various opening hours formats into a consistent JSON structure.

Features:
- Handles structured JSON opening hours (e.g., from Google Places)
- Parses free-text opening hours using LLM ("Mon-Fri 9am-5pm", "24/7", etc.)
- Validates 24-hour time format (HH:MM)
- Handles CLOSED vs null semantics (null = unknown, CLOSED = explicitly closed)
- Retry logic with validation feedback
"""

import re
from typing import Dict, Any, Optional, Tuple, Union
from pydantic import BaseModel, Field, field_validator
from engine.extraction.llm_client import InstructorClient


# Day names for validation
DAYS_OF_WEEK = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']


class TimeRange(BaseModel):
    """Represents opening and closing times for a single day"""
    open: str = Field(..., description="Opening time in 24-hour format (HH:MM)")
    close: str = Field(..., description="Closing time in 24-hour format (HH:MM)")

    @field_validator('open', 'close')
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate that time is in 24-hour format (HH:MM)"""
        pattern = r'^([0-1]\d|2[0-3]):([0-5]\d)$'
        if not re.match(pattern, v):
            raise ValueError(
                f"Time must be in 24-hour format (HH:MM). Got: {v}. "
                "Examples: 09:00, 17:30, 23:59"
            )
        return v


class OpeningHoursStructure(BaseModel):
    """Structured opening hours model for all 7 days"""
    monday: Union[TimeRange, str] = Field(
        ...,
        description="Monday hours (TimeRange object, 'CLOSED', or '24_HOURS')"
    )
    tuesday: Union[TimeRange, str] = Field(
        ...,
        description="Tuesday hours (TimeRange object, 'CLOSED', or '24_HOURS')"
    )
    wednesday: Union[TimeRange, str] = Field(
        ...,
        description="Wednesday hours (TimeRange object, 'CLOSED', or '24_HOURS')"
    )
    thursday: Union[TimeRange, str] = Field(
        ...,
        description="Thursday hours (TimeRange object, 'CLOSED', or '24_HOURS')"
    )
    friday: Union[TimeRange, str] = Field(
        ...,
        description="Friday hours (TimeRange object, 'CLOSED', or '24_HOURS')"
    )
    saturday: Union[TimeRange, str] = Field(
        ...,
        description="Saturday hours (TimeRange object, 'CLOSED', or '24_HOURS')"
    )
    sunday: Union[TimeRange, str] = Field(
        ...,
        description="Sunday hours (TimeRange object, 'CLOSED', or '24_HOURS')"
    )

    @field_validator('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
    @classmethod
    def validate_day_value(cls, v: Union[TimeRange, str]) -> Union[TimeRange, str]:
        """Validate that string values are only CLOSED or 24_HOURS"""
        if isinstance(v, str):
            if v not in ['CLOSED', '24_HOURS']:
                raise ValueError(
                    f"String value must be 'CLOSED' or '24_HOURS'. Got: {v}"
                )
        return v


# Cached LLM client (singleton pattern)
_llm_client: Optional[InstructorClient] = None


def get_llm_client() -> InstructorClient:
    """
    Get or create the LLM client instance (singleton).

    Returns:
        InstructorClient: The global LLM client instance
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = InstructorClient()
    return _llm_client


def parse_opening_hours(
    data: Optional[Union[str, Dict[str, Any]]],
    max_retries: int = 2
) -> Optional[Dict[str, Any]]:
    """
    Parse opening hours from various formats into consistent JSON structure.

    Args:
        data: Opening hours data (structured dict, free-text string, or None)
        max_retries: Maximum number of LLM retry attempts (default: 2)

    Returns:
        Dictionary with days as keys and opening hours as values, or None if unknown

    Examples:
        >>> # Structured format (passthrough)
        >>> parse_opening_hours({"monday": {"open": "09:00", "close": "17:00"}})
        {'monday': {'open': '09:00', 'close': '17:00'}, ...}

        >>> # Free-text format (LLM extraction)
        >>> parse_opening_hours("Mon-Fri 9am-5pm, Sat 10am-4pm, Sun closed")
        {'monday': {'open': '09:00', 'close': '17:00'}, ..., 'sunday': 'CLOSED'}

        >>> # Unknown hours
        >>> parse_opening_hours(None)
        None

        >>> # 24/7
        >>> parse_opening_hours("Open 24/7")
        {'monday': '24_HOURS', 'tuesday': '24_HOURS', ...}
    """
    # Handle None or empty string (unknown hours)
    if data is None or (isinstance(data, str) and not data.strip()):
        return None

    # Handle ambiguous cases (appointment only, varies, etc.)
    if isinstance(data, str):
        lower_data = data.lower().strip()
        ambiguous_patterns = [
            'appointment', 'by appointment', 'varies', 'call', 'contact',
            'seasonal', 'check website', 'tbc', 'to be confirmed'
        ]
        if any(pattern in lower_data for pattern in ambiguous_patterns):
            # Unknown hours, not closed
            return None

    # Handle structured format (dict)
    if isinstance(data, dict):
        return _parse_structured_hours(data)

    # Handle free-text format (string) - requires LLM
    if isinstance(data, str):
        return _parse_freetext_hours(data, max_retries)

    return None


def _parse_structured_hours(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse structured opening hours (already in dict format).

    This is a passthrough function that validates the structure.

    Args:
        data: Structured opening hours dict

    Returns:
        Validated opening hours dict
    """
    # Normalize keys to lowercase
    normalized = {}
    for key, value in data.items():
        day = key.lower()
        if day in DAYS_OF_WEEK:
            # Handle TimeRange dict
            if isinstance(value, dict) and 'open' in value and 'close' in value:
                normalized[day] = {
                    'open': _normalize_time(value['open']),
                    'close': _normalize_time(value['close'])
                }
            # Handle string markers (CLOSED, 24_HOURS)
            elif isinstance(value, str):
                normalized[day] = value.upper()
            else:
                # Invalid value, skip
                continue

    # If we have at least one day, return it
    if normalized:
        return normalized

    return data


def _parse_freetext_hours(text: str, max_retries: int) -> Optional[Dict[str, Any]]:
    """
    Parse free-text opening hours using LLM extraction.

    Args:
        text: Free-text opening hours string
        max_retries: Maximum retry attempts

    Returns:
        Structured opening hours dict or None if parsing fails
    """
    # Check for explicit 24/7 patterns
    if re.search(r'\b(24/7|24\s*hours|open\s+24)\b', text, re.IGNORECASE):
        return {day: '24_HOURS' for day in DAYS_OF_WEEK}

    # Use LLM for complex parsing
    try:
        client = get_llm_client()

        prompt = """
Extract opening hours from the provided text into a structured format.

IMPORTANT RULES:
1. Times MUST be in 24-hour format (HH:MM). Examples: 09:00, 17:30, 23:59
2. Use "CLOSED" for days that are explicitly closed
3. Use "24_HOURS" for venues open 24 hours
4. Do NOT use 12-hour format (am/pm) - convert to 24-hour
5. Ensure all 7 days are included
6. If a day is not mentioned, make a reasonable assumption based on context

Conversion examples:
- 9am → 09:00
- 5pm → 17:00
- 11:30am → 11:30
- 10:30pm → 22:30
"""

        system_message = (
            "You are a data extraction assistant specializing in opening hours. "
            "Extract and normalize opening hours into 24-hour format. "
            "Be precise with time conversions (12-hour to 24-hour format)."
        )

        response = client.extract(
            prompt=prompt,
            response_model=OpeningHoursStructure,
            context=text,
            system_message=system_message,
            max_retries=max_retries
        )

        # Convert Pydantic model to dict
        result = {}
        for day in DAYS_OF_WEEK:
            value = getattr(response, day)
            if isinstance(value, TimeRange):
                result[day] = {
                    'open': value.open,
                    'close': value.close
                }
            else:
                result[day] = value

        return result

    except Exception as e:
        # LLM extraction failed, return None (unknown)
        print(f"Opening hours extraction failed: {e}")
        return None


def _normalize_time(time_str: str) -> str:
    """
    Normalize time string to 24-hour format (HH:MM).

    Args:
        time_str: Time string in various formats

    Returns:
        Normalized time string (HH:MM)
    """
    # Remove whitespace
    time_str = time_str.strip()

    # Already in correct format
    if re.match(r'^([0-1]\d|2[0-3]):([0-5]\d)$', time_str):
        return time_str

    # Try to extract and format
    # Handle formats like "9:00", "17:30", etc.
    match = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
    if match:
        hour, minute = match.groups()
        return f"{int(hour):02d}:{minute}"

    # If can't normalize, return as-is (will fail validation later)
    return time_str


def validate_opening_hours(hours: Dict[str, Any], require_all_days: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Validate opening hours structure and format.

    Args:
        hours: Opening hours dictionary to validate
        require_all_days: If True, all 7 days must be present (default: True)

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if validation passes
        - error_message: Error description if validation fails, None otherwise

    Examples:
        >>> validate_opening_hours({"monday": {"open": "09:00", "close": "17:00"}, ...})
        (True, None)

        >>> validate_opening_hours({"monday": {"open": "9am", "close": "5pm"}})
        (False, "Time must be in 24-hour format...")
    """
    if not hours or not isinstance(hours, dict):
        return False, "Opening hours must be a non-empty dictionary"

    # Check that all 7 days are present (if required)
    if require_all_days:
        missing_days = set(DAYS_OF_WEEK) - set(hours.keys())
        if missing_days:
            return False, f"Missing required days: {', '.join(missing_days)}"

    # Validate each day present in the dict
    for day, value in hours.items():
        # Skip if not a valid day name
        if day not in DAYS_OF_WEEK:
            continue

        if value is None:
            return False, f"Day '{day}' cannot be None (use 'CLOSED' for closed days)"

        # String markers
        if isinstance(value, str):
            if value not in ['CLOSED', '24_HOURS']:
                return False, f"Invalid string value for '{day}': {value}. Must be 'CLOSED' or '24_HOURS'"
            continue

        # TimeRange dict
        if isinstance(value, dict):
            if 'open' not in value or 'close' not in value:
                return False, f"Day '{day}' must have 'open' and 'close' times"

            # Validate time format
            for time_key in ['open', 'close']:
                time_val = value[time_key]
                if not isinstance(time_val, str):
                    return False, f"Time value for '{day}.{time_key}' must be a string"

                # Check 24-hour format (HH:MM)
                if not re.match(r'^([0-1]\d|2[0-3]):([0-5]\d)$', time_val):
                    return False, (
                        f"Time for '{day}.{time_key}' must be in 24-hour format (HH:MM). "
                        f"Got: {time_val}"
                    )

                # Check for 12-hour format indicators
                if re.search(r'(am|pm)', time_val, re.IGNORECASE):
                    return False, (
                        f"Time for '{day}.{time_key}' contains am/pm. "
                        "Use 24-hour format instead"
                    )

            continue

        # Invalid type
        return False, f"Day '{day}' has invalid type: {type(value).__name__}"

    return True, None
