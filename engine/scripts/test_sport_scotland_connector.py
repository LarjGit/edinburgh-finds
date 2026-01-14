"""
Manual Test Script for SportScotland WFS Connector

This script tests the SportScotlandConnector with the real WFS endpoint
at Spatial Hub Scotland to verify end-to-end functionality.

Prerequisites:
1. Register for free account at Spatial Hub Scotland (https://data.spatialhub.scot)
2. Add your API token to engine/config/sources.yaml under sport_scotland.api_key
3. Ensure database is migrated (prisma generate && prisma db push)

Usage:
    python -m engine.scripts.test_sport_scotland_connector
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


async def test_sport_scotland_wfs():
    """Test SportScotlandConnector with real WFS endpoint"""

    print("=" * 70)
    print("SPORTSCOTLAND WFS CONNECTOR MANUAL TEST")
    print("=" * 70)
    print()

    # Check if sources.yaml exists
    config_path = project_root / "engine" / "config" / "sources.yaml"
    if not config_path.exists():
        print("❌ ERROR: sources.yaml not found!")
        print()
        print("Setup Instructions:")
        print("1. Copy engine/config/sources.yaml.example to engine/config/sources.yaml")
        print("2. Edit sources.yaml and add your Spatial Hub Scotland API token")
        print("3. Register at https://data.spatialhub.scot")
        print()
        return False

    print("✓ Configuration file found")
    print()

    # Import and initialize connector
    try:
        from engine.ingestion.sport_scotland import SportScotlandConnector
        from engine.ingestion.deduplication import compute_content_hash
        print("✓ SportScotlandConnector imported successfully")
    except ImportError as e:
        print(f"❌ ERROR: Failed to import SportScotlandConnector: {e}")
        return False

    # Create connector instance
    try:
        connector = SportScotlandConnector()
        print(f"✓ SportScotlandConnector initialized (source: {connector.source_name})")
        print(f"  - Base URL: {connector.base_url}")
        print(f"  - Timeout: {connector.timeout}s")
        print(f"  - API Key: {'Configured' if connector.api_key else 'Not configured'}")
        print(f"  - Edinburgh BBOX: {connector._build_bbox_string()}")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize connector: {e}")
        print()
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

    # Test with pub_sptk layer (SportScotland public facilities - combined layer)
    layer_name = "pub_sptk"
    print(f"🔍 Fetching sports facilities: {layer_name}")
    print("   (Filtered to Edinburgh bbox: -3.4,55.85 to -3.0,56.0)")
    print()

    try:
        data = await connector.fetch(layer_name)
        print("✓ WFS request successful!")
        print()
        print("Response Summary:")
        print(f"  - Type: {data.get('type', 'N/A')}")
        print(f"  - Features: {len(data.get('features', []))}")
        print(f"  - Total Features: {data.get('totalFeatures', 'N/A')}")
        print(f"  - Number Returned: {data.get('numberReturned', 'N/A')}")
        if 'crs' in data:
            crs_name = data['crs'].get('properties', {}).get('name', 'N/A')
            print(f"  - CRS: {crs_name}")
        print()

        # Show first 3 facilities
        features = data.get('features', [])
        if features and len(features) > 0:
            print("First 3 Facilities:")
            for i, feature in enumerate(features[:3], 1):
                props = feature.get('properties', {})
                geom = feature.get('geometry', {})
                coords = geom.get('coordinates', [])

                facility_name = props.get('facility_name', props.get('name', 'N/A'))
                print(f"  {i}. {facility_name}")
                print(f"     ID: {feature.get('id', 'N/A')}")

                if coords:
                    print(f"     Location: {coords}")

                # Show various property fields (schema varies by layer)
                for key in ['sport_type', 'surface', 'ownership', 'postcode', 'local_authority']:
                    if key in props and props[key]:
                        print(f"     {key.replace('_', ' ').title()}: {props[key]}")

                print()
        else:
            print(f"⚠️  No {layer_name} found in Edinburgh area")
            print()

    except Exception as e:
        print(f"❌ ERROR: WFS request failed: {e}")
        print()
        print("Common issues:")
        print("  - Invalid API token (check sources.yaml)")
        print("  - Network connectivity")
        print("  - Invalid layer name")
        print("  - WFS service temporarily unavailable")
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
    source_url = f"{connector.base_url}?service=WFS&version=2.0.0&request=GetFeature&typeName=sport_scotland:{layer_name}&bbox={connector._build_bbox_string()}"
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
    print(f"  - Layer: {layer_name}")
    print(f"  - Features found: {len(data.get('features', []))}")
    print(f"  - Saved to: {file_path}")
    print(f"  - Hash: {content_hash}")
    print()

    # Show discovered facilities
    features = data.get('features', [])
    if features and len(features) > 0:
        print(f"Facilities Discovered ({layer_name}):")
        for feature in features[:15]:  # Show up to 15
            props = feature.get('properties', {})
            facility_name = props.get('facility_name', props.get('name', 'Unknown'))
            local_auth = props.get('local_authority', 'Unknown')
            print(f"  - {facility_name} ({local_auth})")
        print()
        if len(features) > 15:
            print(f"  ... and {len(features) - 15} more")
            print()

    print("Next steps:")
    print("  - Check the raw GeoJSON file to inspect the data structure")
    print("  - Verify the RawIngestion table in your database")
    print("  - Run the test again to verify deduplication works")
    print("  - Test with different layer types:")
    print()
    print("Available layers:")
    print("  - pitches (sports pitches)")
    print("  - tennis_courts (indoor/outdoor tennis)")
    print("  - swimming_pools (swimming/diving)")
    print("  - sports_halls (gyms/halls)")
    print("  - golf_courses")
    print("  - athletics_tracks (tracks/velodromes)")
    print("  - bowling_greens (bowling/croquet)")
    print("  - fitness_suites")
    print("  - ice_rinks (ice/curling)")
    print("  - squash_courts")
    print()

    return True


def main():
    """Main entry point"""
    try:
        success = asyncio.run(test_sport_scotland_wfs())
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
