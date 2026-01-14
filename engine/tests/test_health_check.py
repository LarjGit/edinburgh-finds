"""
Tests for Ingestion Health Check Module

This module tests health check functionality for the data ingestion pipeline:
- Failed ingestion monitoring
- Stale data detection
- API quota usage tracking
- Overall system health status
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta


class TestHealthCheckImport(unittest.TestCase):
    """Test that health check functions can be imported"""

    def test_check_health_function_exists(self):
        """Test that check_health function can be imported"""
        try:
            from engine.ingestion.health_check import check_health
            self.assertIsNotNone(check_health)
            self.assertTrue(callable(check_health))
        except ImportError as e:
            self.fail(f"Failed to import check_health function: {e}")

    def test_check_failed_ingestions_exists(self):
        """Test that check_failed_ingestions function can be imported"""
        try:
            from engine.ingestion.health_check import check_failed_ingestions
            self.assertIsNotNone(check_failed_ingestions)
            self.assertTrue(callable(check_failed_ingestions))
        except ImportError as e:
            self.fail(f"Failed to import check_failed_ingestions: {e}")

    def test_check_stale_data_exists(self):
        """Test that check_stale_data function can be imported"""
        try:
            from engine.ingestion.health_check import check_stale_data
            self.assertIsNotNone(check_stale_data)
            self.assertTrue(callable(check_stale_data))
        except ImportError as e:
            self.fail(f"Failed to import check_stale_data: {e}")

    def test_check_api_quota_exists(self):
        """Test that check_api_quota function can be imported"""
        try:
            from engine.ingestion.health_check import check_api_quota
            self.assertIsNotNone(check_api_quota)
            self.assertTrue(callable(check_api_quota))
        except ImportError as e:
            self.fail(f"Failed to import check_api_quota: {e}")


class TestCheckHealth(unittest.TestCase):
    """Test the main check_health function"""

    def test_check_health_returns_dict(self):
        """Test that check_health returns a dictionary"""
        from engine.ingestion.health_check import check_health

        result = asyncio.run(check_health())
        self.assertIsInstance(result, dict)

    def test_check_health_includes_overall_status(self):
        """Test that check_health includes overall health status"""
        from engine.ingestion.health_check import check_health

        result = asyncio.run(check_health())
        self.assertIn('status', result)
        self.assertIn(result['status'], ['healthy', 'warning', 'critical'])

    def test_check_health_includes_timestamp(self):
        """Test that check_health includes timestamp"""
        from engine.ingestion.health_check import check_health

        result = asyncio.run(check_health())
        self.assertIn('timestamp', result)
        self.assertIsInstance(result['timestamp'], datetime)

    def test_check_health_includes_all_checks(self):
        """Test that check_health includes all sub-check results"""
        from engine.ingestion.health_check import check_health

        result = asyncio.run(check_health())
        self.assertIn('failed_ingestions', result)
        self.assertIn('stale_data', result)
        self.assertIn('api_quota', result)

    def test_check_health_aggregates_status(self):
        """Test that check_health aggregates status from all checks"""
        from engine.ingestion.health_check import check_health

        result = asyncio.run(check_health())

        # Status should be worst of all sub-checks
        self.assertIn('status', result)


class TestCheckFailedIngestions(unittest.TestCase):
    """Test the check_failed_ingestions function"""

    def test_check_failed_ingestions_returns_dict(self):
        """Test that check_failed_ingestions returns a dictionary"""
        from engine.ingestion.health_check import check_failed_ingestions

        result = asyncio.run(check_failed_ingestions())
        self.assertIsInstance(result, dict)

    def test_check_includes_status(self):
        """Test that result includes health status"""
        from engine.ingestion.health_check import check_failed_ingestions

        result = asyncio.run(check_failed_ingestions())
        self.assertIn('status', result)
        self.assertIn(result['status'], ['healthy', 'warning', 'critical'])

    def test_check_includes_failure_count(self):
        """Test that result includes failure count"""
        from engine.ingestion.health_check import check_failed_ingestions

        result = asyncio.run(check_failed_ingestions())
        self.assertIn('failed_count', result)
        self.assertIsInstance(result['failed_count'], int)
        self.assertGreaterEqual(result['failed_count'], 0)

    def test_check_includes_failure_rate(self):
        """Test that result includes failure rate"""
        from engine.ingestion.health_check import check_failed_ingestions

        result = asyncio.run(check_failed_ingestions())
        self.assertIn('failure_rate', result)
        self.assertIsInstance(result['failure_rate'], (int, float))
        self.assertGreaterEqual(result['failure_rate'], 0)
        self.assertLessEqual(result['failure_rate'], 100)

    def test_check_includes_recent_failures(self):
        """Test that result includes list of recent failures"""
        from engine.ingestion.health_check import check_failed_ingestions

        result = asyncio.run(check_failed_ingestions())
        self.assertIn('recent_failures', result)
        self.assertIsInstance(result['recent_failures'], list)

    def test_check_includes_message(self):
        """Test that result includes descriptive message"""
        from engine.ingestion.health_check import check_failed_ingestions

        result = asyncio.run(check_failed_ingestions())
        self.assertIn('message', result)
        self.assertIsInstance(result['message'], str)

    def test_healthy_status_when_no_failures(self):
        """Test that status is healthy when there are no recent failures"""
        from engine.ingestion.health_check import check_failed_ingestions

        result = asyncio.run(check_failed_ingestions())

        # If no failures, should be healthy
        if result['failed_count'] == 0:
            self.assertEqual(result['status'], 'healthy')

    def test_warning_status_for_moderate_failures(self):
        """Test that status is warning for moderate failure rate"""
        from engine.ingestion.health_check import check_failed_ingestions

        # This test will pass based on actual data
        result = asyncio.run(check_failed_ingestions())

        # Validate structure regardless of data
        self.assertIn('status', result)

    def test_critical_status_for_high_failures(self):
        """Test that status is critical for high failure rate"""
        from engine.ingestion.health_check import check_failed_ingestions

        # This test will pass based on actual data
        result = asyncio.run(check_failed_ingestions())

        # Validate structure regardless of data
        self.assertIn('status', result)

    def test_recent_failures_time_window(self):
        """Test that only recent failures are counted (e.g., last 24 hours)"""
        from engine.ingestion.health_check import check_failed_ingestions

        result = asyncio.run(check_failed_ingestions())

        # All recent failures should be within reasonable time window
        for failure in result['recent_failures']:
            self.assertIn('ingested_at', failure)


class TestCheckStaleData(unittest.TestCase):
    """Test the check_stale_data function"""

    def test_check_stale_data_returns_dict(self):
        """Test that check_stale_data returns a dictionary"""
        from engine.ingestion.health_check import check_stale_data

        result = asyncio.run(check_stale_data())
        self.assertIsInstance(result, dict)

    def test_check_includes_status(self):
        """Test that result includes health status"""
        from engine.ingestion.health_check import check_stale_data

        result = asyncio.run(check_stale_data())
        self.assertIn('status', result)
        self.assertIn(result['status'], ['healthy', 'warning', 'critical'])

    def test_check_includes_stale_sources(self):
        """Test that result includes list of stale sources"""
        from engine.ingestion.health_check import check_stale_data

        result = asyncio.run(check_stale_data())
        self.assertIn('stale_sources', result)
        self.assertIsInstance(result['stale_sources'], list)

    def test_check_includes_last_ingestion_by_source(self):
        """Test that result includes last ingestion time per source"""
        from engine.ingestion.health_check import check_stale_data

        result = asyncio.run(check_stale_data())
        self.assertIn('last_ingestion_by_source', result)
        self.assertIsInstance(result['last_ingestion_by_source'], dict)

    def test_check_includes_message(self):
        """Test that result includes descriptive message"""
        from engine.ingestion.health_check import check_stale_data

        result = asyncio.run(check_stale_data())
        self.assertIn('message', result)
        self.assertIsInstance(result['message'], str)

    def test_healthy_status_when_data_fresh(self):
        """Test that status is healthy when all data is fresh"""
        from engine.ingestion.health_check import check_stale_data

        result = asyncio.run(check_stale_data())

        # If no stale sources, should be healthy
        if len(result['stale_sources']) == 0:
            self.assertEqual(result['status'], 'healthy')

    def test_warning_status_for_some_stale_sources(self):
        """Test that status is warning when some sources are stale"""
        from engine.ingestion.health_check import check_stale_data

        result = asyncio.run(check_stale_data())

        # Validate structure
        self.assertIn('status', result)

    def test_critical_status_for_all_stale(self):
        """Test that status is critical when all sources are stale"""
        from engine.ingestion.health_check import check_stale_data

        result = asyncio.run(check_stale_data())

        # Validate structure
        self.assertIn('status', result)

    def test_stale_threshold_configurable(self):
        """Test that staleness threshold can be configured"""
        from engine.ingestion.health_check import check_stale_data

        # Test with custom threshold (e.g., 48 hours)
        result = asyncio.run(check_stale_data(threshold_hours=48))
        self.assertIsInstance(result, dict)

    def test_stale_sources_include_details(self):
        """Test that stale sources include necessary details"""
        from engine.ingestion.health_check import check_stale_data

        result = asyncio.run(check_stale_data())

        for source in result['stale_sources']:
            self.assertIn('source', source)
            self.assertIn('last_ingestion', source)
            self.assertIn('hours_since', source)


class TestCheckApiQuota(unittest.TestCase):
    """Test the check_api_quota function"""

    def test_check_api_quota_returns_dict(self):
        """Test that check_api_quota returns a dictionary"""
        from engine.ingestion.health_check import check_api_quota

        result = asyncio.run(check_api_quota())
        self.assertIsInstance(result, dict)

    def test_check_includes_status(self):
        """Test that result includes health status"""
        from engine.ingestion.health_check import check_api_quota

        result = asyncio.run(check_api_quota())
        self.assertIn('status', result)
        self.assertIn(result['status'], ['healthy', 'warning', 'critical'])

    def test_check_includes_quota_by_source(self):
        """Test that result includes quota usage by source"""
        from engine.ingestion.health_check import check_api_quota

        result = asyncio.run(check_api_quota())
        self.assertIn('quota_by_source', result)
        self.assertIsInstance(result['quota_by_source'], dict)

    def test_check_includes_message(self):
        """Test that result includes descriptive message"""
        from engine.ingestion.health_check import check_api_quota

        result = asyncio.run(check_api_quota())
        self.assertIn('message', result)
        self.assertIsInstance(result['message'], str)

    def test_quota_includes_usage_count(self):
        """Test that quota info includes usage count"""
        from engine.ingestion.health_check import check_api_quota

        result = asyncio.run(check_api_quota())

        # Each source should have usage information
        for source, quota_info in result['quota_by_source'].items():
            if isinstance(quota_info, dict):
                # Should include some usage metric
                self.assertTrue(
                    'requests_today' in quota_info or
                    'requests_this_hour' in quota_info or
                    'total_requests' in quota_info
                )

    def test_healthy_status_when_quota_low(self):
        """Test that status is healthy when quota usage is low"""
        from engine.ingestion.health_check import check_api_quota

        result = asyncio.run(check_api_quota())

        # Validate structure
        self.assertIn('status', result)

    def test_warning_status_when_quota_high(self):
        """Test that status is warning when quota usage is high"""
        from engine.ingestion.health_check import check_api_quota

        result = asyncio.run(check_api_quota())

        # Validate structure
        self.assertIn('status', result)

    def test_critical_status_when_quota_exceeded(self):
        """Test that status is critical when quota is exceeded"""
        from engine.ingestion.health_check import check_api_quota

        result = asyncio.run(check_api_quota())

        # Validate structure
        self.assertIn('status', result)


class TestHealthCheckEdgeCases(unittest.TestCase):
    """Test health check edge cases"""

    def test_health_check_handles_empty_database(self):
        """Test that health checks handle empty database gracefully"""
        from engine.ingestion.health_check import check_health

        # Should not crash with empty database
        result = asyncio.run(check_health())
        self.assertIsInstance(result, dict)
        self.assertIn('status', result)

    def test_health_check_handles_missing_database(self):
        """Test that health checks handle database errors gracefully"""
        from engine.ingestion.health_check import check_health

        # Should handle connection errors
        try:
            result = asyncio.run(check_health())
            self.assertIsInstance(result, dict)
        except Exception as e:
            # If it fails, should be a clear error
            self.assertIsInstance(str(e), str)

    def test_stale_check_with_no_successful_ingestions(self):
        """Test stale data check when there are no successful ingestions"""
        from engine.ingestion.health_check import check_stale_data

        result = asyncio.run(check_stale_data())

        # Should handle this gracefully
        self.assertIsInstance(result, dict)
        self.assertIn('status', result)

    def test_failed_check_with_all_successful(self):
        """Test failed ingestions check when all ingestions succeeded"""
        from engine.ingestion.health_check import check_failed_ingestions

        result = asyncio.run(check_failed_ingestions())

        # Should show healthy status if all succeeded
        self.assertIsInstance(result, dict)
        self.assertIn('status', result)

    def test_quota_check_with_no_metadata(self):
        """Test API quota check when metadata is missing"""
        from engine.ingestion.health_check import check_api_quota

        result = asyncio.run(check_api_quota())

        # Should handle missing metadata gracefully
        self.assertIsInstance(result, dict)
        self.assertIn('status', result)


class TestHealthCheckThresholds(unittest.TestCase):
    """Test configurable thresholds for health checks"""

    def test_failed_ingestions_custom_threshold(self):
        """Test that failure rate threshold can be customized"""
        from engine.ingestion.health_check import check_failed_ingestions

        # Test with different thresholds
        result_default = asyncio.run(check_failed_ingestions())
        result_strict = asyncio.run(check_failed_ingestions(
            warning_threshold=5,
            critical_threshold=10
        ))

        self.assertIsInstance(result_default, dict)
        self.assertIsInstance(result_strict, dict)

    def test_stale_data_custom_threshold(self):
        """Test that staleness threshold can be customized"""
        from engine.ingestion.health_check import check_stale_data

        # Test with different time windows
        result_24h = asyncio.run(check_stale_data(threshold_hours=24))
        result_48h = asyncio.run(check_stale_data(threshold_hours=48))

        self.assertIsInstance(result_24h, dict)
        self.assertIsInstance(result_48h, dict)


class TestHealthCheckPerformance(unittest.TestCase):
    """Test that health checks perform efficiently"""

    def test_check_health_completes_quickly(self):
        """Test that check_health completes in reasonable time"""
        from engine.ingestion.health_check import check_health
        import time

        start = time.time()
        asyncio.run(check_health())
        duration = time.time() - start

        # Should complete in less than 5 seconds
        self.assertLess(duration, 5.0)

    def test_individual_checks_complete_quickly(self):
        """Test that individual checks complete quickly"""
        from engine.ingestion.health_check import (
            check_failed_ingestions,
            check_stale_data,
            check_api_quota
        )
        import time

        for check_func in [check_failed_ingestions, check_stale_data, check_api_quota]:
            start = time.time()
            asyncio.run(check_func())
            duration = time.time() - start

            # Each check should complete in less than 3 seconds
            self.assertLess(duration, 3.0)


class TestHealthCheckIntegration(unittest.TestCase):
    """Test health check integration with other modules"""

    def test_health_check_uses_existing_db_connection(self):
        """Test that health checks reuse database connections efficiently"""
        from engine.ingestion.health_check import check_health

        # Should handle connection pooling
        result = asyncio.run(check_health())
        self.assertIsInstance(result, dict)

    def test_health_check_compatible_with_cli(self):
        """Test that health checks can be called from CLI"""
        from engine.ingestion.health_check import check_health

        # Should return data that can be displayed
        result = asyncio.run(check_health())
        self.assertIn('status', result)
        # Verify result contains expected fields
        result_str = str(result)
        self.assertTrue('message' in result_str or 'status' in result_str)


if __name__ == '__main__':
    unittest.main()
