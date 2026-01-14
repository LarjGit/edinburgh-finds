"""
Manual Test Script for OpenChargeMap Connector

This script tests the OpenChargeMapConnector with known Edinburgh venue
coordinates to verify end-to-end functionality with the OpenChargeMap API.

Prerequisites:
1. Copy engine/config/sources.yaml.example to engine/config/sources.yaml
2. Add your OpenChargeMap API key to sources.yaml (get key at https://openchargemap.org/site/develop/api)
3. Ensure database is migrated (prisma generate && prisma db push)

Usage:
    python -m engine.scripts.test_open_charge_map_connector
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


async def test_open_charge_map_edinburgh_venues():
    """Test OpenChargeMapConnector with Edinburgh venue coordinates"""

    print("=" * 70)
    print("OPENCHARGEMAP CONNECTOR MANUAL TEST")
    print("=" * 70)
    print()

    # Check if sources.yaml exists
    config_path = project_root / "engine" / "config" / "sources.yaml"
    if not config_path.exists():
        print("❌ ERROR: sources.yaml not found!")
        print()
        print("Setup Instructions:")
        print("1. Copy engine/config/sources.yaml.example to engine/config/sources.yaml")
        print("2. Edit sources.yaml and add your OpenChargeMap API key")
        print("3. Get a free API key at https://openchargemap.org/site/develop/api")
        print()
        return False

    print("✓ Configuration file found")
    print()

    # Import and initialize connector
    try:
        from engine.ingestion.open_charge_map import OpenChargeMapConnector
        from engine.ingestion.deduplication import compute_content_hash
        print("✓ OpenChargeMapConnector imported successfully")
    except ImportError as e:
        print(f"❌ ERROR: Failed to import OpenChargeMapConnector: {e}")
        return False

    # Create connector instance
    try:
        connector = OpenChargeMapConnector()
        print(f"✓ OpenChargeMapConnector initialized (source: {connector.source_name})")
        print(f"  - Base URL: {connector.base_url}")
        print(f"  - Timeout: {connector.timeout}s")
        print(f"  - Default params: {connector.default_params}")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize connector: {e}")
        print()
        if "api_key" in str(e).lower():
            print("Hint: Make sure you've set a valid OpenChargeMap API key in sources.yaml")
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

    # Test with known Edinburgh venue coordinates
    # Using coordinates near Edinburgh city center (Castle/Princes Street area)
    coordinates = "55.9533,-3.1883"
    print(f"🔍 Fetching EV charging stations near: {coordinates}")
    print("   (Edinburgh city center - Castle/Princes Street area)")
    print()

    try:
        data = await connector.fetch(coordinates)
        print("✓ API request successful!")
        print()
        print("Response Summary:")
        print(f"  - Charging stations found: {len(data)}")
        print()

        # Show first 3 results
        if data and len(data) > 0:
            print("First 3 Charging Stations:")
            for i, station in enumerate(data[:3], 1):
                address_info = station.get('AddressInfo', {})
                title = address_info.get('Title', 'N/A')
                address_line1 = address_info.get('AddressLine1', 'N/A')
                town = address_info.get('Town', 'N/A')
                postcode = address_info.get('Postcode', 'N/A')
                lat = address_info.get('Latitude', 'N/A')
                lng = address_info.get('Longitude', 'N/A')

                print(f"  {i}. {title}")
                print(f"     Station ID: {station.get('ID', 'N/A')}")
                print(f"     Address: {address_line1}, {town} {postcode}")
                print(f"     Location: {lat}, {lng}")
                print(f"     Charging Points: {station.get('NumberOfPoints', 'N/A')}")

                # Show status
                status = station.get('StatusType', {})
                if status:
                    print(f"     Status: {status.get('Title', 'N/A')}")

                # Show connection types
                connections = station.get('Connections', [])
                if connections:
                    print(f"     Connectors:")
                    for conn in connections[:2]:  # Show first 2 connectors
                        conn_type = conn.get('ConnectionType', {}).get('Title', 'Unknown')
                        power = conn.get('PowerKW', 'N/A')
                        print(f"       - {conn_type} ({power} kW)")

                print()
        else:
            print("⚠️  No charging stations found for this location")
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
    source_url = f"{connector.base_url}/poi/?latitude={coordinates.split(',')[0]}&longitude={coordinates.split(',')[1]}"
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
    print(f"  - Coordinates: {coordinates} (Edinburgh city center)")
    print(f"  - Charging stations found: {len(data)}")
    print(f"  - Saved to: {file_path}")
    print(f"  - Hash: {content_hash}")
    print()

    # Show discovered charging stations
    if data and len(data) > 0:
        print("Charging Stations Discovered:")
        for station in data[:10]:  # Show up to 10
            address_info = station.get('AddressInfo', {})
            title = address_info.get('Title', 'Unknown')
            town = address_info.get('Town', 'Unknown')
            points = station.get('NumberOfPoints', 'N/A')
            print(f"  - {title} ({town}) - {points} charging points")
        print()
        if len(data) > 10:
            print(f"  ... and {len(data) - 10} more")
            print()

    print("Next steps:")
    print("  - Check the raw data file to inspect the JSON")
    print("  - Verify the RawIngestion table in your database")
    print("  - Run the test again to verify deduplication works")
    print("  - Test with different venue coordinates")
    print()
    print("Example venue coordinates to try:")
    print("  - Oriam (Heriot-Watt): 55.9108,-3.3171")
    print("  - Edinburgh Airport: 55.9500,-3.3725")
    print("  - Leith area: 55.9760,-3.1740")
    print()

    return True


def main():
    """Main entry point"""
    try:
        success = asyncio.run(test_open_charge_map_edinburgh_venues())
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
