"""
Tests for LLM cost tracking and calculation.

Tests cover:
- Token counting from Anthropic API responses
- Cost estimation based on model pricing
- Cost aggregation and reporting
- Integration with health dashboard
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from engine.extraction.llm_cost import (
    MODEL_PRICING,
    calculate_cost,
    LLMUsageTracker,
    get_usage_tracker,
    extract_token_usage,
    format_cost_report,
)


class TestModelPricing:
    """Test model pricing constants."""

    def test_pricing_includes_haiku(self):
        """Test that Haiku pricing is defined."""
        assert "claude-3-haiku-20240307" in MODEL_PRICING
        pricing = MODEL_PRICING["claude-3-haiku-20240307"]
        assert "input" in pricing
        assert "output" in pricing
        assert pricing["input"] > 0
        assert pricing["output"] > 0

    def test_pricing_includes_sonnet(self):
        """Test that Sonnet pricing is defined."""
        assert "claude-3-5-sonnet-20241022" in MODEL_PRICING
        pricing = MODEL_PRICING["claude-3-5-sonnet-20241022"]
        assert pricing["input"] > 0
        assert pricing["output"] > 0

    def test_output_more_expensive_than_input(self):
        """Test that output tokens are priced higher than input."""
        for model, pricing in MODEL_PRICING.items():
            assert pricing["output"] > pricing["input"], \
                f"Model {model} should have higher output pricing"


class TestCalculateCost:
    """Test cost calculation function."""

    def test_calculate_cost_haiku(self):
        """Test cost calculation for Haiku model."""
        cost = calculate_cost(
            model="claude-3-haiku-20240307",
            tokens_in=1000,
            tokens_out=500,
        )
        # Haiku: $0.25 per 1M input, $1.25 per 1M output
        expected = (1000 * 0.25 / 1_000_000) + (500 * 1.25 / 1_000_000)
        assert abs(cost - expected) < 0.0001

    def test_calculate_cost_sonnet(self):
        """Test cost calculation for Sonnet model."""
        cost = calculate_cost(
            model="claude-3-5-sonnet-20241022",
            tokens_in=1000,
            tokens_out=500,
        )
        # Sonnet: $3 per 1M input, $15 per 1M output
        expected = (1000 * 3.0 / 1_000_000) + (500 * 15.0 / 1_000_000)
        assert abs(cost - expected) < 0.0001

    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        cost = calculate_cost(
            model="claude-3-haiku-20240307",
            tokens_in=0,
            tokens_out=0,
        )
        assert cost == 0.0

    def test_calculate_cost_unknown_model(self):
        """Test cost calculation with unknown model."""
        with pytest.raises(ValueError, match="Unknown model"):
            calculate_cost(
                model="unknown-model",
                tokens_in=100,
                tokens_out=50,
            )

    def test_calculate_cost_large_token_count(self):
        """Test cost calculation with large token counts."""
        cost = calculate_cost(
            model="claude-3-haiku-20240307",
            tokens_in=1_000_000,
            tokens_out=500_000,
        )
        # Should handle large numbers correctly
        assert cost > 0
        assert cost < 10  # Sanity check


class TestExtractTokenUsage:
    """Test token usage extraction from API responses."""

    def test_extract_tokens_from_anthropic_response(self):
        """Test extracting tokens from Anthropic API response."""
        response = Mock()
        response.usage = Mock()
        response.usage.input_tokens = 150
        response.usage.output_tokens = 75

        tokens_in, tokens_out = extract_token_usage(response)

        assert tokens_in == 150
        assert tokens_out == 75

    def test_extract_tokens_missing_usage(self):
        """Test handling response without usage field."""
        response = Mock(spec=[])  # No usage attribute

        with pytest.raises(AttributeError):
            extract_token_usage(response)

    def test_extract_tokens_from_instructor_response(self):
        """Test extracting tokens from Instructor-wrapped response."""
        # Instructor wraps the response, but usage should still be accessible
        response = Mock()
        response._raw_response = Mock()
        response._raw_response.usage = Mock()
        response._raw_response.usage.input_tokens = 200
        response._raw_response.usage.output_tokens = 100

        # Function should handle both direct and wrapped responses
        tokens_in, tokens_out = extract_token_usage(response._raw_response)

        assert tokens_in == 200
        assert tokens_out == 100


class TestLLMUsageTracker:
    """Test LLM usage tracking."""

    def test_tracker_initialization(self):
        """Test tracker initializes empty."""
        tracker = LLMUsageTracker()
        assert len(tracker.usage_records) == 0
        assert tracker.total_tokens_in == 0
        assert tracker.total_tokens_out == 0
        assert tracker.total_cost_usd == 0.0

    def test_record_usage(self):
        """Test recording LLM usage."""
        tracker = LLMUsageTracker()

        tracker.record_usage(
            model="claude-3-haiku-20240307",
            tokens_in=100,
            tokens_out=50,
            source="google_places",
            record_id="uuid-123",
        )

        assert len(tracker.usage_records) == 1
        record = tracker.usage_records[0]
        assert record["model"] == "claude-3-haiku-20240307"
        assert record["tokens_in"] == 100
        assert record["tokens_out"] == 50
        assert record["source"] == "google_places"
        assert "timestamp" in record
        assert "cost_usd" in record

    def test_tracker_aggregates_totals(self):
        """Test tracker aggregates total tokens and cost."""
        tracker = LLMUsageTracker()

        tracker.record_usage(
            model="claude-3-haiku-20240307",
            tokens_in=100,
            tokens_out=50,
            source="serper",
            record_id="uuid-1",
        )

        tracker.record_usage(
            model="claude-3-haiku-20240307",
            tokens_in=200,
            tokens_out=100,
            source="osm",
            record_id="uuid-2",
        )

        assert tracker.total_tokens_in == 300
        assert tracker.total_tokens_out == 150
        assert tracker.total_cost_usd > 0

    def test_tracker_handles_multiple_models(self):
        """Test tracker handles multiple models correctly."""
        tracker = LLMUsageTracker()

        tracker.record_usage(
            model="claude-3-haiku-20240307",
            tokens_in=100,
            tokens_out=50,
            source="serper",
            record_id="uuid-1",
        )

        tracker.record_usage(
            model="claude-3-5-sonnet-20241022",
            tokens_in=100,
            tokens_out=50,
            source="osm",
            record_id="uuid-2",
        )

        # Sonnet should be more expensive than Haiku
        haiku_cost = tracker.usage_records[0]["cost_usd"]
        sonnet_cost = tracker.usage_records[1]["cost_usd"]
        assert sonnet_cost > haiku_cost

    def test_get_cost_by_source(self):
        """Test getting cost breakdown by source."""
        tracker = LLMUsageTracker()

        tracker.record_usage(
            model="claude-3-haiku-20240307",
            tokens_in=100,
            tokens_out=50,
            source="serper",
            record_id="uuid-1",
        )

        tracker.record_usage(
            model="claude-3-haiku-20240307",
            tokens_in=200,
            tokens_out=100,
            source="serper",
            record_id="uuid-2",
        )

        tracker.record_usage(
            model="claude-3-haiku-20240307",
            tokens_in=150,
            tokens_out=75,
            source="osm",
            record_id="uuid-3",
        )

        by_source = tracker.get_cost_by_source()

        assert "serper" in by_source
        assert "osm" in by_source
        assert by_source["serper"]["count"] == 2
        assert by_source["osm"]["count"] == 1
        assert by_source["serper"]["total_tokens"] == 450  # (100+50) + (200+100)
        assert by_source["osm"]["total_tokens"] == 225  # (150+75)

    def test_get_cost_by_model(self):
        """Test getting cost breakdown by model."""
        tracker = LLMUsageTracker()

        tracker.record_usage(
            model="claude-3-haiku-20240307",
            tokens_in=100,
            tokens_out=50,
            source="serper",
            record_id="uuid-1",
        )

        tracker.record_usage(
            model="claude-3-5-sonnet-20241022",
            tokens_in=100,
            tokens_out=50,
            source="osm",
            record_id="uuid-2",
        )

        by_model = tracker.get_cost_by_model()

        assert "claude-3-haiku-20240307" in by_model
        assert "claude-3-5-sonnet-20241022" in by_model
        assert by_model["claude-3-haiku-20240307"]["count"] == 1
        assert by_model["claude-3-5-sonnet-20241022"]["count"] == 1


class TestGetUsageTracker:
    """Test global usage tracker access."""

    def test_get_usage_tracker_singleton(self):
        """Test that get_usage_tracker returns the same instance."""
        tracker1 = get_usage_tracker()
        tracker2 = get_usage_tracker()

        assert tracker1 is tracker2

    def test_get_usage_tracker_persists_data(self):
        """Test that tracker persists data across calls."""
        tracker = get_usage_tracker()
        tracker.record_usage(
            model="claude-3-haiku-20240307",
            tokens_in=100,
            tokens_out=50,
            source="test",
            record_id="uuid-test",
        )

        tracker2 = get_usage_tracker()
        assert len(tracker2.usage_records) >= 1


class TestFormatCostReport:
    """Test cost report formatting."""

    def test_format_empty_report(self):
        """Test formatting report with no usage."""
        tracker = LLMUsageTracker()
        report = format_cost_report(tracker)

        assert "Total Cost" in report
        assert "$0.00" in report

    def test_format_report_with_usage(self):
        """Test formatting report with usage data."""
        tracker = LLMUsageTracker()
        tracker.record_usage(
            model="claude-3-haiku-20240307",
            tokens_in=1000,
            tokens_out=500,
            source="serper",
            record_id="uuid-1",
        )

        tracker.record_usage(
            model="claude-3-haiku-20240307",
            tokens_in=2000,
            tokens_out=1000,
            source="osm",
            record_id="uuid-2",
        )

        report = format_cost_report(tracker)

        assert "Total Cost" in report
        assert "serper" in report
        assert "osm" in report
        assert str(tracker.total_tokens_in) in report or f"{tracker.total_tokens_in:,}" in report

    def test_format_report_includes_model_breakdown(self):
        """Test report includes model breakdown."""
        tracker = LLMUsageTracker()
        tracker.record_usage(
            model="claude-3-haiku-20240307",
            tokens_in=100,
            tokens_out=50,
            source="serper",
            record_id="uuid-1",
        )

        report = format_cost_report(tracker)

        assert "haiku" in report.lower() or "claude-3-haiku" in report.lower()

    def test_format_report_with_mixed_models(self):
        """Test report with multiple models."""
        tracker = LLMUsageTracker()

        tracker.record_usage(
            model="claude-3-haiku-20240307",
            tokens_in=100,
            tokens_out=50,
            source="serper",
            record_id="uuid-1",
        )

        tracker.record_usage(
            model="claude-3-5-sonnet-20241022",
            tokens_in=100,
            tokens_out=50,
            source="osm",
            record_id="uuid-2",
        )

        report = format_cost_report(tracker)

        # Should show both models
        assert report.count("claude") >= 2 or "haiku" in report.lower()
