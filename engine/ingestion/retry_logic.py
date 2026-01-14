"""
Retry Logic with Exponential Backoff for Data Ingestion

This module provides retry functionality for handling transient failures in
data ingestion connectors (network errors, rate limits, temporary service issues).

Key Components:
- retry_with_backoff: Decorator for applying retry logic to async functions
- MaxRetriesExceeded: Exception raised when all retry attempts are exhausted
- Exponential backoff: Delay increases exponentially between retries
- Configuration loading: Load retry settings from sources.yaml

The retry system helps improve reliability by automatically handling temporary
failures without manual intervention.
"""

import asyncio
import yaml
from pathlib import Path
from typing import Callable, Optional, Dict, Any
from functools import wraps


class MaxRetriesExceeded(Exception):
    """
    Exception raised when maximum retry attempts are exhausted.

    This exception wraps the original exception and includes information
    about the number of retry attempts made.

    Attributes:
        max_retries: Number of retry attempts that were made
        original_exception: The exception that caused the failure
    """

    def __init__(self, max_retries: int, original_exception: Exception):
        """
        Initialize MaxRetriesExceeded exception.

        Args:
            max_retries: Number of retry attempts that were made
            original_exception: The exception that caused the final failure
        """
        self.max_retries = max_retries
        self.original_exception = original_exception

        message = (
            f"Failed after {max_retries} retries. "
            f"Original error: {type(original_exception).__name__}: {str(original_exception)}"
        )
        super().__init__(message)

        # Preserve original exception chain for debugging
        self.__cause__ = original_exception


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0
) -> Callable:
    """
    Decorator to add retry logic with exponential backoff to async functions.

    This decorator automatically retries failed function calls with increasing
    delays between attempts. The delay follows an exponential backoff pattern:
    initial_delay, initial_delay * backoff_factor, initial_delay * backoff_factor^2, ...

    The decorator catches all exceptions and retries until max_retries is exhausted.
    After all retries fail, it raises MaxRetriesExceeded with the original exception.

    Args:
        max_retries: Maximum number of retry attempts (0 means no retries, just one attempt)
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplier for exponential backoff (typically 2.0)
        max_delay: Maximum delay in seconds between retries (caps exponential growth)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(max_retries=3, initial_delay=1.0, backoff_factor=2.0)
        async def fetch_data(url: str):
            response = await http_client.get(url)
            return response.json()

        # If fetch fails, will retry with delays: 1s, 2s, 4s
        # After 3 retries (4 total attempts), raises MaxRetriesExceeded

    Raises:
        MaxRetriesExceeded: When all retry attempts are exhausted
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = initial_delay

            # Attempt the function: 1 initial attempt + max_retries retries
            for attempt in range(max_retries + 1):
                try:
                    # Execute the function
                    result = await func(*args, **kwargs)
                    return result

                except Exception as e:
                    last_exception = e

                    # If this was the last attempt, raise MaxRetriesExceeded
                    if attempt == max_retries:
                        raise MaxRetriesExceeded(
                            max_retries=max_retries,
                            original_exception=e
                        )

                    # Wait before retrying (with exponential backoff)
                    # Cap delay at max_delay to prevent unbounded growth
                    delay = min(current_delay, max_delay)
                    await asyncio.sleep(delay)

                    # Increase delay for next retry (exponential backoff)
                    current_delay *= backoff_factor

            # This should never be reached, but just in case
            raise MaxRetriesExceeded(
                max_retries=max_retries,
                original_exception=last_exception
            )

        return wrapper
    return decorator


def load_retry_config_from_yaml(source: str) -> Dict[str, Any]:
    """
    Load retry configuration for a source from sources.yaml.

    This function reads the retry configuration from the YAML file and returns
    it as a dictionary. It supports both source-specific retry configs and
    global defaults.

    Args:
        source: Name of the data source (e.g., "serper", "google_places")

    Returns:
        Dictionary with retry configuration:
        {
            "max_retries": int,
            "initial_delay": float,
            "backoff_factor": float,
            "max_delay": float
        }

    Raises:
        FileNotFoundError: If sources.yaml doesn't exist
        KeyError: If source not found in configuration

    Example:
        config = load_retry_config_from_yaml("serper")
        limiter = retry_with_backoff(
            max_retries=config["max_retries"],
            initial_delay=config["initial_delay"]
        )
    """
    config_path = Path(__file__).parent.parent / "config" / "sources.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Check if source exists in config
    if source not in config and source != "global":
        raise KeyError(f"Source '{source}' not found in configuration")

    # Try to get source-specific retry config first
    retry_config = {}
    if source in config and "retry" in config[source]:
        retry_config = config[source]["retry"]
    # Fall back to global retry config
    elif "global" in config and "retry" in config["global"]:
        retry_config = config["global"]["retry"]
    else:
        # Return default values if no config found
        return {
            "max_retries": 3,
            "initial_delay": 1.0,
            "backoff_factor": 2.0,
            "max_delay": 60.0
        }

    # Map YAML config keys to function parameter names
    # YAML uses "max_attempts", function uses "max_retries"
    # Subtract 1 because max_attempts includes initial attempt
    max_attempts = retry_config.get("max_attempts", 4)
    max_retries = max(0, max_attempts - 1)  # Convert attempts to retries

    return {
        "max_retries": max_retries,
        "initial_delay": retry_config.get("initial_delay", 1.0),
        "backoff_factor": retry_config.get("backoff_factor", 2.0),
        "max_delay": retry_config.get("max_delay", 60.0)
    }


def create_retry_decorator_from_config(source: str) -> Callable:
    """
    Create a retry decorator configured from sources.yaml.

    This is a convenience function that loads retry configuration from YAML
    and returns a configured retry_with_backoff decorator.

    Args:
        source: Name of the data source

    Returns:
        Configured retry_with_backoff decorator

    Raises:
        FileNotFoundError: If sources.yaml doesn't exist
        KeyError: If source not found in configuration

    Example:
        retry = create_retry_decorator_from_config("serper")

        @retry
        async def fetch_data():
            # API call here
            return response
    """
    config = load_retry_config_from_yaml(source)

    return retry_with_backoff(
        max_retries=config["max_retries"],
        initial_delay=config["initial_delay"],
        backoff_factor=config["backoff_factor"],
        max_delay=config["max_delay"]
    )
