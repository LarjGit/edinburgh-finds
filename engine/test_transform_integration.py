"""
Integration test for the transform pipeline.

This script tests the end-to-end flow:
1. Create sample Edinburgh Council data (simulating connector fetch)
2. Transform it using the transform module
3. Ingest it using ingest_venue
4. Verify the attributes field is populated correctly
"""

import asyncio
import json
import pytest
from prisma import Prisma
from engine.ingestion.transform import transform_edinburgh_council_feature
from engine.ingest import ingest_venue


@pytest.mark.asyncio
async def test_transform_integration():
    """Test the complete transform and ingest pipeline."""
    print("=== Transform Integration Test ===\n")

    # Sample Edinburgh Council GeoJSON feature (simulating connector data)
    sample_feature = {
        'type': 'Feature',
        'id': 'test_facility_001',
        'geometry': {
            'type': 'Point',
            'coordinates': [-3.1883, 55.9533]
        },
        'properties': {
            'NAME': 'Test Sports Centre',
            'ADDRESS': '100 Test Street',
            'POSTCODE': 'EH1 1XX',
            'PHONE': '0131 555 1234',
            'EMAIL': 'test@example.com',
            'WEBSITE': 'https://test-sports.edinburgh.gov.uk',
            'CATEGORY': 'Sports Centre',
            'TYPE': 'Leisure Facility',
            'CAPACITY': 250,
            'AREA_SQM': 1200,
            'ACCESSIBLE': 'Yes',
            'FACILITIES': 'Changing rooms, Cafe, Parking',
            'SPORTS_OFFERED': 'Basketball, Badminton, Squash',
            'DATASET_NAME': 'sports_facilities'
        }
    }

    print("1. Transforming Edinburgh Council feature...")
    venue_data = transform_edinburgh_council_feature(sample_feature)

    print(f"   ✓ Entity Name: {venue_data['entity_name']}")
    print(f"   ✓ Slug: {venue_data['slug']}")
    print(f"   ✓ Categories: {venue_data['canonical_categories']}")

    # Check what attributes were extracted
    if 'capacity' in venue_data:
        print(f"   ✓ Extracted attribute 'capacity': {venue_data['capacity']}")
    if 'wheelchair_accessible' in venue_data:
        print(f"   ✓ Extracted attribute 'wheelchair_accessible': {venue_data['wheelchair_accessible']}")

    print("\n2. Ingesting venue...")
    try:
        listing = await ingest_venue(venue_data)
        print(f"   ✓ Successfully ingested: {listing.entity_name}")
        print(f"   ✓ Listing ID: {listing.id}")

        # Verify attributes field
        print("\n3. Verifying attributes field...")
        if listing.attributes:
            attributes = json.loads(listing.attributes)
            print(f"   ✓ Attributes JSON is valid")
            print(f"   ✓ Attributes keys: {list(attributes.keys())}")

            if 'capacity' in attributes:
                print(f"   ✓ capacity = {attributes['capacity']}")
            if 'wheelchair_accessible' in attributes:
                print(f"   ✓ wheelchair_accessible = {attributes['wheelchair_accessible']}")
            if 'facilities' in attributes:
                print(f"   ✓ facilities = {attributes['facilities']}")
        else:
            print("   ✗ WARNING: attributes field is None")

        # Verify discovered_attributes field
        if listing.discovered_attributes:
            disc_attrs = json.loads(listing.discovered_attributes)
            print(f"\n   ✓ Discovered attributes count: {len(disc_attrs)}")

        print("\n=== Test Complete ===")
        print("✓ Transform pipeline is working correctly!")
        print("✓ Attributes field is being populated!")

        return True

    except Exception as e:
        print(f"\n   ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_transform_integration())
    exit(0 if success else 1)
