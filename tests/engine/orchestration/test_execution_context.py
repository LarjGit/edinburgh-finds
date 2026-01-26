"""
Tests for ExecutionContext modifications.

Validates that ExecutionContext includes new fields for observability:
- metrics: Dict[str, Any] for per-connector execution metrics
- errors: List[Dict[str, Any]] for error tracking
"""

import pytest
from engine.orchestration.execution_context import ExecutionContext


class TestExecutionContextInitialization:
    """Test ExecutionContext initialization with new observability fields."""

    def test_metrics_initialized_as_empty_dict(self):
        """ExecutionContext should initialize metrics as empty dict."""
        context = ExecutionContext()
        assert hasattr(context, "metrics"), "ExecutionContext missing 'metrics' attribute"
        assert isinstance(context.metrics, dict), "metrics should be a dict"
        assert context.metrics == {}, "metrics should be initialized as empty dict"

    def test_errors_initialized_as_empty_list(self):
        """ExecutionContext should initialize errors as empty list."""
        context = ExecutionContext()
        assert hasattr(context, "errors"), "ExecutionContext missing 'errors' attribute"
        assert isinstance(context.errors, list), "errors should be a list"
        assert context.errors == [], "errors should be initialized as empty list"

    def test_metrics_is_mutable(self):
        """metrics dict should be mutable to allow runtime updates."""
        context = ExecutionContext()
        context.metrics["serper"] = {"executed": True, "candidates_added": 5}
        assert context.metrics["serper"]["executed"] is True
        assert context.metrics["serper"]["candidates_added"] == 5

    def test_errors_is_mutable(self):
        """errors list should be mutable to allow runtime updates."""
        context = ExecutionContext()
        context.errors.append({"connector": "google_places", "message": "API timeout"})
        assert len(context.errors) == 1
        assert context.errors[0]["connector"] == "google_places"

    def test_existing_fields_still_present(self):
        """ExecutionContext should maintain all existing fields."""
        context = ExecutionContext()
        # Verify existing fields are not affected
        assert hasattr(context, "candidates")
        assert hasattr(context, "accepted_entities")
        assert hasattr(context, "accepted_entity_keys")
        assert hasattr(context, "evidence")
        assert hasattr(context, "seeds")
        assert hasattr(context, "budget_spent_usd")
        assert hasattr(context, "confidence")


class TestExecutionContextMetricsUsage:
    """Test realistic metrics usage patterns."""

    def test_can_store_per_connector_metrics(self):
        """Should be able to store metrics for multiple connectors."""
        context = ExecutionContext()

        context.metrics["serper"] = {
            "executed": True,
            "candidates_added": 12,
            "execution_time_ms": 340,
            "cost_usd": 0.01
        }

        context.metrics["google_places"] = {
            "executed": True,
            "candidates_added": 8,
            "execution_time_ms": 520,
            "cost_usd": 0.02
        }

        assert len(context.metrics) == 2
        assert context.metrics["serper"]["candidates_added"] == 12
        assert context.metrics["google_places"]["cost_usd"] == 0.02


class TestExecutionContextErrorsUsage:
    """Test realistic error tracking patterns."""

    def test_can_track_multiple_errors(self):
        """Should be able to track errors from multiple connectors."""
        context = ExecutionContext()

        context.errors.append({
            "connector": "serper",
            "phase": "DISCOVERY",
            "error_type": "APITimeout",
            "message": "Request timed out after 30s"
        })

        context.errors.append({
            "connector": "openstreetmap",
            "phase": "DISCOVERY",
            "error_type": "MappingError",
            "message": "Invalid coordinate format"
        })

        assert len(context.errors) == 2
        assert context.errors[0]["connector"] == "serper"
        assert context.errors[1]["error_type"] == "MappingError"

    def test_empty_errors_when_no_failures(self):
        """errors list should remain empty when no errors occur."""
        context = ExecutionContext()

        # Simulate successful execution without errors
        context.metrics["google_places"] = {"executed": True, "candidates_added": 5}

        assert context.errors == []
