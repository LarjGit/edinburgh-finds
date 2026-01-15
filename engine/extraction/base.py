"""
Base Extractor Interface

Defines the abstract BaseExtractor class that all extraction implementations
must follow to ensure consistent behavior across sources.
"""

from abc import ABC, abstractmethod
from typing import Dict, Tuple


class BaseExtractor(ABC):
    """
    Abstract base class for data extraction.

    Implementations are responsible for transforming raw ingestion payloads
    into structured listing fields, validating outputs, and separating
    schema-defined attributes from discovered attributes.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        Unique identifier for this extractor's data source.

        Returns:
            str: Source name (e.g., "google_places", "osm")
        """
        pass

    @abstractmethod
    def extract(self, raw_data: Dict) -> Dict:
        """
        Transform raw data into extracted listing fields.

        Args:
            raw_data: Raw ingestion payload for a single record

        Returns:
            Dict: Extracted fields mapped to schema names
        """
        pass

    @abstractmethod
    def validate(self, extracted: Dict) -> Dict:
        """
        Validate extracted fields against schema rules.

        Args:
            extracted: Extracted fields to validate

        Returns:
            Dict: Validated (and possibly normalized) fields
        """
        pass

    @abstractmethod
    def split_attributes(self, extracted: Dict) -> Tuple[Dict, Dict]:
        """
        Split extracted fields into schema-defined and discovered attributes.

        Args:
            extracted: Extracted fields to split

        Returns:
            Tuple[Dict, Dict]: (attributes, discovered_attributes)
        """
        pass

