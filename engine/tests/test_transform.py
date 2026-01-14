"""
Tests for the transform module.

Tests transformation logic for converting raw connector data into the format
expected by ingest_venue().
"""

import pytest
import json
from engine.ingestion.transform import (
    transform_edinburgh_council_feature,
    _extract_categories,
    _extract_attributes,
    load_and_transform_raw_file
)


class TestTransformEdinburghCouncilFeature:
    """Tests for transform_edinburgh_council_feature function."""

    def test_transform_basic_feature(self):
        """Test transformation of a basic Edinburgh Council feature."""
        feature = {
            'type': 'Feature',
            'id': '123',
            'geometry': {
                'type': 'Point',
                'coordinates': [-3.1883, 55.9533]
            },
            'properties': {
                'NAME': 'Meadowbank Sports Centre',
                'ADDRESS': '139 London Road',
                'POSTCODE': 'EH7 6AE',
                'PHONE': '0131 661 5351',
                'CATEGORY': 'Sports Centre'
            }
        }

        result = transform_edinburgh_council_feature(feature)

        assert result['entity_name'] == 'Meadowbank Sports Centre'
        assert result['slug'] == 'meadowbank-sports-centre'
        assert result['street_address'] == '139 London Road'
        assert result['postcode'] == 'EH7 6AE'
        assert result['phone'] == '0131 661 5351'
        assert result['city'] == 'Edinburgh'
        assert result['country'] == 'Scotland'
        assert result['latitude'] == 55.9533
        assert result['longitude'] == -3.1883

    def test_transform_extracts_categories(self):
        """Test that categories are extracted correctly."""
        feature = {
            'geometry': {'coordinates': []},
            'properties': {
                'NAME': 'Test Facility',
                'CATEGORY': 'Sports Centre'
            }
        }

        result = transform_edinburgh_council_feature(feature)

        assert 'canonical_categories' in result
        assert 'Sports Centre' in result['canonical_categories']

    def test_transform_handles_missing_coordinates(self):
        """Test transformation handles missing geometry gracefully."""
        feature = {
            'geometry': {},
            'properties': {
                'NAME': 'Test Facility'
            }
        }

        result = transform_edinburgh_council_feature(feature)

        assert result['latitude'] is None
        assert result['longitude'] is None

    def test_transform_includes_source_info(self):
        """Test that source tracking information is included."""
        feature = {
            'id': 'abc123',
            'geometry': {'coordinates': []},
            'properties': {
                'NAME': 'Test Facility',
                'DATASET_NAME': 'sports_facilities'
            }
        }

        result = transform_edinburgh_council_feature(feature)

        assert 'source_info' in result
        source_info = json.loads(result['source_info'])
        assert source_info['source'] == 'edinburgh_council'
        assert source_info['dataset'] == 'sports_facilities'
        assert source_info['feature_id'] == 'abc123'

    def test_transform_includes_external_ids(self):
        """Test that external IDs are tracked."""
        feature = {
            'id': 'feature_456',
            'geometry': {'coordinates': []},
            'properties': {'NAME': 'Test Facility'}
        }

        result = transform_edinburgh_council_feature(feature)

        assert 'external_ids' in result
        external_ids = json.loads(result['external_ids'])
        assert external_ids['edinburgh_council_id'] == 'feature_456'

    def test_transform_handles_alternate_name_fields(self):
        """Test that alternate name fields are handled."""
        feature1 = {
            'geometry': {'coordinates': []},
            'properties': {'FACILITY_NAME': 'Test Facility 1'}
        }

        feature2 = {
            'geometry': {'coordinates': []},
            'properties': {'SITE_NAME': 'Test Facility 2'}
        }

        result1 = transform_edinburgh_council_feature(feature1)
        result2 = transform_edinburgh_council_feature(feature2)

        assert result1['entity_name'] == 'Test Facility 1'
        assert result2['entity_name'] == 'Test Facility 2'

    def test_transform_handles_alternate_address_fields(self):
        """Test that alternate address fields are handled."""
        feature = {
            'geometry': {'coordinates': []},
            'properties': {
                'NAME': 'Test',
                'STREET_ADDRESS': '123 Main St',
                'CONTACT_NUMBER': '555-1234',
                'CONTACT_EMAIL': 'test@example.com'
            }
        }

        result = transform_edinburgh_council_feature(feature)

        assert result['street_address'] == '123 Main St'
        assert result['phone'] == '555-1234'
        assert result['email'] == 'test@example.com'

    def test_transform_captures_discovered_attributes(self):
        """Test that extra fields are captured in discovered_attributes."""
        feature = {
            'geometry': {'coordinates': []},
            'properties': {
                'NAME': 'Test',
                'CUSTOM_FIELD': 'custom_value',
                'ANOTHER_FIELD': 123
            }
        }

        result = transform_edinburgh_council_feature(feature)

        assert 'discovered_attributes' in result
        discovered = json.loads(result['discovered_attributes'])
        assert discovered['CUSTOM_FIELD'] == 'custom_value'
        assert discovered['ANOTHER_FIELD'] == 123

    def test_transform_slug_handles_special_characters(self):
        """Test that slug generation handles special characters."""
        feature = {
            'geometry': {'coordinates': []},
            'properties': {
                'NAME': 'Test / Example Facility'
            }
        }

        result = transform_edinburgh_council_feature(feature)

        assert result['slug'] == 'test---example-facility'


class TestExtractCategories:
    """Tests for _extract_categories helper function."""

    def test_extract_category_from_category_field(self):
        """Test extracting from CATEGORY field."""
        properties = {'CATEGORY': 'Sports Centre'}
        result = _extract_categories(properties)
        assert 'Sports Centre' in result

    def test_extract_category_from_type_field(self):
        """Test extracting from TYPE field."""
        properties = {'TYPE': 'Library'}
        result = _extract_categories(properties)
        assert 'Library' in result

    def test_extract_category_from_facility_type(self):
        """Test extracting from FACILITY_TYPE field."""
        properties = {'FACILITY_TYPE': 'Community Center'}
        result = _extract_categories(properties)
        assert 'Community Center' in result

    def test_extract_multiple_categories(self):
        """Test extracting from multiple fields."""
        properties = {
            'CATEGORY': 'Sports',
            'TYPE': 'Leisure',
            'FACILITY_TYPE': 'Recreation'
        }
        result = _extract_categories(properties)
        assert len(result) == 3
        assert 'Sports' in result
        assert 'Leisure' in result
        assert 'Recreation' in result

    def test_extract_default_category(self):
        """Test default category when none found."""
        properties = {}
        result = _extract_categories(properties)
        assert result == ['Community Facility']


class TestExtractAttributes:
    """Tests for _extract_attributes helper function."""

    def test_extract_capacity(self):
        """Test extracting capacity attribute."""
        properties = {'CAPACITY': 500}
        result = _extract_attributes(properties)
        assert result['capacity'] == 500

    def test_extract_area(self):
        """Test extracting area attribute."""
        properties = {'AREA_SQM': 1500.5}
        result = _extract_attributes(properties)
        assert result['area_sqm'] == 1500.5

    def test_extract_facilities(self):
        """Test extracting facilities attribute."""
        properties = {'FACILITIES': 'Changing rooms, Showers'}
        result = _extract_attributes(properties)
        assert result['facilities'] == 'Changing rooms, Showers'

    def test_extract_sports_offered(self):
        """Test extracting sports offered attribute."""
        properties = {'SPORTS_OFFERED': 'Tennis, Badminton'}
        result = _extract_attributes(properties)
        assert result['sports_offered'] == 'Tennis, Badminton'

    def test_extract_wheelchair_accessible_yes(self):
        """Test extracting wheelchair accessible attribute (yes)."""
        for yes_value in ['Yes', 'Y', True, 'true', '1']:
            properties = {'ACCESSIBLE': yes_value}
            result = _extract_attributes(properties)
            assert result['wheelchair_accessible'] is True

    def test_extract_wheelchair_accessible_no(self):
        """Test extracting wheelchair accessible attribute (no)."""
        for no_value in ['No', 'N', False, 'false', '0']:
            properties = {'ACCESSIBLE': no_value}
            result = _extract_attributes(properties)
            assert result['wheelchair_accessible'] is False

    def test_extract_opening_hours(self):
        """Test extracting opening hours attribute."""
        properties = {'OPENING_HOURS': 'Mon-Fri 9am-5pm'}
        result = _extract_attributes(properties)
        assert result['opening_hours'] == 'Mon-Fri 9am-5pm'

    def test_extract_multiple_attributes(self):
        """Test extracting multiple attributes."""
        properties = {
            'CAPACITY': 200,
            'AREA_SQM': 800,
            'ACCESSIBLE': 'Yes'
        }
        result = _extract_attributes(properties)
        assert result['capacity'] == 200
        assert result['area_sqm'] == 800
        assert result['wheelchair_accessible'] is True

    def test_extract_empty_when_no_attributes(self):
        """Test that empty dict is returned when no attributes found."""
        properties = {'NAME': 'Test', 'ADDRESS': '123 Main'}
        result = _extract_attributes(properties)
        assert result == {}


class TestLoadAndTransformRawFile:
    """Tests for load_and_transform_raw_file function."""

    def test_load_and_transform_valid_file(self, tmp_path):
        """Test loading and transforming a valid raw file."""
        # Create temporary test file
        test_file = tmp_path / "test_data.json"
        test_data = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {'coordinates': [-3.1883, 55.9533]},
                    'properties': {
                        'NAME': 'Test Facility 1',
                        'CATEGORY': 'Sports'
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': {'coordinates': [-3.2, 55.95]},
                    'properties': {
                        'NAME': 'Test Facility 2',
                        'CATEGORY': 'Leisure'
                    }
                }
            ]
        }

        with open(test_file, 'w') as f:
            json.dump(test_data, f)

        # Transform the file
        result = load_and_transform_raw_file(str(test_file), 'edinburgh_council')

        assert len(result) == 2
        assert result[0]['entity_name'] == 'Test Facility 1'
        assert result[1]['entity_name'] == 'Test Facility 2'

    def test_load_and_transform_unsupported_source(self, tmp_path):
        """Test that unsupported source raises ValueError."""
        test_file = tmp_path / "test_data.json"
        test_data = {'features': []}

        with open(test_file, 'w') as f:
            json.dump(test_data, f)

        with pytest.raises(ValueError, match="Unsupported source type"):
            load_and_transform_raw_file(str(test_file), 'unknown_source')

    def test_load_and_transform_missing_file(self):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_and_transform_raw_file('/nonexistent/file.json', 'edinburgh_council')
