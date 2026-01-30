"""
Tests for Sport Scotland Extractor

Validates compliance with:
- system-vision.md Invariant 1 (Engine Purity)
- architecture.md Section 4.2 (Extraction Boundary Contract)
"""

import inspect
import pytest
from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor


class TestEnginePurity:
    """Validates system-vision.md Invariant 1: Engine Purity"""

    def test_extractor_contains_no_domain_literals(self):
        """
        Validates: system-vision.md Invariant 1 (Engine Purity)

        The engine must contain zero domain knowledge. No domain-specific
        terms may exist in engine code.

        Forbidden terms: tennis, padel, wine, restaurant (and variations)
        """
        source = inspect.getsource(SportScotlandExtractor)

        # Forbidden domain-specific terms
        forbidden = ["tennis", "padel", "wine", "restaurant"]

        violations = []
        for term in forbidden:
            if term.lower() in source.lower():
                violations.append(term)

        assert not violations, (
            f"Engine Purity violation (system-vision.md Invariant 1): "
            f"Found forbidden domain terms in extractor: {violations}. "
            f"Engine code must contain zero domain knowledge."
        )


class TestExtractionBoundary:
    """Validates architecture.md Section 4.2: Extraction Boundary Contract"""

    def test_extractor_outputs_only_primitives_and_raw_observations(self, mock_ctx):
        """
        Validates: architecture.md Section 4.2 (Extraction Boundary)

        Phase 1 extractors must output ONLY:
        - Schema primitives (entity_name, latitude, longitude, etc.)
        - Raw observations (raw_categories, description, connector-native fields)

        FORBIDDEN outputs:
        - canonical_* dimensions
        - modules or module fields
        - domain-specific interpreted fields (e.g., tennis_*, padel_*)
        """
        extractor = SportScotlandExtractor()

        # Mock Sport Scotland GeoJSON feature with tennis facility
        raw_data = {
            "type": "Feature",
            "id": "tennis_courts.123",
            "geometry": {
                "type": "Point",
                "coordinates": [-3.1883, 55.9533]  # Edinburgh (lng, lat in GeoJSON)
            },
            "properties": {
                "name": "Test Tennis Courts",
                "facility_type": "Tennis Courts",
                "address": "123 Test Street",
                "postcode": "EH1 1AA",
                "phone": "01312345678",
                "website": "https://example.com",
                "number_of_courts": "4",
                "indoor_outdoor": "outdoor",
                "floodlit": "yes",
                "surface_type": "hard",
                "ownership": "public"
            }
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)

        # Forbidden: Domain-specific interpreted fields
        forbidden_prefixes = ["tennis_", "padel_", "wine_", "restaurant_"]
        violations = []

        for key in extracted.keys():
            for prefix in forbidden_prefixes:
                if key.startswith(prefix):
                    violations.append(key)

        assert not violations, (
            f"Extraction Boundary violation (architecture.md 4.2): "
            f"Extractor emitted forbidden domain-specific fields: {violations}. "
            f"Phase 1 extractors must output ONLY schema primitives + raw observations. "
            f"Domain interpretation belongs in Phase 2 (Lens Application)."
        )

        # Also check for "tennis" boolean flag (also forbidden interpretation)
        assert "tennis" not in extracted, (
            "Extraction Boundary violation: 'tennis' boolean flag is semantic "
            "interpretation and belongs in Phase 2 (Lens Application), not Phase 1 extraction."
        )


class TestExtractionCorrectness:
    """Validates extractor still extracts primitives and raw observations correctly"""

    @pytest.fixture
    def sample_geojson_feature(self):
        """Sample Sport Scotland GeoJSON feature for testing"""
        return {
            "type": "Feature",
            "id": "facility.456",
            "geometry": {
                "type": "Point",
                "coordinates": [-3.1883, 55.9533]  # Edinburgh (lng, lat)
            },
            "properties": {
                "name": "Meadowbank Sports Centre",
                "facility_type": "Sports Centre",
                "address": "139 London Road",
                "postcode": "EH7 6AE",
                "phone": "0131 661 5351",
                "website": "https://www.edinburghleisure.co.uk/venues/meadowbank-sports-centre",
                "surface_type": "synthetic",
                "ownership": "council"
            }
        }

    def test_extract_schema_primitives(self, sample_geojson_feature, mock_ctx):
        """
        Validates extractor outputs schema primitives correctly

        Schema primitives: entity_name, latitude, longitude, street_address,
        postcode, phone, website, external_id
        """
        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sample_geojson_feature, ctx=mock_ctx)

        # Verify schema primitives extracted
        assert extracted["entity_name"] == "Meadowbank Sports Centre"
        assert extracted["latitude"] == 55.9533
        assert extracted["longitude"] == -3.1883
        assert extracted["street_address"] == "139 London Road"
        assert extracted["postcode"] == "EH7 6AE"
        assert extracted["phone"] == "+441316615351"  # E.164 format
        assert extracted["website"] == "https://www.edinburghleisure.co.uk/venues/meadowbank-sports-centre"
        assert extracted["external_id"] == "facility.456"

    def test_extract_raw_observations(self, sample_geojson_feature, mock_ctx):
        """
        Validates extractor captures connector-native fields as raw observations

        Raw observations: facility_type, surface_type, ownership
        These will be interpreted by Phase 2 (Lens Application)
        """
        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sample_geojson_feature, ctx=mock_ctx)

        # Verify raw observations captured (connector-native fields)
        assert extracted["facility_type"] == "Sports Centre"
        assert extracted["surface_type"] == "synthetic"
        assert extracted["ownership"] == "council"

        # These raw observations will flow to discovered_attributes
        # and be interpreted by lens mapping rules in Phase 2
