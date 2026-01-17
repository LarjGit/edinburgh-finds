"""
Tests for LLM extraction caching system.

Tests cover:
- Cache key generation from raw data + prompt + model
- Cache hit when identical extraction exists
- Cache miss when no matching extraction exists
- Cache expiration (optional)
- Cache invalidation
"""

import pytest
import hashlib
import json
from unittest.mock import Mock, AsyncMock, patch
from prisma import Prisma
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from extraction.llm_cache import (
    compute_cache_key,
    check_llm_cache,
    get_cache_stats,
)


class TestCacheKeyGeneration:
    """Test cache key computation from inputs."""

    def test_compute_cache_key_basic(self):
        """Cache key should be deterministic hash of inputs."""
        raw_data = {"name": "Test Venue", "address": "123 Main St"}
        prompt = "Extract venue information"
        model = "claude-haiku-20250318"

        key1 = compute_cache_key(raw_data, prompt, model)
        key2 = compute_cache_key(raw_data, prompt, model)

        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 64  # SHA-256 hex digest length

    def test_compute_cache_key_different_data(self):
        """Different raw data should produce different keys."""
        data1 = {"name": "Venue A"}
        data2 = {"name": "Venue B"}
        prompt = "Extract data"
        model = "claude-haiku-20250318"

        key1 = compute_cache_key(data1, prompt, model)
        key2 = compute_cache_key(data2, prompt, model)

        assert key1 != key2

    def test_compute_cache_key_different_prompt(self):
        """Different prompts should produce different keys."""
        data = {"name": "Venue"}
        prompt1 = "Extract venue"
        prompt2 = "Extract location"
        model = "claude-haiku-20250318"

        key1 = compute_cache_key(data, prompt1, model)
        key2 = compute_cache_key(data, prompt2, model)

        assert key1 != key2

    def test_compute_cache_key_different_model(self):
        """Different models should produce different keys."""
        data = {"name": "Venue"}
        prompt = "Extract"
        model1 = "claude-haiku-20250318"
        model2 = "claude-sonnet-4.5"

        key1 = compute_cache_key(data, prompt, model1)
        key2 = compute_cache_key(data, prompt, model2)

        assert key1 != key2

    def test_compute_cache_key_dict_order_invariant(self):
        """Cache key should be independent of dictionary key order."""
        data1 = {"name": "Venue", "address": "123 St", "city": "Edinburgh"}
        data2 = {"city": "Edinburgh", "name": "Venue", "address": "123 St"}
        prompt = "Extract"
        model = "claude-haiku-20250318"

        key1 = compute_cache_key(data1, prompt, model)
        key2 = compute_cache_key(data2, prompt, model)

        assert key1 == key2


@pytest.mark.asyncio
class TestCacheOperations:
    """Test cache hit/miss logic with database."""

    async def test_cache_miss_no_record(self):
        """Cache miss when no matching extraction exists."""
        cache_key = "nonexistent_key_" + "0" * 48  # 64 char total

        result = await check_llm_cache(cache_key)

        assert result is None

    async def test_get_cache_stats(self):
        """get_cache_stats should return cache metrics."""
        stats = await get_cache_stats()

        assert "total_entries" in stats
        assert "entries_by_source" in stats
        assert "entries_by_model" in stats
        assert isinstance(stats["total_entries"], int)
        assert isinstance(stats["entries_by_source"], dict)
        assert isinstance(stats["entries_by_model"], dict)


class TestCacheUtilities:
    """Test cache utility functions."""

    def test_cache_key_format(self):
        """Cache keys should be valid SHA-256 hashes."""
        import re

        raw_data = {"test": "data"}
        prompt = "Extract"
        model = "claude-haiku-20250318"

        cache_key = compute_cache_key(raw_data, prompt, model)

        # Should be 64 hex characters
        assert re.match(r'^[a-f0-9]{64}$', cache_key)

    def test_cache_key_handles_unicode(self):
        """Cache keys should handle unicode characters in data."""
        raw_data = {"name": "Café Español 日本語", "emoji": "🎾"}
        prompt = "Extract venue"
        model = "claude-haiku-20250318"

        cache_key = compute_cache_key(raw_data, prompt, model)

        assert len(cache_key) == 64
        assert isinstance(cache_key, str)

    def test_cache_key_handles_nested_data(self):
        """Cache keys should handle nested dictionaries."""
        raw_data = {
            "venue": {
                "name": "Test",
                "location": {"lat": 55.9, "lng": -3.1},
                "tags": ["padel", "tennis"],
            }
        }
        prompt = "Extract"
        model = "claude-haiku-20250318"

        cache_key = compute_cache_key(raw_data, prompt, model)

        assert len(cache_key) == 64
