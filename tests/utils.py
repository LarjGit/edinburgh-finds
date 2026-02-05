"""Shared test utilities for the engine test suite."""

from prisma._fields import Json as _PrismaJson


def unwrap_prisma_json(obj):
    """Recursively strip prisma Json wrappers to plain Python structures.

    Json.__eq__ is type-only (always True for two Json instances) so any ==
    check on Json-wrapped fields silently passes regardless of content.
    """
    if isinstance(obj, _PrismaJson):
        return unwrap_prisma_json(obj.data)
    if isinstance(obj, dict):
        return {k: unwrap_prisma_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(unwrap_prisma_json(item) for item in obj)
    return obj
