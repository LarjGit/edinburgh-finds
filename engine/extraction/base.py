"""
Base Extractor Interface

Defines the abstract BaseExtractor class that all extraction implementations
must follow to ensure consistent behavior across sources.
"""

from abc import ABC, abstractmethod
from typing import Dict, Tuple, List


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

    def extract_rich_text(self, raw_data: Dict) -> List[str]:
        """
        Extract rich text descriptions from raw data for summary synthesis.

        This method extracts unstructured text content (reviews, descriptions,
        snippets, etc.) that can be used by the summary synthesizer to create
        high-quality summary fields.

        Default implementation returns an empty list. Extractors should override
        this method to return source-specific rich text.

        Args:
            raw_data: Raw ingestion payload for a single record

        Returns:
            List[str]: List of text descriptions/snippets from the raw data

        Examples:
            >>> extractor = GooglePlacesExtractor()
            >>> rich_text = extractor.extract_rich_text(raw_place_data)
            >>> # Returns: ["Editorial summary...", "Review 1 text...", "Review 2 text..."]
        """
        return []

