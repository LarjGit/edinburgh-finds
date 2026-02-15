"""
Tests for Overture local extractor.

Validates Phase-1 extraction boundary compliance for R-02.2.
"""

import inspect
import json
from pathlib import Path

import pytest

from engine.extraction.extractors.overture_local_extractor import OvertureLocalExtractor
from engine.extraction.run import get_extractor_for_source


REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "overture" / "overture_places_contract_samples.json"


def _load_valid_row_sample() -> dict:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return payload["valid_samples"][0]


class TestEnginePurity:
    """Validates system-vision.md Invariant 1 (Engine Purity)."""

    def test_extractor_contains_no_domain_literals(self):
        source = inspect.getsource(OvertureLocalExtractor)
        forbidden = ["tennis", "padel", "wine", "restaurant"]
        violations = [term for term in forbidden if term.lower() in source.lower()]
        assert not violations, (
            "Engine Purity violation (system-vision.md Invariant 1): "
            f"found forbidden domain terms in extractor: {violations}"
        )


class TestExtractionBoundary:
    """Validates target-architecture.md Section 4.2 extraction boundary."""

    def test_extractor_outputs_only_phase1_fields_for_row_sample(self, mock_ctx):
        extractor = OvertureLocalExtractor()
        extracted = extractor.extract(_load_valid_row_sample(), ctx=mock_ctx)
        validated = extractor.validate(extracted)
        attributes, discovered = extractor.split_attributes(validated)

        # Required Phase-1 primitives from fixture input.
        assert attributes["entity_name"] == "Example Club"
        assert attributes["raw_categories"] == ["sports_centre"]
        assert attributes["longitude"] == -3.1902
        assert attributes["latitude"] == 55.9521
        assert validated["external_id"] == "08f2a3f1b87c9b1f03f0c1671dc10000"

        # Forbidden Phase-2 fields.
        forbidden = [
            "canonical_activities",
            "canonical_roles",
            "canonical_place_types",
            "canonical_access",
            "modules",
        ]
        assert all(field not in validated for field in forbidden), (
            "Extraction boundary violation: Phase-1 output contained canonical/module fields"
        )

        # Raw observation remains connector-native evidence.
        assert discovered["overture_source_datasets"] == ["osm"]

    def test_extractor_rejects_feature_collection_wrapper(self, mock_ctx):
        extractor = OvertureLocalExtractor()
        with pytest.raises(ValueError, match="FeatureCollection wrapper is not accepted"):
            extractor.extract({"type": "FeatureCollection", "features": []}, ctx=mock_ctx)


def test_source_dispatch_returns_overture_extractor():
    extractor = get_extractor_for_source("overture_local")
    assert isinstance(extractor, OvertureLocalExtractor)
