"""
Manual Test Script for Google Places Connector

This script tests the GooglePlacesConnector with a real "padel edinburgh" query
to verify end-to-end functionality with the Google Places API.

Prerequisites:
1. Copy engine/config/sources.yaml.example to engine/config/sources.yaml
2. Add your Google Places API key to sources.yaml (get key at https://developers.google.com/maps/documentation/places/web-service/get-api-key)
3. Ensure database is migrated (prisma generate && prisma db push)

Usage:
    python -m engine.scripts.run_google_places_connector
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


async def test_google_places_padel_query():
    """Test GooglePlacesConnector with 'padel edinburgh' query"""

    print("=" * 70)
    print("GOOGLE PLACES CONNECTOR MANUAL TEST")
    print("=" * 70)
    print()

    # Check if sources.yaml exists
    config_path = project_root / "engine" / "config" / "sources.yaml"
    if not config_path.exists():
        print("❌ ERROR: sources.yaml not found!")
        print()
        print("Setup Instructions:")
        print("1. Copy engine/config/sources.yaml.example to engine/config/sources.yaml")
        print("2. Edit sources.yaml and add your Google Places API key")
        print("3. Get a free API key at https://developers.google.com/maps/documentation/places/web-service/get-api-key")
        print()
        return False

    print("✓ Configuration file found")
    print()

    # Import and initialize connector
    try:
        from engine.ingestion.connectors.google_places import GooglePlacesConnector
        from engine.ingestion.deduplication import compute_content_hash
        print("✓ GooglePlacesConnector imported successfully")
    except ImportError as e:
        print(f"❌ ERROR: Failed to import GooglePlacesConnector: {e}")
        return False

    # Create connector instance
    try:
        connector = GooglePlacesConnector()
        print(f"✓ GooglePlacesConnector initialized (source: {connector.source_name})")
        print(f"  - Base URL: {connector.base_url}")
        print(f"  - Timeout: {connector.timeout}s")
        print(f"  - Default params: {connector.default_params}")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize connector: {e}")
        print()
        if "api_key" in str(e).lower():
            print("Hint: Make sure you've set a valid Google Places API key in sources.yaml")
        return False

    # Connect to database
    try:
        await connector.db.connect()
        print("✓ Database connected")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to database: {e}")
        print()
        print("Hint: Run 'prisma generate && prisma db push' to set up the database")
        return False

    # Fetch data from Google Places API
    query = "padel edinburgh"
    print(f"🔍 Fetching place results for: '{query}'")
    print()

    try:
        data = await connector.fetch(query)
        print("✓ API request successful!")
        print()
        print("Response Summary:")
        print(f"  - Results: {len(data.get('places', []))} places")
        print()

        # Show first 3 results
        places = data.get('places', [])
        if places:
            print("First 3 Places:")
            for i, place in enumerate(places[:3], 1):
                display_name = place.get('displayName', {})
                name = display_name.get('text', 'N/A') if isinstance(display_name, dict) else 'N/A'

                print(f"  {i}. {name}")
                print(f"     Place ID: {place.get('id', 'N/A')}")
                print(f"     Address: {place.get('formattedAddress', 'N/A')}")

                # Show location
                location = place.get('location', {})
                if location:
                    print(f"     Location: {location.get('latitude', 'N/A')}, {location.get('longitude', 'N/A')}")

                # Show rating
                rating = place.get('rating')
                user_rating_count = place.get('userRatingCount')
                if rating:
                    print(f"     Rating: {rating}/5 ({user_rating_count} reviews)")

                print()

    except Exception as e:
        print(f"❌ ERROR: API request failed: {e}")
        await connector.db.disconnect()
        return False

    # Check for duplicates
    content_hash = compute_content_hash(data)
    print(f"🔐 Content hash: {content_hash[:16]}...")

    try:
        is_dup = await connector.is_duplicate(content_hash)
        if is_dup:
            print("⚠️  This data has already been ingested (duplicate detected)")
            print()
        else:
            print("✓ No duplicate found - this is new data")
            print()
    except Exception as e:
        print(f"❌ ERROR: Duplicate check failed: {e}")
        await connector.db.disconnect()
        return False

    # Save data to filesystem and database
    source_url = f"{connector.base_url}/textsearch/json"
    print(f"💾 Saving data to filesystem and database...")

    try:
        file_path = await connector.save(data, source_url)
        print(f"✓ Data saved successfully!")
        print(f"  - File path: {file_path}")
        print()

        # Verify file exists
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"✓ File verified on disk ({file_size:,} bytes)")
        else:
            print(f"⚠️  Warning: File not found at {file_path}")
        print()

    except Exception as e:
        print(f"❌ ERROR: Failed to save data: {e}")
        await connector.db.disconnect()
        return False

    # Query database to verify record was created
    try:
        record = await connector.db.rawingestion.find_first(
            where={"hash": content_hash}
        )
        if record:
            print("✓ Database record verified:")
            print(f"  - ID: {record.id}")
            print(f"  - Source: {record.source}")
            print(f"  - Status: {record.status}")
            print(f"  - Ingested at: {record.ingested_at}")
            print(f"  - Metadata: {record.metadata_json}")
            print()
        else:
            print("⚠️  Warning: Database record not found")
            print()
    except Exception as e:
        print(f"⚠️  Warning: Could not verify database record: {e}")
        print()

    # Disconnect from database
    await connector.db.disconnect()
    print("✓ Database disconnected")
    print()

    # Success summary
    print("=" * 70)
    print("✅ TEST COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  - Query: '{query}'")
    print(f"  - Results: {len(data.get('places', []))} places")
    print(f"  - Saved to: {file_path}")
    print(f"  - Hash: {content_hash}")
    print()

    # Show discovered venues
    places = data.get('places', [])
    if places:
        print("Venues Discovered:")
        for place in places:
            display_name = place.get('displayName', {})
            name = display_name.get('text', 'N/A') if isinstance(display_name, dict) else 'N/A'
            address = place.get('formattedAddress', 'N/A').split(',')[0]  # Just street
            print(f"  - {name} ({address})")
        print()

    print("Next steps:")
    print("  - Check the raw data file to inspect the JSON")
    print("  - Verify the RawIngestion table in your database")
    print("  - Run the test again to verify deduplication works")
    print("  - Compare results with Serper connector output")
    print()

    return True


def main():
    """Main entry point"""
    try:
        success = asyncio.run(test_google_places_padel_query())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
