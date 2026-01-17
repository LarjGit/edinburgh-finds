"""
LLM cost tracking and calculation.

Provides functionality to:
- Track token usage from Anthropic API calls
- Calculate costs based on model pricing
- Aggregate usage statistics by source and model
- Generate cost reports
"""

from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any


# Anthropic API pricing (as of January 2025)
# Prices in USD per 1 million tokens
MODEL_PRICING = {
    "claude-3-haiku-20240307": {
        "input": 0.25,  # $0.25 per 1M input tokens
        "output": 1.25,  # $1.25 per 1M output tokens
    },
    "claude-3-5-sonnet-20241022": {
        "input": 3.0,  # $3 per 1M input tokens
        "output": 15.0,  # $15 per 1M output tokens
    },
    "claude-3-opus-20240229": {
        "input": 15.0,  # $15 per 1M input tokens
        "output": 75.0,  # $75 per 1M output tokens
    },
}


def calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """
    Calculate cost in USD for a given token usage.

    Args:
        model: Model identifier (e.g., "claude-3-haiku-20240307")
        tokens_in: Number of input tokens
        tokens_out: Number of output tokens

    Returns:
        float: Cost in USD

    Raises:
        ValueError: If model is not in pricing table
    """
    if model not in MODEL_PRICING:
        raise ValueError(f"Unknown model: {model}")

    pricing = MODEL_PRICING[model]

    cost_in = (tokens_in / 1_000_000) * pricing["input"]
    cost_out = (tokens_out / 1_000_000) * pricing["output"]

    return cost_in + cost_out


def extract_token_usage(response: Any) -> Tuple[int, int]:
    """
    Extract token usage from Anthropic API response.

    Args:
        response: Anthropic API response object with usage field

    Returns:
        Tuple[int, int]: (input_tokens, output_tokens)

    Raises:
        AttributeError: If response doesn't have usage field
    """
    return response.usage.input_tokens, response.usage.output_tokens


class LLMUsageTracker:
    """
    Tracks LLM API usage and costs.

    Maintains a record of all LLM calls with token counts, costs,
    and metadata for reporting and cost analysis.
    """

    def __init__(self):
        """Initialize empty usage tracker."""
        self.usage_records: List[Dict[str, Any]] = []

    @property
    def total_tokens_in(self) -> int:
        """Get total input tokens across all records."""
        return sum(r["tokens_in"] for r in self.usage_records)

    @property
    def total_tokens_out(self) -> int:
        """Get total output tokens across all records."""
        return sum(r["tokens_out"] for r in self.usage_records)

    @property
    def total_cost_usd(self) -> float:
        """Get total cost in USD across all records."""
        return sum(r["cost_usd"] for r in self.usage_records)

    def record_usage(
        self,
        model: str,
        tokens_in: int,
        tokens_out: int,
        source: str,
        record_id: str,
    ) -> None:
        """
        Record an LLM API call.

        Args:
            model: Model identifier
            tokens_in: Input tokens used
            tokens_out: Output tokens used
            source: Data source name
            record_id: Raw ingestion record ID
        """
        cost = calculate_cost(model, tokens_in, tokens_out)

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost,
            "source": source,
            "record_id": record_id,
        }

        self.usage_records.append(record)

    def get_cost_by_source(self) -> Dict[str, Dict[str, Any]]:
        """
        Get cost breakdown by source.

        Returns:
            Dict mapping source name to usage stats:
            {
                "source_name": {
                    "count": int,
                    "total_tokens": int,
                    "total_cost_usd": float,
                }
            }
        """
        by_source: Dict[str, Dict[str, Any]] = {}

        for record in self.usage_records:
            source = record["source"]

            if source not in by_source:
                by_source[source] = {
                    "count": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                }

            by_source[source]["count"] += 1
            by_source[source]["total_tokens"] += record["tokens_in"] + record["tokens_out"]
            by_source[source]["total_cost_usd"] += record["cost_usd"]

        return by_source

    def get_cost_by_model(self) -> Dict[str, Dict[str, Any]]:
        """
        Get cost breakdown by model.

        Returns:
            Dict mapping model name to usage stats:
            {
                "model_name": {
                    "count": int,
                    "total_tokens": int,
                    "total_cost_usd": float,
                }
            }
        """
        by_model: Dict[str, Dict[str, Any]] = {}

        for record in self.usage_records:
            model = record["model"]

            if model not in by_model:
                by_model[model] = {
                    "count": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                }

            by_model[model]["count"] += 1
            by_model[model]["total_tokens"] += record["tokens_in"] + record["tokens_out"]
            by_model[model]["total_cost_usd"] += record["cost_usd"]

        return by_model


# Global singleton tracker
_usage_tracker: LLMUsageTracker | None = None


def get_usage_tracker() -> LLMUsageTracker:
    """
    Get the global LLM usage tracker.

    Returns:
        LLMUsageTracker: Singleton tracker instance
    """
    global _usage_tracker

    if _usage_tracker is None:
        _usage_tracker = LLMUsageTracker()

    return _usage_tracker


def format_cost_report(tracker: LLMUsageTracker) -> str:
    """
    Format a cost report from usage tracker.

    Args:
        tracker: LLMUsageTracker instance

    Returns:
        str: Formatted report string
    """
    lines = []
    lines.append("=" * 60)
    lines.append("LLM COST REPORT")
    lines.append("=" * 60)
    lines.append("")

    # Overall totals
    lines.append(f"Total API Calls:    {len(tracker.usage_records):,}")
    lines.append(f"Total Input Tokens: {tracker.total_tokens_in:,}")
    lines.append(f"Total Output Tokens: {tracker.total_tokens_out:,}")
    lines.append(f"Total Tokens:       {tracker.total_tokens_in + tracker.total_tokens_out:,}")
    lines.append(f"Total Cost:         ${tracker.total_cost_usd:.4f} USD")
    lines.append("")

    # Cost by source
    by_source = tracker.get_cost_by_source()
    if by_source:
        lines.append("COST BY SOURCE:")
        lines.append("-" * 60)
        for source, stats in sorted(by_source.items()):
            lines.append(f"  {source}:")
            lines.append(f"    Calls:  {stats['count']:,}")
            lines.append(f"    Tokens: {stats['total_tokens']:,}")
            lines.append(f"    Cost:   ${stats['total_cost_usd']:.4f} USD")
        lines.append("")

    # Cost by model
    by_model = tracker.get_cost_by_model()
    if by_model:
        lines.append("COST BY MODEL:")
        lines.append("-" * 60)
        for model, stats in sorted(by_model.items()):
            # Shorten model name for display
            model_display = model.replace("claude-3-", "").replace("claude-3-5-", "")
            lines.append(f"  {model_display}:")
            lines.append(f"    Calls:  {stats['count']:,}")
            lines.append(f"    Tokens: {stats['total_tokens']:,}")
            lines.append(f"    Cost:   ${stats['total_cost_usd']:.4f} USD")
        lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)
