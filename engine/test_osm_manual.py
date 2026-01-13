"""
Manual test script for OSM Overpass API Connector

This script performs real API calls to validate the OSMConnector implementation
with actual Padel and sports facility queries.

Usage:
    python -m engine.test_osm_manual
"""

import asyncio
import json
from engine.ingestion.open_street_map import OSMConnector
from engine.ingestion.deduplication import compute_content_hash


async def test_osm_connector():
    """Test OSMConnector with real Padel facility queries"""
    print("=" * 80)
    print("OSM Overpass API Connector - Manual Test")
    print("=" * 80)

    # Initialize connector
    print("\n[1/5] Initializing OSMConnector...")
    try:
        connector = OSMConnector()
        print(f"✓ Connector initialized")
        print(f"  - Source name: {connector.source_name}")
        print(f"  - Base URL: {connector.base_url}")
        print(f"  - Timeout: {connector.timeout_seconds}s")
        print(f"  - Default location: {connector.default_lat}, {connector.default_lon}")
        print(f"  - Default radius: {connector.default_radius}m")
    except Exception as e:
        print(f"✗ Failed to initialize connector: {e}")
        return

    # Connect to database
    print("\n[2/5] Connecting to database...")
    try:
        await connector.db.connect()
        print("✓ Database connected")
    except Exception as e:
        print(f"✗ Failed to connect to database: {e}")
        return

    # Test query: Padel facilities
    query = "padel"
    print(f"\n[3/5] Fetching data from Overpass API (query: '{query}')...")
    try:
        data = await connector.fetch(query)
        element_count = len(data.get('elements', []))
        print(f"✓ Data fetched successfully")
        print(f"  - Elements found: {element_count}")
        print(f"  - API version: {data.get('version', 'unknown')}")
        print(f"  - Generator: {data.get('generator', 'unknown')}")

        # Show sample elements
        if element_count > 0:
            print(f"\n  Sample elements:")
            for i, element in enumerate(data['elements'][:3]):  # Show first 3
                print(f"    [{i+1}] Type: {element.get('type', 'N/A')}, "
                      f"ID: {element.get('id', 'N/A')}")
                if 'tags' in element:
                    name = element['tags'].get('name', 'Unnamed')
                    sport = element['tags'].get('sport', 'N/A')
                    print(f"        Name: {name}, Sport: {sport}")
    except Exception as e:
        print(f"✗ Failed to fetch data: {e}")
        await connector.db.disconnect()
        return

    # Check for duplicates
    print(f"\n[4/5] Checking for duplicates...")
    try:
        content_hash = compute_content_hash(data)
        is_dup = await connector.is_duplicate(content_hash)
        print(f"  - Content hash: {content_hash[:16]}...")
        print(f"  - Is duplicate: {is_dup}")
    except Exception as e:
        print(f"✗ Failed to check duplicates: {e}")

    # Save data (only if not duplicate)
    if not is_dup:
        print(f"\n[5/5] Saving data to filesystem and database...")
        try:
            source_url = f"{connector.base_url}?query={query}"
            file_path = await connector.save(data, source_url)
            print(f"✓ Data saved successfully")
            print(f"  - File path: {file_path}")
            print(f"  - Element count: {element_count}")

            # Verify file exists and contains data
            with open(file_path, 'r') as f:
                saved_data = json.load(f)
                saved_element_count = len(saved_data.get('elements', []))
                print(f"  - Verified: {saved_element_count} elements in saved file")
        except Exception as e:
            print(f"✗ Failed to save data: {e}")
    else:
        print(f"\n[5/5] Skipping save (duplicate data already exists)")

    # Disconnect from database
    print(f"\nDisconnecting from database...")
    await connector.db.disconnect()
    print("✓ Database disconnected")

    print("\n" + "=" * 80)
    print("Test completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_osm_connector())
