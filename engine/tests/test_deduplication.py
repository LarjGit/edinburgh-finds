import unittest
from prisma import Prisma


class TestDeduplicationHelpers(unittest.TestCase):
    """Test hash-based deduplication helper functions"""

    def test_deduplication_module_exists(self):
        """Test that deduplication module can be imported"""
        try:
            from engine.ingestion import deduplication
            self.assertIsNotNone(deduplication)
        except ImportError as e:
            self.fail(f"Failed to import deduplication module: {e}")

    def test_compute_content_hash_exists(self):
        """Test that compute_content_hash function exists"""
        try:
            from engine.ingestion.deduplication import compute_content_hash
            self.assertIsNotNone(compute_content_hash)
        except ImportError as e:
            self.fail(f"Failed to import compute_content_hash: {e}")

    def test_compute_content_hash_returns_string(self):
        """Test that compute_content_hash returns a string hash"""
        from engine.ingestion.deduplication import compute_content_hash

        test_data = {"query": "test", "results": [1, 2, 3]}
        hash_value = compute_content_hash(test_data)

        self.assertIsInstance(hash_value, str)
        self.assertGreater(len(hash_value), 0)

    def test_compute_content_hash_consistent(self):
        """Test that same data produces same hash"""
        from engine.ingestion.deduplication import compute_content_hash

        test_data = {"query": "padel edinburgh", "count": 42}

        hash1 = compute_content_hash(test_data)
        hash2 = compute_content_hash(test_data)

        self.assertEqual(hash1, hash2)

    def test_compute_content_hash_different_data(self):
        """Test that different data produces different hashes"""
        from engine.ingestion.deduplication import compute_content_hash

        data1 = {"query": "padel edinburgh"}
        data2 = {"query": "golf edinburgh"}

        hash1 = compute_content_hash(data1)
        hash2 = compute_content_hash(data2)

        self.assertNotEqual(hash1, hash2)

    def test_compute_content_hash_order_independent(self):
        """Test that hash is order-independent for dict keys"""
        from engine.ingestion.deduplication import compute_content_hash

        # Same data, different key order
        data1 = {"a": 1, "b": 2, "c": 3}
        data2 = {"c": 3, "a": 1, "b": 2}

        hash1 = compute_content_hash(data1)
        hash2 = compute_content_hash(data2)

        # Should be the same since content is identical
        self.assertEqual(hash1, hash2)

    def test_compute_content_hash_nested_data(self):
        """Test that hash works with deeply nested data structures"""
        from engine.ingestion.deduplication import compute_content_hash

        test_data = {
            "query": "test",
            "results": [
                {"name": "place1", "rating": 4.5},
                {"name": "place2", "rating": 3.8}
            ],
            "metadata": {
                "count": 2,
                "timestamp": "2026-01-13"
            }
        }

        hash_value = compute_content_hash(test_data)

        self.assertIsInstance(hash_value, str)
        self.assertGreater(len(hash_value), 0)

    def test_compute_content_hash_uses_sha256(self):
        """Test that hash is SHA-256 (64 hexadecimal characters)"""
        from engine.ingestion.deduplication import compute_content_hash

        test_data = {"test": "data"}
        hash_value = compute_content_hash(test_data)

        # SHA-256 produces 64 hex characters
        self.assertEqual(len(hash_value), 64)
        # Should only contain hexadecimal characters
        self.assertTrue(all(c in '0123456789abcdef' for c in hash_value))


class TestDeduplicationDatabase(unittest.IsolatedAsyncioTestCase):
    """Test database-based deduplication checking"""

    async def asyncSetUp(self):
        """Set up test database connection"""
        self.db = Prisma()
        await self.db.connect()

    async def asyncTearDown(self):
        """Clean up test database connection"""
        await self.db.disconnect()

    async def test_check_duplicate_exists(self):
        """Test that check_duplicate function exists"""
        try:
            from engine.ingestion.deduplication import check_duplicate
            self.assertIsNotNone(check_duplicate)
        except ImportError as e:
            self.fail(f"Failed to import check_duplicate: {e}")

    async def test_check_duplicate_returns_false_for_new_hash(self):
        """Test that check_duplicate returns False for non-existent hash"""
        from engine.ingestion.deduplication import check_duplicate

        # Use a unique hash that doesn't exist
        unique_hash = "abc123unique_test_hash_not_in_db"

        is_duplicate = await check_duplicate(self.db, unique_hash)

        self.assertFalse(is_duplicate)

    async def test_check_duplicate_returns_true_for_existing_hash(self):
        """Test that check_duplicate returns True for existing hash"""
        from engine.ingestion.deduplication import check_duplicate

        # Create a test record with a known hash
        test_hash = "test_duplicate_hash_12345"
        record = await self.db.rawingestion.create(data={
            "source": "test_source",
            "source_url": "https://test.com/duplicate",
            "file_path": "engine/data/raw/test/duplicate.json",
            "status": "success",
            "hash": test_hash
        })

        try:
            # Check if it's detected as duplicate
            is_duplicate = await check_duplicate(self.db, test_hash)

            self.assertTrue(is_duplicate)
        finally:
            # Cleanup
            await self.db.rawingestion.delete(where={"id": record.id})

    async def test_check_duplicate_multiple_sources(self):
        """Test that check_duplicate works across different sources"""
        from engine.ingestion.deduplication import check_duplicate

        # Same hash from different sources should still be duplicate
        test_hash = "shared_content_hash_67890"

        record1 = await self.db.rawingestion.create(data={
            "source": "serper",
            "source_url": "https://serper.com/test",
            "file_path": "engine/data/raw/serper/test.json",
            "status": "success",
            "hash": test_hash
        })

        try:
            # Check duplicate (should be True even from different source)
            is_duplicate = await check_duplicate(self.db, test_hash)

            self.assertTrue(is_duplicate)
        finally:
            # Cleanup
            await self.db.rawingestion.delete(where={"id": record1.id})


if __name__ == "__main__":
    unittest.main()
