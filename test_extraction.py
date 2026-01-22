"""
Direct extraction test to validate the Entity model pipeline.
"""
import asyncio
import json
from pathlib import Path
from prisma import Prisma
from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

async def test_extraction():
    # Load the raw Google Places file
    file_path = Path("engine/data/raw/google_places/20260119_places_6_0ece5829.json")
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    print(f"✓ Loaded raw data with {len(raw_data.get('places', []))} places")

    # Get first place
    if not raw_data.get('places'):
        print("✗ No places in data")
        return

    place = raw_data['places'][0]
    print(f"\n📍 Testing extraction for: {place.get('displayName', {}).get('text', 'UNKNOWN')}")
    print(f"   Types: {place.get('types', [])}")

    # Create extractor
    extractor = GooglePlacesExtractor()

    # Extract
    try:
        extracted_data = extractor.extract(place)
        print(f"\n✓ Extraction successful!")
        print(f"   entity_name: {extracted_data.get('entity_name')}")
        print(f"   entity_class: {extracted_data.get('entity_class')}")
        print(f"   slug: {extracted_data.get('slug')}")
        print(f"   latitude: {extracted_data.get('latitude')}")
        print(f"   longitude: {extracted_data.get('longitude')}")
        print(f"   raw_categories: {extracted_data.get('raw_categories')}")

        # Try to create Entity in database
        db = Prisma()
        await db.connect()

        try:
            entity = await db.entity.create(
                data={
                    'entity_name': extracted_data['entity_name'],
                    'slug': extracted_data['slug'],
                    'entity_class': extracted_data.get('entity_class', 'place'),
                    'modules': json.dumps({}),
                    'latitude': extracted_data.get('latitude'),
                    'longitude': extracted_data.get('longitude'),
                    'street_address': extracted_data.get('street_address'),
                    'city': extracted_data.get('city'),
                    'postcode': extracted_data.get('postcode'),
                    'raw_categories': extracted_data.get('raw_categories', []),
                }
            )
            print(f"\n✓ Entity created in database!")
            print(f"   ID: {entity.id}")
            print(f"   Name: {entity.entity_name}")
            print(f"   raw_categories: {entity.raw_categories}")

        except Exception as e:
            print(f"\n✗ Failed to create entity: {e}")
        finally:
            await db.disconnect()

    except Exception as e:
        print(f"\n✗ Extraction failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_extraction())
