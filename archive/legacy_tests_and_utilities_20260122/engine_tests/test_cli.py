"""
Tests for CLI module for data ingestion connectors

Note: These are primarily integration-style tests that verify CLI structure
and basic functionality. Full end-to-end testing with real APIs should be done
manually as documented in the track plan.
"""
import unittest
from unittest.mock import patch
import sys
from io import StringIO

from engine.ingestion.cli import (
    CONNECTORS,
    list_connectors,
    main
)


class TestCLIConnectorRegistry(unittest.TestCase):
    """Test the connector registry"""

    def test_connectors_registry_exists(self):
        """Test that CONNECTORS dictionary exists"""
        self.assertIsInstance(CONNECTORS, dict)

    def test_connectors_registry_has_required_connectors(self):
        """Test that required connectors are registered"""
        required = ['serper', 'google_places', 'openstreetmap']
        for connector_name in required:
            self.assertIn(
                connector_name,
                CONNECTORS,
                f"Connector '{connector_name}' should be registered"
            )

    def test_connectors_are_classes(self):
        """Test that registered connectors are classes"""
        for name, cls in CONNECTORS.items():
            self.assertTrue(
                callable(cls),
                f"Connector '{name}' should be a class (callable)"
            )


class TestCLIModules(unittest.TestCase):
    """Test that CLI modules exist and are importable"""

    def test_cli_main_module_exists(self):
        """Test that main CLI module exists"""
        try:
            import engine.ingestion.cli
            self.assertIsNotNone(engine.ingestion.cli)
        except ImportError as e:
            self.fail(f"Failed to import CLI module: {e}")

    def test_individual_runner_modules_exist(self):
        """Test that individual runner modules exist"""
        runners = ['run_serper', 'run_google_places', 'run_osm']
        for runner in runners:
            try:
                module = __import__(f'engine.ingestion.{runner}', fromlist=[runner])
                self.assertIsNotNone(module)
                self.assertTrue(hasattr(module, 'main'), f"{runner} should have main() function")
            except ImportError as e:
                self.fail(f"Failed to import {runner}: {e}")

    def test_cli_has_main_entry_point(self):
        """Test that CLI module has main entry point"""
        from engine.ingestion import cli
        self.assertTrue(hasattr(cli, 'main'))
        self.assertTrue(callable(cli.main))

    def test_cli_has_run_connector_function(self):
        """Test that CLI module has run_connector function"""
        from engine.ingestion import cli
        self.assertTrue(hasattr(cli, 'run_connector'))
        self.assertTrue(callable(cli.run_connector))

    def test_cli_has_list_connectors_function(self):
        """Test that CLI module has list_connectors function"""
        from engine.ingestion import cli
        self.assertTrue(hasattr(cli, 'list_connectors'))
        self.assertTrue(callable(cli.list_connectors))


class TestListConnectors(unittest.TestCase):
    """Test the list_connectors function"""

    @patch('sys.stdout', new_callable=StringIO)
    def test_list_connectors_output(self, mock_stdout):
        """Test that list_connectors produces output"""
        list_connectors()
        output = mock_stdout.getvalue()

        self.assertIn('Available connectors:', output)
        self.assertIn('serper', output)
        self.assertIn('google_places', output)
        self.assertIn('openstreetmap', output)


class TestMainCLI(unittest.TestCase):
    """Test the main CLI entry point"""

    @patch('sys.argv', ['cli.py', '--list'])
    @patch('engine.ingestion.cli.list_connectors')
    def test_main_list_flag(self, mock_list):
        """Test main with --list flag"""
        result = main()
        mock_list.assert_called_once()
        self.assertEqual(result, 0)

    @patch('sys.argv', ['cli.py'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_no_args_shows_help(self, mock_stdout):
        """Test that main without args shows help"""
        result = main()
        self.assertEqual(result, 1)

    @patch('sys.argv', ['cli.py', 'serper'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_missing_query_shows_help(self, mock_stdout):
        """Test that main without query shows help"""
        result = main()
        self.assertEqual(result, 1)

    @patch('sys.argv', ['cli.py', 'serper', 'test query'])
    @patch('engine.ingestion.cli.asyncio.run')
    def test_main_runs_connector(self, mock_asyncio_run):
        """Test that main runs the connector"""
        mock_asyncio_run.return_value = 0

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 0)
        mock_asyncio_run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
