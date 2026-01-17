"""
Extraction health dashboard CLI.

Provides a command-line interface for viewing extraction health metrics and
formatted output suitable for quick diagnostics.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from prisma import Prisma

from engine.extraction.health_check import calculate_health_metrics


ANSI_RESET = "\x1b[0m"
ANSI_COLORS = {
    "healthy": "\x1b[32m",
    "warning": "\x1b[33m",
    "critical": "\x1b[31m",
}

STATUS_ORDER = {"healthy": 0, "warning": 1, "critical": 2}

SUCCESS_WARNING_THRESHOLD = 85.0
SUCCESS_CRITICAL_THRESHOLD = 60.0
NULL_WARNING_THRESHOLD = 50.0
NULL_CRITICAL_THRESHOLD = 80.0
UNPROCESSED_WARNING_THRESHOLD = 1
UNPROCESSED_CRITICAL_THRESHOLD = 50
FAILURE_WARNING_THRESHOLD = 1
FAILURE_CRITICAL_THRESHOLD = 10
MERGE_WARNING_THRESHOLD = 1
MERGE_CRITICAL_THRESHOLD = 10


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _colorize(text: str, severity: str, use_color: bool) -> str:
    if not use_color:
        return text
    color = ANSI_COLORS.get(severity)
    if not color:
        return text
    return f"{color}{text}{ANSI_RESET}"


def _severity_for_rate(
    rate: float,
    warning_threshold: float,
    critical_threshold: float,
    higher_is_worse: bool = False,
) -> str:
    if higher_is_worse:
        if rate >= critical_threshold:
            return "critical"
        if rate >= warning_threshold:
            return "warning"
        return "healthy"
    if rate <= critical_threshold:
        return "critical"
    if rate <= warning_threshold:
        return "warning"
    return "healthy"


def _severity_for_count(
    count: int,
    warning_threshold: int,
    critical_threshold: int,
) -> str:
    if count >= critical_threshold:
        return "critical"
    if count >= warning_threshold:
        return "warning"
    return "healthy"


def _worst_status(statuses: Iterable[str]) -> str:
    worst = "healthy"
    for status in statuses:
        if STATUS_ORDER.get(status, 0) > STATUS_ORDER[worst]:
            worst = status
    return worst


def _format_timestamp(value: Optional[datetime]) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return "unknown"


async def fetch_health_metrics() -> Dict[str, Any]:
    """Fetch extraction health metrics from the database."""
    db = Prisma()

    await db.connect()

    try:
        raw_records = await db.rawingestion.find_many()
        extracted_listings = await db.extractedlisting.find_many()
        failed_extractions = await db.failedextraction.find_many()

        merge_conflicts: List[Any] = []
        if hasattr(db, "mergeconflict"):
            merge_conflicts = await db.mergeconflict.find_many()

        return calculate_health_metrics(
            raw_records=raw_records,
            extracted_listings=extracted_listings,
            failed_extractions=failed_extractions,
            merge_conflicts=merge_conflicts,
        )
    finally:
        await db.disconnect()


def format_health_report(
    metrics: Dict[str, Any],
    *,
    use_color: bool = True,
    max_fields: int = 10,
    max_failures: int = 10,
) -> str:
    """Format extraction health metrics for console output."""
    timestamp = metrics.get("timestamp") or _now_utc()
    if isinstance(timestamp, datetime) and timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    unprocessed = metrics.get("unprocessed", {})
    unprocessed_count = int(unprocessed.get("count", 0) or 0)
    unprocessed_by_source = unprocessed.get("by_source", {}) or {}

    success_by_source = metrics.get("success_rate_by_source", {}) or {}
    field_null_rates = metrics.get("field_null_rates", {}) or {}
    recent_failures = metrics.get("recent_failures", []) or []
    llm_usage = metrics.get("llm_usage", {}) or {}
    merge_conflicts = int(metrics.get("merge_conflicts", 0) or 0)

    unprocessed_status = _severity_for_count(
        unprocessed_count,
        UNPROCESSED_WARNING_THRESHOLD,
        UNPROCESSED_CRITICAL_THRESHOLD,
    )
    failure_status = _severity_for_count(
        len(recent_failures),
        FAILURE_WARNING_THRESHOLD,
        FAILURE_CRITICAL_THRESHOLD,
    )
    merge_status = _severity_for_count(
        merge_conflicts,
        MERGE_WARNING_THRESHOLD,
        MERGE_CRITICAL_THRESHOLD,
    )

    max_null_rate = 0.0
    for data in field_null_rates.values():
        try:
            max_null_rate = max(max_null_rate, float(data.get("null_rate", 0.0) or 0.0))
        except (TypeError, ValueError):
            continue

    null_rate_status = _severity_for_rate(
        max_null_rate,
        NULL_WARNING_THRESHOLD,
        NULL_CRITICAL_THRESHOLD,
        higher_is_worse=True,
    )

    per_source_statuses = []
    for data in success_by_source.values():
        try:
            rate = float(data.get("success_rate", 0.0) or 0.0)
        except (TypeError, ValueError):
            rate = 0.0
        per_source_statuses.append(
            _severity_for_rate(rate, SUCCESS_WARNING_THRESHOLD, SUCCESS_CRITICAL_THRESHOLD)
        )

    overall_status = _worst_status(
        [unprocessed_status, failure_status, merge_status, null_rate_status] + per_source_statuses
    )

    lines: List[str] = []
    lines.append("=" * 80)
    lines.append("EXTRACTION HEALTH DASHBOARD")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Generated: {timestamp.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    lines.append("")

    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(
        f"  Overall Status:          {_colorize(overall_status.upper(), overall_status, use_color)}"
    )
    lines.append(
        f"  Unprocessed Raw Records: {_colorize(str(unprocessed_count), unprocessed_status, use_color)}"
    )
    lines.append(
        f"  Recent Failures:         {_colorize(str(len(recent_failures)), failure_status, use_color)}"
    )
    lines.append(
        f"  Merge Conflicts:         {_colorize(str(merge_conflicts), merge_status, use_color)}"
    )
    if field_null_rates:
        lines.append(
            f"  Worst Field Null Rate:   {_colorize(f'{max_null_rate:.1f}%', null_rate_status, use_color)}"
        )
    lines.append("")

    lines.append("SUCCESS RATE BY SOURCE")
    lines.append("-" * 80)
    if success_by_source:
        header = f"  {'Source':20s} {'Total':>7s} {'Extracted':>9s} {'Success':>9s}"
        lines.append(header)
        lines.append(f"  {'-' * 20} {'-' * 7} {'-' * 9} {'-' * 9}")

        for source, data in sorted(
            success_by_source.items(), key=lambda item: item[0]
        ):
            total = int(data.get("total", 0) or 0)
            extracted = int(data.get("extracted", 0) or 0)
            try:
                rate = float(data.get("success_rate", 0.0) or 0.0)
            except (TypeError, ValueError):
                rate = 0.0
            rate_text = f"{rate:6.1f}%"
            rate_status = _severity_for_rate(
                rate, SUCCESS_WARNING_THRESHOLD, SUCCESS_CRITICAL_THRESHOLD
            )
            rate_display = _colorize(rate_text.rjust(9), rate_status, use_color)
            lines.append(
                f"  {source:20.20s} {total:7d} {extracted:9d} {rate_display}"
            )
    else:
        lines.append("  No extraction records found")
    lines.append("")

    lines.append("UNPROCESSED BY SOURCE")
    lines.append("-" * 80)
    if unprocessed_by_source:
        header = f"  {'Source':20s} {'Unprocessed':>12s}"
        lines.append(header)
        lines.append(f"  {'-' * 20} {'-' * 12}")
        for source, count in sorted(
            unprocessed_by_source.items(), key=lambda item: item[1], reverse=True
        ):
            lines.append(f"  {source:20.20s} {int(count):12d}")
    else:
        lines.append("  None")
    lines.append("")

    lines.append("FIELD NULL RATES")
    lines.append("-" * 80)
    if field_null_rates:
        header = f"  {'Field':25s} {'Nulls':>7s} {'Total':>7s} {'Null %':>9s}"
        lines.append(header)
        lines.append(f"  {'-' * 25} {'-' * 7} {'-' * 7} {'-' * 9}")

        sorted_fields = sorted(
            field_null_rates.items(),
            key=lambda item: float(item[1].get("null_rate", 0.0) or 0.0),
            reverse=True,
        )
        for field, data in sorted_fields[:max_fields]:
            null_count = int(data.get("null_count", 0) or 0)
            total = int(data.get("total", 0) or 0)
            try:
                null_rate = float(data.get("null_rate", 0.0) or 0.0)
            except (TypeError, ValueError):
                null_rate = 0.0
            rate_text = f"{null_rate:6.1f}%"
            rate_status = _severity_for_rate(
                null_rate,
                NULL_WARNING_THRESHOLD,
                NULL_CRITICAL_THRESHOLD,
                higher_is_worse=True,
            )
            rate_display = _colorize(rate_text.rjust(9), rate_status, use_color)
            lines.append(
                f"  {field:25.25s} {null_count:7d} {total:7d} {rate_display}"
            )
        if len(sorted_fields) > max_fields:
            lines.append(f"  ... {len(sorted_fields) - max_fields} more fields not shown")
    else:
        lines.append("  No extracted fields available")
    lines.append("")

    lines.append("RECENT FAILURES")
    lines.append("-" * 80)
    if recent_failures:
        header = f"  {'Last Attempt':19s} {'Source':15s} Error"
        lines.append(header)
        lines.append(f"  {'-' * 19} {'-' * 15} {'-' * 30}")
        for failure in recent_failures[:max_failures]:
            last_attempt = _format_timestamp(failure.get("last_attempt_at"))
            source = str(failure.get("source", "unknown"))
            error = str(failure.get("error_message", "") or "")
            if len(error) > 60:
                error = error[:57] + "..."
            lines.append(f"  {last_attempt:19s} {source:15.15s} {error}")
        if len(recent_failures) > max_failures:
            lines.append(f"  ... {len(recent_failures) - max_failures} more failures not shown")
    else:
        lines.append("  None")
    lines.append("")

    lines.append("LLM USAGE")
    lines.append("-" * 80)
    total_llm = int(llm_usage.get("total_llm_extractions", 0) or 0)
    input_tokens = int(llm_usage.get("input_tokens", 0) or 0)
    output_tokens = int(llm_usage.get("output_tokens", 0) or 0)
    estimated_cost = float(llm_usage.get("estimated_cost", 0.0) or 0.0)

    lines.append(f"  Total LLM Extractions: {total_llm}")
    lines.append(f"  Input Tokens:          {input_tokens:,}")
    lines.append(f"  Output Tokens:         {output_tokens:,}")
    lines.append(f"  Estimated Cost:        GBP {estimated_cost:.4f}")

    if llm_usage.get("has_usage_data") is False:
        lines.append("  Note: Usage data missing on some records.")

    by_model = llm_usage.get("by_model", {}) or {}
    if by_model:
        lines.append("  By Model:")
        for model, count in sorted(by_model.items(), key=lambda item: item[1], reverse=True):
            lines.append(f"    {model}: {int(count)}")
    lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def main() -> int:
    """CLI entry point for extraction health dashboard."""
    parser = argparse.ArgumentParser(description="Extraction health dashboard")
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in output",
    )
    parser.add_argument(
        "--max-fields",
        type=int,
        default=10,
        help="Maximum number of fields to display in null rate table",
    )
    parser.add_argument(
        "--max-failures",
        type=int,
        default=10,
        help="Maximum number of failures to display",
    )

    args = parser.parse_args()

    try:
        metrics = asyncio.run(fetch_health_metrics())
    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    report = format_health_report(
        metrics,
        use_color=not args.no_color,
        max_fields=args.max_fields,
        max_failures=args.max_failures,
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
