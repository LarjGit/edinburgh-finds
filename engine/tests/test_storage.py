import unittest
import os
import json
import shutil
from datetime import datetime


class TestStorageHelpers(unittest.TestCase):
    """Test filesystem storage helper functions"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_data_dir = "engine/data/test_raw"
        self.test_source = "test_source"

    def tearDown(self):
        """Clean up test data"""
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)

    def test_storage_module_exists(self):
        """Test that storage module can be imported"""
        try:
            from engine.ingestion import storage
            self.assertIsNotNone(storage)
        except ImportError as e:
            self.fail(f"Failed to import storage module: {e}")

    def test_generate_file_path_format(self):
        """Test that generate_file_path creates paths with correct format"""
        from engine.ingestion.storage import generate_file_path

        source = "serper"
        record_id = "test123"

        file_path = generate_file_path(source, record_id)

        # Should follow format: engine/data/raw/<source>/<timestamp>_<id>.json
        self.assertTrue(file_path.startswith("engine/data/raw/"))
        self.assertIn(source, file_path)
        self.assertIn(record_id, file_path)
        self.assertTrue(file_path.endswith(".json"))

    def test_generate_file_path_includes_timestamp(self):
        """Test that generated paths include timestamp"""
        from engine.ingestion.storage import generate_file_path

        file_path = generate_file_path("test_source", "id123")

        # Extract filename and check for timestamp pattern (YYYYMMDD)
        filename = os.path.basename(file_path)
        today = datetime.now().strftime("%Y%m%d")
        self.assertIn(today, filename)

    def test_generate_file_path_unique(self):
        """Test that consecutive calls generate unique paths"""
        from engine.ingestion.storage import generate_file_path

        path1 = generate_file_path("source1", "id1")
        path2 = generate_file_path("source1", "id2")

        # Different IDs should result in different paths
        self.assertNotEqual(path1, path2)

    def test_ensure_directory_exists_creates_dir(self):
        """Test that ensure_directory_exists creates directories"""
        from engine.ingestion.storage import ensure_directory_exists

        test_path = os.path.join(self.test_data_dir, "subdir", "test.json")

        # Directory should not exist yet
        dir_path = os.path.dirname(test_path)
        self.assertFalse(os.path.exists(dir_path))

        # Create directory
        ensure_directory_exists(test_path)

        # Directory should now exist
        self.assertTrue(os.path.exists(dir_path))
        self.assertTrue(os.path.isdir(dir_path))

    def test_ensure_directory_exists_idempotent(self):
        """Test that ensure_directory_exists is idempotent (safe to call multiple times)"""
        from engine.ingestion.storage import ensure_directory_exists

        test_path = os.path.join(self.test_data_dir, "test.json")

        # Call multiple times
        ensure_directory_exists(test_path)
        ensure_directory_exists(test_path)
        ensure_directory_exists(test_path)

        # Should not raise error and directory should exist
        self.assertTrue(os.path.exists(os.path.dirname(test_path)))

    def test_save_json_creates_file(self):
        """Test that save_json creates a JSON file"""
        from engine.ingestion.storage import save_json

        test_data = {"test": "data", "count": 42}
        file_path = os.path.join(self.test_data_dir, "test.json")

        # File should not exist yet
        self.assertFalse(os.path.exists(file_path))

        # Save JSON
        save_json(file_path, test_data)

        # File should now exist
        self.assertTrue(os.path.exists(file_path))
        self.assertTrue(os.path.isfile(file_path))

    def test_save_json_content_valid(self):
        """Test that save_json writes valid JSON content"""
        from engine.ingestion.storage import save_json

        test_data = {
            "source": "test",
            "results": [1, 2, 3],
            "nested": {"key": "value"}
        }
        file_path = os.path.join(self.test_data_dir, "test.json")

        # Create directory first
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save and read back
        save_json(file_path, test_data)

        with open(file_path, 'r') as f:
            loaded_data = json.load(f)

        # Content should match
        self.assertEqual(loaded_data, test_data)

    def test_save_json_handles_nested_data(self):
        """Test that save_json handles deeply nested structures"""
        from engine.ingestion.storage import save_json

        test_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "items": [1, 2, 3],
                        "text": "deep"
                    }
                }
            }
        }
        file_path = os.path.join(self.test_data_dir, "nested.json")

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        save_json(file_path, test_data)

        with open(file_path, 'r') as f:
            loaded_data = json.load(f)

        self.assertEqual(loaded_data, test_data)

    def test_save_json_pretty_prints(self):
        """Test that save_json formats JSON with indentation for readability"""
        from engine.ingestion.storage import save_json

        test_data = {"key": "value", "list": [1, 2, 3]}
        file_path = os.path.join(self.test_data_dir, "pretty.json")

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        save_json(file_path, test_data)

        with open(file_path, 'r') as f:
            content = f.read()

        # Should have newlines and indentation (not all on one line)
        self.assertIn('\n', content)
        self.assertGreater(len(content.split('\n')), 1)

    def test_get_raw_data_dir_returns_correct_path(self):
        """Test that get_raw_data_dir returns base directory for raw data"""
        from engine.ingestion.storage import get_raw_data_dir

        base_dir = get_raw_data_dir()

        # Should return engine/data/raw
        self.assertEqual(base_dir, "engine/data/raw")

    def test_get_source_dir_returns_source_specific_path(self):
        """Test that get_source_dir returns source-specific directory"""
        from engine.ingestion.storage import get_source_dir

        source = "serper"
        source_dir = get_source_dir(source)

        # Should return engine/data/raw/<source> with forward slashes
        expected = "engine/data/raw/serper"
        self.assertEqual(source_dir, expected)


if __name__ == "__main__":
    unittest.main()
