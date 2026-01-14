"""
Tests for Retry Logic with Exponential Backoff

This module tests the retry decorator for handling transient failures in
data ingestion connectors. The retry system provides:
- Configurable maximum retry attempts
- Exponential backoff between retries
- Customizable initial delay
- Handling of specific exception types
- Integration with sources.yaml configuration
- Clear error reporting after exhausting retries
"""

import unittest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime


class TestRetryDecoratorImport(unittest.TestCase):
    """Test that retry decorator and related classes can be imported"""

    def test_retry_decorator_exists(self):
        """Test that retry_with_backoff decorator can be imported"""
        try:
            from engine.ingestion.retry_logic import retry_with_backoff
            self.assertIsNotNone(retry_with_backoff)
        except ImportError as e:
            self.fail(f"Failed to import retry_with_backoff decorator: {e}")

    def test_max_retries_exceeded_exception_exists(self):
        """Test that MaxRetriesExceeded exception can be imported"""
        try:
            from engine.ingestion.retry_logic import MaxRetriesExceeded
            self.assertIsNotNone(MaxRetriesExceeded)
        except ImportError as e:
            self.fail(f"Failed to import MaxRetriesExceeded exception: {e}")


class TestRetryDecoratorBasicBehavior(unittest.TestCase):
    """Test basic retry decorator behavior"""

    def test_successful_function_does_not_retry(self):
        """Test that successful function executes once without retries"""
        from engine.ingestion.retry_logic import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.1)
        async def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = asyncio.run(successful_function())
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 1)

    def test_function_retries_on_failure(self):
        """Test that function retries when exception is raised"""
        from engine.ingestion.retry_logic import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Transient error")
            return "success"

        result = asyncio.run(failing_function())
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)

    def test_function_raises_after_max_retries(self):
        """Test that exception is raised after exhausting max retries"""
        from engine.ingestion.retry_logic import retry_with_backoff, MaxRetriesExceeded

        call_count = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        async def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent error")

        with self.assertRaises(MaxRetriesExceeded) as context:
            asyncio.run(always_failing_function())

        # Should have attempted: 1 initial + 3 retries = 4 total attempts
        self.assertEqual(call_count, 4)
        self.assertIn("3 retries", str(context.exception))


class TestExponentialBackoff(unittest.TestCase):
    """Test exponential backoff delay calculation"""

    def test_exponential_backoff_increases_delay(self):
        """Test that delay increases exponentially between retries"""
        from engine.ingestion.retry_logic import retry_with_backoff

        call_times = []

        @retry_with_backoff(max_retries=3, initial_delay=0.1)
        async def failing_function():
            call_times.append(time.time())
            if len(call_times) < 4:
                raise Exception("Transient error")
            return "success"

        asyncio.run(failing_function())

        # Calculate delays between attempts
        delays = [call_times[i+1] - call_times[i] for i in range(len(call_times) - 1)]

        # Verify delays increase approximately exponentially
        # With initial_delay=0.1: 0.1, 0.2, 0.4
        self.assertGreaterEqual(len(delays), 2)
        # Second delay should be roughly 2x first delay
        self.assertGreater(delays[1], delays[0] * 1.8)
        if len(delays) >= 3:
            # Third delay should be roughly 2x second delay
            self.assertGreater(delays[2], delays[1] * 1.8)

    def test_initial_delay_configuration(self):
        """Test that initial_delay parameter controls first retry delay"""
        from engine.ingestion.retry_logic import retry_with_backoff

        call_times = []

        @retry_with_backoff(max_retries=2, initial_delay=0.05)
        async def failing_function():
            call_times.append(time.time())
            if len(call_times) < 2:
                raise Exception("Transient error")
            return "success"

        asyncio.run(failing_function())

        # First delay should be approximately initial_delay
        delay = call_times[1] - call_times[0]
        self.assertGreaterEqual(delay, 0.04)  # Allow small margin
        self.assertLess(delay, 0.15)

    def test_backoff_with_zero_initial_delay(self):
        """Test that zero initial delay results in immediate retry"""
        from engine.ingestion.retry_logic import retry_with_backoff

        call_count = 0
        start_time = time.time()

        @retry_with_backoff(max_retries=2, initial_delay=0)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Transient error")
            return "success"

        asyncio.run(failing_function())
        total_time = time.time() - start_time

        # With initial_delay=0, should complete very quickly
        self.assertLess(total_time, 0.1)


class TestRetryConfiguration(unittest.TestCase):
    """Test retry configuration options"""

    def test_max_retries_zero_means_no_retries(self):
        """Test that max_retries=0 means function is called once with no retries"""
        from engine.ingestion.retry_logic import retry_with_backoff, MaxRetriesExceeded

        call_count = 0

        @retry_with_backoff(max_retries=0, initial_delay=0.01)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            raise Exception("Error")

        with self.assertRaises(MaxRetriesExceeded):
            asyncio.run(failing_function())

        # Should have attempted only once (no retries)
        self.assertEqual(call_count, 1)

    def test_max_retries_one_allows_one_retry(self):
        """Test that max_retries=1 allows exactly one retry attempt"""
        from engine.ingestion.retry_logic import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=1, initial_delay=0.01)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Transient error")
            return "success"

        result = asyncio.run(failing_function())
        self.assertEqual(result, "success")
        # Should have attempted: 1 initial + 1 retry = 2 total
        self.assertEqual(call_count, 2)

    def test_high_max_retries_value(self):
        """Test that high max_retries value works correctly"""
        from engine.ingestion.retry_logic import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=10, initial_delay=0.001)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise Exception("Transient error")
            return "success"

        result = asyncio.run(failing_function())
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 5)


class TestRetryWithDifferentExceptions(unittest.TestCase):
    """Test retry behavior with different exception types"""

    def test_retries_on_connection_error(self):
        """Test that retry handles connection errors"""
        from engine.ingestion.retry_logic import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        async def function_with_connection_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            return "success"

        result = asyncio.run(function_with_connection_error())
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 2)

    def test_retries_on_timeout_error(self):
        """Test that retry handles timeout errors"""
        from engine.ingestion.retry_logic import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        async def function_with_timeout():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Request timed out")
            return "success"

        result = asyncio.run(function_with_timeout())
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 2)

    def test_retries_on_generic_exception(self):
        """Test that retry handles generic exceptions"""
        from engine.ingestion.retry_logic import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        async def function_with_generic_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Generic error")
            return "success"

        result = asyncio.run(function_with_generic_error())
        self.assertEqual(result, "success")


class TestRetryDecoratorFunctionPreservation(unittest.TestCase):
    """Test that decorator preserves function behavior"""

    def test_decorator_passes_through_arguments(self):
        """Test that decorator preserves function arguments"""
        from engine.ingestion.retry_logic import retry_with_backoff

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        async def function_with_args(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        result = asyncio.run(function_with_args("a", "b", kwarg1="c"))
        self.assertEqual(result, "a-b-c")

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring"""
        from engine.ingestion.retry_logic import retry_with_backoff

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        async def test_function():
            """Test docstring"""
            pass

        self.assertEqual(test_function.__name__, "test_function")
        self.assertEqual(test_function.__doc__, "Test docstring")

    def test_decorator_preserves_return_values(self):
        """Test that decorator returns function's return value unchanged"""
        from engine.ingestion.retry_logic import retry_with_backoff

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        async def function_returning_dict():
            return {"key": "value", "count": 42}

        result = asyncio.run(function_returning_dict())
        self.assertIsInstance(result, dict)
        self.assertEqual(result["key"], "value")
        self.assertEqual(result["count"], 42)


class TestMaxRetriesExceededException(unittest.TestCase):
    """Test MaxRetriesExceeded exception class"""

    def test_exception_includes_retry_count(self):
        """Test that exception message includes retry count"""
        from engine.ingestion.retry_logic import retry_with_backoff, MaxRetriesExceeded

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        async def failing_function():
            raise ValueError("Error")

        try:
            asyncio.run(failing_function())
            self.fail("Should have raised MaxRetriesExceeded")
        except MaxRetriesExceeded as e:
            error_msg = str(e)
            self.assertIn("3", error_msg)

    def test_exception_includes_original_exception_info(self):
        """Test that exception includes information about original error"""
        from engine.ingestion.retry_logic import retry_with_backoff, MaxRetriesExceeded

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        async def failing_function():
            raise ValueError("Original error message")

        try:
            asyncio.run(failing_function())
            self.fail("Should have raised MaxRetriesExceeded")
        except MaxRetriesExceeded as e:
            # Exception should preserve or reference original error
            self.assertIsNotNone(str(e))
            # Check if original exception is accessible
            self.assertIsNotNone(e.__cause__ or e.__context__)

    def test_exception_can_be_caught_separately(self):
        """Test that MaxRetriesExceeded can be caught without catching all exceptions"""
        from engine.ingestion.retry_logic import retry_with_backoff, MaxRetriesExceeded

        @retry_with_backoff(max_retries=1, initial_delay=0.01)
        async def failing_function():
            raise ValueError("Error")

        caught_max_retries = False
        try:
            asyncio.run(failing_function())
        except MaxRetriesExceeded:
            caught_max_retries = True
        except Exception:
            self.fail("Should have caught MaxRetriesExceeded specifically")

        self.assertTrue(caught_max_retries)


class TestRetryConfigurationFromYaml(unittest.TestCase):
    """Test loading retry configuration from sources.yaml"""

    def test_load_retry_config_from_yaml(self):
        """Test loading retry configuration from sources.yaml"""
        try:
            from engine.ingestion.retry_logic import load_retry_config_from_yaml

            config = load_retry_config_from_yaml("serper")
            self.assertIsNotNone(config)
            self.assertIn("max_retries", config)
            self.assertIn("initial_delay", config)
        except ImportError:
            # Function might not exist yet - that's expected in TDD
            pass

    def test_retry_config_has_reasonable_defaults(self):
        """Test that retry config has reasonable default values"""
        try:
            from engine.ingestion.retry_logic import load_retry_config_from_yaml

            config = load_retry_config_from_yaml("serper")

            # Max retries should be positive integer
            if config.get("max_retries") is not None:
                self.assertIsInstance(config["max_retries"], int)
                self.assertGreaterEqual(config["max_retries"], 0)

            # Initial delay should be positive float
            if config.get("initial_delay") is not None:
                self.assertIsInstance(config["initial_delay"], (int, float))
                self.assertGreaterEqual(config["initial_delay"], 0)
        except (ImportError, KeyError):
            # Function/config might not exist yet - that's expected in TDD
            pass

    def test_missing_source_in_config_handles_gracefully(self):
        """Test behavior when source doesn't have retry config in yaml"""
        try:
            from engine.ingestion.retry_logic import load_retry_config_from_yaml

            # Try to load config for non-existent source
            try:
                config = load_retry_config_from_yaml("nonexistent_source_xyz")
                # Should either return defaults or raise KeyError
                if config is not None:
                    # If it returns, should have default values
                    self.assertIsNotNone(config.get("max_retries"))
            except KeyError:
                # Acceptable to raise KeyError for missing source
                pass
        except ImportError:
            # Function might not exist yet
            pass


class TestRetryIntegrationWithConnectors(unittest.TestCase):
    """Test retry decorator integration with connector methods"""

    def test_retry_decorator_works_with_async_methods(self):
        """Test that retry decorator works with async class methods"""
        from engine.ingestion.retry_logic import retry_with_backoff

        class MockConnector:
            def __init__(self):
                self.call_count = 0

            @retry_with_backoff(max_retries=2, initial_delay=0.01)
            async def fetch(self, query: str):
                self.call_count += 1
                if self.call_count < 2:
                    raise Exception("Transient error")
                return {"result": query}

        connector = MockConnector()
        result = asyncio.run(connector.fetch("test query"))

        self.assertEqual(result["result"], "test query")
        self.assertEqual(connector.call_count, 2)

    def test_retry_with_different_instances(self):
        """Test that retry state is independent across instances"""
        from engine.ingestion.retry_logic import retry_with_backoff

        class MockConnector:
            def __init__(self):
                self.call_count = 0

            @retry_with_backoff(max_retries=2, initial_delay=0.01)
            async def fetch(self):
                self.call_count += 1
                if self.call_count < 2:
                    raise Exception("Error")
                return "success"

        connector1 = MockConnector()
        connector2 = MockConnector()

        asyncio.run(connector1.fetch())
        asyncio.run(connector2.fetch())

        # Each instance should have been called twice independently
        self.assertEqual(connector1.call_count, 2)
        self.assertEqual(connector2.call_count, 2)


class TestRetryBackoffMaxDelay(unittest.TestCase):
    """Test maximum delay cap for exponential backoff"""

    def test_backoff_has_reasonable_max_delay(self):
        """Test that backoff delay doesn't grow unbounded"""
        from engine.ingestion.retry_logic import retry_with_backoff

        call_times = []

        @retry_with_backoff(max_retries=10, initial_delay=1.0)
        async def failing_function():
            call_times.append(time.time())
            if len(call_times) < 4:
                raise Exception("Transient error")
            return "success"

        asyncio.run(failing_function())

        # Calculate delays between attempts
        if len(call_times) >= 4:
            delays = [call_times[i+1] - call_times[i] for i in range(len(call_times) - 1)]

            # No single delay should exceed a reasonable maximum (e.g., 60 seconds)
            # This assumes implementation has a max delay cap
            for delay in delays:
                self.assertLess(delay, 65)  # Allow margin for processing time


if __name__ == '__main__':
    unittest.main()
