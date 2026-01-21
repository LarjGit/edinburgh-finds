"""
Tests for lens membership operations.

Tests the explicit lens membership API in engine.lenses.ops.
"""

import json
import pytest
from prisma import Prisma
from engine.lenses.ops import (
    attach_entity_to_lens,
    detach_entity_from_lens,
    get_entity_lenses,
    get_lens_entities,
)


async def create_test_entity(entity_id: str) -> None:
    """Create a test entity in the database."""
    db = Prisma()
    await db.connect()
    try:
        await db.entity.create(
            data={
                'id': entity_id,
                'entity_name': f'Test Entity {entity_id}',
                'slug': f'test-entity-{entity_id}',
                'entity_class': 'place',
                'modules': json.dumps({}),  # Required Json field
            }
        )
    finally:
        await db.disconnect()


async def delete_test_entity(entity_id: str) -> None:
    """Delete a test entity from the database."""
    db = Prisma()
    await db.connect()
    try:
        await db.entity.delete(where={'id': entity_id})
    except Exception:
        pass  # Entity may not exist
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_attach_entity_to_lens_creates_new_membership():
    """Test attaching an entity to a lens creates a new LensEntity record."""
    entity_id = "test-entity-1"
    lens_id = "test-lens-1"

    # Setup: Create test entity
    await create_test_entity(entity_id)

    try:
        result = await attach_entity_to_lens(entity_id, lens_id)
        assert result is True  # New membership created
    finally:
        # Cleanup
        await detach_entity_from_lens(entity_id, lens_id)
        await delete_test_entity(entity_id)


@pytest.mark.asyncio
async def test_attach_entity_to_lens_returns_false_if_already_exists():
    """Test attaching an entity to a lens returns False if membership already exists."""
    entity_id = "test-entity-2"
    lens_id = "test-lens-2"

    # Setup: Create test entity
    await create_test_entity(entity_id)

    try:
        # Create membership first time
        result1 = await attach_entity_to_lens(entity_id, lens_id)
        assert result1 is True

        # Try to create again - should return False
        result2 = await attach_entity_to_lens(entity_id, lens_id)
        assert result2 is False
    finally:
        # Cleanup
        await detach_entity_from_lens(entity_id, lens_id)
        await delete_test_entity(entity_id)


@pytest.mark.asyncio
async def test_detach_entity_from_lens_removes_membership():
    """Test detaching an entity from a lens removes the LensEntity record."""
    entity_id = "test-entity-3"
    lens_id = "test-lens-3"

    # Setup: Create test entity
    await create_test_entity(entity_id)

    try:
        # Create membership
        await attach_entity_to_lens(entity_id, lens_id)

        # Detach
        result = await detach_entity_from_lens(entity_id, lens_id)
        assert result is True

        # Verify it's gone - detaching again should return False
        result2 = await detach_entity_from_lens(entity_id, lens_id)
        assert result2 is False
    finally:
        # Cleanup
        await delete_test_entity(entity_id)


@pytest.mark.asyncio
async def test_detach_entity_from_lens_returns_false_if_not_exists():
    """Test detaching a non-existent membership returns False."""
    entity_id = "non-existent-entity"
    lens_id = "non-existent-lens"

    result = await detach_entity_from_lens(entity_id, lens_id)
    assert result is False


@pytest.mark.asyncio
async def test_get_entity_lenses_returns_all_lenses():
    """Test getting all lenses for an entity."""
    entity_id = "test-entity-4"
    lens_ids = ["test-lens-4a", "test-lens-4b", "test-lens-4c"]

    # Setup: Create test entity
    await create_test_entity(entity_id)

    try:
        # Attach to multiple lenses
        for lens_id in lens_ids:
            await attach_entity_to_lens(entity_id, lens_id)

        # Get all lenses
        result = await get_entity_lenses(entity_id)

        assert len(result) == 3
        assert set(result) == set(lens_ids)
    finally:
        # Cleanup
        for lens_id in lens_ids:
            await detach_entity_from_lens(entity_id, lens_id)
        await delete_test_entity(entity_id)


@pytest.mark.asyncio
async def test_get_entity_lenses_returns_empty_list_if_none():
    """Test getting lenses for an entity with no memberships returns empty list."""
    entity_id = "test-entity-5"

    result = await get_entity_lenses(entity_id)

    assert result == []


@pytest.mark.asyncio
async def test_get_lens_entities_returns_all_entities():
    """Test getting all entities in a lens."""
    lens_id = "test-lens-6"
    entity_ids = ["test-entity-6a", "test-entity-6b", "test-entity-6c"]

    # Setup: Create test entities
    for entity_id in entity_ids:
        await create_test_entity(entity_id)

    try:
        # Attach multiple entities
        for entity_id in entity_ids:
            await attach_entity_to_lens(entity_id, lens_id)

        # Get all entities
        result = await get_lens_entities(lens_id)

        assert len(result) == 3
        assert set(result) == set(entity_ids)
    finally:
        # Cleanup
        for entity_id in entity_ids:
            await detach_entity_from_lens(entity_id, lens_id)
            await delete_test_entity(entity_id)


@pytest.mark.asyncio
async def test_get_lens_entities_returns_empty_list_if_none():
    """Test getting entities for a lens with no memberships returns empty list."""
    lens_id = "test-lens-7"

    result = await get_lens_entities(lens_id)

    assert result == []


@pytest.mark.asyncio
async def test_multiple_entities_multiple_lenses():
    """Test complex scenario with multiple entities and multiple lenses."""
    entities = ["entity-a", "entity-b", "entity-c"]
    lenses = ["lens-x", "lens-y"]

    # Setup: Create test entities
    for entity_id in entities:
        await create_test_entity(entity_id)

    try:
        # entity-a -> lens-x, lens-y
        # entity-b -> lens-x
        # entity-c -> lens-y

        await attach_entity_to_lens("entity-a", "lens-x")
        await attach_entity_to_lens("entity-a", "lens-y")
        await attach_entity_to_lens("entity-b", "lens-x")
        await attach_entity_to_lens("entity-c", "lens-y")

        # Verify entity-a is in both lenses
        entity_a_lenses = await get_entity_lenses("entity-a")
        assert set(entity_a_lenses) == {"lens-x", "lens-y"}

        # Verify lens-x has entity-a and entity-b
        lens_x_entities = await get_lens_entities("lens-x")
        assert set(lens_x_entities) == {"entity-a", "entity-b"}

        # Verify lens-y has entity-a and entity-c
        lens_y_entities = await get_lens_entities("lens-y")
        assert set(lens_y_entities) == {"entity-a", "entity-c"}
    finally:
        # Cleanup
        await detach_entity_from_lens("entity-a", "lens-x")
        await detach_entity_from_lens("entity-a", "lens-y")
        await detach_entity_from_lens("entity-b", "lens-x")
        await detach_entity_from_lens("entity-c", "lens-y")
        for entity_id in entities:
            await delete_test_entity(entity_id)
