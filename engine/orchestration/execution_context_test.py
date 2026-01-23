"""
Unit tests for ExecutionContext.

Tests verify:
- Proper initialization of all storage containers
- Correct types for each container
- Mutable state management (lists, sets, dicts)
- Deduplication logic (key generation, accept_entity)
- Name normalization
- Stable hashing
"""

import pytest
from typing import Dict, Any, Optional
from engine.orchestration.execution_context import ExecutionContext


class TestExecutionContextStructure:
    """Tests for ExecutionContext structure and initialization."""

    def test_initialization_creates_empty_containers(self):
        """ExecutionContext should initialize with empty containers."""
        context = ExecutionContext()

        assert context.candidates == []
        assert context.accepted_entities == []
        assert context.accepted_entity_keys == set()
        assert context.evidence == {}
        assert context.seeds == {}

    def test_candidates_is_list(self):
        """candidates should be a list."""
        context = ExecutionContext()
        assert isinstance(context.candidates, list)

    def test_accepted_entities_is_list(self):
        """accepted_entities should be a list."""
        context = ExecutionContext()
        assert isinstance(context.accepted_entities, list)

    def test_accepted_entity_keys_is_set(self):
        """accepted_entity_keys should be a set."""
        context = ExecutionContext()
        assert isinstance(context.accepted_entity_keys, set)

    def test_evidence_is_dict(self):
        """evidence should be a dict."""
        context = ExecutionContext()
        assert isinstance(context.evidence, dict)

    def test_seeds_is_dict(self):
        """seeds should be a dict."""
        context = ExecutionContext()
        assert isinstance(context.seeds, dict)

    def test_containers_are_mutable(self):
        """All containers should be mutable (allow additions)."""
        context = ExecutionContext()

        # Should be able to modify lists
        context.candidates.append("test_candidate")
        assert len(context.candidates) == 1

        context.accepted_entities.append("test_entity")
        assert len(context.accepted_entities) == 1

        # Should be able to modify set
        context.accepted_entity_keys.add("test_key")
        assert len(context.accepted_entity_keys) == 1

        # Should be able to modify dicts
        context.evidence["test"] = "value"
        assert context.evidence["test"] == "value"

        context.seeds["test"] = "seed_value"
        assert context.seeds["test"] == "seed_value"

    def test_multiple_contexts_are_independent(self):
        """Multiple ExecutionContext instances should be independent."""
        context1 = ExecutionContext()
        context2 = ExecutionContext()

        context1.candidates.append("candidate1")
        context2.candidates.append("candidate2")

        assert len(context1.candidates) == 1
        assert len(context2.candidates) == 1
        assert context1.candidates[0] == "candidate1"
        assert context2.candidates[0] == "candidate2"


class TestNameNormalization:
    """Tests for name normalization logic."""

    def test_normalize_name_casefold(self):
        """Name normalization should convert to lowercase using casefold."""
        context = ExecutionContext()
        assert context._normalize_name("HELLO") == "hello"
        assert context._normalize_name("HeLLo WoRLd") == "hello world"

    def test_normalize_name_strips_whitespace(self):
        """Name normalization should strip leading/trailing whitespace."""
        context = ExecutionContext()
        assert context._normalize_name("  hello  ") == "hello"
        assert context._normalize_name("\thello\n") == "hello"

    def test_normalize_name_collapses_whitespace(self):
        """Name normalization should collapse multiple spaces to single space."""
        context = ExecutionContext()
        assert context._normalize_name("hello    world") == "hello world"
        assert context._normalize_name("hello  \t  world") == "hello world"

    def test_normalize_name_combined(self):
        """Name normalization should handle all transformations together."""
        context = ExecutionContext()
        assert context._normalize_name("  HELLO    WORLD  ") == "hello world"


class TestStrongIDKeyGeneration:
    """Tests for strong ID-based key generation."""

    def test_generate_key_with_google_id(self):
        """Should generate key from google_id when available."""
        context = ExecutionContext()
        candidate = {"name": "Test Place", "ids": {"google": "ChIJ123"}}
        key = context._generate_entity_key(candidate)
        assert key == "google:ChIJ123"

    def test_generate_key_with_osm_id(self):
        """Should generate key from osm_id when available."""
        context = ExecutionContext()
        candidate = {"name": "Test Place", "ids": {"osm": "node/123456"}}
        key = context._generate_entity_key(candidate)
        assert key == "osm:node/123456"

    def test_generate_key_prioritizes_ids_lexicographically(self):
        """Should prioritize IDs in lexicographic order when multiple present."""
        context = ExecutionContext()
        candidate = {
            "name": "Test Place",
            "ids": {"google": "ChIJ123", "osm": "node/123456"},
        }
        # "google" comes before "osm" lexicographically
        key = context._generate_entity_key(candidate)
        assert key == "google:ChIJ123"

    def test_generate_key_from_seeds(self):
        """Should check context.seeds for strong IDs if not in candidate."""
        context = ExecutionContext()
        context.seeds = {"google": "ChIJ999"}
        candidate = {"name": "Test Place"}
        key = context._generate_entity_key(candidate)
        assert key == "google:ChIJ999"


class TestGeoKeyGeneration:
    """Tests for geo-based key generation."""

    def test_generate_key_with_geo_coordinates(self):
        """Should generate key from normalized name + rounded lat/lng."""
        context = ExecutionContext()
        candidate = {
            "name": "Test Place",
            "lat": 55.953251,
            "lng": -3.188267,
        }
        key = context._generate_entity_key(candidate)
        # Rounded to 4 decimal places
        assert key == "test place:55.9533:-3.1883"

    def test_generate_key_geo_rounds_to_4_decimals(self):
        """Geo coordinates should be rounded to exactly 4 decimal places."""
        context = ExecutionContext()
        candidate = {
            "name": "Test Place",
            "lat": 55.95329999,
            "lng": -3.18829999,
        }
        key = context._generate_entity_key(candidate)
        assert key == "test place:55.9533:-3.1883"

    def test_generate_key_geo_handles_zero_coordinates(self):
        """Should accept 0.0 as valid coordinates (not None)."""
        context = ExecutionContext()
        candidate = {
            "name": "Test Place",
            "lat": 0.0,
            "lng": 0.0,
        }
        key = context._generate_entity_key(candidate)
        assert key == "test place:0.0:0.0"

    def test_generate_key_geo_skips_if_lat_is_none(self):
        """Should skip geo key if lat is None."""
        context = ExecutionContext()
        candidate = {
            "name": "Test Place",
            "lat": None,
            "lng": -3.188267,
        }
        # Should fall back to hash since geo is incomplete
        key = context._generate_entity_key(candidate)
        assert not key.startswith("test place:")

    def test_generate_key_geo_skips_if_lng_is_none(self):
        """Should skip geo key if lng is None."""
        context = ExecutionContext()
        candidate = {
            "name": "Test Place",
            "lat": 55.953251,
            "lng": None,
        }
        # Should fall back to hash since geo is incomplete
        key = context._generate_entity_key(candidate)
        assert not key.startswith("test place:")


class TestHashKeyGeneration:
    """Tests for SHA1 hash-based key generation (fallback)."""

    def test_generate_key_with_hash_fallback(self):
        """Should generate SHA1 hash when no strong IDs or geo available."""
        context = ExecutionContext()
        candidate = {"name": "Test Place", "description": "A test"}
        key = context._generate_entity_key(candidate)
        # Should be a hash (40 char hex string from SHA1)
        assert len(key) == 40
        assert all(c in "0123456789abcdef" for c in key)

    def test_generate_key_hash_is_stable(self):
        """Same input should generate same hash (determinism)."""
        context = ExecutionContext()
        candidate1 = {"name": "Test Place", "description": "A test"}
        candidate2 = {"name": "Test Place", "description": "A test"}
        key1 = context._generate_entity_key(candidate1)
        key2 = context._generate_entity_key(candidate2)
        assert key1 == key2

    def test_generate_key_hash_sorts_keys_alphabetically(self):
        """Hash should be deterministic regardless of dict key order."""
        context = ExecutionContext()
        candidate1 = {"name": "Test", "description": "A", "address": "B"}
        candidate2 = {"description": "A", "address": "B", "name": "Test"}
        key1 = context._generate_entity_key(candidate1)
        key2 = context._generate_entity_key(candidate2)
        assert key1 == key2

    def test_generate_key_hash_normalizes_string_values(self):
        """Hash should normalize string values (casefold, strip)."""
        context = ExecutionContext()
        candidate1 = {"name": "  TEST PLACE  "}
        candidate2 = {"name": "test place"}
        key1 = context._generate_entity_key(candidate1)
        key2 = context._generate_entity_key(candidate2)
        assert key1 == key2


class TestAcceptEntity:
    """Tests for accept_entity method."""

    def test_accept_entity_returns_tuple(self):
        """accept_entity should return (bool, str, Optional[str])."""
        context = ExecutionContext()
        candidate = {"name": "Test", "ids": {"google": "ChIJ123"}}
        result = context.accept_entity(candidate)
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)
        assert result[2] is None or isinstance(result[2], str)

    def test_accept_entity_first_acceptance(self):
        """First entity should be accepted."""
        context = ExecutionContext()
        candidate = {"name": "Test", "ids": {"google": "ChIJ123"}}
        accepted, key, reason = context.accept_entity(candidate)
        assert accepted is True
        assert key == "google:ChIJ123"
        assert reason is None

    def test_accept_entity_updates_accepted_entities(self):
        """accept_entity should add candidate to accepted_entities."""
        context = ExecutionContext()
        candidate = {"name": "Test", "ids": {"google": "ChIJ123"}}
        context.accept_entity(candidate)
        assert len(context.accepted_entities) == 1
        assert context.accepted_entities[0] == candidate

    def test_accept_entity_updates_accepted_entity_keys(self):
        """accept_entity should add key to accepted_entity_keys set."""
        context = ExecutionContext()
        candidate = {"name": "Test", "ids": {"google": "ChIJ123"}}
        context.accept_entity(candidate)
        assert "google:ChIJ123" in context.accepted_entity_keys

    def test_accept_entity_rejects_duplicate(self):
        """Duplicate candidate should be rejected."""
        context = ExecutionContext()
        candidate1 = {"name": "Test", "ids": {"google": "ChIJ123"}}
        candidate2 = {"name": "Test", "ids": {"google": "ChIJ123"}}

        accepted1, key1, reason1 = context.accept_entity(candidate1)
        accepted2, key2, reason2 = context.accept_entity(candidate2)

        assert accepted1 is True
        assert accepted2 is False
        assert key1 == key2
        assert reason2 == "duplicate"

    def test_accept_entity_duplicate_maintains_stable_count(self):
        """Duplicate should not increase accepted_entities count."""
        context = ExecutionContext()
        candidate1 = {"name": "Test", "ids": {"google": "ChIJ123"}}
        candidate2 = {"name": "Test", "ids": {"google": "ChIJ123"}}

        context.accept_entity(candidate1)
        context.accept_entity(candidate2)

        assert len(context.accepted_entities) == 1
        assert len(context.accepted_entity_keys) == 1

    def test_accept_entity_multiple_unique_entities(self):
        """Multiple unique entities should all be accepted."""
        context = ExecutionContext()
        candidate1 = {"name": "Test 1", "ids": {"google": "ChIJ123"}}
        candidate2 = {"name": "Test 2", "ids": {"google": "ChIJ456"}}
        candidate3 = {"name": "Test 3", "ids": {"osm": "node/789"}}

        accepted1, _, _ = context.accept_entity(candidate1)
        accepted2, _, _ = context.accept_entity(candidate2)
        accepted3, _, _ = context.accept_entity(candidate3)

        assert accepted1 is True
        assert accepted2 is True
        assert accepted3 is True
        assert len(context.accepted_entities) == 3
        assert len(context.accepted_entity_keys) == 3
