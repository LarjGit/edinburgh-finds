"""
Manual Test Script for Serper Connector

This script tests the SerperConnector with a real "padel edinburgh" query
to verify end-to-end functionality with the Serper API.

Prerequisites:
1. Copy engine/config/sources.yaml.example to engine/config/sources.yaml
2. Add your Serper API key to sources.yaml (sign up at https://serper.dev/)
3. Ensure database is migrated (prisma generate && prisma db push)

Usage:
    python -m engine.scripts.run_serper_connector
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


async def test_serper_padel_query():
    """Test SerperConnector with 'padel edinburgh' query"""

    print("=" * 70)
    print("SERPER CONNECTOR MANUAL TEST")
    print("=" * 70)
    print()

    # Check if sources.yaml exists
    config_path = project_root / "engine" / "config" / "sources.yaml"
    if not config_path.exists():
        print("❌ ERROR: sources.yaml not found!")
        print()
        print("Setup Instructions:")
        print("1. Copy engine/config/sources.yaml.example to engine/config/sources.yaml")
        print("2. Edit sources.yaml and add your Serper API key")
        print("3. Sign up for a free API key at https://serper.dev/")
        print()
        return False

    print("✓ Configuration file found")
    print()

    # Import and initialize connector
    try:
        from engine.ingestion.connectors.serper import SerperConnector
        from engine.ingestion.deduplication import compute_content_hash
        print("✓ SerperConnector imported successfully")
    except ImportError as e:
        print(f"❌ ERROR: Failed to import SerperConnector: {e}")
        return False

    # Create connector instance
    try:
        connector = SerperConnector()
        print(f"✓ SerperConnector initialized (source: {connector.source_name})")
        print(f"  - Base URL: {connector.base_url}")
        print(f"  - Timeout: {connector.timeout}s")
        print(f"  - Default params: {connector.default_params}")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize connector: {e}")
        print()
        if "api_key" in str(e).lower():
            print("Hint: Make sure you've set a valid Serper API key in sources.yaml")
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

    # Fetch data from Serper API
    query = "padel edinburgh"
    print(f"🔍 Fetching search results for: '{query}'")
    print()

    try:
        data = await connector.fetch(query)
        print("✓ API request successful!")
        print()
        print("Response Summary:")
        print(f"  - Search parameters: {data.get('searchParameters', {})}")
        print(f"  - Organic results: {len(data.get('organic', []))} results")
        print(f"  - Credits used: {data.get('credits', 'N/A')}")
        print()

        # Show first 3 results
        organic = data.get('organic', [])
        if organic:
            print("First 3 Results:")
            for i, result in enumerate(organic[:3], 1):
                print(f"  {i}. {result.get('title', 'N/A')}")
                print(f"     URL: {result.get('link', 'N/A')}")
                print(f"     Snippet: {result.get('snippet', 'N/A')[:80]}...")
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
    source_url = f"{connector.base_url}/search"
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
    print(f"  - Results: {len(data.get('organic', []))} organic results")
    print(f"  - Saved to: {file_path}")
    print(f"  - Hash: {content_hash}")
    print()
    print("Next steps:")
    print("  - Check the raw data file to inspect the JSON")
    print("  - Verify the RawIngestion table in your database")
    print("  - Run the test again to verify deduplication works")
    print()

    return True


def main():
    """Main entry point"""
    try:
        success = asyncio.run(test_serper_padel_query())
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
