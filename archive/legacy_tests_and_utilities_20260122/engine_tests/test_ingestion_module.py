import unittest
import os
import importlib.util


class TestIngestionModuleStructure(unittest.TestCase):
    """Test that the ingestion module structure exists and is properly configured"""

    def test_ingestion_directory_exists(self):
        """Test that engine/ingestion/ directory exists"""
        ingestion_path = os.path.join("engine", "ingestion")
        self.assertTrue(
            os.path.exists(ingestion_path),
            f"Expected directory {ingestion_path} to exist"
        )
        self.assertTrue(
            os.path.isdir(ingestion_path),
            f"Expected {ingestion_path} to be a directory"
        )

    def test_ingestion_module_importable(self):
        """Test that engine.ingestion module can be imported"""
        try:
            import engine.ingestion
            self.assertIsNotNone(engine.ingestion)
        except ImportError as e:
            self.fail(f"Failed to import engine.ingestion: {e}")

    def test_ingestion_init_exists(self):
        """Test that engine/ingestion/__init__.py exists"""
        init_path = os.path.join("engine", "ingestion", "__init__.py")
        self.assertTrue(
            os.path.exists(init_path),
            f"Expected {init_path} to exist for proper module structure"
        )

    def test_ingestion_module_has_docstring(self):
        """Test that engine.ingestion module has a descriptive docstring"""
        import engine.ingestion
        self.assertIsNotNone(
            engine.ingestion.__doc__,
            "Module should have a docstring describing its purpose"
        )
        self.assertGreater(
            len(engine.ingestion.__doc__.strip()),
            20,
            "Module docstring should be descriptive (>20 characters)"
        )


if __name__ == "__main__":
    unittest.main()
