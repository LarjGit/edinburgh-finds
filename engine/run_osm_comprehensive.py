"""
Comprehensive test script for OSM Overpass API Connector

Tests multiple sports types to validate connector functionality with
data that exists in OpenStreetMap.

Usage:
    python -m engine.test_osm_comprehensive
"""

import asyncio
import json
from engine.ingestion.connectors.open_street_map import OSMConnector
from engine.ingestion.deduplication import compute_content_hash


async def test_query(connector, query_name, sport_tag):
    """Test a single query and return results"""
    print(f"\n{'─' * 80}")
    print(f"Testing: {query_name}")
    print(f"{'─' * 80}")

    try:
        # Fetch data
        print(f"Fetching '{sport_tag}' facilities...")
        data = await connector.fetch(sport_tag)
        element_count = len(data.get('elements', []))
        print(f"✓ Found {element_count} elements")

        # Show sample results
        if element_count > 0:
            print(f"\nSample results (first 5):")
            for i, element in enumerate(data['elements'][:5]):
                elem_type = element.get('type', 'N/A')
                elem_id = element.get('id', 'N/A')
                tags = element.get('tags', {})
                name = tags.get('name', 'Unnamed')
                sport = tags.get('sport', tags.get('leisure', 'N/A'))

                print(f"  {i+1}. {name}")
                print(f"     Type: {elem_type} | ID: {elem_id} | Sport: {sport}")

                # Show location if available
                if 'lat' in element and 'lon' in element:
                    print(f"     Location: {element['lat']}, {element['lon']}")

            # Check and save if not duplicate
            content_hash = compute_content_hash(data)
            is_dup = await connector.is_duplicate(content_hash)

            if not is_dup:
                source_url = f"{connector.base_url}?query={sport_tag}"
                file_path = await connector.save(data, source_url)
                print(f"\n✓ Saved to: {file_path}")
            else:
                print(f"\n⊘ Duplicate data (already ingested)")

        return element_count

    except Exception as e:
        print(f"✗ Error: {e}")
        return 0


async def main():
    """Run comprehensive tests with multiple sports"""
    print("=" * 80)
    print("OSM Overpass API Connector - Comprehensive Test")
    print("=" * 80)

    # Initialize connector
    print("\nInitializing connector...")
    connector = OSMConnector()
    await connector.db.connect()
    print("✓ Ready")

    # Test queries (ordered by likelihood of having data in Edinburgh)
    test_queries = [
        ("Tennis Facilities", "tennis"),
        ("Football/Soccer Facilities", "soccer"),
        ("Golf Courses", "golf"),
        ("Swimming Pools/Swimming", "swimming"),
        ("Padel Courts", "padel"),
    ]

    results = {}
    for name, sport in test_queries:
        count = await test_query(connector, name, sport)
        results[name] = count
        await asyncio.sleep(1)  # Be respectful to the API

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    total_elements = 0
    for name, count in results.items():
        print(f"  {name:<30} {count:>5} elements")
        total_elements += count

    print(f"  {'-' * 40}")
    print(f"  {'Total':<30} {total_elements:>5} elements")

    # Disconnect
    await connector.db.disconnect()
    print(f"\n{'=' * 80}")
    print("All tests completed!")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    asyncio.run(main())
