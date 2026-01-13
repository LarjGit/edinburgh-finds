"""
Serper Connector CLI Entry Point

Usage:
    python -m engine.ingestion.run_serper "padel edinburgh"
    python -m engine.ingestion.run_serper "padel courts near me"
"""

import sys
from engine.ingestion.cli import run_connector
import asyncio


def main():
    """Run Serper connector"""
    if len(sys.argv) < 2:
        print("Usage: python -m engine.ingestion.run_serper <query>")
        print("Example: python -m engine.ingestion.run_serper 'padel edinburgh'")
        sys.exit(1)

    query = ' '.join(sys.argv[1:])
    exit_code = asyncio.run(run_connector('serper', query, verbose=True))
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
