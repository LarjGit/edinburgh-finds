"""
Transform Module - Raw Data to Listing Format

⚠️ DEPRECATION NOTICE ⚠️
=========================

This module is part of the LEGACY ingestion pipeline and is being superseded
by the new extraction engine architecture.

**Old Architecture (this file):**
- Raw data → Transform → Ingest directly to database
- Tightly coupled transformation and ingestion
- No standardized interface across sources
- Limited observability and error handling

**New Architecture (engine/extraction/):**
- Raw data → Extract (BaseExtractor) → Validate → Merge → Ingest
- Clean separation of concerns with standardized BaseExtractor interface
- Schema-driven attribute splitting
- Built-in validation, quarantine, health monitoring, deduplication
- Multi-source merging with trust hierarchy

**Migration Path:**
- New code should use: `engine/extraction/extractors/edinburgh_council_extractor.py`
- This file remains functional for backward compatibility with existing tests
- Will be removed in Phase 8 (Integration & End-to-End Testing) after full migration

**For Edinburgh Council data, use:**
```python
from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

extractor = EdinburghCouncilExtractor()
extracted = extractor.extract(feature)
validated = extractor.validate(extracted)
attributes, discovered = extractor.split_attributes(validated)
```

This module provides transformation functions that convert raw connector data
into the format expected by the ingest_venue function. Each connector type
may have its own transformation logic to map source-specific fields to the
Universal Entity Framework schema.
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from engine.schema.types import EntityType


def transform_edinburgh_council_feature(feature: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a single Edinburgh Council GeoJSON feature into venue format.

    Args:
        feature: A GeoJSON feature from Edinburgh Council ArcGIS data

    Returns:
        dict: Venue data formatted for ingest_venue()
    """
    properties = feature.get('properties', {})
    geometry = feature.get('geometry', {})
    coordinates = geometry.get('coordinates', [])

    # Extract core fields
    entity_name = properties.get('NAME') or properties.get('FACILITY_NAME') or properties.get('SITE_NAME', 'Unknown')

    # Generate slug from name
    slug = entity_name.lower().replace(' ', '-').replace('/', '-')

    # Location data
    longitude = coordinates[0] if len(coordinates) > 0 else None
    latitude = coordinates[1] if len(coordinates) > 1 else None

    # Build the venue dict
    venue_data = {
        'entity_name': entity_name,
        'slug': slug,
        'entity_type': EntityType.VENUE,  # Use Enum
        'canonical_categories': _extract_categories(properties),

        # Location
        'street_address': properties.get('ADDRESS') or properties.get('STREET_ADDRESS'),
        'city': 'Edinburgh',
        'postcode': properties.get('POSTCODE'),
        'country': 'Scotland',
        'latitude': latitude,
        'longitude': longitude,

        # Contact
        'phone': properties.get('PHONE') or properties.get('CONTACT_NUMBER'),
        'email': properties.get('EMAIL') or properties.get('CONTACT_EMAIL'),
        'website_url': properties.get('WEBSITE') or properties.get('URL'),

        # Summary
        'summary': properties.get('DESCRIPTION') or properties.get('SUMMARY'),

        # Source tracking (as dict - ingest.py will convert to JSON)
        'source_info': {
            'source': 'edinburgh_council',
            'dataset': properties.get('DATASET_NAME', 'unknown'),
            'feature_id': feature.get('id') or properties.get('OBJECTID') or properties.get('FID')
        },

        # External IDs (as dict - ingest.py will convert to JSON)
        'external_ids': {
            'edinburgh_council_id': feature.get('id') or properties.get('OBJECTID') or properties.get('FID')
        },

        # Discovered attributes - capture all remaining fields (as dict - ingest.py will convert to JSON)
        'discovered_attributes': {
            k: v for k, v in properties.items()
            if k not in ['NAME', 'FACILITY_NAME', 'SITE_NAME', 'ADDRESS', 'STREET_ADDRESS',
                        'POSTCODE', 'PHONE', 'CONTACT_NUMBER', 'EMAIL', 'CONTACT_EMAIL',
                        'WEBSITE', 'URL', 'DESCRIPTION', 'SUMMARY', 'DATASET_NAME',
                        'OBJECTID', 'FID'] and v is not None
        }
    }

    # Extract specific attributes based on field names
    attributes = _extract_attributes(properties)
    if attributes:
        venue_data.update(attributes)

    return venue_data


def _extract_categories(properties: Dict[str, Any]) -> List[str]:
    """
    Extract category/categories from Edinburgh Council properties.

    Args:
        properties: Feature properties dictionary

    Returns:
        List of category strings
    """
    categories = []

    # Check various category fields
    if 'CATEGORY' in properties and properties['CATEGORY']:
        categories.append(properties['CATEGORY'])
    if 'TYPE' in properties and properties['TYPE']:
        categories.append(properties['TYPE'])
    if 'FACILITY_TYPE' in properties and properties['FACILITY_TYPE']:
        categories.append(properties['FACILITY_TYPE'])

    # Default category if none found
    if not categories:
        categories = ['Community Facility']

    return categories


def _extract_attributes(properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured attributes from Edinburgh Council properties.

    This function maps known Edinburgh Council fields to our attribute schema.
    Attributes here will be validated against the FieldSpec schema and stored
    in the `attributes` JSON column.

    Args:
        properties: Feature properties dictionary

    Returns:
        Dictionary of structured attributes
    """
    attributes = {}

    # Capacity/size attributes
    if 'CAPACITY' in properties and properties['CAPACITY']:
        attributes['capacity'] = properties['CAPACITY']

    if 'AREA_SQM' in properties and properties['AREA_SQM']:
        attributes['area_sqm'] = properties['AREA_SQM']

    # Facility attributes
    if 'FACILITIES' in properties and properties['FACILITIES']:
        attributes['facilities'] = properties['FACILITIES']

    if 'SPORTS_OFFERED' in properties and properties['SPORTS_OFFERED']:
        attributes['sports_offered'] = properties['SPORTS_OFFERED']

    # Accessibility
    if 'ACCESSIBLE' in properties and properties['ACCESSIBLE'] in ['Yes', 'Y', True, 'true', '1']:
        attributes['wheelchair_accessible'] = True
    elif 'ACCESSIBLE' in properties and properties['ACCESSIBLE'] in ['No', 'N', False, 'false', '0']:
        attributes['wheelchair_accessible'] = False

    # Opening hours (if structured)
    if 'OPENING_HOURS' in properties and properties['OPENING_HOURS']:
        attributes['opening_hours'] = properties['OPENING_HOURS']

    return attributes


def load_and_transform_raw_file(file_path: str, source: str = 'edinburgh_council') -> List[Dict[str, Any]]:
    """
    Load a raw JSON file and transform all features into venue format.

    Args:
        file_path: Path to the raw JSON file
        source: Source connector name (determines transformation logic)

    Returns:
        List of venue dictionaries ready for ingest_venue()

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If source type is not supported
    """
    # Load raw JSON
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    # Apply source-specific transformation
    if source == 'edinburgh_council':
        features = raw_data.get('features', [])
        return [transform_edinburgh_council_feature(feature) for feature in features]
    else:
        raise ValueError(f"Unsupported source type: {source}")


async def process_raw_ingestion(db, raw_ingestion_id: str):
    """
    Process a RawIngestion record: load file, transform, and ingest venues.

    This is the main entry point for the transform pipeline.

    Args:
        db: Connected Prisma database client
        raw_ingestion_id: ID of the RawIngestion record to process

    Returns:
        int: Number of venues successfully ingested
    """
    from engine.ingest import ingest_venue

    # Fetch the RawIngestion record
    raw_record = await db.rawingestion.find_unique(where={'id': raw_ingestion_id})

    if not raw_record:
        raise ValueError(f"RawIngestion record {raw_ingestion_id} not found")

    # Load and transform the raw data
    venues = load_and_transform_raw_file(raw_record.file_path, raw_record.source)

    # Ingest each venue
    success_count = 0
    for venue_data in venues:
        try:
            await ingest_venue(venue_data)
            success_count += 1
        except Exception as e:
            print(f"Failed to ingest venue {venue_data.get('entity_name')}: {e}")
            # Continue processing other venues

    return success_count
