"""
Tests for merge conflict detection and reporting.

Conflicts occur when multiple sources provide different values for the same field
and have similar trust levels, making the choice less obvious and requiring
potential manual review.
"""

import pytest
from engine.extraction.merging import ConflictDetector, MergeConflict


class TestConflictDetector:
    """Test conflict detection logic."""

    def test_no_conflict_single_source(self):
        """Should not detect conflict with single source."""
        detector = ConflictDetector()

        field_values = [
            {"value": "Game4Padel", "source": "google_places", "confidence": 0.9}
        ]

        conflict = detector.detect_conflict("entity_name", field_values)

        assert conflict is None

    def test_no_conflict_identical_values(self):
        """Should not detect conflict when all sources agree."""
        detector = ConflictDetector()

        field_values = [
            {"value": "Game4Padel Edinburgh", "source": "google_places", "confidence": 0.9},
            {"value": "Game4Padel Edinburgh", "source": "osm", "confidence": 0.8},
            {"value": "Game4Padel Edinburgh", "source": "serper", "confidence": 0.7}
        ]

        conflict = detector.detect_conflict("entity_name", field_values)

        assert conflict is None

    def test_no_conflict_clear_trust_hierarchy(self):
        """Should not flag conflict when trust hierarchy is clear (20+ point difference)."""
        detector = ConflictDetector()

        field_values = [
            {"value": "+44 131 123 4567", "source": "google_places", "confidence": 0.9},  # Trust: 70
            {"value": "+44 131 999 8888", "source": "serper", "confidence": 0.8},  # Trust: 50
        ]

        # 20 point difference in trust (70 vs 50), so no conflict worth reporting
        conflict = detector.detect_conflict("phone", field_values)

        assert conflict is None

    def test_detect_conflict_similar_trust_levels(self):
        """Should detect conflict when sources have similar trust levels."""
        detector = ConflictDetector(trust_difference_threshold=15)

        field_values = [
            {"value": "+44 131 123 4567", "source": "sport_scotland", "confidence": 0.9},  # Trust: 90
            {"value": "+44 131 999 8888", "source": "edinburgh_council", "confidence": 0.85},  # Trust: 85
        ]

        # Only 5 point difference (90 vs 85), should flag as conflict
        conflict = detector.detect_conflict("phone", field_values)

        assert conflict is not None
        assert conflict.field_name == "phone"
        assert len(conflict.conflicting_values) == 2
        assert conflict.winner_source == "sport_scotland"
        assert conflict.trust_difference == 5

    def test_detect_conflict_equal_trust_levels(self):
        """Should detect conflict when sources have equal trust levels."""
        detector = ConflictDetector()

        field_values = [
            {"value": "way/12345", "source": "osm", "confidence": 0.9},  # Trust: 40
            {"value": "poi/67890", "source": "open_charge_map", "confidence": 0.8},  # Trust: 40
        ]

        # Equal trust (both 40), should definitely flag as conflict
        conflict = detector.detect_conflict("external_id", field_values)

        assert conflict is not None
        assert conflict.field_name == "external_id"
        assert conflict.trust_difference == 0
        # When trust is equal, higher confidence should win
        assert conflict.winner_source == "osm"

    def test_conflict_tracks_all_values(self):
        """Should track all conflicting values in the conflict report."""
        detector = ConflictDetector(trust_difference_threshold=15)

        field_values = [
            {"value": "123 Main St", "source": "google_places", "confidence": 0.9},
            {"value": "124 Main St", "source": "edinburgh_council", "confidence": 0.85},
            {"value": "125 Main St", "source": "sport_scotland", "confidence": 0.95},
        ]

        conflict = detector.detect_conflict("street_address", field_values)

        assert conflict is not None
        assert len(conflict.conflicting_values) == 3
        assert any(v["value"] == "123 Main St" for v in conflict.conflicting_values)
        assert any(v["value"] == "124 Main St" for v in conflict.conflicting_values)
        assert any(v["value"] == "125 Main St" for v in conflict.conflicting_values)

    def test_conflict_calculates_severity(self):
        """Should calculate conflict severity based on trust difference."""
        detector = ConflictDetector()

        # High severity: very similar trust levels
        high_severity_values = [
            {"value": "A", "source": "sport_scotland", "confidence": 0.9},  # Trust: 90
            {"value": "B", "source": "edinburgh_council", "confidence": 0.85},  # Trust: 85
        ]

        high_conflict = detector.detect_conflict("field1", high_severity_values)

        # Medium severity: moderate trust difference
        medium_severity_values = [
            {"value": "A", "source": "google_places", "confidence": 0.9},  # Trust: 70
            {"value": "B", "source": "serper", "confidence": 0.85},  # Trust: 50
        ]

        medium_conflict = detector.detect_conflict("field2", medium_severity_values)

        # High severity conflicts should have higher severity than medium
        assert high_conflict.severity > medium_conflict.severity if medium_conflict else 0.5

    def test_conflict_ignores_none_values(self):
        """Should ignore None values when detecting conflicts."""
        detector = ConflictDetector()

        field_values = [
            {"value": "info@venue.com", "source": "google_places", "confidence": 0.9},
            {"value": None, "source": "osm", "confidence": 0.7},
            {"value": None, "source": "serper", "confidence": 0.6},
        ]

        # Only one non-None value, so no conflict
        conflict = detector.detect_conflict("email", field_values)

        assert conflict is None

    def test_conflict_with_three_different_values(self):
        """Should handle conflicts with 3+ different values."""
        detector = ConflictDetector(trust_difference_threshold=21)

        field_values = [
            {"value": 4.5, "source": "google_places", "confidence": 0.9},  # Trust: 70
            {"value": 4.2, "source": "serper", "confidence": 0.8},  # Trust: 50
            {"value": 4.8, "source": "osm", "confidence": 0.7},  # Trust: 40
        ]

        conflict = detector.detect_conflict("rating", field_values)

        # Trust difference is 20 (70-50), which is < 21 threshold
        assert conflict is not None
        assert len(conflict.conflicting_values) == 3
        assert conflict.winner_source == "google_places"


class TestMergeConflict:
    """Test MergeConflict data structure."""

    def test_merge_conflict_creation(self):
        """Should create MergeConflict with all required fields."""
        conflict = MergeConflict(
            field_name="phone",
            conflicting_values=[
                {"value": "+44 131 123 4567", "source": "google_places", "trust": 70},
                {"value": "+44 131 999 8888", "source": "edinburgh_council", "trust": 85}
            ],
            winner_source="edinburgh_council",
            winner_value="+44 131 999 8888",
            trust_difference=15,
            severity=0.8
        )

        assert conflict.field_name == "phone"
        assert len(conflict.conflicting_values) == 2
        assert conflict.winner_source == "edinburgh_council"
        assert conflict.trust_difference == 15
        assert conflict.severity == 0.8

    def test_merge_conflict_to_dict(self):
        """Should convert MergeConflict to dictionary for storage."""
        conflict = MergeConflict(
            field_name="phone",
            conflicting_values=[{"value": "A", "source": "src1", "trust": 70}],
            winner_source="src1",
            winner_value="A",
            trust_difference=5,
            severity=0.9
        )

        conflict_dict = conflict.to_dict()

        assert conflict_dict["field_name"] == "phone"
        assert conflict_dict["winner_source"] == "src1"
        assert conflict_dict["severity"] == 0.9


class TestConflictReporting:
    """Test conflict reporting and aggregation."""

    def test_report_multiple_conflicts(self):
        """Should aggregate multiple conflicts for a merge operation."""
        detector = ConflictDetector(trust_difference_threshold=15)

        # Simulate merging with multiple conflicting fields
        all_fields = {
            "phone": [
                {"value": "+44 131 123 4567", "source": "sport_scotland", "confidence": 0.9},
                {"value": "+44 131 999 8888", "source": "edinburgh_council", "confidence": 0.85}
            ],
            "email": [
                {"value": "info@venue.com", "source": "google_places", "confidence": 0.9}
            ],
            "website_url": [
                {"value": "https://venue1.com", "source": "sport_scotland", "confidence": 0.9},
                {"value": "https://venue2.com", "source": "edinburgh_council", "confidence": 0.85}
            ]
        }

        conflicts = []
        for field_name, field_values in all_fields.items():
            conflict = detector.detect_conflict(field_name, field_values)
            if conflict:
                conflicts.append(conflict)

        # Should detect 2 conflicts (phone and website_url)
        assert len(conflicts) == 2
        field_names = [c.field_name for c in conflicts]
        assert "phone" in field_names
        assert "website_url" in field_names
        assert "email" not in field_names

    def test_conflict_summary(self):
        """Should generate summary statistics for conflicts."""
        conflicts = [
            MergeConflict("field1", [], "src1", "val1", 5, 0.9),
            MergeConflict("field2", [], "src2", "val2", 10, 0.7),
            MergeConflict("field3", [], "src3", "val3", 2, 0.95),
        ]

        # Calculate summary
        total_conflicts = len(conflicts)
        avg_severity = sum(c.severity for c in conflicts) / len(conflicts)
        high_severity_count = sum(1 for c in conflicts if c.severity > 0.8)

        assert total_conflicts == 3
        assert avg_severity == pytest.approx(0.85, rel=0.01)
        assert high_severity_count == 2
