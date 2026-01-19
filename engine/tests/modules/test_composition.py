"""
Module composition tests.

Tests module composition contracts:
- CONTRACT 1: Field names may duplicate across different modules (namespacing makes this safe)
- CONTRACT 2: Duplicate module keys in YAML are rejected at load time
- CONTRACT 3: Flattened JSONB is rejected (modules must be namespaced)
- CONTRACT 4: Namespaced JSONB is accepted
- CONTRACT 5: Extraction pipeline produces namespaced modules
- CONTRACT 6: Database preserves namespaced structure
"""

import os
import unittest
import pytest
import yaml
import tempfile
from pathlib import Path
from typing import Dict, Any
from prisma import Prisma

from engine.modules.validator import (
    validate_modules_namespacing,
    load_yaml_strict,
    ModuleValidationError,
    DuplicateKeyError,
    StrictYAMLLoader
)
from engine.extraction.base import extract_with_lens_contract


# Check if DATABASE_URL is set for database tests
DATABASE_URL_SET = os.environ.get("DATABASE_URL") is not None


class TestModuleComposition(unittest.TestCase):
    """Test module composition contracts."""

    def test_duplicate_field_names_across_modules_allowed(self):
        """
        CONTRACT 1: Field names can duplicate across DIFFERENT modules due to namespacing.

        Example: Both sports_facility.name and wine_production.name are allowed
        because they're namespaced under different module keys.
        """
        # This is a valid modules structure
        modules = {
            "location": {"name": "Location Name", "latitude": 55.95},
            "sports_facility": {"name": "Facility Name", "inventory": {}}
        }

        # Should NOT raise - duplicate field names across modules are allowed
        validate_modules_namespacing(modules)

        # Verify we can access both names via namespacing
        self.assertEqual(modules["location"]["name"], "Location Name")
        self.assertEqual(modules["sports_facility"]["name"], "Facility Name")

    def test_duplicate_module_keys_in_yaml_rejected(self):
        """
        CONTRACT 2: YAML with duplicate module keys should be rejected by the YAML loader.

        The StrictYAMLLoader detects duplicate keys at any level and raises DuplicateKeyError.
        """
        yaml_content = """
modules:
  sports_facility:
    inventory: {}
  sports_facility:
    name: "Test"
"""

        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            # Should raise ModuleValidationError (wrapping DuplicateKeyError)
            with pytest.raises(ModuleValidationError, match="Duplicate keys detected"):
                load_yaml_strict(temp_path)
        finally:
            # Cleanup
            temp_path.unlink()

    def test_duplicate_module_keys_in_nested_yaml_rejected(self):
        """
        Test that duplicate keys are detected even in nested structures.
        """
        yaml_content = """
modules:
  location:
    latitude: 55.95
    latitude: 56.00
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ModuleValidationError, match="Duplicate keys detected"):
                load_yaml_strict(temp_path)
        finally:
            temp_path.unlink()

    def test_valid_modules_with_unique_keys_pass(self):
        """
        Test that valid YAML with unique module keys passes validation.
        """
        yaml_content = """
modules:
  location:
    latitude: 55.95
    longitude: -3.18
  contact:
    phone: "+44 131 555 0100"
    email: "test@example.com"
  sports_facility:
    inventory:
      courts: 4
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            # Should not raise
            data = load_yaml_strict(temp_path)

            # Verify structure
            self.assertIn("modules", data)
            self.assertIn("location", data["modules"])
            self.assertIn("contact", data["modules"])
            self.assertIn("sports_facility", data["modules"])

            # Verify modules are properly namespaced
            validate_modules_namespacing(data["modules"])
        finally:
            temp_path.unlink()

    def test_flattened_jsonb_rejected(self):
        """
        CONTRACT 3: Flattened JSONB structure is rejected.

        Modules MUST be namespaced by module key.
        Wrong: {"latitude": 55.95, "phone": "+44123"}
        Correct: {"location": {"latitude": 55.95}, "contact": {"phone": "+44123"}}
        """
        # Flattened structure (invalid)
        modules_data = {
            "latitude": 55.95,
            "phone": "+44123",
            "inventory": {"courts": 4}
        }

        # Should raise ModuleValidationError
        with pytest.raises(ModuleValidationError, match="must be namespaced"):
            validate_modules_namespacing(modules_data)

    def test_mixed_flattened_namespaced_rejected(self):
        """
        Test that mixed structures (some flattened, some namespaced) are rejected.
        """
        # Mixed structure - some fields flattened, some namespaced
        modules_data = {
            "location": {"latitude": 55.95},  # Namespaced (correct)
            "phone": "+44123"  # Flattened (incorrect)
        }

        with pytest.raises(ModuleValidationError, match="must be namespaced"):
            validate_modules_namespacing(modules_data)

    def test_namespaced_jsonb_accepted(self):
        """
        CONTRACT 4: Namespaced JSONB structure is accepted.

        All module data should be under module keys.
        """
        # Properly namespaced structure
        modules_data = {
            "location": {"latitude": 55.95, "longitude": -3.18},
            "contact": {"phone": "+44123", "email": "test@example.com"}
        }

        # Should not raise
        validate_modules_namespacing(modules_data)

    def test_empty_modules_accepted(self):
        """
        Test that empty modules dict is accepted.
        """
        modules_data = {}

        # Should not raise
        validate_modules_namespacing(modules_data)

    def test_empty_module_namespace_accepted(self):
        """
        Test that modules with empty namespaces are accepted.
        """
        modules_data = {
            "location": {},
            "contact": {}
        }

        # Should not raise
        validate_modules_namespacing(modules_data)


class TestExtractionPipelineNamespacing(unittest.TestCase):
    """
    Test that extraction pipeline produces namespaced modules.

    CONTRACT 5: Extraction pipeline must produce namespaced JSONB structure.
    """

    def test_extraction_produces_namespaced_modules(self):
        """
        Test that extract_with_lens_contract produces namespaced modules.

        Note: extract_with_lens_contract only includes modules that are:
        1. Engine modules for the entity_class (e.g., 'core', 'location' for place)
        2. Modules triggered by module_triggers based on canonical values

        This test verifies the STRUCTURE is namespaced, not specific module content.
        """
        # Mock raw data - minimal data to classify as 'place'
        raw_data = {
            "name": "Test Venue",
            "address": "123 Test St"
        }

        # Mock lens contract with module triggers
        # For a 'place' entity, engine automatically adds 'core' and 'location' modules
        lens_contract = {
            "facets": {
                "activity": {"dimension_source": "canonical_activities"}
            },
            "values": [
                {"key": "padel", "facet": "activity", "display_name": "Padel"}
            ],
            "mapping_rules": [
                {"pattern": r"(?i)\bpadel\b", "canonical": "padel", "confidence": 1.0}
            ],
            "modules": {
                "core": {},
                "location": {},
                "sports_facility": {}
            },
            "module_triggers": [
                {
                    "when": {"facet": "activity", "value": "padel"},
                    "add_modules": ["sports_facility"],
                    "conditions": [{"entity_class": "place"}]
                }
            ]
        }

        # Add category to trigger the module
        raw_data["categories"] = ["Padel Court"]

        # Extract with lens contract
        result = extract_with_lens_contract(raw_data, lens_contract)

        # Verify modules are present
        self.assertIn("modules", result)

        # Verify modules are namespaced (not flattened)
        modules = result["modules"]

        # Verify structure passes validation
        validate_modules_namespacing(modules)

        # Engine should add 'core' and 'location' for 'place'
        self.assertIn("core", modules)
        self.assertIn("location", modules)

        # Trigger should add 'sports_facility'
        self.assertIn("sports_facility", modules)

        # Verify modules is a dict of dicts (namespaced), not flattened
        for module_name, module_data in modules.items():
            self.assertIsInstance(module_data, dict,
                f"Module '{module_name}' should be a dict (namespaced structure)")

    def test_extraction_with_multiple_modules(self):
        """
        Test extraction with multiple modules to ensure consistent namespacing.
        """
        raw_data = {
            "name": "Sports Centre",
            "address": "123 Test St",
            "categories": ["Tennis Court", "Padel Court"]
        }

        lens_contract = {
            "facets": {
                "activity": {"dimension_source": "canonical_activities"}
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"},
                {"key": "padel", "facet": "activity", "display_name": "Padel"}
            ],
            "mapping_rules": [
                {"pattern": r"(?i)\btennis\b", "canonical": "tennis", "confidence": 1.0},
                {"pattern": r"(?i)\bpadel\b", "canonical": "padel", "confidence": 1.0}
            ],
            "modules": {
                "core": {},
                "location": {},
                "sports_facility": {}
            },
            "module_triggers": [
                {
                    "when": {"facet": "activity", "value": "tennis"},
                    "add_modules": ["sports_facility"],
                    "conditions": [{"entity_class": "place"}]
                },
                {
                    "when": {"facet": "activity", "value": "padel"},
                    "add_modules": ["sports_facility"],
                    "conditions": [{"entity_class": "place"}]
                }
            ]
        }

        result = extract_with_lens_contract(raw_data, lens_contract)
        modules = result["modules"]

        # Verify engine modules are present
        self.assertIn("core", modules)
        self.assertIn("location", modules)

        # Verify triggered module is present
        self.assertIn("sports_facility", modules)

        # Verify namespacing structure
        validate_modules_namespacing(modules)

        # Verify all modules are dict (not primitives - which would indicate flattening)
        for module_name, module_data in modules.items():
            self.assertIsInstance(module_data, dict,
                f"Module '{module_name}' should be a dict (namespaced structure)")


@pytest.mark.skipif(not DATABASE_URL_SET, reason="DATABASE_URL environment variable not set")
class TestDatabaseModuleStorage(unittest.IsolatedAsyncioTestCase):
    """
    Test that database preserves namespaced module structure.

    CONTRACT 6: Database must preserve namespaced JSONB structure.

    Note: These tests require DATABASE_URL environment variable to be set.
    """

    async def asyncSetUp(self):
        """Set up test database connection."""
        self.db = Prisma()
        await self.db.connect()

    async def asyncTearDown(self):
        """Clean up test database connection."""
        await self.db.disconnect()

    async def test_store_and_retrieve_namespaced_modules(self):
        """
        Test that namespaced modules can be stored and retrieved from database.
        """
        # Create entity with namespaced modules
        modules_data = {
            "location": {"latitude": 55.95, "longitude": -3.18},
            "contact": {"phone": "+44 131 555 0100", "email": "test@example.com"},
            "sports_facility": {"inventory": {"courts": 4}}
        }

        # Verify structure before storing
        validate_modules_namespacing(modules_data)

        # Store entity
        entity = await self.db.listing.create(data={
            "name": "Test Venue",
            "slug": "test-venue-modules-" + str(hash(str(modules_data)))[:8],
            "entity_class": "place",
            "modules": modules_data
        })

        try:
            # Verify entity was created
            self.assertIsNotNone(entity.id)

            # Read back from database
            retrieved = await self.db.listing.find_unique(
                where={"id": entity.id}
            )

            self.assertIsNotNone(retrieved)
            self.assertIsNotNone(retrieved.modules)

            # Verify JSONB structure is preserved
            retrieved_modules = retrieved.modules

            # Verify namespacing is preserved
            self.assertIn("location", retrieved_modules)
            self.assertIn("contact", retrieved_modules)
            self.assertIn("sports_facility", retrieved_modules)

            # Verify NOT flattened
            self.assertNotIn("latitude", retrieved_modules)
            self.assertNotIn("phone", retrieved_modules)

            # Verify data integrity
            self.assertEqual(retrieved_modules["location"]["latitude"], 55.95)
            self.assertEqual(retrieved_modules["location"]["longitude"], -3.18)
            self.assertEqual(retrieved_modules["contact"]["phone"], "+44 131 555 0100")
            self.assertEqual(retrieved_modules["sports_facility"]["inventory"]["courts"], 4)

            # Verify structure still passes validation
            validate_modules_namespacing(retrieved_modules)

        finally:
            # Cleanup
            await self.db.listing.delete(where={"id": entity.id})

    async def test_update_namespaced_modules(self):
        """
        Test that updating namespaced modules preserves structure.
        """
        # Initial modules
        initial_modules = {
            "location": {"latitude": 55.95, "longitude": -3.18}
        }

        # Create entity
        entity = await self.db.listing.create(data={
            "name": "Test Update Venue",
            "slug": "test-update-venue-modules-" + str(hash(str(initial_modules)))[:8],
            "entity_class": "place",
            "modules": initial_modules
        })

        try:
            # Update with additional module
            updated_modules = {
                "location": {"latitude": 55.95, "longitude": -3.18},
                "contact": {"phone": "+44 131 555 0100"}
            }

            await self.db.listing.update(
                where={"id": entity.id},
                data={"modules": updated_modules}
            )

            # Read back
            retrieved = await self.db.listing.find_unique(
                where={"id": entity.id}
            )

            # Verify structure
            validate_modules_namespacing(retrieved.modules)
            self.assertIn("location", retrieved.modules)
            self.assertIn("contact", retrieved.modules)
            self.assertEqual(retrieved.modules["contact"]["phone"], "+44 131 555 0100")

        finally:
            # Cleanup
            await self.db.listing.delete(where={"id": entity.id})

    async def test_query_modules_jsonb_field(self):
        """
        Test that we can query within JSONB modules structure.
        """
        # Create entities with different module structures
        entity1 = await self.db.listing.create(data={
            "name": "Entity with Location",
            "slug": "entity-location-query-test-1",
            "entity_class": "place",
            "modules": {
                "location": {"latitude": 55.95, "longitude": -3.18}
            }
        })

        entity2 = await self.db.listing.create(data={
            "name": "Entity with Contact",
            "slug": "entity-contact-query-test-2",
            "entity_class": "place",
            "modules": {
                "contact": {"phone": "+44 131 555 0100"}
            }
        })

        try:
            # Query entities (basic retrieval to verify storage)
            all_entities = await self.db.listing.find_many(
                where={
                    "slug": {"in": ["entity-location-query-test-1", "entity-contact-query-test-2"]}
                }
            )

            # Verify both entities were stored correctly
            self.assertEqual(len(all_entities), 2)

            # Verify each has proper namespacing
            for entity in all_entities:
                validate_modules_namespacing(entity.modules)

        finally:
            # Cleanup
            await self.db.listing.delete(where={"id": entity1.id})
            await self.db.listing.delete(where={"id": entity2.id})


if __name__ == "__main__":
    unittest.main()
