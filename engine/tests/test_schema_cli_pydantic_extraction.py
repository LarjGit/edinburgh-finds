"""
Tests for schema CLI pydantic extraction integration.
"""

import unittest
from pathlib import Path
from unittest.mock import patch


class TestSchemaCliPydanticExtraction(unittest.TestCase):
    """Validate --pydantic-extraction CLI behavior."""

    @patch("engine.schema.cli.print_error")
    @patch("sys.argv", ["cli.py", "--schema", "venue", "--pydantic-extraction"])
    def test_cli_rejects_non_listing_schema(self, mock_print_error):
        """--pydantic-extraction should reject non-listing schema."""
        from engine.schema import cli

        with self.assertRaises(SystemExit) as cm:
            cli.main()

        self.assertEqual(cm.exception.code, 1)
        mock_print_error.assert_called_once()

    @patch("engine.schema.cli.generate_pydantic_extraction_model")
    @patch("engine.schema.cli.generate_python_schema")
    @patch("engine.schema.cli.find_schema_files")
    @patch("engine.schema.cli.print_info")
    @patch("engine.schema.cli.print_warning")
    @patch("sys.argv", ["cli.py", "--schema", "listing", "--pydantic-extraction", "--dry-run"])
    def test_cli_calls_pydantic_generator_for_listing(
        self,
        mock_print_warning,
        mock_print_info,
        mock_find_schema_files,
        mock_generate_python_schema,
        mock_generate_pydantic,
    ):
        """--pydantic-extraction should invoke the generator for listing."""
        from engine.schema import cli

        mock_find_schema_files.return_value = [Path("listing.yaml")]
        mock_generate_python_schema.return_value = (True, "ok")
        mock_generate_pydantic.return_value = (True, "ok")

        cli.main()

        mock_generate_pydantic.assert_called_once()


if __name__ == "__main__":
    unittest.main()
