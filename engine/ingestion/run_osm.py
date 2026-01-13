"""
OpenStreetMap Connector CLI Entry Point

Usage:
    python -m engine.ingestion.run_osm "padel"
    python -m engine.ingestion.run_osm "tennis"
"""

import sys
from engine.ingestion.cli import run_connector
import asyncio


def main():
    """Run OpenStreetMap connector"""
    if len(sys.argv) < 2:
        print("Usage: python -m engine.ingestion.run_osm <sport>")
        print("Example: python -m engine.ingestion.run_osm 'padel'")
        print("\nNote: OSM searches for sports facilities by sport tag (e.g., 'padel', 'tennis', 'golf')")
        sys.exit(1)

    query = ' '.join(sys.argv[1:])
    exit_code = asyncio.run(run_connector('openstreetmap', query, verbose=True))
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
