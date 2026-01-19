"""
Tests for Prisma array filters with Postgres text[] arrays.

Tests the has, hasSome, hasEvery array filter operations and verifies
that GIN indexes are used for efficient querying.

IMPORTANT: These tests require PostgreSQL with text[] array support.
They will be skipped when running against SQLite.
"""

import os
import pytest
import unittest
from prisma import Prisma
from typing import List, Dict, Any


def is_postgres() -> bool:
    """Check if the database is PostgreSQL (not SQLite)."""
    database_url = os.getenv("DATABASE_URL", "")
    return "postgres" in database_url or "postgresql" in database_url


# Skip all tests in this file if not using Postgres
pytestmark = pytest.mark.skipif(
    not is_postgres(),
    reason="Array filters require PostgreSQL - skipping on SQLite"
)


class TestPrismaArrayFilters(unittest.IsolatedAsyncioTestCase):
    """Test Prisma array filter operations with Postgres text[] arrays."""

    async def asyncSetUp(self):
        """Set up test database connection and create test fixtures."""
        self.db = Prisma()
        await self.db.connect()

        # Clean up any existing test data
        await self.db.listing.delete_many(
            where={"entity_name": {"contains": "TEST_ARRAY_FILTER"}}
        )

        # Create test fixtures
        self.fixtures = await self._create_test_fixtures()

    async def asyncTearDown(self):
        """Clean up test database connection and test data."""
        # Clean up test fixtures
        await self.db.listing.delete_many(
            where={"entity_name": {"contains": "TEST_ARRAY_FILTER"}}
        )
        await self.db.disconnect()

    async def _create_test_fixtures(self) -> List[Any]:
        """Create test fixtures with various array configurations."""
        fixtures = []

        # Fixture 1: Entity with single activity (padel only)
        fixture1 = await self.db.listing.create(data={
            "entity_name": "TEST_ARRAY_FILTER - Padel Centre",
            "entityType": "VENUE",
            "slug": "test-array-filter-padel-centre",
            "canonical_activities": ["padel"],
            "canonical_place_types": ["sports_centre"],
            "canonical_roles": [],
            "canonical_access": ["public"]
        })
        fixtures.append(fixture1)

        # Fixture 2: Entity with multiple activities (padel + tennis)
        fixture2 = await self.db.listing.create(data={
            "entity_name": "TEST_ARRAY_FILTER - Multi Sport Complex",
            "entityType": "VENUE",
            "slug": "test-array-filter-multi-sport",
            "canonical_activities": ["padel", "tennis"],
            "canonical_place_types": ["sports_centre"],
            "canonical_roles": [],
            "canonical_access": ["public", "members"]
        })
        fixtures.append(fixture2)

        # Fixture 3: Entity with no activities (empty array)
        fixture3 = await self.db.listing.create(data={
            "entity_name": "TEST_ARRAY_FILTER - Empty Activities",
            "entityType": "VENUE",
            "slug": "test-array-filter-empty",
            "canonical_activities": [],
            "canonical_place_types": ["community_centre"],
            "canonical_roles": [],
            "canonical_access": []
        })
        fixtures.append(fixture3)

        # Fixture 4: Entity with tennis only (for OR/AND tests)
        fixture4 = await self.db.listing.create(data={
            "entity_name": "TEST_ARRAY_FILTER - Tennis Club",
            "entityType": "VENUE",
            "slug": "test-array-filter-tennis",
            "canonical_activities": ["tennis"],
            "canonical_place_types": ["sports_centre"],
            "canonical_roles": [],
            "canonical_access": ["members"]
        })
        fixtures.append(fixture4)

        # Fixture 5: Entity with activities but different place_type (for AND across facets)
        fixture5 = await self.db.listing.create(data={
            "entity_name": "TEST_ARRAY_FILTER - Park Tennis",
            "entityType": "VENUE",
            "slug": "test-array-filter-park-tennis",
            "canonical_activities": ["tennis"],
            "canonical_place_types": ["park"],
            "canonical_roles": [],
            "canonical_access": ["public"]
        })
        fixtures.append(fixture5)

        return fixtures

    async def test_has_filter_single_value(self):
        """Test 'has' filter for single value in array."""
        # Query for entities with 'padel' in activities
        result = await self.db.listing.find_many(
            where={
                "entity_name": {"contains": "TEST_ARRAY_FILTER"},
                "canonical_activities": {"has": "padel"}
            }
        )

        # Should return 2 entities: Padel Centre and Multi Sport Complex
        self.assertEqual(len(result), 2)
        entity_names = {r.entity_name for r in result}
        self.assertIn("TEST_ARRAY_FILTER - Padel Centre", entity_names)
        self.assertIn("TEST_ARRAY_FILTER - Multi Sport Complex", entity_names)

    async def test_has_some_filter_or_semantics(self):
        """Test 'hasSome' filter (OR semantics within facet)."""
        # Query for entities with padel OR tennis
        result = await self.db.listing.find_many(
            where={
                "entity_name": {"contains": "TEST_ARRAY_FILTER"},
                "canonical_activities": {"hasSome": ["padel", "tennis"]}
            }
        )

        # Should return 4 entities: Padel Centre, Multi Sport, Tennis Club, Park Tennis
        self.assertEqual(len(result), 4)
        entity_names = {r.entity_name for r in result}
        self.assertIn("TEST_ARRAY_FILTER - Padel Centre", entity_names)
        self.assertIn("TEST_ARRAY_FILTER - Multi Sport Complex", entity_names)
        self.assertIn("TEST_ARRAY_FILTER - Tennis Club", entity_names)
        self.assertIn("TEST_ARRAY_FILTER - Park Tennis", entity_names)

    async def test_has_every_filter_and_semantics(self):
        """Test 'hasEvery' filter (AND semantics within facet)."""
        # Query for entities with BOTH padel AND tennis
        result = await self.db.listing.find_many(
            where={
                "entity_name": {"contains": "TEST_ARRAY_FILTER"},
                "canonical_activities": {"hasEvery": ["padel", "tennis"]}
            }
        )

        # Should return only 1 entity: Multi Sport Complex
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].entity_name, "TEST_ARRAY_FILTER - Multi Sport Complex")

    async def test_and_across_facets(self):
        """Test AND combination across different facets."""
        # Query for sports_centre with padel OR tennis
        result = await self.db.listing.find_many(
            where={
                "AND": [
                    {"entity_name": {"contains": "TEST_ARRAY_FILTER"}},
                    {"canonical_activities": {"hasSome": ["padel", "tennis"]}},
                    {"canonical_place_types": {"has": "sports_centre"}}
                ]
            }
        )

        # Should return 3 entities: Padel Centre, Multi Sport, Tennis Club
        # (Park Tennis is excluded because it's a park, not sports_centre)
        self.assertEqual(len(result), 3)
        entity_names = {r.entity_name for r in result}
        self.assertIn("TEST_ARRAY_FILTER - Padel Centre", entity_names)
        self.assertIn("TEST_ARRAY_FILTER - Multi Sport Complex", entity_names)
        self.assertIn("TEST_ARRAY_FILTER - Tennis Club", entity_names)
        self.assertNotIn("TEST_ARRAY_FILTER - Park Tennis", entity_names)

    async def test_empty_array_handling(self):
        """Test querying entities with empty arrays."""
        # Query for entities with no activities
        result = await self.db.listing.find_many(
            where={
                "entity_name": {"contains": "TEST_ARRAY_FILTER"},
                "canonical_activities": {"equals": []}
            }
        )

        # Should return 1 entity: Empty Activities
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].entity_name, "TEST_ARRAY_FILTER - Empty Activities")
        self.assertEqual(result[0].canonical_activities, [])

    async def test_has_filter_excludes_empty_arrays(self):
        """Test that 'has' filter excludes entities with empty arrays."""
        # Query for any activity
        result = await self.db.listing.find_many(
            where={
                "entity_name": {"contains": "TEST_ARRAY_FILTER"},
                "canonical_activities": {"has": "padel"}
            }
        )

        # Should not include the entity with empty activities array
        entity_names = {r.entity_name for r in result}
        self.assertNotIn("TEST_ARRAY_FILTER - Empty Activities", entity_names)


class TestPrismaArrayFiltersPerformance(unittest.IsolatedAsyncioTestCase):
    """Test query performance and GIN index usage."""

    async def asyncSetUp(self):
        """Set up test database connection."""
        self.db = Prisma()
        await self.db.connect()

        # Clean up any existing performance test data
        await self.db.listing.delete_many(
            where={"entity_name": {"contains": "PERF_TEST"}}
        )

    async def asyncTearDown(self):
        """Clean up test database connection and test data."""
        # Clean up performance test data
        await self.db.listing.delete_many(
            where={"entity_name": {"contains": "PERF_TEST"}}
        )
        await self.db.disconnect()

    @pytest.mark.slow
    async def test_query_performance_with_large_dataset(self):
        """Test query performance with 10,000 entities."""
        # Create 10,000 test entities
        batch_size = 100
        num_batches = 100  # 100 batches * 100 entities = 10,000

        activities_pool = [
            ["padel"],
            ["tennis"],
            ["padel", "tennis"],
            ["squash"],
            ["badminton"],
            ["tennis", "badminton"],
            []
        ]

        for batch_num in range(num_batches):
            batch_data = []
            for i in range(batch_size):
                entity_num = batch_num * batch_size + i
                activities = activities_pool[entity_num % len(activities_pool)]

                batch_data.append({
                    "entity_name": f"PERF_TEST Entity {entity_num}",
                    "entityType": "VENUE",
                    "slug": f"perf-test-entity-{entity_num}",
                    "canonical_activities": activities,
                    "canonical_place_types": ["sports_centre"],
                    "canonical_roles": [],
                    "canonical_access": ["public"]
                })

            # Create batch
            await self.db.listing.create_many(data=batch_data, skip_duplicates=True)

        # Verify we created the entities
        count = await self.db.listing.count(
            where={"entity_name": {"contains": "PERF_TEST"}}
        )
        self.assertEqual(count, 10000)

        # Test query performance
        import time
        start_time = time.time()

        result = await self.db.listing.find_many(
            where={
                "entity_name": {"contains": "PERF_TEST"},
                "canonical_activities": {"hasSome": ["padel", "tennis"]}
            }
        )

        end_time = time.time()
        query_time_ms = (end_time - start_time) * 1000

        # Verify query returned expected results
        self.assertGreater(len(result), 0)

        # Performance assertion: query should complete in < 100ms
        # Note: This may fail on slower systems - adjust threshold as needed
        self.assertLess(
            query_time_ms,
            100,
            f"Query took {query_time_ms:.2f}ms, expected < 100ms. "
            "This may indicate GIN indexes are not being used."
        )

    async def test_gin_index_usage_with_explain(self):
        """Test that GIN indexes are used for array queries using EXPLAIN ANALYZE."""
        # This test uses raw SQL to run EXPLAIN ANALYZE
        # Note: Prisma Client Python doesn't have built-in EXPLAIN support,
        # so we need to use query_raw

        # First create a few test entities
        await self.db.listing.create(data={
            "entity_name": "PERF_TEST GIN Index Test 1",
            "entityType": "VENUE",
            "slug": "perf-test-gin-1",
            "canonical_activities": ["padel", "tennis"],
            "canonical_place_types": ["sports_centre"],
            "canonical_roles": [],
            "canonical_access": ["public"]
        })

        await self.db.listing.create(data={
            "entity_name": "PERF_TEST GIN Index Test 2",
            "entityType": "VENUE",
            "slug": "perf-test-gin-2",
            "canonical_activities": ["tennis"],
            "canonical_place_types": ["sports_centre"],
            "canonical_roles": [],
            "canonical_access": ["public"]
        })

        # Run EXPLAIN ANALYZE on array query
        explain_result = await self.db.query_raw(
            """
            EXPLAIN ANALYZE
            SELECT * FROM "Listing"
            WHERE canonical_activities && ARRAY['padel', 'tennis']::text[]
            """
        )

        # Convert result to string for analysis
        explain_text = str(explain_result)

        # Verify that GIN index is mentioned in the execution plan
        # The exact format depends on PostgreSQL version, but should contain:
        # - "Index Scan" or "Bitmap Index Scan"
        # - Reference to the GIN index name (entities_activities_gin or similar)
        self.assertTrue(
            "Index Scan" in explain_text or "Bitmap Index Scan" in explain_text,
            f"Expected index scan in EXPLAIN output, got: {explain_text}"
        )

        # Note: The actual index name in the EXPLAIN output may vary
        # This is a basic check - manual verification of EXPLAIN output is recommended


if __name__ == "__main__":
    unittest.main()
