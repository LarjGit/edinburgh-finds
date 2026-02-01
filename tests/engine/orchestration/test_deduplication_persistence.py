"""
Tests for ingestion-level deduplication in orchestration persistence.

Architecture.md 4.1 Stage 5 requires: "Perform ingestion-level deduplication of
identical payloads". This test suite verifies that identical raw payloads create
only one RawIngestion record, preventing storage waste and ensuring replay stability.
"""

import pytest
from unittest.mock import Mock
from prisma import Prisma
from engine.orchestration.persistence import PersistenceManager


@pytest.mark.asyncio
class TestIngestionLevelDeduplication:
    """Test RI-001: Ingestion-level deduplication enforcement."""

    async def test_duplicate_payload_creates_only_one_raw_ingestion(self):
        """
        Verify that ingesting the same raw payload twice creates only one
        RawIngestion record.

        Architecture requirement: Stage 5 - "Perform ingestion-level deduplication"
        """
        # Setup
        db = Prisma()
        await db.connect()
        manager = PersistenceManager(db)

        # Create identical candidates with same raw payload
        candidate = {
            "source": "serper",
            "name": "Test Dedup Venue",
            "raw": {
                "title": "Test Dedup Venue",
                "link": "https://example.com/dedup",
                "snippet": "A test venue for deduplication"
            }
        }

        try:
            # Count before any ingestion
            count_before = await db.rawingestion.count(where={"source": "serper"})

            # First ingestion
            errors = []
            await manager.persist_entities([candidate], errors)

            # Count after first ingestion
            count_after_first = await db.rawingestion.count(where={"source": "serper"})

            # Second ingestion (identical payload)
            errors2 = []
            await manager.persist_entities([candidate], errors2)

            # Count after second ingestion
            count_after_second = await db.rawingestion.count(where={"source": "serper"})

            # Assertions
            assert count_after_first == count_before + 1, \
                "First ingestion should create one RawIngestion record"
            assert count_after_second == count_after_first, \
                "Second ingestion should not create new RawIngestion record (deduplication)"

        finally:
            # Cleanup - delete any test records created
            await db.rawingestion.delete_many(
                where={"source": "serper", "source_url": {"contains": "example.com/dedup"}}
            )
            await db.disconnect()

    async def test_duplicate_payload_reuses_file_path(self):
        """
        Verify that duplicate payloads reuse the same file_path, ensuring
        replay stability (RI-002 requirement).
        """
        db = Prisma()
        await db.connect()
        manager = PersistenceManager(db)

        candidate = {
            "source": "google_places",
            "name": "Replay Test Venue",
            "raw": {"place_id": "ChIJ123replay", "name": "Replay Test Venue"}
        }

        try:
            # First ingestion
            errors = []
            await manager.persist_entities([candidate], errors)

            # Find the RawIngestion record
            raw_ingestion_1 = await db.rawingestion.find_first(
                where={"source": "google_places", "source_url": {"contains": "ChIJ123replay"}}
            )

            # Second ingestion (same payload)
            errors2 = []
            await manager.persist_entities([candidate], errors2)

            # Find all matching records
            all_records = await db.rawingestion.find_many(
                where={"source": "google_places", "source_url": {"contains": "ChIJ123replay"}}
            )

            # Assertions
            assert len(all_records) == 1, \
                f"Should only have 1 RawIngestion record for duplicate payload, found {len(all_records)}"
            assert raw_ingestion_1.id == all_records[0].id, \
                "Should be same RawIngestion record"

        finally:
            # Cleanup
            await db.rawingestion.delete_many(
                where={"source": "google_places", "source_url": {"contains": "ChIJ123replay"}}
            )
            await db.disconnect()

    async def test_different_payloads_create_separate_records(self):
        """
        Verify that different payloads still create separate RawIngestion records.
        Deduplication should only affect identical content.
        """
        import hashlib
        import json

        db = Prisma()
        await db.connect()
        manager = PersistenceManager(db)

        candidate1 = {
            "source": "openstreetmap",
            "name": "Venue A Different",
            "raw": {"name": "Venue A Different", "id": "osm_diff_1", "type": "node"}
        }

        candidate2 = {
            "source": "openstreetmap",
            "name": "Venue B Different",
            "raw": {"name": "Venue B Different", "id": "osm_diff_2", "type": "node"}
        }

        # Compute expected hashes
        hash1 = hashlib.sha256(json.dumps(candidate1["raw"], indent=2).encode()).hexdigest()[:16]
        hash2 = hashlib.sha256(json.dumps(candidate2["raw"], indent=2).encode()).hexdigest()[:16]

        try:
            # Count before ingestion
            count_before = await db.rawingestion.count(where={"source": "openstreetmap"})

            # Ingest different candidates
            errors1 = []
            errors2 = []
            await manager.persist_entities([candidate1], errors1)
            await manager.persist_entities([candidate2], errors2)

            # Count after ingestion
            count_after = await db.rawingestion.count(where={"source": "openstreetmap"})

            # Assertions
            assert count_after == count_before + 2, \
                f"Different payloads should create 2 separate records, expected {count_before + 2}, got {count_after}"

            # Verify both records exist with different hashes
            record1 = await db.rawingestion.find_first(where={"hash": hash1})
            record2 = await db.rawingestion.find_first(where={"hash": hash2})

            assert record1 is not None, f"Record 1 with hash {hash1} not found"
            assert record2 is not None, f"Record 2 with hash {hash2} not found"
            assert record1.hash != record2.hash, \
                "Different payloads should have different hashes"

        finally:
            # Cleanup by hash
            if 'hash1' in locals():
                await db.rawingestion.delete_many(where={"hash": hash1})
            if 'hash2' in locals():
                await db.rawingestion.delete_many(where={"hash": hash2})
            await db.disconnect()
