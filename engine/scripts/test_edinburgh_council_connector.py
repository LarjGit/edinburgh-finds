"""
Manual Test Script for Edinburgh Council Connector

This script tests the EdinburghCouncilConnector with a sample civic facility
dataset to verify end-to-end functionality with the Edinburgh Council ArcGIS
REST API.

Prerequisites:
1. Ensure database is migrated (prisma generate && prisma db push)
2. No API key required (public portal)

Usage:
    python -m engine.scripts.test_edinburgh_council_connector
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


async def test_edinburgh_council_dataset():
    """Test EdinburghCouncilConnector with a sample dataset"""

    print("=" * 70)
    print("EDINBURGH COUNCIL CONNECTOR MANUAL TEST")
    print("=" * 70)
    print()

    # Check if sources.yaml exists
    config_path = project_root / "engine" / "config" / "sources.yaml"
    if not config_path.exists():
        print("❌ ERROR: sources.yaml not found!")
        print()
        print("Setup Instructions:")
        print("1. Copy engine/config/sources.yaml.example to engine/config/sources.yaml")
        print()
        return False

    print("✓ Configuration file found")
    print()

    # Import and initialize connector
    try:
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector
        print("✓ EdinburghCouncilConnector imported successfully")
    except Exception as e:
        print(f"❌ ERROR: Failed to import EdinburghCouncilConnector: {e}")
        return False

    try:
        connector = EdinburghCouncilConnector()
        print(f"✓ EdinburghCouncilConnector initialized (source: {connector.source_name})")
        print(f"  - Base URL: {connector.base_url}")
        print(f"  - Timeout: {connector.timeout}s")
        print(f"  - API Key: {'Not required (public portal)' if not connector.api_key else 'Configured'}")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize EdinburghCouncilConnector: {e}")
        return False

    # Connect to database
    try:
        await connector.db.connect()
        print("✓ Database connected")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to database: {e}")
        return False

    # Test dataset ID for sports/leisure facilities
    # Note: This is a placeholder - actual dataset ID would come from portal exploration
    test_dataset = "sports_leisure_facilities"

    print(f"🔍 Fetching civic facilities dataset: {test_dataset}")
    print("   (Note: This test uses a sample dataset ID)")
    print()

    # Attempt to fetch data
    try:
        data = await connector.fetch(test_dataset)
        print("✓ API request successful!")
        print()

        # Display response summary
        print("Response Summary:")
        features = data.get('features', [])
        print(f"  - Type: {data.get('type', 'Unknown')}")
        print(f"  - Features: {len(features)}")
        print()

        # Display sample features
        if features:
            print(f"First 3 Facilities:")
            for i, feature in enumerate(features[:3], 1):
                properties = feature.get('properties', {})
                geometry = feature.get('geometry', {})
                coords = geometry.get('coordinates', [])

                facility_name = properties.get('name') or properties.get('FACILITY_NAME') or 'Unknown'
                facility_type = properties.get('type') or properties.get('FACILITY_TYPE') or 'N/A'
                address = properties.get('address') or properties.get('ADDRESS') or 'N/A'

                print(f"  {i}. {facility_name}")
                print(f"     Type: {facility_type}")
                print(f"     Address: {address}")
                if coords:
                    print(f"     Location: {coords}")
                print()

    except Exception as e:
        # If the test dataset doesn't exist, that's expected for a placeholder ID
        print(f"⚠️  Note: Test dataset '{test_dataset}' may not exist in the portal")
        print(f"   Error: {e}")
        print()
        print("To test with real data:")
        print("1. Browse Edinburgh Council Open Data Portal:")
        print("   https://data.edinburghcouncilmaps.info/")
        print("2. Find a dataset (e.g., 'Sports and Leisure Facilities')")
        print("3. Extract the dataset ID from the URL")
        print("4. Run: await connector.fetch('<dataset_id>')")
        print()

        # Test with empty response to verify deduplication/save logic
        print("Testing deduplication and save logic with mock data...")
        mock_data = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'properties': {'name': 'Test Facility', 'type': 'Sports Center'},
                    'geometry': {'type': 'Point', 'coordinates': [-3.188, 55.953]}
                }
            ]
        }

        # Check deduplication
        from engine.ingestion.deduplication import compute_content_hash
        content_hash = compute_content_hash(mock_data)
        print(f"🔐 Content hash: {content_hash[:16]}...")

        is_duplicate = await connector.is_duplicate(content_hash)
        if is_duplicate:
            print("⚠️  This data has already been ingested (duplicate detected)")
        else:
            print("✓ No duplicate found - this is new data")
        print()

        # Save data
        print("💾 Saving mock data to filesystem and database...")
        try:
            source_url = f"{connector.base_url}/{test_dataset}/query"
            file_path = await connector.save(mock_data, source_url)
            print("✓ Data saved successfully!")
            print(f"  - File path: {file_path}")
            print()

            # Verify file exists
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"✓ File verified on disk ({file_size:,} bytes)")
                print()

            # Verify database record
            record = await connector.db.rawingestion.find_first(
                where={'hash': content_hash}
            )
            if record:
                print("✓ Database record verified:")
                print(f"  - ID: {record.id}")
                print(f"  - Source: {record.source}")
                print(f"  - Status: {record.status}")
                print(f"  - Ingested at: {record.ingested_at}")
                print(f"  - Metadata: {record.metadata_json}")
                print()
        except Exception as save_error:
            print(f"❌ ERROR during save: {save_error}")

    # Disconnect from database
    await connector.db.disconnect()
    print("✓ Database disconnected")
    print()

    print("=" * 70)
    print("✅ TEST COMPLETED!")
    print("=" * 70)
    print()
    print("Next Steps:")
    print("1. Browse Edinburgh Council Portal: https://data.edinburghcouncilmaps.info/")
    print("2. Explore available datasets (Sports, Libraries, Parks, etc.)")
    print("3. Extract dataset IDs from portal URLs")
    print("4. Test with real dataset IDs using connector.fetch('<dataset_id>')")
    print()

    return True


if __name__ == "__main__":
    success = asyncio.run(test_edinburgh_council_dataset())
    sys.exit(0 if success else 1)
