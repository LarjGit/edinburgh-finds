"""
Tests for extraction health CLI formatting.

These tests validate the formatted dashboard output using sample metrics.
"""

import unittest
from datetime import datetime, timezone

from engine.extraction.health import format_health_report


class TestExtractionHealthReportFormatting(unittest.TestCase):
    """Validate formatted health dashboard output."""

    def setUp(self):
        self.sample_metrics = {
            "timestamp": datetime(2026, 1, 17, 12, 0, 0, tzinfo=timezone.utc),
            "unprocessed": {
                "count": 3,
                "by_source": {"serper": 2, "osm": 1},
            },
            "success_rate_by_source": {
                "serper": {"total": 10, "extracted": 6, "success_rate": 60.0},
                "google_places": {"total": 5, "extracted": 5, "success_rate": 100.0},
            },
            "field_null_rates": {
                "entity_name": {"null_count": 1, "total": 10, "null_rate": 10.0},
                "postcode": {"null_count": 7, "total": 10, "null_rate": 70.0},
            },
            "recent_failures": [
                {
                    "id": "f1",
                    "source": "serper",
                    "error_message": "timeout",
                    "last_attempt_at": datetime(2026, 1, 17, 10, 0, 0, tzinfo=timezone.utc),
                }
            ],
            "llm_usage": {
                "total_llm_extractions": 2,
                "by_model": {"claude-haiku-20250318": 2},
                "input_tokens": 1000,
                "output_tokens": 200,
                "estimated_cost": 0.004,
                "has_usage_data": True,
            },
            "merge_conflicts": 2,
        }

    def test_format_health_report_includes_sections(self):
        output = format_health_report(self.sample_metrics, use_color=False)

        self.assertIn("EXTRACTION HEALTH DASHBOARD", output)
        self.assertIn("SUMMARY", output)
        self.assertIn("SUCCESS RATE BY SOURCE", output)
        self.assertIn("FIELD NULL RATES", output)
        self.assertIn("RECENT FAILURES", output)
        self.assertIn("LLM USAGE", output)

    def test_format_health_report_uses_color_when_enabled(self):
        output = format_health_report(self.sample_metrics, use_color=True)

        self.assertIn("\x1b[33m", output)
        self.assertIn("\x1b[0m", output)

    def test_format_health_report_disables_color_when_requested(self):
        output = format_health_report(self.sample_metrics, use_color=False)

        self.assertNotIn("\x1b[", output)


if __name__ == "__main__":
    unittest.main()
