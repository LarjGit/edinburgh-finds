"""
Tests for extraction health metrics calculation.

These tests validate the health dashboard metrics for the extraction engine:
- Unprocessed record counts
- Success rates per source
- Field null rates
- Recent failures ordering
- LLM usage and cost estimation
- Merge conflict counts
"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from engine.extraction.health_check import (
    calculate_unprocessed_count,
    calculate_success_rate_by_source,
    calculate_field_null_rates,
    get_recent_failures,
    calculate_llm_usage,
    calculate_merge_conflict_count,
    calculate_health_metrics,
)


class TestHealthMetricsImports(unittest.TestCase):
    """Validate that health metric helpers are importable."""

    def test_helpers_exist(self):
        self.assertTrue(callable(calculate_unprocessed_count))
        self.assertTrue(callable(calculate_success_rate_by_source))
        self.assertTrue(callable(calculate_field_null_rates))
        self.assertTrue(callable(get_recent_failures))
        self.assertTrue(callable(calculate_llm_usage))
        self.assertTrue(callable(calculate_merge_conflict_count))
        self.assertTrue(callable(calculate_health_metrics))


class TestUnprocessedCount(unittest.TestCase):
    """Test unprocessed record calculation."""

    def test_unprocessed_count_excludes_processed_and_failed(self):
        raw_records = [
            SimpleNamespace(id="r1", source="google_places", status="success"),
            SimpleNamespace(id="r2", source="google_places", status="success"),
            SimpleNamespace(id="r3", source="serper", status="success"),
        ]
        extracted = [
            SimpleNamespace(raw_ingestion_id="r1", source="google_places"),
        ]
        failed = [
            SimpleNamespace(raw_ingestion_id="r2", source="google_places"),
        ]

        result = calculate_unprocessed_count(raw_records, extracted, failed)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["by_source"]["serper"], 1)


class TestSuccessRateBySource(unittest.TestCase):
    """Test success rate calculations per source."""

    def test_success_rate_uses_successful_raw_records(self):
        raw_records = [
            SimpleNamespace(id="g1", source="google_places", status="success"),
            SimpleNamespace(id="g2", source="google_places", status="success"),
            SimpleNamespace(id="g3", source="google_places", status="failed"),
            SimpleNamespace(id="s1", source="serper", status="success"),
        ]
        extracted = [
            SimpleNamespace(raw_ingestion_id="g1", source="google_places"),
            SimpleNamespace(raw_ingestion_id="s1", source="serper"),
        ]

        result = calculate_success_rate_by_source(raw_records, extracted)

        google_stats = result["google_places"]
        serper_stats = result["serper"]

        self.assertEqual(google_stats["total"], 2)
        self.assertEqual(google_stats["extracted"], 1)
        self.assertAlmostEqual(google_stats["success_rate"], 50.0, places=2)

        self.assertEqual(serper_stats["total"], 1)
        self.assertEqual(serper_stats["extracted"], 1)
        self.assertAlmostEqual(serper_stats["success_rate"], 100.0, places=2)


class TestFieldNullRates(unittest.TestCase):
    """Test null rate calculations for extracted fields."""

    def test_field_null_rates_count_missing_and_null(self):
        extracted = [
            SimpleNamespace(
                attributes={"entity_name": "Alpha", "postcode": None}
            ),
            SimpleNamespace(
                attributes={"postcode": "EH1 2AB"}
            ),
        ]
        fields = ["entity_name", "postcode"]

        result = calculate_field_null_rates(extracted, fields)

        self.assertEqual(result["entity_name"]["null_count"], 1)
        self.assertAlmostEqual(result["entity_name"]["null_rate"], 50.0, places=2)
        self.assertEqual(result["postcode"]["null_count"], 1)
        self.assertAlmostEqual(result["postcode"]["null_rate"], 50.0, places=2)

    def test_field_null_rates_parse_json_string(self):
        extracted = [
            SimpleNamespace(
                attributes='{"entity_name": "Beta", "postcode": "EH3 1AA"}'
            )
        ]
        fields = ["entity_name", "postcode"]

        result = calculate_field_null_rates(extracted, fields)

        self.assertEqual(result["entity_name"]["null_count"], 0)
        self.assertEqual(result["postcode"]["null_count"], 0)


class TestRecentFailures(unittest.TestCase):
    """Test recent failure ordering."""

    def test_recent_failures_sorted_by_last_attempt(self):
        now = datetime(2026, 1, 17, 12, 0, 0, tzinfo=timezone.utc)
        failures = [
            SimpleNamespace(
                id="f1",
                source="serper",
                error_message="timeout",
                last_attempt_at=now - timedelta(hours=2),
                createdAt=now - timedelta(hours=5),
            ),
            SimpleNamespace(
                id="f2",
                source="osm",
                error_message="validation",
                last_attempt_at=now - timedelta(hours=1),
                createdAt=now - timedelta(hours=4),
            ),
        ]

        result = get_recent_failures(failures, limit=2)

        self.assertEqual(result[0]["id"], "f2")
        self.assertEqual(result[1]["id"], "f1")

    def test_recent_failures_handles_naive_and_iso_strings(self):
        failures = [
            SimpleNamespace(
                id="f1",
                source="serper",
                error_message="timeout",
                last_attempt_at="2026-01-17T09:00:00Z",
            ),
            SimpleNamespace(
                id="f2",
                source="osm",
                error_message="validation",
                last_attempt_at=datetime(2026, 1, 17, 11, 0, 0),
            ),
            SimpleNamespace(
                id="f3",
                source="osm",
                error_message="other",
                last_attempt_at=datetime(2026, 1, 17, 10, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        result = get_recent_failures(failures, limit=3)

        self.assertEqual(result[0]["id"], "f2")
        self.assertEqual(result[1]["id"], "f3")
        self.assertEqual(result[2]["id"], "f1")


class TestLlmUsageMetrics(unittest.TestCase):
    """Test LLM usage and cost estimates."""

    def test_llm_usage_counts_and_cost(self):
        extracted = [
            SimpleNamespace(
                source="serper",
                model_used="claude-haiku-20250318",
                attributes={"llm_usage": {"input_tokens": 1000, "output_tokens": 500}},
            ),
            SimpleNamespace(
                source="osm",
                model_used=None,
                attributes={},
            ),
            SimpleNamespace(
                source="google_places",
                model_used=None,
                attributes={},
            ),
        ]

        result = calculate_llm_usage(extracted)

        self.assertEqual(result["total_llm_extractions"], 2)
        self.assertEqual(result["by_model"]["claude-haiku-20250318"], 1)
        self.assertEqual(result["by_model"]["unknown"], 1)
        self.assertEqual(result["input_tokens"], 1000)
        self.assertEqual(result["output_tokens"], 500)
        self.assertTrue(result["has_usage_data"])
        self.assertAlmostEqual(result["estimated_cost"], 0.0028, places=4)


class TestMergeConflictMetrics(unittest.TestCase):
    """Test merge conflict counts."""

    def test_merge_conflict_count(self):
        conflicts = [SimpleNamespace(id="c1"), SimpleNamespace(id="c2")]
        self.assertEqual(calculate_merge_conflict_count(conflicts), 2)


class TestHealthMetricsAggregate(unittest.TestCase):
    """Test aggregate health metrics output."""

    def test_health_metrics_includes_all_sections(self):
        raw_records = [SimpleNamespace(id="r1", source="serper", status="success")]
        extracted = [SimpleNamespace(raw_ingestion_id="r1", source="serper", attributes={})]
        failed = []
        conflicts = []

        result = calculate_health_metrics(
            raw_records=raw_records,
            extracted_listings=extracted,
            failed_extractions=failed,
            merge_conflicts=conflicts,
            field_names=["entity_name"],
        )

        self.assertIn("timestamp", result)
        self.assertIn("unprocessed", result)
        self.assertIn("success_rate_by_source", result)
        self.assertIn("field_null_rates", result)
        self.assertIn("recent_failures", result)
        self.assertIn("llm_usage", result)
        self.assertIn("merge_conflicts", result)


if __name__ == "__main__":
    unittest.main()
