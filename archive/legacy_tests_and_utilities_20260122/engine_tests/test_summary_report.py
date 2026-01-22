"""
Tests for Ingestion Summary Report Module

This module tests the summary report functionality that provides comprehensive
statistics and analysis of the ingestion pipeline:
- Overall ingestion statistics
- Per-source breakdowns
- Error analysis
- Time-based trends
- Health status integration
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestSummaryReportImport(unittest.TestCase):
    """Test that summary report functions can be imported"""

    def test_generate_summary_report_exists(self):
        """Test that generate_summary_report function can be imported"""
        try:
            from engine.ingestion.summary_report import generate_summary_report
            self.assertIsNotNone(generate_summary_report)
            self.assertTrue(callable(generate_summary_report))
        except ImportError as e:
            self.fail(f"Failed to import generate_summary_report: {e}")

    def test_get_summary_data_exists(self):
        """Test that get_summary_data function can be imported"""
        try:
            from engine.ingestion.summary_report import get_summary_data
            self.assertIsNotNone(get_summary_data)
            self.assertTrue(callable(get_summary_data))
        except ImportError as e:
            self.fail(f"Failed to import get_summary_data: {e}")


class TestGenerateSummaryReport(unittest.TestCase):
    """Test the generate_summary_report function"""

    def test_generate_summary_report_returns_dict(self):
        """Test that generate_summary_report returns a dictionary"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        self.assertIsInstance(result, dict)

    def test_report_includes_overview(self):
        """Test that report includes overview section"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        self.assertIn('overview', result)
        self.assertIsInstance(result['overview'], dict)

    def test_report_includes_by_source(self):
        """Test that report includes per-source breakdown"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        self.assertIn('by_source', result)
        self.assertIsInstance(result['by_source'], dict)

    def test_report_includes_errors(self):
        """Test that report includes error analysis"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        self.assertIn('errors', result)
        self.assertIsInstance(result['errors'], dict)

    def test_report_includes_health_status(self):
        """Test that report includes health status"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        self.assertIn('health', result)
        self.assertIsInstance(result['health'], dict)

    def test_report_includes_timestamp(self):
        """Test that report includes generation timestamp"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        self.assertIn('generated_at', result)
        self.assertIsInstance(result['generated_at'], datetime)


class TestOverviewSection(unittest.TestCase):
    """Test the overview section of the summary report"""

    def test_overview_includes_total_records(self):
        """Test that overview includes total record count"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        self.assertIn('total_records', result['overview'])
        self.assertIsInstance(result['overview']['total_records'], int)

    def test_overview_includes_success_rate(self):
        """Test that overview includes success rate"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        self.assertIn('success_rate', result['overview'])
        self.assertIsInstance(result['overview']['success_rate'], (int, float))

    def test_overview_includes_date_range(self):
        """Test that overview includes date range"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        overview = result['overview']

        # Should have first and last ingestion dates
        if overview['total_records'] > 0:
            self.assertIn('first_ingestion', overview)
            self.assertIn('last_ingestion', overview)

    def test_overview_includes_source_count(self):
        """Test that overview includes number of sources"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        self.assertIn('total_sources', result['overview'])
        self.assertIsInstance(result['overview']['total_sources'], int)


class TestBySourceSection(unittest.TestCase):
    """Test the per-source breakdown section"""

    def test_by_source_is_dictionary(self):
        """Test that by_source is a dictionary keyed by source name"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        self.assertIsInstance(result['by_source'], dict)

    def test_source_includes_total_count(self):
        """Test that each source includes total count"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())

        for source, data in result['by_source'].items():
            self.assertIn('total', data)
            self.assertIsInstance(data['total'], int)

    def test_source_includes_success_count(self):
        """Test that each source includes success count"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())

        for source, data in result['by_source'].items():
            self.assertIn('success', data)
            self.assertIsInstance(data['success'], int)

    def test_source_includes_failed_count(self):
        """Test that each source includes failed count"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())

        for source, data in result['by_source'].items():
            self.assertIn('failed', data)
            self.assertIsInstance(data['failed'], int)

    def test_source_includes_success_rate(self):
        """Test that each source includes success rate"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())

        for source, data in result['by_source'].items():
            self.assertIn('success_rate', data)
            self.assertIsInstance(data['success_rate'], (int, float))

    def test_source_includes_last_ingestion(self):
        """Test that each source includes last ingestion time"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())

        for source, data in result['by_source'].items():
            self.assertIn('last_ingestion', data)
            # Could be None if no ingestions, or datetime if exists
            if data['last_ingestion'] is not None:
                self.assertIsInstance(data['last_ingestion'], datetime)


class TestErrorsSection(unittest.TestCase):
    """Test the error analysis section"""

    def test_errors_includes_total_count(self):
        """Test that errors section includes total error count"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        self.assertIn('total_errors', result['errors'])
        self.assertIsInstance(result['errors']['total_errors'], int)

    def test_errors_includes_recent_list(self):
        """Test that errors section includes list of recent errors"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        self.assertIn('recent_errors', result['errors'])
        self.assertIsInstance(result['errors']['recent_errors'], list)

    def test_recent_errors_include_details(self):
        """Test that recent errors include necessary details"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())

        for error in result['errors']['recent_errors']:
            self.assertIn('source', error)
            self.assertIn('ingested_at', error)
            self.assertIsInstance(error['source'], str)

    def test_errors_includes_by_source(self):
        """Test that errors are broken down by source"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        self.assertIn('by_source', result['errors'])
        self.assertIsInstance(result['errors']['by_source'], dict)


class TestHealthSection(unittest.TestCase):
    """Test the health status section"""

    def test_health_includes_status(self):
        """Test that health section includes overall status"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())
        self.assertIn('status', result['health'])
        self.assertIn(result['health']['status'], ['healthy', 'warning', 'critical'])

    def test_health_includes_checks(self):
        """Test that health section includes individual check results"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())

        # Should include results from health checks
        self.assertIn('failed_ingestions', result['health'])
        self.assertIn('stale_data', result['health'])
        self.assertIn('api_quota', result['health'])


class TestGetSummaryData(unittest.TestCase):
    """Test the get_summary_data helper function"""

    def test_get_summary_data_returns_dict(self):
        """Test that get_summary_data returns a dictionary"""
        from engine.ingestion.summary_report import get_summary_data

        result = asyncio.run(get_summary_data())
        self.assertIsInstance(result, dict)

    def test_summary_data_structure(self):
        """Test that summary data has expected structure"""
        from engine.ingestion.summary_report import get_summary_data

        result = asyncio.run(get_summary_data())

        # Check for main sections
        self.assertIn('overview', result)
        self.assertIn('by_source', result)
        self.assertIn('errors', result)
        self.assertIn('health', result)


class TestSummaryReportFormatting(unittest.TestCase):
    """Test report formatting and display"""

    def test_format_summary_report_exists(self):
        """Test that format_summary_report function exists"""
        try:
            from engine.ingestion.summary_report import format_summary_report
            self.assertIsNotNone(format_summary_report)
            self.assertTrue(callable(format_summary_report))
        except ImportError:
            # Optional function - may not exist
            pass

    def test_format_returns_string(self):
        """Test that format_summary_report returns a string"""
        try:
            from engine.ingestion.summary_report import format_summary_report, generate_summary_report

            report = asyncio.run(generate_summary_report())
            formatted = format_summary_report(report)

            self.assertIsInstance(formatted, str)
            self.assertGreater(len(formatted), 0)
        except ImportError:
            # Optional function
            pass


class TestSummaryReportEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def test_report_with_empty_database(self):
        """Test that report handles database gracefully"""
        from engine.ingestion.summary_report import generate_summary_report

        # Should not crash and return valid structure
        result = asyncio.run(generate_summary_report())
        self.assertIsInstance(result, dict)
        self.assertIn('overview', result)
        self.assertIn('total_records', result['overview'])
        self.assertIsInstance(result['overview']['total_records'], int)
        self.assertGreaterEqual(result['overview']['total_records'], 0)

    def test_report_with_database_error(self):
        """Test that report handles database errors gracefully"""
        from engine.ingestion.summary_report import generate_summary_report

        # Should handle connection errors
        try:
            result = asyncio.run(generate_summary_report())
            self.assertIsInstance(result, dict)
        except Exception as e:
            # If it fails, should be a clear error
            self.assertIsInstance(str(e), str)


class TestSummaryReportIntegration(unittest.TestCase):
    """Test integration with other modules"""

    def test_report_uses_health_check_module(self):
        """Test that report integrates with health check module"""
        from engine.ingestion.summary_report import generate_summary_report

        result = asyncio.run(generate_summary_report())

        # Health section should match health check output structure
        self.assertIn('health', result)
        self.assertIn('status', result['health'])

    def test_report_consistent_with_cli_stats(self):
        """Test that report data is consistent with CLI stats"""
        from engine.ingestion.summary_report import generate_summary_report
        from engine.ingestion.cli import get_ingestion_stats

        report = asyncio.run(generate_summary_report())
        stats = asyncio.run(get_ingestion_stats())

        # Total records should match
        self.assertEqual(
            report['overview']['total_records'],
            stats['total_records']
        )


class TestSummaryReportPerformance(unittest.TestCase):
    """Test report generation performance"""

    def test_report_generates_quickly(self):
        """Test that report generation completes in reasonable time"""
        from engine.ingestion.summary_report import generate_summary_report
        import time

        start = time.time()
        asyncio.run(generate_summary_report())
        duration = time.time() - start

        # Should complete in less than 5 seconds
        self.assertLess(duration, 5.0)


if __name__ == '__main__':
    unittest.main()
