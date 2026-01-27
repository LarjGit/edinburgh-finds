"""
Tests for CLI module.

Validates the CLI entry point and report formatting:
- CLI run command accepts query argument
- Report is formatted and displayed
- Basic report structure and content
"""

import pytest
from io import StringIO
from unittest.mock import patch
from engine.orchestration.cli import main, format_report


class TestFormatReport:
    """Test report formatting functions."""

    def test_format_report_returns_string(self):
        """format_report should return a string."""
        report = {
            "query": "tennis courts Edinburgh",
            "candidates_found": 15,
            "accepted_entities": 10,
            "connectors": {
                "serper": {
                    "executed": True,
                    "candidates_added": 12,
                    "execution_time_ms": 340,
                    "cost_usd": 0.01,
                }
            },
            "errors": [],
        }

        formatted = format_report(report)

        assert isinstance(formatted, str), "format_report should return a string"
        assert len(formatted) > 0, "formatted report should not be empty"

    def test_format_report_includes_query(self):
        """format_report should include the query string."""
        report = {
            "query": "tennis courts Edinburgh",
            "candidates_found": 15,
            "accepted_entities": 10,
            "connectors": {},
            "errors": [],
        }

        formatted = format_report(report)

        assert "tennis courts Edinburgh" in formatted, "report should include query"

    def test_format_report_includes_summary_counts(self):
        """format_report should include candidates and accepted counts."""
        report = {
            "query": "tennis courts Edinburgh",
            "candidates_found": 15,
            "accepted_entities": 10,
            "connectors": {},
            "errors": [],
        }

        formatted = format_report(report)

        assert "15" in formatted, "report should include candidates_found"
        assert "10" in formatted, "report should include accepted_entities"

    def test_format_report_includes_connector_metrics(self):
        """format_report should display per-connector metrics."""
        report = {
            "query": "tennis courts Edinburgh",
            "candidates_found": 15,
            "accepted_entities": 10,
            "connectors": {
                "serper": {
                    "executed": True,
                    "candidates_added": 12,
                    "execution_time_ms": 340,
                    "cost_usd": 0.01,
                },
                "google_places": {
                    "executed": True,
                    "candidates_added": 8,
                    "execution_time_ms": 520,
                    "cost_usd": 0.02,
                },
            },
            "errors": [],
        }

        formatted = format_report(report)

        assert "serper" in formatted, "report should include serper connector"
        assert "google_places" in formatted, "report should include google_places connector"
        assert "340" in formatted or "340ms" in formatted, "report should include execution time"

    def test_format_report_shows_errors_when_present(self):
        """format_report should display errors if any occurred."""
        report = {
            "query": "tennis courts Edinburgh",
            "candidates_found": 5,
            "accepted_entities": 5,
            "connectors": {
                "serper": {
                    "executed": False,
                    "error": "API timeout",
                    "execution_time_ms": 30000,
                    "cost_usd": 0.0,
                }
            },
            "errors": [
                {
                    "connector": "serper",
                    "error": "API timeout",
                    "execution_time_ms": 30000,
                }
            ],
        }

        formatted = format_report(report)

        assert "error" in formatted.lower() or "failed" in formatted.lower(), \
            "report should indicate errors occurred"

    def test_format_report_includes_success_status_indicators(self):
        """format_report should include SUCCESS/FAILED status indicators."""
        report = {
            "query": "test query",
            "candidates_found": 10,
            "accepted_entities": 10,
            "connectors": {
                "serper": {
                    "executed": True,
                    "candidates_added": 10,
                    "execution_time_ms": 100,
                    "cost_usd": 0.01,
                },
                "google_places": {
                    "executed": False,
                    "error": "API error",
                    "execution_time_ms": 50,
                }
            },
            "errors": [],
        }

        formatted = format_report(report)

        # Should include status indicators
        assert "SUCCESS" in formatted or "✓" in formatted or "✔" in formatted, \
            "report should include success indicator for executed connector"
        assert "FAILED" in formatted or "✗" in formatted or "✘" in formatted, \
            "report should include failure indicator for failed connector"

    def test_format_report_has_visual_separators(self):
        """format_report should have clear visual section separators."""
        report = {
            "query": "test query",
            "candidates_found": 5,
            "accepted_entities": 5,
            "connectors": {},
            "errors": [],
        }

        formatted = format_report(report)

        # Should have section separators (=, -, or similar)
        assert "=" * 20 in formatted or "-" * 20 in formatted or "─" * 20 in formatted, \
            "report should include visual separators for sections"

    def test_format_report_includes_persistence_metrics(self):
        """format_report should display persistence metrics when available."""
        report = {
            "query": "test query",
            "candidates_found": 10,
            "accepted_entities": 10,
            "persisted_count": 8,
            "persistence_errors": [
                {
                    "source": "serper",
                    "error": "Duplicate slug",
                    "entity_name": "Test Venue"
                }
            ],
            "connectors": {},
            "errors": [],
        }

        formatted = format_report(report)

        # Should include persistence count
        assert "8" in formatted and ("Persisted" in formatted or "persisted" in formatted), \
            "report should include persisted count"

        # Should show persistence errors
        assert "Duplicate slug" in formatted, \
            "report should include persistence error details"


class TestCLIMain:
    """Test CLI main() entry point."""

    def test_main_requires_query_argument(self):
        """main() should require a query argument."""
        # Test that main() expects a query argument
        # This will be implementation-dependent
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["cli.py", "run"]):
                main()

    def test_main_run_command_with_query(self):
        """main() run command should accept query argument."""
        with patch("sys.argv", ["cli.py", "run", "tennis courts Edinburgh"]):
            with patch("engine.orchestration.cli.orchestrate") as mock_orchestrate:
                mock_orchestrate.return_value = {
                    "query": "tennis courts Edinburgh",
                    "candidates_found": 15,
                    "accepted_entities": 10,
                    "connectors": {},
                    "errors": [],
                }

                # Should not raise
                try:
                    main()
                except SystemExit as e:
                    # Exit code 0 is success
                    assert e.code == 0, "main() should exit successfully"

    @patch("sys.stdout", new_callable=StringIO)
    def test_main_prints_formatted_report(self, mock_stdout):
        """main() should print formatted report to stdout."""
        with patch("sys.argv", ["cli.py", "run", "tennis courts Edinburgh"]):
            with patch("engine.orchestration.cli.orchestrate") as mock_orchestrate:
                mock_orchestrate.return_value = {
                    "query": "tennis courts Edinburgh",
                    "candidates_found": 15,
                    "accepted_entities": 10,
                    "connectors": {},
                    "errors": [],
                }

                try:
                    main()
                except SystemExit:
                    pass

                output = mock_stdout.getvalue()
                assert len(output) > 0, "main() should print output"
                assert "tennis courts Edinburgh" in output, "output should include query"


class TestCLIIntegration:
    """Integration tests for CLI with real orchestration."""

    @pytest.mark.integration
    def test_cli_run_executes_orchestration(self):
        """CLI run command should execute full orchestration flow."""
        with patch("sys.argv", ["cli.py", "run", "tennis courts Edinburgh"]):
            # Real execution (requires API keys)
            # In CI/CD, skip or mock connectors
            try:
                main()
            except SystemExit as e:
                # Should exit successfully (code 0)
                assert e.code == 0, "CLI should complete successfully"
