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
    """

    # Default character limits for summaries
    DEFAULT_MIN_CHARS = 100
    DEFAULT_MAX_CHARS = 200

    # Maximum retry attempts for character limit enforcement
    DEFAULT_MAX_RETRIES = 3

    # Mapping of summary types to their relevant fact fields
    SUMMARY_TYPE_FIELDS = {
        "padel_summary": ["padel", "padel_total_courts"],
        "tennis_summary": [
            "tennis", "tennis_total_courts", "tennis_indoor_courts",
            "tennis_outdoor_courts", "tennis_covered_courts", "tennis_floodlit_courts"
        ],
        "pickleball_summary": ["pickleball", "pickleball_total_courts"],
        "badminton_summary": ["badminton", "badminton_total_courts"],
        "squash_summary": ["squash", "squash_total_courts", "squash_glass_back_courts"],
        "table_tennis_summary": ["table_tennis", "table_tennis_total_tables"],
        "football_summary": [
            "football_5_a_side", "football_5_a_side_total_pitches",
            "football_7_a_side", "football_7_a_side_total_pitches",
            "football_11_a_side", "football_11_a_side_total_pitches"
        ],
        "swimming_summary": [
            "indoor_pool", "outdoor_pool", "indoor_pool_length_m",
            "outdoor_pool_length_m", "family_swim", "adult_only_swim", "swimming_lessons"
        ],
        "gym_summary": [
            "gym_available", "gym_size"
        ],
        "classes_summary": [
            "classes_per_week", "hiit_classes", "yoga_classes",
            "pilates_classes", "strength_classes", "cycling_studio", "functional_training_zone"
        ],
        "spa_summary": [
            "spa_available", "sauna", "steam_room", "hydro_pool",
            "hot_tub", "outdoor_spa", "ice_cold_plunge", "relaxation_area"
        ],
        "amenities_summary": [
            "restaurant", "bar", "cafe", "childrens_menu", "wifi"
        ],
        "family_summary": [
            "creche_available", "creche_age_min", "creche_age_max",
            "kids_swimming_lessons", "kids_tennis_lessons", "holiday_club", "play_area"
        ],
        "parking_and_transport_summary": [
            "parking_spaces", "disabled_parking", "parent_child_parking",
            "ev_charging_available", "ev_charging_connectors",
            "public_transport_nearby", "nearest_railway_station"
        ],
        "reviews_summary": [
            "review_count", "google_review_count", "facebook_likes"
        ]
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
   - Use contextual bridges: "Just a short walk from [Landmark]" or "Perfect for those who prefer [Specific Need]"
   - Be a "Knowledgeable Local Friend" - helpful, warm, authoritative
   - Utility over hype: If expensive, say "Premium-priced". If basic, say "Functional and focused"
   - Never use marketing fluff

3. TONE:
   - Practical and informative
   - Warm but not effusive
   - Specific details over generic praise
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

    def _has_relevant_data(self, summary_type: str, facts: Dict) -> bool:
        """
        Check if venue has relevant data for this summary type.

        Args:
            summary_type: Type of summary to check
            facts: Structured facts dictionary

        Returns:
            bool: True if venue has at least one relevant field with data
        """
        relevant_fields = self.SUMMARY_TYPE_FIELDS.get(summary_type, [])

        for field in relevant_fields:
            value = facts.get(field)
            # Check for meaningful values (not None, not False for booleans)
            if value is not None and value is not False:
                return True

        return False

    def _extract_relevant_facts(self, summary_type: str, facts: Dict) -> Dict:
        """
        Extract only the facts relevant to this summary type.

        Args:
            summary_type: Type of summary
            facts: Full structured facts dictionary

        Returns:
            Dict: Filtered facts containing only relevant fields
        """
        relevant_fields = self.SUMMARY_TYPE_FIELDS.get(summary_type, [])

        # Always include entity_name for context
        relevant_facts = {}
        if "entity_name" in facts:
            relevant_facts["entity_name"] = facts["entity_name"]

        # Add summary-specific fields
        for field in relevant_fields:
            if field in facts and facts[field] is not None:
                relevant_facts[field] = facts[field]

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
