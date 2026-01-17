"""
Entry point for schema generation CLI tool.

Allows running as:
    python -m engine.schema.generate [options]
"""

from engine.schema.cli import main

if __name__ == '__main__':
    main()
