"""
Base Extractor Interface

Defines the abstract BaseExtractor class that all extraction implementations
must follow to ensure consistent behavior across sources.
"""

import time
import re
from abc import ABC, abstractmethod
from typing import Dict, Tuple, List, Optional, Any

from engine.extraction.logging_config import (
    get_extraction_logger,
    log_extraction_start,
    log_extraction_success,
    log_extraction_failure,
)
from engine.orchestration.execution_context import ExecutionContext


class BaseExtractor(ABC):
    """
    Abstract base class for data extraction.

    Implementations are responsible for transforming raw ingestion payloads
    into structured entity fields, validating outputs, and separating
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
    def extract(self, raw_data: dict, *, ctx: ExecutionContext) -> dict:
        """
        Transform raw data into extracted entity fields.

        Args:
            raw_data: Raw ingestion payload for a single record
            ctx: Execution context with lens contract and execution metadata

        Returns:
            dict: Extracted fields mapped to schema names
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

    def extract_with_logging(
        self,
        raw_data: Dict,
        record_id: str,
        confidence_score: Optional[float] = None,
        *,
        ctx: ExecutionContext,
    ) -> Dict:
        """
        Wrapper method that executes extraction with structured logging.

        This method wraps the extract() call with start/success/failure logging,
        including timing and metadata capture.

        Args:
            raw_data: Raw ingestion payload for a single record
            record_id: RawIngestion record ID for tracking
            confidence_score: Optional confidence score for this extraction
            ctx: Execution context with lens contract and execution metadata

        Returns:
            Dict: Extracted fields mapped to schema names

        Raises:
            Exception: Re-raises any exception from extract() after logging
        """
        logger = get_extraction_logger()
        extractor_name = self.__class__.__name__

        log_extraction_start(
            logger=logger,
            source=self.source_name,
            record_id=record_id,
            extractor=extractor_name,
        )

        start_time = time.time()

        try:
            extracted = self.extract(raw_data, ctx=ctx)
            duration = time.time() - start_time

            # Count non-null fields
            fields_extracted = sum(1 for v in extracted.values() if v is not None)

            log_extraction_success(
                logger=logger,
                source=self.source_name,
                record_id=record_id,
                extractor=extractor_name,
                duration_seconds=round(duration, 3),
                fields_extracted=fields_extracted,
                confidence_score=confidence_score,
            )

            return extracted

        except Exception as e:
            duration = time.time() - start_time

            log_extraction_failure(
                logger=logger,
                source=self.source_name,
                record_id=record_id,
                extractor=extractor_name,
                error=str(e),
                duration_seconds=round(duration, 3),
            )

            raise

