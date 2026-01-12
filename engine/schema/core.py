from dataclasses import dataclass, field
from typing import Optional, List, Any

@dataclass
class FieldSpec:
    """
    Specification for a single field (common or entity-specific).

    This is framework-neutral - no SQLModel, no Pydantic.
    Generators will create SQLModel and Pydantic projections from this.
    """
    name: str
    type_annotation: str  # e.g. "str", "Optional[str]", "Optional[bool]", "Optional[List[str]]"
    description: str
    nullable: bool = True

    # Semantic metadata for search/LLM extraction
    search_category: Optional[str] = None
    search_keywords: Optional[List[str]] = None

    # Database constraints
    index: bool = False
    unique: bool = False
    default: Optional[str] = "None"

    # Special handling
    exclude: bool = False  # Exclude from LLM extraction (internal/auto-generated fields)
    primary_key: bool = False
    foreign_key: Optional[str] = None
    sa_column: Optional[str] = None  # e.g. "Column(ARRAY(String))" for special column types
    required: bool = False  # True if field is required (not Optional)
