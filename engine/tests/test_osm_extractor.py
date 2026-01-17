"""
Tests for OSM Extractor

This module tests the OSMExtractor which transforms raw OpenStreetMap Overpass
API responses into structured listing fields using LLM-based extraction.

OSM provides structured but free-form tag data (key-value pairs like sport=padel,
addr:city=Edinburgh), which requires intelligent parsing to map to our schema.
The LLM handles:
- Tag mapping to schema fields (sport=* → facilities, amenity=* → categories)
- Multi-lingual tag handling (name:en, name:fr, etc.)
- Address extraction from OSM addr:* tags
- Missing data handling with appropriate null values
- OSM ID extraction for deduplication

Test Coverage:
- Extractor initialization and source_name property
- LLM-based extraction from OSM elements
- Tag aggregation (combining tags from nodes, ways, relations)
- OSM ID extraction
- Null semantics enforcement
- Attribute splitting (schema-defined vs discovered)
- Multi-lingual tag handling
- Error handling for extraction failures
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def osm_fixture():
    """Load the OSM Overpass sports facility test fixture"""
    fixture_path = Path(__file__).parent / "fixtures" / "osm_overpass_sports_facility.json"
    with open(fixture_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def osm_minimal_fixture():
    """Load the minimal OSM element (tests null semantics)"""
    fixture_path = Path(__file__).parent / "fixtures" / "osm_minimal_element.json"
    with open(fixture_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def osm_single_element(osm_fixture):
    """Extract the first element for single-element tests"""
    return {"elements": [osm_fixture["elements"][0]]}


class TestOSMExtractorInitialization:
    """Test OSM extractor initialization and basic properties"""

    def test_osm_extractor_can_be_imported(self):
        """Test that OSMExtractor class can be imported"""
        try:
            from engine.extraction.extractors.osm_extractor import OSMExtractor
            assert OSMExtractor is not None
        except ImportError:
            pytest.fail("Failed to import OSMExtractor - implementation not yet created")

    def test_osm_extractor_can_be_instantiated(self):
        """Test that OSMExtractor can be instantiated"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor

        # Pass mock LLM client to avoid requiring API key
        mock_client = Mock()
        extractor = OSMExtractor(llm_client=mock_client)
        assert extractor is not None

    def test_osm_extractor_has_correct_source_name(self):
        """Test that source_name property returns 'openstreetmap'"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor

        # Pass mock LLM client to avoid requiring API key
        mock_client = Mock()
        extractor = OSMExtractor(llm_client=mock_client)
        assert extractor.source_name == "openstreetmap"


class TestOSMTagAggregation:
    """Test tag aggregation from OSM elements"""

    def test_aggregate_tags_combines_element_data(self, osm_fixture):
        """Test that OSM element tags are aggregated into single context"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor

        mock_client = Mock()
        extractor = OSMExtractor(llm_client=mock_client)
        aggregated = extractor._aggregate_osm_elements(osm_fixture["elements"])

        # Should combine all element tags
        assert "sport" in aggregated.lower() or "padel" in aggregated.lower()
        assert "edinburgh" in aggregated.lower()

    def test_aggregate_tags_includes_element_id(self, osm_fixture):
        """Test that aggregation includes OSM element IDs for deduplication"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor

        mock_client = Mock()
        extractor = OSMExtractor(llm_client=mock_client)
        aggregated = extractor._aggregate_osm_elements(osm_fixture["elements"])

        # Should include element ID
        first_element_id = str(osm_fixture["elements"][0]["id"])
        assert first_element_id in aggregated

    def test_aggregate_tags_handles_coordinates(self, osm_fixture):
        """Test that aggregation preserves coordinate information"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor

        mock_client = Mock()
        extractor = OSMExtractor(llm_client=mock_client)
        aggregated = extractor._aggregate_osm_elements(osm_fixture["elements"])

        # Should mention lat/lon or coordinates
        assert "lat" in aggregated.lower() or "latitude" in aggregated.lower()


class TestOSMExtraction:
    """Test OSM extraction with LLM"""

    def test_extract_handles_osm_elements(self, osm_fixture):
        """Test that extract processes OSM elements correctly"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor
        from engine.extraction.models.entity_extraction import EntityExtraction

        # Create mock LLM client with expected response
        mock_client = Mock()
        mock_extraction = Mock(spec=EntityExtraction)
        mock_extraction.model_dump.return_value = {
            "entity_name": "Edinburgh Padel Club",
            "entity_type": "VENUE",
            "city": "Edinburgh",
            "latitude": 55.9533,
            "longitude": -3.1883,
            "postcode": "EH1 1AA",
            "padel": True,
            "padel_total_courts": 2
        }
        mock_client.extract.return_value = mock_extraction

        extractor = OSMExtractor(llm_client=mock_client)
        extracted = extractor.extract(osm_fixture)

        # Verify LLM was called
        assert mock_client.extract.called
        assert extracted["entity_name"] == "Edinburgh Padel Club"
        assert extracted["entity_type"] == "VENUE"

    def test_extract_raises_error_on_empty_elements(self):
        """Test that extract raises ValueError when no elements found"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor

        mock_client = Mock()
        extractor = OSMExtractor(llm_client=mock_client)

        empty_data = {"elements": []}

        with pytest.raises(ValueError, match="No OSM elements found"):
            extractor.extract(empty_data)

    def test_extract_extracts_osm_id(self, osm_fixture):
        """Test that extract captures OSM element ID to external_ids"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor
        from engine.extraction.models.entity_extraction import EntityExtraction

        # Create mock LLM client
        mock_client = Mock()
        mock_extraction = Mock(spec=EntityExtraction)
        mock_extraction.model_dump.return_value = {
            "entity_name": "Edinburgh Padel Club",
            "entity_type": "VENUE",
            "city": "Edinburgh"
        }
        mock_client.extract.return_value = mock_extraction

        extractor = OSMExtractor(llm_client=mock_client)
        extracted = extractor.extract(osm_fixture)

        # OSM ID should be added to external_ids
        assert "external_ids" in extracted
        assert "osm" in extracted["external_ids"]

    def test_extract_uses_osm_specific_prompt(self, osm_fixture):
        """Test that extract uses OSM-specific system message"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor
        from engine.extraction.models.entity_extraction import EntityExtraction

        mock_client = Mock()
        mock_extraction = Mock(spec=EntityExtraction)
        mock_extraction.model_dump.return_value = {
            "entity_name": "Test Venue",
            "entity_type": "VENUE"
        }
        mock_client.extract.return_value = mock_extraction

        extractor = OSMExtractor(llm_client=mock_client)
        extractor.extract(osm_fixture)

        # Verify system_message was passed
        call_kwargs = mock_client.extract.call_args.kwargs
        assert "system_message" in call_kwargs
        assert call_kwargs["system_message"] == extractor.system_message


class TestOSMValidation:
    """Test OSM validation logic"""

    def test_validate_requires_entity_name(self):
        """Test that validation requires entity_name field"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor

        mock_client = Mock()
        extractor = OSMExtractor(llm_client=mock_client)

        # Missing entity_name
        invalid_data = {
            "entity_type": "VENUE",
            "city": "Edinburgh"
        }

        with pytest.raises(ValueError, match="entity_name"):
            extractor.validate(invalid_data)

    def test_validate_passes_valid_data(self):
        """Test that validation passes for valid extracted data"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor

        mock_client = Mock()
        extractor = OSMExtractor(llm_client=mock_client)

        valid_data = {
            "entity_name": "Edinburgh Padel Club",
            "entity_type": "VENUE",
            "city": "Edinburgh",
            "padel": True
        }

        # Should not raise
        result = extractor.validate(valid_data)
        assert result == valid_data


class TestOSMAttributeSplitting:
    """Test attribute splitting for OSM-extracted data"""

    def test_split_attributes_separates_schema_and_discovered(self):
        """Test that split_attributes correctly separates fields"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor

        mock_client = Mock()
        extractor = OSMExtractor(llm_client=mock_client)

        extracted = {
            "entity_name": "Edinburgh Padel Club",
            "entity_type": "VENUE",
            "city": "Edinburgh",
            "padel": True,
            "custom_osm_tag": "custom value",
            "osm_specific_field": 123
        }

        attributes, discovered = extractor.split_attributes(extracted)

        # Schema-defined fields should be in attributes
        assert "entity_name" in attributes
        assert "city" in attributes
        assert "padel" in attributes

    def test_split_attributes_preserves_nulls(self):
        """Test that split_attributes preserves null values correctly"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor

        mock_client = Mock()
        extractor = OSMExtractor(llm_client=mock_client)

        extracted = {
            "entity_name": "Test Venue",
            "entity_type": "VENUE",
            "phone": None,  # Explicitly null
            "website_url": None
        }

        attributes, discovered = extractor.split_attributes(extracted)

        # Nulls should be preserved in attributes
        assert "phone" in attributes
        assert attributes["phone"] is None


class TestOSMMultilingualHandling:
    """Test handling of multi-lingual OSM tags"""

    def test_aggregate_handles_multilingual_names(self):
        """Test that aggregation includes multilingual name tags"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor

        mock_client = Mock()
        extractor = OSMExtractor(llm_client=mock_client)

        multilingual_element = [{
            "type": "node",
            "id": 123,
            "lat": 55.95,
            "lon": -3.18,
            "tags": {
                "name": "Edinburgh Padel Club",
                "name:en": "Edinburgh Padel Club",
                "name:fr": "Club de Padel d'Édimbourg",
                "sport": "padel"
            }
        }]

        aggregated = extractor._aggregate_osm_elements(multilingual_element)

        # Should include multilingual names
        assert "name:en" in aggregated or "English" in aggregated


class TestOSMErrorHandling:
    """Test error handling for OSM extraction"""

    def test_extract_handles_llm_failure(self, osm_fixture):
        """Test that extract handles LLM extraction failures gracefully"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor

        # Mock LLM client that raises exception
        mock_client = Mock()
        mock_client.extract.side_effect = Exception("LLM extraction failed")

        extractor = OSMExtractor(llm_client=mock_client)

        with pytest.raises(Exception, match="LLM extraction failed"):
            extractor.extract(osm_fixture)

    def test_extract_handles_missing_tags(self):
        """Test that extract handles OSM elements with minimal tags"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor
        from engine.extraction.models.entity_extraction import EntityExtraction

        minimal_osm = {
            "elements": [{
                "type": "node",
                "id": 123,
                "lat": 55.95,
                "lon": -3.18,
                "tags": {
                    "sport": "padel"  # Only sport tag, no name or address
                }
            }]
        }

        mock_client = Mock()
        mock_extraction = Mock(spec=EntityExtraction)
        mock_extraction.model_dump.return_value = {
            "entity_name": "Unnamed Padel Facility",
            "entity_type": "VENUE",
            "padel": True,
            "latitude": 55.95,
            "longitude": -3.18
        }
        mock_client.extract.return_value = mock_extraction

        extractor = OSMExtractor(llm_client=mock_client)
        extracted = extractor.extract(minimal_osm)

        # Should extract successfully even with minimal data
        assert extracted["entity_name"] is not None
        assert extracted["padel"] is True


class TestOSMCoordinateExtraction:
    """Test coordinate extraction from OSM elements"""

    def test_extract_captures_coordinates(self, osm_fixture):
        """Test that extract captures latitude and longitude"""
        from engine.extraction.extractors.osm_extractor import OSMExtractor
        from engine.extraction.models.entity_extraction import EntityExtraction

        mock_client = Mock()
        mock_extraction = Mock(spec=EntityExtraction)
        mock_extraction.model_dump.return_value = {
            "entity_name": "Edinburgh Padel Club",
            "entity_type": "VENUE",
            "latitude": 55.9533,
            "longitude": -3.1883
        }
        mock_client.extract.return_value = mock_extraction

        extractor = OSMExtractor(llm_client=mock_client)
        extracted = extractor.extract(osm_fixture)

        # Coordinates should be present
        assert "latitude" in extracted
        assert "longitude" in extracted
        assert isinstance(extracted["latitude"], (int, float))
        assert isinstance(extracted["longitude"], (int, float))
