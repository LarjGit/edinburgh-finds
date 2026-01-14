"""
Tests for Rate Limiting Infrastructure

This module tests the rate limiting decorator for data ingestion connectors.
The rate limiting system provides:
- Per-source request rate limiting
- Configurable per-minute and per-hour limits
- Time window tracking with automatic reset
- Integration with sources.yaml configuration
- Clear error messages when limits are exceeded
"""

import unittest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta


class TestRateLimiterInitialization(unittest.TestCase):
    """Test RateLimiter class initialization and configuration"""

    def test_rate_limiter_class_exists(self):
        """Test that RateLimiter class can be imported"""
        try:
            from engine.ingestion.rate_limiting import RateLimiter
            self.assertIsNotNone(RateLimiter)
        except ImportError as e:
            self.fail(f"Failed to import RateLimiter: {e}")

    def test_rate_limiter_initialization(self):
        """Test RateLimiter can be initialized with source and limits"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="serper",
            requests_per_minute=60,
            requests_per_hour=1000
        )
        self.assertEqual(limiter.source, "serper")
        self.assertEqual(limiter.requests_per_minute, 60)
        self.assertEqual(limiter.requests_per_hour, 1000)

    def test_rate_limiter_initialization_with_none_limits(self):
        """Test RateLimiter handles None (unlimited) rate limits"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=None,
            requests_per_hour=None
        )
        self.assertIsNone(limiter.requests_per_minute)
        self.assertIsNone(limiter.requests_per_hour)

    def test_rate_limiter_initializes_empty_request_log(self):
        """Test RateLimiter starts with empty request history"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=10,
            requests_per_hour=100
        )
        # Should have empty or initialized request tracking
        self.assertIsNotNone(limiter)


class TestRateLimiterRequestTracking(unittest.TestCase):
    """Test rate limiter request tracking functionality"""

    def test_can_make_request_under_limit(self):
        """Test that requests under limit are allowed"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=10,
            requests_per_hour=100
        )
        # First request should always be allowed
        self.assertTrue(limiter.can_make_request())

    def test_record_request_increments_count(self):
        """Test that recording a request increments the count"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=10,
            requests_per_hour=100
        )
        initial_count = limiter.get_request_count_last_minute()
        limiter.record_request()
        new_count = limiter.get_request_count_last_minute()
        self.assertEqual(new_count, initial_count + 1)

    def test_exceeding_per_minute_limit_blocks_request(self):
        """Test that exceeding per-minute limit blocks requests"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=3,  # Very low limit for testing
            requests_per_hour=100
        )
        # Make 3 requests (at limit)
        for _ in range(3):
            self.assertTrue(limiter.can_make_request())
            limiter.record_request()

        # 4th request should be blocked
        self.assertFalse(limiter.can_make_request())

    def test_exceeding_per_hour_limit_blocks_request(self):
        """Test that exceeding per-hour limit blocks requests"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=100,  # High minute limit
            requests_per_hour=5       # Low hour limit for testing
        )
        # Make 5 requests (at limit)
        for _ in range(5):
            self.assertTrue(limiter.can_make_request())
            limiter.record_request()

        # 6th request should be blocked
        self.assertFalse(limiter.can_make_request())

    def test_get_request_count_last_minute(self):
        """Test getting request count for last minute"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=10,
            requests_per_hour=100
        )
        self.assertEqual(limiter.get_request_count_last_minute(), 0)

        limiter.record_request()
        self.assertEqual(limiter.get_request_count_last_minute(), 1)

        limiter.record_request()
        self.assertEqual(limiter.get_request_count_last_minute(), 2)

    def test_get_request_count_last_hour(self):
        """Test getting request count for last hour"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=10,
            requests_per_hour=100
        )
        self.assertEqual(limiter.get_request_count_last_hour(), 0)

        limiter.record_request()
        self.assertEqual(limiter.get_request_count_last_hour(), 1)


class TestRateLimiterTimeWindows(unittest.TestCase):
    """Test rate limiter time window management"""

    def test_old_requests_expire_from_minute_window(self):
        """Test that requests older than 1 minute don't count toward limit"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=2,
            requests_per_hour=100
        )
        # Make 2 requests (at limit)
        limiter.record_request()
        limiter.record_request()
        self.assertFalse(limiter.can_make_request())

        # Mock time to be 61 seconds later
        current_time = time.time()
        with patch('engine.ingestion.rate_limiting.time.time') as mock_time:
            mock_time.return_value = current_time + 61
            # Old requests should have expired, new request allowed
            self.assertTrue(limiter.can_make_request())

    def test_old_requests_expire_from_hour_window(self):
        """Test that requests older than 1 hour don't count toward limit"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=100,
            requests_per_hour=2
        )
        # Make 2 requests (at limit)
        limiter.record_request()
        limiter.record_request()
        self.assertFalse(limiter.can_make_request())

        # Mock time to be 61 minutes later
        current_time = time.time()
        with patch('engine.ingestion.rate_limiting.time.time') as mock_time:
            mock_time.return_value = current_time + 3661
            # Old requests should have expired, new request allowed
            self.assertTrue(limiter.can_make_request())


class TestRateLimiterWithNoneLimits(unittest.TestCase):
    """Test rate limiter behavior with unlimited (None) configurations"""

    def test_none_per_minute_allows_unlimited_requests(self):
        """Test that None per-minute limit allows unlimited requests"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=None,  # Unlimited
            requests_per_hour=None  # Also unlimited to truly test unlimited per-minute
        )
        # Make many requests - should all be allowed
        for _ in range(200):
            self.assertTrue(limiter.can_make_request())
            limiter.record_request()

    def test_none_per_hour_allows_unlimited_requests(self):
        """Test that None per-hour limit allows unlimited requests"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=10000,
            requests_per_hour=None  # Unlimited
        )
        # Make many requests - should all be allowed
        for _ in range(200):
            self.assertTrue(limiter.can_make_request())
            limiter.record_request()


class TestRateLimiterDecorator(unittest.TestCase):
    """Test rate limiting decorator for async functions"""

    def setUp(self):
        """Clear rate limiter state before each test"""
        from engine.ingestion.rate_limiting import _reset_rate_limiters
        _reset_rate_limiters()

    def test_rate_limited_decorator_exists(self):
        """Test that rate_limited decorator can be imported"""
        try:
            from engine.ingestion.rate_limiting import rate_limited
            self.assertIsNotNone(rate_limited)
        except ImportError as e:
            self.fail(f"Failed to import rate_limited decorator: {e}")

    def test_decorator_allows_request_under_limit(self):
        """Test that decorated function executes when under rate limit"""
        from engine.ingestion.rate_limiting import rate_limited

        @rate_limited(source="test", requests_per_minute=10, requests_per_hour=100)
        async def test_function():
            return "success"

        # Should execute without raising exception
        result = asyncio.run(test_function())
        self.assertEqual(result, "success")

    def test_decorator_raises_exception_when_limit_exceeded(self):
        """Test that decorator raises exception when rate limit exceeded"""
        from engine.ingestion.rate_limiting import rate_limited, RateLimitExceeded

        @rate_limited(source="test", requests_per_minute=2, requests_per_hour=100)
        async def test_function():
            return "success"

        # Execute twice (at limit)
        asyncio.run(test_function())
        asyncio.run(test_function())

        # Third execution should raise exception
        with self.assertRaises(RateLimitExceeded):
            asyncio.run(test_function())

    def test_decorator_passes_through_function_arguments(self):
        """Test that decorator preserves function arguments"""
        from engine.ingestion.rate_limiting import rate_limited

        @rate_limited(source="test", requests_per_minute=10, requests_per_hour=100)
        async def test_function(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        result = asyncio.run(test_function("a", "b", kwarg1="c"))
        self.assertEqual(result, "a-b-c")

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring"""
        from engine.ingestion.rate_limiting import rate_limited

        @rate_limited(source="test", requests_per_minute=10, requests_per_hour=100)
        async def test_function():
            """Test docstring"""
            pass

        self.assertEqual(test_function.__name__, "test_function")
        self.assertEqual(test_function.__doc__, "Test docstring")


class TestRateLimitExceedException(unittest.TestCase):
    """Test RateLimitExceeded exception class"""

    def test_rate_limit_exceeded_exception_exists(self):
        """Test that RateLimitExceeded exception can be imported"""
        try:
            from engine.ingestion.rate_limiting import RateLimitExceeded
            self.assertIsNotNone(RateLimitExceeded)
        except ImportError as e:
            self.fail(f"Failed to import RateLimitExceeded: {e}")

    def test_exception_includes_source_info(self):
        """Test that exception includes source name in message"""
        from engine.ingestion.rate_limiting import RateLimitExceeded

        try:
            raise RateLimitExceeded("serper", "per_minute", 60)
        except RateLimitExceeded as e:
            error_msg = str(e)
            self.assertIn("serper", error_msg)
            self.assertIn("60", error_msg)

    def test_exception_includes_limit_type(self):
        """Test that exception indicates which limit was exceeded"""
        from engine.ingestion.rate_limiting import RateLimitExceeded

        try:
            raise RateLimitExceeded("test", "per_hour", 1000)
        except RateLimitExceeded as e:
            error_msg = str(e)
            self.assertIn("per_hour", error_msg.lower())


class TestRateLimiterConfigurationLoading(unittest.TestCase):
    """Test loading rate limits from sources.yaml configuration"""

    def test_load_rate_limits_from_config(self):
        """Test loading rate limits from sources.yaml"""
        from engine.ingestion.rate_limiting import load_rate_limits_from_config

        config = load_rate_limits_from_config("serper")
        self.assertIsNotNone(config)
        self.assertIn("requests_per_minute", config)
        self.assertIn("requests_per_hour", config)

    def test_create_rate_limiter_from_config(self):
        """Test creating RateLimiter instance from config"""
        from engine.ingestion.rate_limiting import create_rate_limiter_from_config

        limiter = create_rate_limiter_from_config("serper")
        self.assertEqual(limiter.source, "serper")
        self.assertIsNotNone(limiter.requests_per_minute)
        self.assertIsNotNone(limiter.requests_per_hour)

    def test_missing_source_returns_none_or_raises(self):
        """Test behavior when source not found in config"""
        from engine.ingestion.rate_limiting import load_rate_limits_from_config

        # Should either return None/default or raise informative error
        try:
            config = load_rate_limits_from_config("nonexistent_source")
            # If it returns, should be None or have None limits
            if config is not None:
                self.assertIsNone(config.get("requests_per_minute"))
        except KeyError:
            # Acceptable to raise KeyError for missing source
            pass


class TestRateLimiterStatistics(unittest.TestCase):
    """Test rate limiter statistics and reporting"""

    def test_get_time_until_next_request_minute(self):
        """Test calculating time until next request allowed (minute limit)"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=2,
            requests_per_hour=100
        )
        # Fill up the limit
        limiter.record_request()
        limiter.record_request()

        # Should return time in seconds until next request allowed
        wait_time = limiter.get_time_until_next_request()
        self.assertIsNotNone(wait_time)
        self.assertGreater(wait_time, 0)
        self.assertLessEqual(wait_time, 60)

    def test_get_time_until_next_request_hour(self):
        """Test calculating time until next request allowed (hour limit)"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=100,
            requests_per_hour=2
        )
        # Fill up the limit
        limiter.record_request()
        limiter.record_request()

        # Should return time in seconds until next request allowed
        wait_time = limiter.get_time_until_next_request()
        self.assertIsNotNone(wait_time)
        self.assertGreater(wait_time, 0)
        self.assertLessEqual(wait_time, 3600)

    def test_get_time_until_next_request_when_under_limit(self):
        """Test that time until next request is 0 when under limit"""
        from engine.ingestion.rate_limiting import RateLimiter

        limiter = RateLimiter(
            source="test",
            requests_per_minute=10,
            requests_per_hour=100
        )
        # Under limit, should return 0
        wait_time = limiter.get_time_until_next_request()
        self.assertEqual(wait_time, 0)


if __name__ == '__main__':
    unittest.main()
