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
from pathlib import Path
from engine.orchestration.cli import main, format_report, bootstrap_lens
from engine.lenses.loader import LensConfigError


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
        # Mock orchestrate as async function (with ctx parameter)
        async def mock_async_orchestrate(request, *, ctx=None):
            return {
                "query": request.query,
                "candidates_found": 15,
                "accepted_entities": 10,
                "connectors": {},
                "errors": [],
            }

        with patch("sys.argv", ["cli.py", "run", "--lens", "edinburgh_finds", "tennis courts Edinburgh"]):
            with patch("engine.orchestration.cli.orchestrate", side_effect=mock_async_orchestrate):
                with patch("engine.orchestration.cli.bootstrap_lens") as mock_bootstrap:
                    # Mock bootstrap to return minimal context
                    from engine.orchestration.execution_context import ExecutionContext
                    mock_bootstrap.return_value = ExecutionContext(
                        lens_id="edinburgh_finds",
                        lens_contract={
                            "mapping_rules": [],
                            "module_triggers": [],
                            "modules": {},
                            "facets": {},
                            "values": [],
                            "confidence_threshold": 0.7,
                        },
                        lens_hash="test_hash"
                    )

                    # Should not raise
                    try:
                        main()
                    except SystemExit as e:
                        # Exit code 0 is success
                        assert e.code == 0, "main() should exit successfully"

    @patch("sys.stdout", new_callable=StringIO)
    def test_main_prints_formatted_report(self, mock_stdout):
        """main() should print formatted report to stdout."""
        # Mock orchestrate as async function (with ctx parameter)
        async def mock_async_orchestrate(request, *, ctx=None):
            return {
                "query": request.query,
                "candidates_found": 15,
                "accepted_entities": 10,
                "connectors": {},
                "errors": [],
            }

        with patch("sys.argv", ["cli.py", "run", "--lens", "edinburgh_finds", "tennis courts Edinburgh"]):
            with patch("engine.orchestration.cli.orchestrate", side_effect=mock_async_orchestrate):
                with patch("engine.orchestration.cli.bootstrap_lens") as mock_bootstrap:
                    # Mock bootstrap to return minimal context
                    from engine.orchestration.execution_context import ExecutionContext
                    mock_bootstrap.return_value = ExecutionContext(
                        lens_id="edinburgh_finds",
                        lens_contract={
                            "mapping_rules": [],
                            "module_triggers": [],
                            "modules": {},
                            "facets": {},
                            "values": [],
                            "confidence_threshold": 0.7,
                        },
                        lens_hash="test_hash"
                    )

                    try:
                        main()
                    except SystemExit:
                        pass

                    output = mock_stdout.getvalue()
                    assert len(output) > 0, "main() should print output"
                    assert "tennis courts Edinburgh" in output, "output should include query"

    def test_main_run_with_connector_override_executes_single_connector_path(self):
        """--connector should execute manual single-connector path and bypass planner orchestration."""
        async def mock_async_single(connector_name, request, *, ctx):
            assert connector_name == "overture_release"
            return {
                "query": request.query,
                "candidates_found": 1,
                "accepted_entities": 1,
                "connectors": {
                    "overture_release": {
                        "executed": True,
                        "candidates_added": 1,
                        "execution_time_ms": 10,
                        "cost_usd": 0.0,
                    }
                },
                "errors": [],
            }

        with patch("sys.argv", ["cli.py", "run", "--lens", "edinburgh_finds", "--connector", "overture_release", "overture live slice"]):
            with patch("engine.orchestration.cli.orchestrate_single_connector", side_effect=mock_async_single) as mock_single:
                with patch("engine.orchestration.cli.orchestrate") as mock_orchestrate:
                    with patch("engine.orchestration.cli.bootstrap_lens") as mock_bootstrap:
                        from engine.orchestration.execution_context import ExecutionContext
                        mock_bootstrap.return_value = ExecutionContext(
                            lens_id="edinburgh_finds",
                            lens_contract={
                                "mapping_rules": [],
                                "module_triggers": [],
                                "modules": {},
                                "facets": {},
                                "values": [],
                                "confidence_threshold": 0.7,
                            },
                            lens_hash="test_hash"
                        )

                        with pytest.raises(SystemExit) as exc_info:
                            main()

                        assert exc_info.value.code == 0
                        mock_single.assert_called_once()
                        mock_orchestrate.assert_not_called()

    def test_main_run_with_unknown_connector_override_exits(self):
        """Unknown --connector value should fail fast with non-zero exit."""
        with patch("sys.argv", ["cli.py", "run", "--lens", "edinburgh_finds", "--connector", "does_not_exist", "test query"]):
            with patch("engine.orchestration.cli.bootstrap_lens") as mock_bootstrap:
                from engine.orchestration.execution_context import ExecutionContext
                mock_bootstrap.return_value = ExecutionContext(
                    lens_id="edinburgh_finds",
                    lens_contract={
                        "mapping_rules": [],
                        "module_triggers": [],
                        "modules": {},
                        "facets": {},
                        "values": [],
                        "confidence_threshold": 0.7,
                    },
                    lens_hash="test_hash"
                )

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1


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


class TestBootstrapLens:
    """Test lens bootstrap function (LB-001 compliance)."""

    def test_bootstrap_lens_returns_execution_context(self):
        """
        bootstrap_lens() should return ExecutionContext with lens contract.

        Per docs/target-architecture.md 3.2: Bootstrap loads lens once and creates context.
        """
        from engine.orchestration.execution_context import ExecutionContext

        # Bootstrap lens (assuming edinburgh_finds exists)
        ctx = bootstrap_lens("edinburgh_finds")

        # Should return ExecutionContext
        assert isinstance(ctx, ExecutionContext), "bootstrap_lens should return ExecutionContext"

        # Should have lens_contract
        assert hasattr(ctx, "lens_contract"), "ExecutionContext should have lens_contract"
        assert ctx.lens_contract is not None, "lens_contract should not be None"

    def test_bootstrap_lens_contract_contains_required_fields(self):
        """
        Lens contract should contain all required fields per architecture.md.

        Required fields: mapping_rules, module_triggers, modules, facets,
        values, confidence_threshold, lens_id.
        """
        ctx = bootstrap_lens("edinburgh_finds")

        # Verify all required fields present
        # Verify ExecutionContext has lens_id as top-level field per docs/target-architecture.md 3.6
        assert ctx.lens_id == "edinburgh_finds", "ExecutionContext should have lens_id field"

        # Verify lens_contract contains required fields (but NOT lens_id, which is top-level)
        required_fields = [
            "mapping_rules",
            "module_triggers",
            "modules",
            "facets",
            "values",
            "confidence_threshold",
        ]

        for field in required_fields:
            assert field in ctx.lens_contract, f"lens_contract should contain {field}"

    def test_bootstrap_lens_fails_fast_on_invalid_lens(self):
        """
        bootstrap_lens() should fail fast on invalid lens (LensConfigError).

        Per docs/target-architecture.md 3.2: "Fail fast on invalid lens."
        """
        with pytest.raises((LensConfigError, FileNotFoundError)):
            bootstrap_lens("nonexistent_lens")

    def test_bootstrap_lens_contract_is_immutable(self):
        """
        ExecutionContext should be immutable (frozen dataclass).

        Per docs/target-architecture.md 3.6: ExecutionContext is a frozen dataclass
        that cannot be mutated.
        """
        from dataclasses import FrozenInstanceError

        ctx = bootstrap_lens("edinburgh_finds")

        # ExecutionContext should be frozen (attempting to modify raises FrozenInstanceError)
        with pytest.raises(FrozenInstanceError):
            ctx.lens_id = "modified"

        # lens_contract should also be immutable via frozen dataclass
        with pytest.raises(FrozenInstanceError):
            ctx.lens_contract = {}

    def test_bootstrap_lens_loads_from_correct_path(self):
        """
        bootstrap_lens() should load from engine/lenses/<lens_id>/lens.yaml.
        """
        # Bootstrap should succeed if file exists
        ctx = bootstrap_lens("edinburgh_finds")

        # Verify lens_id field matches (top-level field per docs/target-architecture.md 3.6)
        assert ctx.lens_id == "edinburgh_finds"

        # Verify lens file exists at expected path
        expected_path = Path(__file__).parent.parent.parent.parent / "engine" / "lenses" / "edinburgh_finds" / "lens.yaml"
        assert expected_path.exists(), f"Lens file should exist at {expected_path}"
