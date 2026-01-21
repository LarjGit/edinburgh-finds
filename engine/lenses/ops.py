"""
Lens membership operations.

Provides explicit API for managing entity membership in lenses via the LensEntity table.
These operations perform direct DB writes and are the single source of truth for lens membership.
"""

from prisma import Prisma
from typing import Optional


async def attach_entity_to_lens(entity_id: str, lens_id: str) -> bool:
    """
    Attach an entity to a lens by creating a LensEntity record.

    Args:
        entity_id: The ID of the entity to attach
        lens_id: The ID of the lens to attach to

    Returns:
        True if the membership was created, False if it already existed

    Raises:
        Exception: If the database operation fails
    """
    db = Prisma()
    await db.connect()

    try:
        # Check if membership already exists
        existing = await db.lensentity.find_unique(
            where={
                'lensId_entityId': {
                    'lensId': lens_id,
                    'entityId': entity_id
                }
            }
        )

        if existing:
            return False

        # Create new membership
        await db.lensentity.create(
            data={
                'lensId': lens_id,
                'entityId': entity_id
            }
        )

        return True

    finally:
        await db.disconnect()


async def detach_entity_from_lens(entity_id: str, lens_id: str) -> bool:
    """
    Detach an entity from a lens by deleting the LensEntity record.

    Args:
        entity_id: The ID of the entity to detach
        lens_id: The ID of the lens to detach from

    Returns:
        True if the membership was deleted, False if it didn't exist

    Raises:
        Exception: If the database operation fails
    """
    db = Prisma()
    await db.connect()

    try:
        # Try to delete the membership
        result = await db.lensentity.delete(
            where={
                'lensId_entityId': {
                    'lensId': lens_id,
                    'entityId': entity_id
                }
            }
        )

        return result is not None

    except Exception as e:
        # If the record doesn't exist, Prisma will raise an exception
        # Check if it's a "not found" error
        if 'Record to delete does not exist' in str(e):
            return False
        raise

    finally:
        await db.disconnect()


async def get_entity_lenses(entity_id: str) -> list[str]:
    """
    Get all lens IDs that an entity is a member of.

    Args:
        entity_id: The ID of the entity

    Returns:
        List of lens IDs

    Raises:
        Exception: If the database operation fails
    """
    db = Prisma()
    await db.connect()

    try:
        memberships = await db.lensentity.find_many(
            where={'entityId': entity_id}
        )

        return [m.lensId for m in memberships]

    finally:
        await db.disconnect()


async def get_lens_entities(lens_id: str) -> list[str]:
    """
    Get all entity IDs that are members of a lens.

    Args:
        lens_id: The ID of the lens

    Returns:
        List of entity IDs

    Raises:
        Exception: If the database operation fails
    """
    db = Prisma()
    await db.connect()

    try:
        memberships = await db.lensentity.find_many(
            where={'lensId': lens_id}
        )

        return [m.entityId for m in memberships]

    finally:
        await db.disconnect()
