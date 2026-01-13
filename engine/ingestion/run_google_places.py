"""
Google Places Connector CLI Entry Point

Usage:
    python -m engine.ingestion.run_google_places "padel edinburgh"
    python -m engine.ingestion.run_google_places "padel courts"
"""

import sys
from engine.ingestion.cli import run_connector
import asyncio


def main():
    """Run Google Places connector"""
    if len(sys.argv) < 2:
        print("Usage: python -m engine.ingestion.run_google_places <query>")
        print("Example: python -m engine.ingestion.run_google_places 'padel courts edinburgh'")
        sys.exit(1)

    query = ' '.join(sys.argv[1:])
    exit_code = asyncio.run(run_connector('google_places', query, verbose=True))
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
