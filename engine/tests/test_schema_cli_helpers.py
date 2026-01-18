"""
Tests for schema CLI helper functions.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from engine.schema import cli


def _write_schema(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "schema:",
                "  name: Listing",
                "  description: Test schema",
                "",
                "fields:",
                "  - name: entity_name",
                "    type: string",
                "    description: Name",
                "    nullable: false",
                "    required: true",
            ]
        ),
        encoding="utf-8",
    )


class TestSchemaCliHelpers(unittest.TestCase):
    """Unit tests for CLI helper functions."""

    def test_print_helpers(self):
        cli.print_info("info")
        cli.print_warning("warning")
        cli.print_error("error")
        cli.print_success("success")

    def test_find_schema_files_specific(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir)
            listing = schema_dir / "listing.yaml"
            venue = schema_dir / "venue.yaml"
            _write_schema(listing)
            _write_schema(venue)

            result = cli.find_schema_files(schema_dir, "listing")
            self.assertEqual(result, [listing])

    def test_find_schema_files_all(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir)
            listing = schema_dir / "listing.yaml"
            venue = schema_dir / "venue.yaml"
            _write_schema(listing)
            _write_schema(venue)

            result = cli.find_schema_files(schema_dir)
            self.assertEqual(result, sorted([listing, venue]))

    @patch("engine.schema.cli.print_error")
    def test_find_schema_files_missing_raises(self, mock_print_error):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir)
            with self.assertRaises(SystemExit) as cm:
                cli.find_schema_files(schema_dir, "missing")

            self.assertEqual(cm.exception.code, 1)
            mock_print_error.assert_called_once()

    @patch("engine.schema.cli.print_error")
    def test_find_schema_files_no_yaml_raises(self, mock_print_error):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir)
            with self.assertRaises(SystemExit) as cm:
                cli.find_schema_files(schema_dir)

            self.assertEqual(cm.exception.code, 1)
            mock_print_error.assert_called_once()

    def test_generate_python_schema_dry_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir)
            output_dir = Path(temp_dir) / "out"
            listing = schema_dir / "listing.yaml"
            _write_schema(listing)

            success, message = cli.generate_python_schema(
                listing, output_dir, dry_run=True
            )
            self.assertTrue(success)
            self.assertIn("Would generate", message)

    def test_generate_python_schema_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir)
            output_dir = Path(temp_dir) / "out"
            output_dir.mkdir()
            listing = schema_dir / "listing.yaml"
            _write_schema(listing)

            success, message = cli.generate_python_schema(
                listing, output_dir, dry_run=False, force=True
            )
            self.assertTrue(success)
            self.assertIn("Generated", message)
            self.assertTrue((output_dir / "listing.py").exists())

    def test_generate_typescript_schema_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir)
            output_dir = Path(temp_dir) / "types"
            listing = schema_dir / "listing.yaml"
            _write_schema(listing)

            success, message = cli.generate_typescript_schema(
                listing, output_dir, include_zod=True, dry_run=False, force=True
            )
            self.assertTrue(success)
            self.assertIn("Generated", message)
            self.assertTrue((output_dir / "listing.ts").exists())

    def test_generate_typescript_schema_dry_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir)
            output_dir = Path(temp_dir) / "types"
            listing = schema_dir / "listing.yaml"
            _write_schema(listing)

            success, message = cli.generate_typescript_schema(
                listing, output_dir, include_zod=False, dry_run=True
            )
            self.assertTrue(success)
            self.assertIn("Would generate", message)

    @patch("builtins.input", return_value="n")
    def test_generate_typescript_schema_skip_existing(self, mock_input):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir)
            output_dir = Path(temp_dir) / "types"
            output_dir.mkdir()
            listing = schema_dir / "listing.yaml"
            _write_schema(listing)
            existing = output_dir / "listing.ts"
            existing.write_text("existing", encoding="utf-8")

            success, message = cli.generate_typescript_schema(
                listing, output_dir, include_zod=False, dry_run=False, force=False
            )
            self.assertFalse(success)
            self.assertIn("Skipped", message)
            mock_input.assert_called_once()

    def test_generate_pydantic_extraction_model_dry_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir)
            listing = schema_dir / "listing.yaml"
            output_file = schema_dir / "entity_extraction.py"
            _write_schema(listing)

            success, message = cli.generate_pydantic_extraction_model(
                listing, output_file, dry_run=True
            )
            self.assertTrue(success)
            self.assertIn("Would generate", message)

    def test_generate_pydantic_extraction_model_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir)
            listing = schema_dir / "listing.yaml"
            output_file = schema_dir / "entity_extraction.py"
            _write_schema(listing)

            success, message = cli.generate_pydantic_extraction_model(
                listing, output_file, dry_run=False, force=True
            )
            self.assertTrue(success)
            self.assertIn("Generated", message)
            self.assertTrue(output_file.exists())

    @patch("builtins.input", return_value="n")
    def test_generate_pydantic_extraction_model_skip_existing(self, mock_input):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir)
            listing = schema_dir / "listing.yaml"
            output_file = schema_dir / "entity_extraction.py"
            _write_schema(listing)
            output_file.write_text("existing", encoding="utf-8")

            success, message = cli.generate_pydantic_extraction_model(
                listing, output_file, dry_run=False, force=False
            )
            self.assertFalse(success)
            self.assertIn("Skipped", message)
            mock_input.assert_called_once()

    def test_validate_schema_sync_in_sync(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir) / "schemas"
            python_dir = Path(temp_dir) / "python"
            schema_dir.mkdir()
            python_dir.mkdir()

            listing = schema_dir / "listing.yaml"
            _write_schema(listing)

            parser = cli.SchemaParser()
            schema = parser.parse(listing)
            generator = cli.PythonFieldSpecGenerator()
            expected_code = generator.generate(schema, source_file="listing.yaml")
            (python_dir / "listing.py").write_text(expected_code, encoding="utf-8")

            all_valid, messages = cli.validate_schema_sync(schema_dir, python_dir)
            self.assertTrue(all_valid)
            self.assertTrue(any("In sync" in msg for msg in messages))

    def test_validate_schema_sync_missing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir) / "schemas"
            python_dir = Path(temp_dir) / "python"
            schema_dir.mkdir()
            python_dir.mkdir()

            listing = schema_dir / "listing.yaml"
            _write_schema(listing)

            all_valid, messages = cli.validate_schema_sync(schema_dir, python_dir)
            self.assertFalse(all_valid)
            self.assertTrue(any("File not found" in msg for msg in messages))

    def test_validate_schema_sync_out_of_sync(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_dir = Path(temp_dir) / "schemas"
            python_dir = Path(temp_dir) / "python"
            schema_dir.mkdir()
            python_dir.mkdir()

            listing = schema_dir / "listing.yaml"
            _write_schema(listing)
            (python_dir / "listing.py").write_text("out of sync", encoding="utf-8")

            all_valid, messages = cli.validate_schema_sync(schema_dir, python_dir)
            self.assertFalse(all_valid)
            self.assertTrue(any("OUT OF SYNC" in msg for msg in messages))

    @patch("engine.schema.cli.print_success")
    @patch("subprocess.run")
    def test_format_generated_files_success(self, mock_run, mock_print_success):
        mock_run.return_value = type("Result", (), {"returncode": 0})()
        cli.format_generated_files([Path("listing.py")])
        mock_print_success.assert_called_once()

    @patch("engine.schema.cli.print_warning")
    @patch("subprocess.run")
    def test_format_generated_files_failure(self, mock_run, mock_print_warning):
        mock_run.return_value = type("Result", (), {"returncode": 1, "stderr": "err"})()
        cli.format_generated_files([Path("listing.py")])
        mock_print_warning.assert_called_once()

    @patch("engine.schema.cli.print_warning")
    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_format_generated_files_black_missing(self, mock_run, mock_print_warning):
        cli.format_generated_files([Path("listing.py")])
        mock_print_warning.assert_called_once()


class TestSchemaCliMain(unittest.TestCase):
    """Tests for CLI main entry point branches."""

    @patch("engine.schema.cli.print_error")
    @patch("sys.argv", ["cli.py", "--zod"])
    def test_main_rejects_zod_without_typescript(self, mock_print_error):
        with self.assertRaises(SystemExit) as cm:
            cli.main()

        self.assertEqual(cm.exception.code, 1)
        mock_print_error.assert_called_once()

    @patch("engine.schema.cli.print_success")
    @patch("engine.schema.cli.print_error")
    @patch("engine.schema.cli.print_info")
    @patch("engine.schema.cli.validate_schema_sync")
    @patch("sys.argv", ["cli.py", "--validate"])
    def test_main_validate_mode_success(
        self, mock_validate, mock_print_info, mock_print_error, mock_print_success
    ):
        mock_validate.return_value = (True, ["✓ listing.py: In sync"])
        with self.assertRaises(SystemExit) as cm:
            cli.main()

        self.assertEqual(cm.exception.code, 0)
        mock_print_success.assert_called()

    @patch("engine.schema.cli.print_success")
    @patch("engine.schema.cli.print_error")
    @patch("engine.schema.cli.print_info")
    @patch("engine.schema.cli.validate_schema_sync")
    @patch("sys.argv", ["cli.py", "--validate"])
    def test_main_validate_mode_failure(
        self, mock_validate, mock_print_info, mock_print_error, mock_print_success
    ):
        mock_validate.return_value = (False, ["✗ listing.py: OUT OF SYNC"])
        with self.assertRaises(SystemExit) as cm:
            cli.main()

        self.assertEqual(cm.exception.code, 1)
        mock_print_error.assert_called()

    @patch("engine.schema.cli.print_error")
    @patch("engine.schema.cli.print_info")
    @patch("engine.schema.cli.find_schema_files")
    @patch("engine.schema.cli.generate_python_schema")
    @patch("sys.argv", ["cli.py", "--dry-run"])
    def test_main_generate_mode_reports_errors(
        self,
        mock_generate_python_schema,
        mock_find_schema_files,
        mock_print_info,
        mock_print_error,
    ):
        mock_find_schema_files.return_value = [Path("listing.yaml")]
        mock_generate_python_schema.return_value = (False, "fail")

        with self.assertRaises(SystemExit) as cm:
            cli.main()

        self.assertEqual(cm.exception.code, 1)
        mock_print_error.assert_called()

if __name__ == "__main__":
    unittest.main()
