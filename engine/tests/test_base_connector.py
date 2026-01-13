import unittest
from abc import ABC
from unittest.mock import AsyncMock, MagicMock, patch
from prisma import Prisma


class TestBaseConnectorInterface(unittest.TestCase):
    """Test the BaseConnector abstract interface"""

    def test_base_connector_exists(self):
        """Test that BaseConnector class can be imported"""
        try:
            from engine.ingestion.base import BaseConnector
            self.assertIsNotNone(BaseConnector)
        except ImportError as e:
            self.fail(f"Failed to import BaseConnector: {e}")

    def test_base_connector_is_abstract(self):
        """Test that BaseConnector is an abstract base class"""
        from engine.ingestion.base import BaseConnector

        # BaseConnector should inherit from ABC
        self.assertTrue(
            issubclass(BaseConnector, ABC),
            "BaseConnector should inherit from ABC"
        )

    def test_base_connector_cannot_be_instantiated(self):
        """Test that BaseConnector cannot be instantiated directly"""
        from engine.ingestion.base import BaseConnector

        # Attempting to instantiate should raise TypeError
        with self.assertRaises(TypeError) as context:
            BaseConnector()

        self.assertIn("abstract", str(context.exception).lower())

    def test_base_connector_has_fetch_method(self):
        """Test that BaseConnector defines abstract fetch method"""
        from engine.ingestion.base import BaseConnector

        # Check that fetch method exists and is abstract
        self.assertTrue(
            hasattr(BaseConnector, "fetch"),
            "BaseConnector should define fetch method"
        )

    def test_base_connector_has_save_method(self):
        """Test that BaseConnector defines abstract save method"""
        from engine.ingestion.base import BaseConnector

        # Check that save method exists and is abstract
        self.assertTrue(
            hasattr(BaseConnector, "save"),
            "BaseConnector should define save method"
        )

    def test_base_connector_has_is_duplicate_method(self):
        """Test that BaseConnector defines is_duplicate method"""
        from engine.ingestion.base import BaseConnector

        # Check that is_duplicate method exists
        self.assertTrue(
            hasattr(BaseConnector, "is_duplicate"),
            "BaseConnector should define is_duplicate method"
        )

    def test_base_connector_has_source_name_property(self):
        """Test that BaseConnector defines source_name property"""
        from engine.ingestion.base import BaseConnector

        # Check that source_name property exists
        self.assertTrue(
            hasattr(BaseConnector, "source_name"),
            "BaseConnector should define source_name property"
        )


class TestBaseConnectorSubclass(unittest.IsolatedAsyncioTestCase):
    """Test BaseConnector with a concrete implementation"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        from engine.ingestion.base import BaseConnector

        # Create a concrete subclass for testing
        class TestConnector(BaseConnector):
            """Test implementation of BaseConnector"""

            @property
            def source_name(self) -> str:
                return "test_source"

            async def fetch(self, query: str) -> dict:
                """Fetch test data"""
                return {"query": query, "results": []}

            async def save(self, data: dict, source_url: str) -> str:
                """Save test data"""
                return "engine/data/raw/test_source/test.json"

            async def is_duplicate(self, content_hash: str) -> bool:
                """Check for duplicates"""
                return False

        self.TestConnector = TestConnector

    async def test_concrete_connector_can_be_instantiated(self):
        """Test that concrete connector implementing all methods can be instantiated"""
        connector = self.TestConnector()
        self.assertIsNotNone(connector)

    async def test_concrete_connector_has_source_name(self):
        """Test that concrete connector provides source_name"""
        connector = self.TestConnector()
        self.assertEqual(connector.source_name, "test_source")

    async def test_concrete_connector_fetch_returns_data(self):
        """Test that concrete connector fetch method works"""
        connector = self.TestConnector()
        result = await connector.fetch("test query")
        self.assertIsInstance(result, dict)
        self.assertIn("query", result)

    async def test_concrete_connector_save_returns_path(self):
        """Test that concrete connector save method returns file path"""
        connector = self.TestConnector()
        path = await connector.save({"test": "data"}, "https://example.com")
        self.assertIsInstance(path, str)
        self.assertIn("engine/data/raw", path)

    async def test_concrete_connector_is_duplicate_returns_bool(self):
        """Test that concrete connector is_duplicate method returns boolean"""
        connector = self.TestConnector()
        result = await connector.is_duplicate("test_hash_123")
        self.assertIsInstance(result, bool)

    async def test_incomplete_connector_cannot_be_instantiated(self):
        """Test that connector missing abstract methods cannot be instantiated"""
        from engine.ingestion.base import BaseConnector

        # Create incomplete subclass (missing methods)
        class IncompleteConnector(BaseConnector):
            @property
            def source_name(self) -> str:
                return "incomplete"
            # Missing fetch, save, is_duplicate

        # Should raise TypeError when trying to instantiate
        with self.assertRaises(TypeError):
            IncompleteConnector()


if __name__ == "__main__":
    unittest.main()
