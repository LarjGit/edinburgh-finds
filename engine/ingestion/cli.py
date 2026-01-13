"""
CLI Tool for Data Ingestion Connectors

This module provides a command-line interface for running individual data
source connectors to fetch and save raw data.

Usage:
    # Run specific connector
    python -m engine.ingestion.cli serper "padel edinburgh"
    python -m engine.ingestion.cli google_places "padel courts edinburgh"
    python -m engine.ingestion.cli openstreetmap "padel"

    # With verbose output
    python -m engine.ingestion.cli -v serper "padel edinburgh"

    # Check status without fetching
    python -m engine.ingestion.cli --list
"""

import argparse
import asyncio
import sys
from datetime import datetime
from typing import Optional

from engine.ingestion.serper import SerperConnector
from engine.ingestion.google_places import GooglePlacesConnector
from engine.ingestion.open_street_map import OSMConnector
from engine.ingestion.deduplication import compute_content_hash


# Connector registry
CONNECTORS = {
    'serper': SerperConnector,
    'google_places': GooglePlacesConnector,
    'openstreetmap': OSMConnector,
}


async def run_connector(connector_name: str, query: str, verbose: bool = False):
    """
    Run a specific connector with the given query.

    Args:
        connector_name: Name of the connector to run
        query: Search query string
        verbose: Enable verbose output

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Validate connector name
    if connector_name not in CONNECTORS:
        print(f"Error: Unknown connector '{connector_name}'")
        print(f"Available connectors: {', '.join(CONNECTORS.keys())}")
        return 1

    print(f"{'=' * 80}")
    print(f"Running {connector_name} connector")
    print(f"Query: {query}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}\n")

    try:
        # Initialize connector
        if verbose:
            print(f"[1/5] Initializing {connector_name} connector...")

        ConnectorClass = CONNECTORS[connector_name]
        connector = ConnectorClass()

        if verbose:
            print(f"  ✓ Connector: {connector.source_name}")
            if hasattr(connector, 'base_url'):
                print(f"  ✓ Base URL: {connector.base_url}")
            print()

        # Connect to database
        if verbose:
            print(f"[2/5] Connecting to database...")

        await connector.db.connect()

        if verbose:
            print(f"  ✓ Database connected\n")

        # Fetch data
        print(f"[3/5] Fetching data from {connector_name}...")

        data = await connector.fetch(query)

        # Determine result count based on connector type
        if connector_name == 'serper':
            result_count = len(data.get('organic', []))
        elif connector_name == 'google_places':
            result_count = len(data.get('places', []))
        elif connector_name == 'openstreetmap':
            result_count = len(data.get('elements', []))
        else:
            result_count = 0

        print(f"  ✓ Fetched {result_count} results")

        if verbose and result_count > 0:
            print(f"\n  Sample results:")
            if connector_name == 'serper':
                for i, result in enumerate(data.get('organic', [])[:3]):
                    print(f"    {i+1}. {result.get('title', 'N/A')}")
            elif connector_name == 'google_places':
                for i, place in enumerate(data.get('places', [])[:3]):
                    name = place.get('displayName', {}).get('text', 'N/A')
                    print(f"    {i+1}. {name}")
            elif connector_name == 'openstreetmap':
                for i, element in enumerate(data.get('elements', [])[:3]):
                    name = element.get('tags', {}).get('name', 'Unnamed')
                    print(f"    {i+1}. {name}")
        print()

        # Check for duplicates
        print(f"[4/5] Checking for duplicates...")

        content_hash = compute_content_hash(data)
        is_duplicate = await connector.is_duplicate(content_hash)

        print(f"  - Content hash: {content_hash[:16]}...")
        print(f"  - Is duplicate: {is_duplicate}")
        print()

        # Save data
        if not is_duplicate:
            print(f"[5/5] Saving data...")

            # Build source URL (best effort)
            if hasattr(connector, 'base_url'):
                source_url = f"{connector.base_url}?query={query}"
            else:
                source_url = f"query:{query}"

            file_path = await connector.save(data, source_url)

            print(f"  ✓ Data saved successfully")
            print(f"  ✓ File: {file_path}")
            print(f"  ✓ Results: {result_count}")
        else:
            print(f"[5/5] Skipping save (duplicate data)")

        # Disconnect
        await connector.db.disconnect()

        print(f"\n{'=' * 80}")
        print(f"✓ Success!")
        print(f"{'=' * 80}")

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()

        # Try to disconnect from database
        try:
            await connector.db.disconnect()
        except:
            pass

        return 1


def list_connectors():
    """List all available connectors"""
    print("Available connectors:")
    print()
    for name, cls in CONNECTORS.items():
        print(f"  • {name}")
        # Instantiate to get description (if available)
        try:
            instance = cls()
            if hasattr(instance, 'base_url'):
                print(f"    URL: {instance.base_url}")
        except:
            pass
        print()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Run data ingestion connectors',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m engine.ingestion.cli serper "padel edinburgh"
  python -m engine.ingestion.cli google_places "padel courts"
  python -m engine.ingestion.cli openstreetmap "tennis"
  python -m engine.ingestion.cli --list
        """
    )

    parser.add_argument(
        'connector',
        nargs='?',
        choices=list(CONNECTORS.keys()),
        help='Connector to run'
    )

    parser.add_argument(
        'query',
        nargs='?',
        help='Search query string'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List available connectors'
    )

    args = parser.parse_args()

    # Handle --list flag
    if args.list:
        list_connectors()
        return 0

    # Validate required arguments
    if not args.connector or not args.query:
        parser.print_help()
        return 1

    # Run the connector
    exit_code = asyncio.run(run_connector(args.connector, args.query, args.verbose))
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
