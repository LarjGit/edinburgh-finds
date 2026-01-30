"""
Tests for BaseExtractor interface contract.

Validates architecture.md Section 3.8 (Extractor Interface Contract).
"""

import inspect
import pytest

from engine.extraction.base import BaseExtractor


class TestExtractorInterfaceContract:
    """
    Validates that BaseExtractor enforces the required interface contract
    per architecture.md Section 3.8.
    """

    def test_base_extractor_requires_ctx_parameter(self):
        """
        Validates architecture.md 3.8: Extractor Interface Contract.

        The abstract extract() method must require an ExecutionContext parameter
        to enable lens contract access and maintain boundary purity.

        Required signature:
            def extract(self, raw_data: dict, *, ctx: ExecutionContext) -> dict:
        """
        sig = inspect.signature(BaseExtractor.extract)

        # Must have ctx parameter
        assert 'ctx' in sig.parameters, \
            "BaseExtractor.extract() must have 'ctx' parameter (architecture.md 3.8)"

        # Must be keyword-only (enforced by * in signature)
        ctx_param = sig.parameters['ctx']
        assert ctx_param.kind == inspect.Parameter.KEYWORD_ONLY, \
            "ctx parameter must be keyword-only (*, ctx: ...) per architecture.md 3.8"

    def test_extract_with_logging_accepts_ctx(self):
        """
        Validates that extract_with_logging accepts and passes ctx to extract().

        This ensures the wrapper method can propagate ExecutionContext through
        the extraction pipeline.
        """
        sig = inspect.signature(BaseExtractor.extract_with_logging)

        # Must have ctx parameter
        assert 'ctx' in sig.parameters, \
            "extract_with_logging() must accept 'ctx' parameter to pass to extract()"
