"""
Rate Limiting Infrastructure for Data Ingestion

This module provides rate limiting functionality for data source connectors to
prevent API quota exhaustion and comply with service-specific rate limits.

Key Components:
- RateLimiter: Class for tracking and enforcing rate limits
- rate_limited: Decorator for applying rate limits to async functions
- RateLimitExceeded: Exception raised when rate limits are exceeded
- Configuration loading: Load rate limits from sources.yaml

Rate limits support both per-minute and per-hour windows with automatic
request expiry based on sliding time windows.
"""

import time
import yaml
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from functools import wraps
from collections import deque


class RateLimitExceeded(Exception):
    """
    Exception raised when a rate limit is exceeded.

    This exception includes information about which source and limit type
    (per-minute or per-hour) was exceeded to help with debugging and logging.
    """

    def __init__(self, source: str, limit_type: str, limit_value: int):
        """
        Initialize RateLimitExceeded exception.

        Args:
            source: Name of the data source (e.g., "serper", "google_places")
            limit_type: Type of limit exceeded ("per_minute" or "per_hour")
            limit_value: The limit value that was exceeded
        """
        self.source = source
        self.limit_type = limit_type
        self.limit_value = limit_value

        message = (
            f"Rate limit exceeded for source '{source}': "
            f"{limit_type} limit of {limit_value} requests reached"
        )
        super().__init__(message)


class RateLimiter:
    """
    Rate limiter for tracking and enforcing request rate limits.

    Uses sliding time windows to track requests over the last minute and hour.
    Automatically expires old requests that fall outside the time windows.

    Supports unlimited rate limits by setting limits to None.

    Example:
        limiter = RateLimiter(
            source="serper",
            requests_per_minute=60,
            requests_per_hour=1000
        )

        if limiter.can_make_request():
            limiter.record_request()
            # Make API request
        else:
            wait_time = limiter.get_time_until_next_request()
            # Wait or raise exception
    """

    def __init__(
        self,
        source: str,
        requests_per_minute: Optional[int] = None,
        requests_per_hour: Optional[int] = None
    ):
        """
        Initialize RateLimiter with source name and limits.

        Args:
            source: Name of the data source
            requests_per_minute: Maximum requests per minute (None for unlimited)
            requests_per_hour: Maximum requests per hour (None for unlimited)
        """
        self.source = source
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour

        # Use deque for efficient FIFO operations
        # Store timestamps of requests
        self._request_log: deque = deque()

    def _clean_expired_requests(self, window_seconds: int) -> None:
        """
        Remove requests older than the specified time window.

        Args:
            window_seconds: Time window in seconds (60 for minute, 3600 for hour)
        """
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        # Remove all requests older than cutoff
        while self._request_log and self._request_log[0] < cutoff_time:
            self._request_log.popleft()

    def get_request_count_last_minute(self) -> int:
        """
        Get the number of requests made in the last minute.

        Returns:
            Number of requests in the last 60 seconds
        """
        self._clean_expired_requests(60)
        return len(self._request_log)

    def get_request_count_last_hour(self) -> int:
        """
        Get the number of requests made in the last hour.

        Returns:
            Number of requests in the last 3600 seconds
        """
        self._clean_expired_requests(3600)
        return len(self._request_log)

    def can_make_request(self) -> bool:
        """
        Check if a request can be made without exceeding rate limits.

        Returns:
            True if request is allowed, False if rate limit would be exceeded
        """
        # Check per-minute limit
        if self.requests_per_minute is not None:
            count_last_minute = self.get_request_count_last_minute()
            if count_last_minute >= self.requests_per_minute:
                return False

        # Check per-hour limit
        if self.requests_per_hour is not None:
            count_last_hour = self.get_request_count_last_hour()
            if count_last_hour >= self.requests_per_hour:
                return False

        return True

    def record_request(self) -> None:
        """
        Record that a request was made at the current time.

        This should be called immediately after making an API request.
        """
        self._request_log.append(time.time())

    def get_time_until_next_request(self) -> float:
        """
        Calculate time in seconds until next request is allowed.

        Returns:
            Number of seconds to wait (0 if request can be made now)
        """
        if self.can_make_request():
            return 0

        current_time = time.time()
        wait_times = []

        # Check per-minute limit
        if self.requests_per_minute is not None:
            count_last_minute = self.get_request_count_last_minute()
            if count_last_minute >= self.requests_per_minute:
                # Find the oldest request in the minute window
                # It will expire 60 seconds after it was made
                oldest_request = self._request_log[0]
                wait_time = 60 - (current_time - oldest_request)
                if wait_time > 0:
                    wait_times.append(wait_time)

        # Check per-hour limit
        if self.requests_per_hour is not None:
            count_last_hour = self.get_request_count_last_hour()
            if count_last_hour >= self.requests_per_hour:
                # Find the oldest request in the hour window
                oldest_request = self._request_log[0]
                wait_time = 3600 - (current_time - oldest_request)
                if wait_time > 0:
                    wait_times.append(wait_time)

        # Return the minimum wait time (earliest we can make a request)
        return min(wait_times) if wait_times else 0


# Global registry of rate limiters (one per source)
_rate_limiters: Dict[str, RateLimiter] = {}


def _reset_rate_limiters():
    """
    Reset the global rate limiter registry.

    This function is intended for testing purposes only to clear
    state between test runs.
    """
    global _rate_limiters
    _rate_limiters = {}


def get_or_create_rate_limiter(
    source: str,
    requests_per_minute: Optional[int] = None,
    requests_per_hour: Optional[int] = None
) -> RateLimiter:
    """
    Get existing rate limiter for source or create a new one.

    This ensures that all decorated functions for the same source
    share the same rate limiter instance.

    Args:
        source: Name of the data source
        requests_per_minute: Maximum requests per minute
        requests_per_hour: Maximum requests per hour

    Returns:
        RateLimiter instance for the source
    """
    if source not in _rate_limiters:
        _rate_limiters[source] = RateLimiter(
            source=source,
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour
        )
    return _rate_limiters[source]


def rate_limited(
    source: str,
    requests_per_minute: Optional[int] = None,
    requests_per_hour: Optional[int] = None
) -> Callable:
    """
    Decorator to apply rate limiting to async functions.

    This decorator checks rate limits before executing the function and
    raises RateLimitExceeded if limits would be exceeded. It automatically
    records successful requests.

    Args:
        source: Name of the data source
        requests_per_minute: Maximum requests per minute (None for unlimited)
        requests_per_hour: Maximum requests per hour (None for unlimited)

    Returns:
        Decorated function with rate limiting

    Example:
        @rate_limited(source="serper", requests_per_minute=60, requests_per_hour=1000)
        async def fetch_data(query: str):
            # API call here
            return response

    Raises:
        RateLimitExceeded: When rate limit is exceeded
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            limiter = get_or_create_rate_limiter(
                source=source,
                requests_per_minute=requests_per_minute,
                requests_per_hour=requests_per_hour
            )

            # Check if request is allowed
            if not limiter.can_make_request():
                # Determine which limit was exceeded
                count_minute = limiter.get_request_count_last_minute()
                count_hour = limiter.get_request_count_last_hour()

                if (limiter.requests_per_minute is not None and
                    count_minute >= limiter.requests_per_minute):
                    raise RateLimitExceeded(
                        source=source,
                        limit_type="per_minute",
                        limit_value=limiter.requests_per_minute
                    )
                elif (limiter.requests_per_hour is not None and
                      count_hour >= limiter.requests_per_hour):
                    raise RateLimitExceeded(
                        source=source,
                        limit_type="per_hour",
                        limit_value=limiter.requests_per_hour
                    )

            # Record the request
            limiter.record_request()

            # Execute the function
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def load_rate_limits_from_config(source: str) -> Dict[str, Any]:
    """
    Load rate limits for a source from sources.yaml configuration.

    Args:
        source: Name of the data source (e.g., "serper", "google_places")

    Returns:
        Dictionary with rate limit configuration:
        {
            "requests_per_minute": int or None,
            "requests_per_hour": int or None
        }

    Raises:
        KeyError: If source not found in configuration
        FileNotFoundError: If sources.yaml doesn't exist
    """
    config_path = Path(__file__).parent.parent / "config" / "sources.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    if source not in config:
        raise KeyError(f"Source '{source}' not found in configuration")

    source_config = config[source]
    rate_limits = source_config.get("rate_limits", {})

    return {
        "requests_per_minute": rate_limits.get("requests_per_minute"),
        "requests_per_hour": rate_limits.get("requests_per_hour")
    }


def create_rate_limiter_from_config(source: str) -> RateLimiter:
    """
    Create a RateLimiter instance from sources.yaml configuration.

    Args:
        source: Name of the data source

    Returns:
        RateLimiter instance configured with limits from sources.yaml

    Raises:
        KeyError: If source not found in configuration
        FileNotFoundError: If sources.yaml doesn't exist

    Example:
        limiter = create_rate_limiter_from_config("serper")
        if limiter.can_make_request():
            limiter.record_request()
            # Make API call
    """
    rate_limits = load_rate_limits_from_config(source)

    return RateLimiter(
        source=source,
        requests_per_minute=rate_limits["requests_per_minute"],
        requests_per_hour=rate_limits["requests_per_hour"]
    )
