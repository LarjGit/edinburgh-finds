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

from engine.ingestion.connectors.serper import SerperConnector
from engine.ingestion.connectors.google_places import GooglePlacesConnector
from engine.ingestion.connectors.open_street_map import OSMConnector
from engine.ingestion.deduplication import compute_content_hash
from prisma import Prisma


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


async def get_ingestion_stats() -> dict:
    """
    Get comprehensive ingestion statistics from the database.

    Returns:
        Dictionary containing:
        - total_records: Total number of ingestion records
        - by_source: Dictionary of counts by source
        - by_status: Dictionary of counts by status
        - recent_ingestions: List of most recent ingestions (last 10)
        - failed_ingestions: List of failed ingestions
        - success_count: Number of successful ingestions
        - failed_count: Number of failed ingestions
        - success_rate: Percentage of successful ingestions
    """
    db = Prisma()

    try:
        await db.connect()
    except Exception as e:
        # Return empty stats if connection fails
        return {
            'total_records': 0,
            'by_source': {},
            'by_status': {},
            'recent_ingestions': [],
            'failed_ingestions': [],
            'success_count': 0,
            'failed_count': 0,
            'success_rate': 0
        }

    try:
        # Get total count
        total_records = await db.rawingestion.count()

        # Get counts by source
        all_records = await db.rawingestion.find_many()
        by_source = {}
        by_status = {}

        for record in all_records:
            # Count by source
            if record.source not in by_source:
                by_source[record.source] = 0
            by_source[record.source] += 1

            # Count by status
            if record.status not in by_status:
                by_status[record.status] = 0
            by_status[record.status] += 1

        # Get recent ingestions (last 10)
        recent_ingestions = await db.rawingestion.find_many(
            order={'ingested_at': 'desc'},
            take=10
        )

        # Convert to dict for easier testing/use
        recent_list = []
        for record in recent_ingestions:
            recent_list.append({
                'id': record.id,
                'source': record.source,
                'status': record.status,
                'ingested_at': record.ingested_at,
                'source_url': record.source_url
            })

        # Get failed ingestions
        failed_ingestions = await db.rawingestion.find_many(
            where={'status': 'failed'},
            order={'ingested_at': 'desc'},
            take=10
        )

        # Convert to dict
        failed_list = []
        for record in failed_ingestions:
            failed_list.append({
                'id': record.id,
                'source': record.source,
                'status': record.status,
                'ingested_at': record.ingested_at,
                'source_url': record.source_url
            })

        # Calculate success rate
        success_count = by_status.get('success', 0)
        failed_count = by_status.get('failed', 0)
        success_rate = (success_count / total_records * 100) if total_records > 0 else 0

        return {
            'total_records': total_records,
            'by_source': by_source,
            'by_status': by_status,
            'recent_ingestions': recent_list,
            'failed_ingestions': failed_list,
            'success_count': success_count,
            'failed_count': failed_count,
            'success_rate': success_rate
        }

    finally:
        await db.disconnect()


async def show_status():
    """
    Display comprehensive ingestion statistics to the console.

    Shows:
    - Total ingestion records
    - Breakdown by source
    - Breakdown by status
    - Success rate
    - Recent ingestions
    - Failed ingestions (if any)
    """
    print(f"{'=' * 80}")
    print(f"Ingestion Status Report")
    print(f"{'=' * 80}\n")

    stats = await get_ingestion_stats()

    # Overview
    print(f"OVERVIEW")
    print(f"  Total Records:    {stats['total_records']:,}")
    print(f"  Successful:       {stats['success_count']:,} ({stats['success_rate']:.1f}%)")
    print(f"  Failed:           {stats['failed_count']:,}")
    print()

    # By Source
    print(f"BY SOURCE")
    if stats['by_source']:
        # Sort by count (descending)
        sorted_sources = sorted(
            stats['by_source'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        for source, count in sorted_sources:
            percentage = (count / stats['total_records'] * 100) if stats['total_records'] > 0 else 0
            print(f"  {source:20s} {count:6,} ({percentage:5.1f}%)")
    else:
        print(f"  No records yet")
    print()

    # By Status
    print(f"BY STATUS")
    if stats['by_status']:
        # Sort by count (descending)
        sorted_statuses = sorted(
            stats['by_status'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        for status, count in sorted_statuses:
            percentage = (count / stats['total_records'] * 100) if stats['total_records'] > 0 else 0
            print(f"  {status:20s} {count:6,} ({percentage:5.1f}%)")
    else:
        print(f"  No records yet")
    print()

    # Recent Ingestions
    print(f"RECENT INGESTIONS (Last 10)")
    if stats['recent_ingestions']:
        for record in stats['recent_ingestions']:
            timestamp = record['ingested_at'].strftime('%Y-%m-%d %H:%M:%S')
            status_indicator = '✓' if record['status'] == 'success' else '✗'
            print(f"  {status_indicator} {timestamp}  {record['source']:20s} {record['status']}")
    else:
        print(f"  No ingestions yet")
    print()

    # Failed Ingestions (if any)
    if stats['failed_ingestions']:
        print(f"FAILED INGESTIONS (Last 10)")
        for record in stats['failed_ingestions']:
            timestamp = record['ingested_at'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"  ✗ {timestamp}  {record['source']:20s}")
            # Truncate URL if too long
            url = record['source_url']
            if len(url) > 60:
                url = url[:57] + '...'
            print(f"    URL: {url}")
        print()

    print(f"{'=' * 80}")


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
  python -m engine.ingestion.cli status
  python -m engine.ingestion.cli --list
        """
    )

    # Add special commands to connector choices
    connector_choices = list(CONNECTORS.keys()) + ['status']

    parser.add_argument(
        'connector',
        nargs='?',
        choices=connector_choices,
        help='Connector to run or command (status)'
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

    parser.add_argument(
        '--status',
        action='store_true',
        help='Show ingestion statistics'
    )

    args = parser.parse_args()

    # Handle --list flag
    if args.list:
        list_connectors()
        return 0

    # Handle --status flag or 'status' command
    if args.status or args.connector == 'status':
        asyncio.run(show_status())
        return 0

    # Validate required arguments for connector commands
    if not args.connector or not args.query:
        parser.print_help()
        return 1

    # Run the connector
    exit_code = asyncio.run(run_connector(args.connector, args.query, args.verbose))
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
