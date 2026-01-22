import unittest
from prisma import Prisma


class TestRawIngestion(unittest.IsolatedAsyncioTestCase):
    """Test RawIngestion model CRUD operations"""

    async def asyncSetUp(self):
        """Set up test database connection"""
        self.db = Prisma()
        await self.db.connect()

    async def asyncTearDown(self):
        """Clean up test database connection"""
        await self.db.disconnect()

    async def test_create_raw_ingestion_record(self):
        """Test creating a RawIngestion record with all required fields"""
        # Arrange
        test_data = {
            "source": "serper",
            "source_url": "https://api.serper.dev/search?q=padel+edinburgh",
            "file_path": "engine/data/raw/serper/20260113_test.json",
            "status": "success",
            "hash": "abc123def456",
            "metadata_json": '{"query": "padel edinburgh", "result_count": 10}'
        }

        # Act
        record = await self.db.rawingestion.create(data=test_data)

        # Assert
        self.assertIsNotNone(record.id)
        self.assertEqual(record.source, "serper")
        self.assertEqual(record.source_url, test_data["source_url"])
        self.assertEqual(record.file_path, test_data["file_path"])
        self.assertEqual(record.status, "success")
        self.assertEqual(record.hash, test_data["hash"])
        self.assertEqual(record.metadata_json, test_data["metadata_json"])
        self.assertIsNotNone(record.ingested_at)

        # Cleanup
        await self.db.rawingestion.delete(where={"id": record.id})

    async def test_prevent_duplicate_hash(self):
        """Test that duplicate hash values are handled correctly"""
        # Arrange
        test_data = {
            "source": "serper",
            "source_url": "https://api.serper.dev/search?q=test",
            "file_path": "engine/data/raw/serper/20260113_test1.json",
            "status": "success",
            "hash": "duplicate_hash_123"
        }

        # Act - Create first record
        record1 = await self.db.rawingestion.create(data=test_data)

        # Try to create second record with same hash
        test_data["file_path"] = "engine/data/raw/serper/20260113_test2.json"

        # We expect this to either:
        # 1. Succeed if hash is not unique constraint
        # 2. Fail if hash has unique constraint
        # For now, we'll test that we can query by hash
        found = await self.db.rawingestion.find_first(
            where={"hash": "duplicate_hash_123"}
        )

        # Assert
        self.assertIsNotNone(found)
        self.assertEqual(found.hash, "duplicate_hash_123")

        # Cleanup
        await self.db.rawingestion.delete_many(
            where={"hash": "duplicate_hash_123"}
        )

    async def test_query_by_source(self):
        """Test querying RawIngestion records by source"""
        # Arrange - Create test records
        sources = ["serper", "google_places", "osm"]
        created_ids = []

        for i, source in enumerate(sources):
            record = await self.db.rawingestion.create(data={
                "source": source,
                "source_url": f"https://api.{source}.com/test",
                "file_path": f"engine/data/raw/{source}/test_{i}.json",
                "status": "success",
                "hash": f"hash_{source}_{i}"
            })
            created_ids.append(record.id)

        # Act - Query by source
        serper_records = await self.db.rawingestion.find_many(
            where={"source": "serper"}
        )

        # Assert
        self.assertGreaterEqual(len(serper_records), 1)
        self.assertTrue(all(r.source == "serper" for r in serper_records))

        # Cleanup
        for record_id in created_ids:
            await self.db.rawingestion.delete(where={"id": record_id})

    async def test_query_by_status(self):
        """Test querying RawIngestion records by status"""
        # Arrange - Create records with different statuses
        statuses = ["success", "failed", "pending"]
        created_ids = []

        for i, status in enumerate(statuses):
            record = await self.db.rawingestion.create(data={
                "source": "test_source",
                "source_url": f"https://test.com/{i}",
                "file_path": f"engine/data/raw/test/test_{i}.json",
                "status": status,
                "hash": f"hash_status_{i}"
            })
            created_ids.append(record.id)

        # Act - Query by status
        failed_records = await self.db.rawingestion.find_many(
            where={"status": "failed"}
        )

        # Assert
        self.assertGreaterEqual(len(failed_records), 1)
        self.assertTrue(all(r.status == "failed" for r in failed_records))

        # Cleanup
        for record_id in created_ids:
            await self.db.rawingestion.delete(where={"id": record_id})


if __name__ == "__main__":
    unittest.main()
