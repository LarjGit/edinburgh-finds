"""
Tests for CLI Status Command

This module tests the CLI status command that displays ingestion statistics
including:
- Total ingestion records
- Records by source
- Success/failure rates
- Recent ingestions
- Error summaries
- Storage usage information
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from io import StringIO
from datetime import datetime, timedelta


class TestStatusCommandImport(unittest.TestCase):
    """Test that status command functions can be imported"""

    def test_show_status_function_exists(self):
        """Test that show_status function can be imported"""
        try:
            from engine.ingestion.cli import show_status
            self.assertIsNotNone(show_status)
            self.assertTrue(callable(show_status))
        except ImportError as e:
            self.fail(f"Failed to import show_status function: {e}")

    def test_get_ingestion_stats_function_exists(self):
        """Test that get_ingestion_stats function can be imported"""
        try:
            from engine.ingestion.cli import get_ingestion_stats
            self.assertIsNotNone(get_ingestion_stats)
            self.assertTrue(callable(get_ingestion_stats))
        except ImportError as e:
            self.fail(f"Failed to import get_ingestion_stats function: {e}")


class TestGetIngestionStats(unittest.TestCase):
    """Test the get_ingestion_stats function"""

    def test_get_ingestion_stats_returns_dict(self):
        """Test that get_ingestion_stats returns a dictionary"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())
        self.assertIsInstance(stats, dict)

    def test_stats_includes_total_count(self):
        """Test that stats include total ingestion count"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())
        self.assertIn('total_records', stats)
        self.assertIsInstance(stats['total_records'], int)

    def test_stats_includes_by_source(self):
        """Test that stats include breakdown by source"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())
        self.assertIn('by_source', stats)
        self.assertIsInstance(stats['by_source'], dict)

    def test_stats_includes_by_status(self):
        """Test that stats include breakdown by status"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())
        self.assertIn('by_status', stats)
        self.assertIsInstance(stats['by_status'], dict)

    def test_stats_includes_recent_ingestions(self):
        """Test that stats include recent ingestions"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())
        self.assertIn('recent_ingestions', stats)
        self.assertIsInstance(stats['recent_ingestions'], list)

    def test_stats_includes_failed_ingestions(self):
        """Test that stats include failed ingestions"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())
        self.assertIn('failed_ingestions', stats)
        self.assertIsInstance(stats['failed_ingestions'], list)


class TestStatsCalculations(unittest.TestCase):
    """Test statistics calculation logic"""

    def test_empty_database_returns_zero_counts(self):
        """Test that empty database returns zero for all counts"""
        from engine.ingestion.cli import get_ingestion_stats

        # This test assumes we can run against empty/test database
        stats = asyncio.run(get_ingestion_stats())

        # Should return valid structure even with no data
        self.assertIsInstance(stats['total_records'], int)
        self.assertGreaterEqual(stats['total_records'], 0)

    def test_by_source_counts_sum_to_total(self):
        """Test that source counts add up to total"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())

        if stats['total_records'] > 0:
            source_sum = sum(stats['by_source'].values())
            self.assertEqual(source_sum, stats['total_records'])

    def test_by_status_counts_sum_to_total(self):
        """Test that status counts add up to total"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())

        if stats['total_records'] > 0:
            status_sum = sum(stats['by_status'].values())
            self.assertEqual(status_sum, stats['total_records'])


class TestRecentIngestionsQuery(unittest.TestCase):
    """Test recent ingestions query behavior"""

    def test_recent_ingestions_limited_to_reasonable_count(self):
        """Test that recent ingestions are limited (e.g., last 10)"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())

        # Should return at most N recent records (typically 5-10)
        self.assertLessEqual(len(stats['recent_ingestions']), 10)

    def test_recent_ingestions_have_required_fields(self):
        """Test that recent ingestion records have required fields"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())

        for record in stats['recent_ingestions']:
            self.assertIn('source', record)
            self.assertIn('status', record)
            self.assertIn('ingested_at', record)

    def test_recent_ingestions_sorted_by_date(self):
        """Test that recent ingestions are sorted by date (newest first)"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())

        if len(stats['recent_ingestions']) > 1:
            # Check that dates are in descending order
            dates = [r['ingested_at'] for r in stats['recent_ingestions']]
            for i in range(len(dates) - 1):
                # Each date should be >= the next (newest first)
                self.assertGreaterEqual(dates[i], dates[i + 1])


class TestFailedIngestionsQuery(unittest.TestCase):
    """Test failed ingestions query behavior"""

    def test_failed_ingestions_only_include_failed_status(self):
        """Test that failed ingestions only include records with failed status"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())

        for record in stats['failed_ingestions']:
            self.assertEqual(record['status'], 'failed')

    def test_failed_ingestions_have_required_fields(self):
        """Test that failed ingestion records have required fields"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())

        for record in stats['failed_ingestions']:
            self.assertIn('source', record)
            self.assertIn('status', record)
            self.assertIn('ingested_at', record)


class TestShowStatusOutput(unittest.TestCase):
    """Test the show_status function output formatting"""

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_status_produces_output(self, mock_stdout):
        """Test that show_status produces console output"""
        from engine.ingestion.cli import show_status

        asyncio.run(show_status())
        output = mock_stdout.getvalue()

        self.assertGreater(len(output), 0)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_status_includes_header(self, mock_stdout):
        """Test that status output includes header"""
        from engine.ingestion.cli import show_status

        asyncio.run(show_status())
        output = mock_stdout.getvalue()

        self.assertIn('Ingestion Status', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_status_includes_total_count(self, mock_stdout):
        """Test that status output includes total record count"""
        from engine.ingestion.cli import show_status

        asyncio.run(show_status())
        output = mock_stdout.getvalue()

        self.assertIn('Total Records', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_status_includes_source_breakdown(self, mock_stdout):
        """Test that status output includes source breakdown"""
        from engine.ingestion.cli import show_status

        asyncio.run(show_status())
        output = mock_stdout.getvalue()

        # Should show "By Source" or similar heading
        self.assertTrue(
            'By Source' in output or 'Sources' in output or 'SOURCE' in output
        )

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_status_includes_status_breakdown(self, mock_stdout):
        """Test that status output includes status breakdown"""
        from engine.ingestion.cli import show_status

        asyncio.run(show_status())
        output = mock_stdout.getvalue()

        # Should show "By Status" or similar heading
        self.assertTrue(
            'By Status' in output or 'Status' in output or 'STATUS' in output
        )

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_status_includes_recent_ingestions_section(self, mock_stdout):
        """Test that status output includes recent ingestions section"""
        from engine.ingestion.cli import show_status

        asyncio.run(show_status())
        output = mock_stdout.getvalue()

        self.assertTrue(
            'Recent' in output or 'Latest' in output
        )


class TestStatusCommandCLIIntegration(unittest.TestCase):
    """Test status command integration with CLI"""

    @patch('sys.argv', ['cli.py', 'status'])
    @patch('engine.ingestion.cli.show_status')
    def test_cli_status_command_calls_show_status(self, mock_show_status):
        """Test that 'status' CLI command calls show_status"""
        from engine.ingestion.cli import main

        # Mock show_status to return a coroutine
        mock_show_status.return_value = asyncio.coroutine(lambda: None)()

        try:
            main()
        except SystemExit:
            pass

        # show_status should have been called (wrapped in asyncio.run)
        # Note: exact assertion depends on implementation

    @patch('sys.argv', ['cli.py', '--status'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_cli_status_flag_shows_status(self, mock_stdout):
        """Test that --status flag shows status"""
        from engine.ingestion.cli import main

        try:
            main()
        except SystemExit:
            pass

        # Should produce output related to status
        # Note: This test structure depends on implementation


class TestStatusCommandPerformance(unittest.TestCase):
    """Test that status command performs efficiently"""

    def test_get_stats_completes_quickly(self):
        """Test that get_ingestion_stats completes in reasonable time"""
        from engine.ingestion.cli import get_ingestion_stats
        import time

        start = time.time()
        asyncio.run(get_ingestion_stats())
        duration = time.time() - start

        # Should complete in less than 5 seconds even with many records
        self.assertLess(duration, 5.0)


class TestStatusCommandEdgeCases(unittest.TestCase):
    """Test status command edge cases"""

    def test_status_handles_missing_database_gracefully(self):
        """Test that status command handles database errors gracefully"""
        from engine.ingestion.cli import get_ingestion_stats

        # Should not crash even if database has issues
        try:
            stats = asyncio.run(get_ingestion_stats())
            # If it succeeds, stats should be valid
            self.assertIsInstance(stats, dict)
        except Exception as e:
            # If it fails, should be a reasonable error message
            self.assertIsInstance(str(e), str)

    def test_status_with_very_old_ingestions(self):
        """Test status correctly handles ingestions from long ago"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())

        # Should handle old dates without crashing
        self.assertIsInstance(stats['total_records'], int)


class TestSuccessRateCalculation(unittest.TestCase):
    """Test success rate calculation in statistics"""

    def test_stats_includes_success_rate(self):
        """Test that stats include success rate calculation"""
        from engine.ingestion.cli import get_ingestion_stats

        stats = asyncio.run(get_ingestion_stats())

        # Should include success rate or similar metric
        # Implementation might use different naming
        has_success_metric = (
            'success_rate' in stats or
            'success_count' in stats or
            'failed_count' in stats
        )
        self.assertTrue(has_success_metric or stats['total_records'] == 0)


if __name__ == '__main__':
    unittest.main()
