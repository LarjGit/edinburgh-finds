"""
Extractors Module

This module contains concrete extractor implementations for various data sources.
Each extractor extends BaseExtractor and implements source-specific extraction logic.
"""

from .google_places_extractor import GooglePlacesExtractor
from .sport_scotland_extractor import SportScotlandExtractor
from .edinburgh_council_extractor import EdinburghCouncilExtractor
from .open_charge_map_extractor import OpenChargeMapExtractor
from .serper_extractor import SerperExtractor
from .osm_extractor import OSMExtractor

__all__ = [
    'GooglePlacesExtractor',
    'SportScotlandExtractor',
    'EdinburghCouncilExtractor',
    'OpenChargeMapExtractor',
    'SerperExtractor',
    'OSMExtractor'
]
