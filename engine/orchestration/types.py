"""
Core immutable types for orchestration system.

Defines the foundational types used throughout the ingestion orchestration:
- IngestRequest: The primary request object for ingestion operations
- IngestionMode: Enum defining the two ingestion modes
- BoundingBox: Geographic bounding box for spatial queries
- GeoPoint: Individual geographic coordinate

All types are immutable (frozen dataclasses) to ensure thread safety and
prevent accidental mutation during orchestration.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IngestionMode(Enum):
    """
    Defines the mode of ingestion operation.

    RESOLVE_ONE: Focus on finding and validating a single entity with high confidence
    DISCOVER_MANY: Discover multiple entities matching criteria
    """

    RESOLVE_ONE = "resolve_one"
    DISCOVER_MANY = "discover_many"


@dataclass(frozen=True)
class GeoPoint:
    """
    Immutable geographic coordinate.

    Represents a single point on Earth using latitude and longitude.
    Supports 0.0 as valid coordinate (equator/prime meridian).

    Attributes:
        lat: Latitude in decimal degrees (-90 to 90)
        lng: Longitude in decimal degrees (-180 to 180)
    """

    lat: float
    lng: float


@dataclass(frozen=True)
class BoundingBox:
    """
    Immutable geographic bounding box.

    Defines a rectangular geographic area using southwest and northeast corners.

    Attributes:
        southwest: Southwest corner of the bounding box
        northeast: Northeast corner of the bounding box
    """

    southwest: GeoPoint
    northeast: GeoPoint


@dataclass(frozen=True)
class IngestRequest:
    """
    Immutable request object for ingestion operations.

    Encapsulates all parameters needed to orchestrate an ingestion run.
    Optional fields (target_entity_count, min_confidence, budget_usd, persist) default to None/False
    and should be resolved by configuration at orchestration startup.

    Attributes:
        ingestion_mode: The mode of operation (RESOLVE_ONE or DISCOVER_MANY)
        query: Raw query string for connector execution
        target_entity_count: Maximum number of entities to accept (optional)
        min_confidence: Minimum confidence threshold for acceptance (optional, 0.0-1.0)
        budget_usd: Maximum budget in USD for the ingestion run (optional)
        persist: Whether to persist accepted entities to database (default: False)
        lens: Lens identifier for vertical-specific interpretation (e.g., "padel", "wine")
              Defaults to None which becomes "padel" lens
    """

    ingestion_mode: IngestionMode
    query: str
    target_entity_count: Optional[int] = None
    min_confidence: Optional[float] = None
    budget_usd: Optional[float] = None
    persist: bool = False
    lens: Optional[str] = None  # Defaults to "padel" if None
