"""
Summary Synthesis Utility

Synthesizes high-quality, character-limited summary fields for venue attributes.
Follows "Knowledgeable Local Friend" voice from product-guidelines.md.

Multi-Stage Process:
1. Extract structured facts (already done by main extractor)
2. Gather rich text descriptions from raw data
3. LLM synthesis combining facts + descriptions with character limits
4. Retry with character limit enforcement (max 3 attempts)

Features:
- Sport-specific summaries (padel_summary, tennis_summary, gym_summary, etc.)
- Character limit enforcement with retry logic
- Brand voice compliance (no marketing fluff)
- Handles missing rich text gracefully
- Null semantics (null = no relevant data, not "no summary available")
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from pathlib import Path
import yaml

from engine.extraction.llm_client import InstructorClient


class SummaryOutput(BaseModel):
    """Pydantic model for summary LLM output with character limit validation"""
    summary: str = Field(
        ...,
        description="The synthesized summary text within character limits"
    )

    @field_validator('summary')
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Ensure summary is not empty"""
        if not v or not v.strip():
            raise ValueError("Summary cannot be empty")
        return v.strip()


# Cached LLM client (singleton pattern)
_llm_client: Optional[InstructorClient] = None


def get_llm_client() -> InstructorClient:
    """
    Get or create the LLM client instance (singleton).

    Returns:
        InstructorClient: The global LLM client instance
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = InstructorClient()
    return _llm_client


class SummarySynthesizer:
    """
    Synthesizes high-quality summary fields for venue attributes.

    Combines structured facts with rich text descriptions to create
    concise, engaging summaries that follow the "Knowledgeable Local Friend"
    voice from product-guidelines.md.

    Convention-based approach:
    - Automatically discovers relevant fields based on naming conventions
    - Summary type "padel_summary" → finds all fields starting with "padel_"
    - Summary type "restaurant_summary" → finds all fields starting with "restaurant_"
    - Fully extensible: adding new entity types or fields requires no code changes

    Special cases with custom prefixes can be defined in CUSTOM_FIELD_PREFIXES.
    """

    # Default character limits for summaries
    DEFAULT_MIN_CHARS = 100
    DEFAULT_MAX_CHARS = 200

    # Maximum retry attempts for character limit enforcement
    DEFAULT_MAX_RETRIES = 3

    # Custom field prefix mappings for summary types that don't follow the standard convention
    # Format: {"summary_type": ["prefix1_", "prefix2_", ...]}
    CUSTOM_FIELD_PREFIXES = {
        # "swimming_summary" matches both "swimming_" and pool-related fields
        "swimming_summary": ["swimming_", "pool"],
        # "parking_and_transport_summary" matches parking and transport fields
        "parking_and_transport_summary": ["parking_", "transport", "ev_charging"],
        # "amenities_summary" matches amenity fields
        "amenities_summary": ["restaurant", "bar", "cafe", "wifi", "childrens_menu"],
        # "family_summary" matches family/kids fields
        "family_summary": ["family_", "kids_", "creche_", "holiday_club", "play_area"],
        # "reviews_summary" matches review/social fields
        "reviews_summary": ["review_", "_review", "facebook_", "rating"],
    }

    def __init__(self):
        """Initialize the summary synthesizer"""
        self.llm_client = get_llm_client()
        self._load_brand_voice_guidelines()

    def _load_brand_voice_guidelines(self):
        """Load brand voice guidelines from product-guidelines.md"""
        # For now, hardcode the key guidelines
        # In future, could parse from product-guidelines.md
        self.brand_voice_rules = """
CRITICAL BRAND VOICE RULES (from product-guidelines.md):
1. PROHIBITED PHRASES (never use these):
   - "Located at"
   - "Features include"
   - "A great place for"
   - "Welcome to"
   - "Proud to offer"

2. REQUIRED STYLE:
   - Be CONCISE - every word must add value
   - Use contextual bridges: "Just a short walk from [Landmark]" or "Perfect for those who prefer [Specific Need]"
   - Be a "Knowledgeable Local Friend" - helpful, warm, authoritative
   - Utility over hype: If expensive, say "Premium-priced". If basic, say "Functional and focused"
   - Never use marketing fluff

3. TONE:
   - Practical and informative
   - Warm but not effusive
   - Specific details over generic praise
   - Brief and to-the-point - avoid verbose descriptions
"""

    def synthesize_summary(
        self,
        summary_type: str,
        structured_facts: Optional[Dict],
        rich_text: List[str],
        min_chars: Optional[int] = None,
        max_chars: Optional[int] = None,
        max_retries: Optional[int] = None
    ) -> Optional[str]:
        """
        Synthesize a summary field from structured facts and rich text.

        Args:
            summary_type: Type of summary (e.g., "padel_summary", "tennis_summary")
            structured_facts: Extracted structured facts from main extractor
            rich_text: List of rich text descriptions (reviews, editorial, etc.)
            min_chars: Minimum character count (default: 100)
            max_chars: Maximum character count (default: 200)
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            Synthesized summary string, or None if no relevant data

        Examples:
            >>> synthesizer = SummarySynthesizer()
            >>> facts = {"padel": True, "padel_total_courts": 4}
            >>> rich = ["Great padel venue with 4 courts..."]
            >>> summary = synthesizer.synthesize_summary("padel_summary", facts, rich)
            >>> print(summary)
            "Edinburgh's premier padel facility with 4 indoor courts..."
        """
        # Set defaults
        min_chars = min_chars or self.DEFAULT_MIN_CHARS
        max_chars = max_chars or self.DEFAULT_MAX_CHARS
        max_retries = max_retries or self.DEFAULT_MAX_RETRIES

        # Validate inputs
        if not structured_facts:
            return None

        # Check if venue has relevant data for this summary type
        if not self._has_relevant_data(summary_type, structured_facts):
            return None

        # Extract relevant facts for this summary type
        relevant_facts = self._extract_relevant_facts(summary_type, structured_facts)

        # Build context from facts + rich text
        context = self._build_context(relevant_facts, rich_text)

        # Synthesize with retry logic
        for attempt in range(max_retries + 1):
            try:
                summary = self._synthesize_with_llm(
                    summary_type=summary_type,
                    context=context,
                    min_chars=min_chars,
                    max_chars=max_chars,
                    attempt=attempt
                )

                # Validate character limits
                if min_chars <= len(summary) <= max_chars:
                    return summary

                # Length violation - prepare for retry
                if attempt < max_retries:
                    if len(summary) < min_chars:
                        print(f"Summary too short ({len(summary)} chars). Retrying... (Attempt {attempt + 1}/{max_retries})")
                    else:
                        print(f"Summary too long ({len(summary)} chars). Retrying... (Attempt {attempt + 1}/{max_retries})")
                    continue
                else:
                    # Max retries exhausted - return best attempt or None
                    print(f"Max retries exhausted. Summary length: {len(summary)} (target: {min_chars}-{max_chars})")
                    # If it's close enough (within 20% tolerance), accept it
                    if min_chars * 0.8 <= len(summary) <= max_chars * 1.2:
                        return summary
                    return None

            except Exception as e:
                print(f"Summary synthesis failed on attempt {attempt + 1}: {e}")
                if attempt == max_retries:
                    return None
                continue

        return None

    def _get_field_prefixes(self, summary_type: str) -> list:
        """
        Get the field prefixes relevant to this summary type.

        Uses convention-based approach:
        - "padel_summary" → ["padel_"]
        - "restaurant_summary" → ["restaurant_"]

        Special cases defined in CUSTOM_FIELD_PREFIXES override the convention.

        Args:
            summary_type: Type of summary (e.g., "padel_summary")

        Returns:
            list: List of field prefixes to match against
        """
        # Check for custom prefix mapping
        if summary_type in self.CUSTOM_FIELD_PREFIXES:
            return self.CUSTOM_FIELD_PREFIXES[summary_type]

        # Convention-based: extract prefix from summary type
        # "padel_summary" → "padel_"
        # "tennis_summary" → "tennis_"
        if summary_type.endswith("_summary"):
            prefix = summary_type[:-8]  # Remove "_summary"
            return [prefix + "_", prefix]  # Match "padel_" or "padel"

        # Fallback: use the whole summary type as prefix
        return [summary_type]

    def _field_matches_prefixes(self, field_name: str, prefixes: list) -> bool:
        """
        Check if a field name matches any of the given prefixes.

        Args:
            field_name: Name of the field to check
            prefixes: List of prefixes to match against

        Returns:
            bool: True if field matches any prefix
        """
        for prefix in prefixes:
            if field_name.startswith(prefix) or prefix in field_name:
                return True
        return False

    def _has_relevant_data(self, summary_type: str, facts: Dict) -> bool:
        """
        Check if venue has relevant data for this summary type.

        Uses convention-based field discovery: finds fields matching the
        summary type's prefix (e.g., "padel_summary" → "padel_*" fields).

        Args:
            summary_type: Type of summary to check
            facts: Structured facts dictionary

        Returns:
            bool: True if venue has at least one relevant field with data
        """
        prefixes = self._get_field_prefixes(summary_type)

        for field_name, value in facts.items():
            # Skip entity_name (it's metadata, not relevant data)
            if field_name == "entity_name":
                continue

            # Check if field matches any prefix
            if self._field_matches_prefixes(field_name, prefixes):
                # Check for meaningful values (not None, not False for booleans)
                if value is not None and value is not False:
                    return True

        return False

    def _extract_relevant_facts(self, summary_type: str, facts: Dict) -> Dict:
        """
        Extract only the facts relevant to this summary type.

        Uses convention-based field discovery to automatically find
        relevant fields based on naming patterns.

        Args:
            summary_type: Type of summary
            facts: Full structured facts dictionary

        Returns:
            Dict: Filtered facts containing only relevant fields
        """
        prefixes = self._get_field_prefixes(summary_type)
        relevant_facts = {}

        # Always include entity_name for context
        if "entity_name" in facts:
            relevant_facts["entity_name"] = facts["entity_name"]

        # Add summary-specific fields based on prefix matching
        for field_name, value in facts.items():
            # Skip entity_name (already added)
            if field_name == "entity_name":
                continue

            # Check if field matches any prefix
            if self._field_matches_prefixes(field_name, prefixes):
                if value is not None:
                    relevant_facts[field_name] = value

        return relevant_facts

    def _build_context(self, relevant_facts: Dict, rich_text: List[str]) -> str:
        """
        Build context string from structured facts and rich text.

        Args:
            relevant_facts: Filtered relevant facts
            rich_text: List of rich text descriptions

        Returns:
            str: Combined context for LLM
        """
        context_parts = []

        # Add structured facts
        if relevant_facts:
            context_parts.append("STRUCTURED FACTS:")
            for key, value in relevant_facts.items():
                context_parts.append(f"- {key}: {value}")

        # Add rich text
        if rich_text:
            context_parts.append("\nRICH TEXT DESCRIPTIONS:")
            for idx, text in enumerate(rich_text[:10], 1):  # Limit to first 10
                context_parts.append(f"{idx}. {text}")

        return "\n".join(context_parts)

    def _synthesize_with_llm(
        self,
        summary_type: str,
        context: str,
        min_chars: int,
        max_chars: int,
        attempt: int
    ) -> str:
        """
        Synthesize summary using LLM.

        Args:
            summary_type: Type of summary
            context: Combined context (facts + rich text)
            min_chars: Minimum character count
            max_chars: Maximum character count
            attempt: Current attempt number (for retry feedback)

        Returns:
            str: Synthesized summary
        """
        # Build prompt with character limit emphasis based on attempt
        emphasis = ""
        if attempt > 0:
            emphasis = f"\n\n⚠️ CRITICAL: Previous attempt violated character limits. The summary MUST be between {min_chars} and {max_chars} characters. This is attempt {attempt + 1}."

        prompt = f"""
Synthesize a {summary_type.replace('_', ' ')} for this venue.

CHARACTER LIMIT: The summary MUST be between {min_chars} and {max_chars} characters (including spaces and punctuation).
{emphasis}

{self.brand_voice_rules}

SYNTHESIS INSTRUCTIONS:
1. Combine structured facts with insights from rich text descriptions
2. Focus on practical, specific details (court types, facilities, unique features)
3. Write in "Knowledgeable Local Friend" voice - warm, helpful, authoritative
4. NO marketing fluff or generic praise
5. Be concise and informative
6. MUST stay within {min_chars}-{max_chars} character limit

EXAMPLES OF GOOD SUMMARIES:
- "Edinburgh's premier padel facility with 4 indoor heated courts. Professional-grade glass walls and LED lighting make this ideal for year-round play. Beginners welcome with coaching available."
- "Comprehensive tennis centre offering 12 courts split between 4 climate-controlled indoor courts and 8 outdoor courts, 6 of which are floodlit for evening play. Popular with both members and casual players."
- "Modern 150-station gym with extensive free weights section and 45 weekly classes including HIIT, yoga, and spin. Open 24/7 with quiet periods mid-morning and late evening."

EXAMPLES OF BAD SUMMARIES (never do this):
- "Located at a great venue, features include amazing courts. A great place for sports enthusiasts!" ❌ (Marketing fluff, prohibited phrases)
- "This is a padel venue." ❌ (Too vague, no useful details)
"""

        system_message = (
            "You are a venue description writer following strict brand guidelines. "
            "Your summaries are practical, informative, and written in a warm but authoritative tone. "
            f"You MUST respect character limits: {min_chars}-{max_chars} characters."
        )

        # Use the LLM client to extract structured summary
        # We don't use response_model validation for character limits here
        # because Pydantic can't easily enforce dynamic length constraints
        # Instead, we validate in the calling function
        response = self.llm_client.anthropic_client.messages.create(
            model=self.llm_client.model_name,
            max_tokens=1024,
            system=system_message,
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nContext:\n{context}"
                }
            ]
        )

        # Extract text from response
        summary = response.content[0].text.strip()

        # Remove quotes if LLM wrapped the summary
        if summary.startswith('"') and summary.endswith('"'):
            summary = summary[1:-1]
        if summary.startswith("'") and summary.endswith("'"):
            summary = summary[1:-1]

        return summary
