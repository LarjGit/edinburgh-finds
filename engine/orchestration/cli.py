"""
CLI for Intelligent Ingestion Orchestration.

Provides command-line interface for executing orchestrated ingestion:
- python -m engine.orchestration.cli run "query string"

Outputs a structured report with:
- Query echo
- Candidates found vs accepted
- Per-connector metrics (latency, cost, candidates added)
- Errors (if any)
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from engine.orchestration.planner import orchestrate
from engine.orchestration.types import IngestRequest, IngestionMode


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal formatting."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


def colorize(text: str, color: str) -> str:
    """
    Apply color to text using ANSI codes.

    Args:
        text: The text to colorize
        color: The color code to apply

    Returns:
        Colorized text with reset code
    """
    return f"{color}{text}{Colors.RESET}"


def format_report(report: Dict[str, Any]) -> str:
    """
    Format orchestration report for CLI output with colors and visual indicators.

    Creates a human-readable report with:
    - Query echo
    - Summary statistics (with color-coded values)
    - Per-connector metrics table (with status indicators)
    - Errors (if any, highlighted in red)

    Args:
        report: The orchestration report dict

    Returns:
        Formatted string for CLI display with ANSI color codes
    """
    lines = []

    # Header with color
    separator = "=" * 80
    lines.append(colorize(separator, Colors.CYAN))
    lines.append(colorize("INTELLIGENT INGESTION ORCHESTRATION REPORT", Colors.BOLD + Colors.CYAN))
    lines.append(colorize(separator, Colors.CYAN))
    lines.append("")

    # Query in bold
    lines.append(f"{colorize('Query:', Colors.BOLD)} {colorize(report['query'], Colors.BLUE)}")
    lines.append("")

    # Summary with color-coded values
    lines.append(colorize("Summary:", Colors.BOLD))
    lines.append(f"  Candidates Found:    {colorize(str(report['candidates_found']), Colors.CYAN)}")
    lines.append(f"  Accepted Entities:   {colorize(str(report['accepted_entities']), Colors.GREEN)}")
    deduped = report['candidates_found'] - report['accepted_entities']
    lines.append(f"  Duplicates Removed:  {colorize(str(deduped), Colors.YELLOW)}")

    # Add persistence info if available
    if "persisted_count" in report:
        lines.append(f"  Persisted to DB:     {colorize(str(report['persisted_count']), Colors.GREEN)}")

    lines.append("")

    # Warnings section (display prominently before other sections)
    if report.get("warnings"):
        lines.append(colorize("Warnings:", Colors.BOLD + Colors.YELLOW))
        lines.append(colorize("-" * 80, Colors.GRAY))
        for warning in report["warnings"]:
            message = warning.get("message", str(warning))
            lines.append(colorize(f"  {message}", Colors.YELLOW))
        lines.append("")

    # Extraction Pipeline section
    if "extraction_total" in report:
        lines.append(colorize("Extraction Pipeline:", Colors.BOLD))
        lines.append(colorize("-" * 80, Colors.GRAY))

        extraction_total = report["extraction_total"]
        extraction_success = report["extraction_success"]
        extraction_failed = extraction_total - extraction_success

        # Color code based on success rate
        if extraction_failed == 0:
            status_color = Colors.GREEN
        elif extraction_success == 0:
            status_color = Colors.RED
        else:
            status_color = Colors.YELLOW

        lines.append(
            f"  {colorize(f'{extraction_success}/{extraction_total}', status_color)} "
            f"entities extracted successfully"
        )

        # List extraction failures if any
        extraction_errors = report.get("extraction_errors", [])
        if extraction_errors:
            lines.append("")
            lines.append(colorize("  Extraction Failures:", Colors.RED))
            for error in extraction_errors:
                source = error.get("source", "unknown")
                entity_name = error.get("entity_name", "N/A")
                error_msg = error.get("error", "Unknown error")
                timestamp = error.get("timestamp", "")
                lines.append(colorize(f"    [{source}] {entity_name}: {error_msg}", Colors.RED))

        lines.append("")

    # Connector Metrics with color
    lines.append(colorize("Connector Metrics:", Colors.BOLD))
    lines.append(colorize("-" * 80, Colors.GRAY))

    if report['connectors']:
        # Table header
        header = f"{'Connector':<20} {'Status':<15} {'Time (ms)':<12} {'Candidates':<12} {'Cost (USD)':<12}"
        lines.append(colorize(header, Colors.BOLD))
        lines.append(colorize("-" * 80, Colors.GRAY))

        # Table rows with color-coded status
        for connector_name, metrics in report['connectors'].items():
            if metrics.get("executed", False):
                status = colorize("✓ SUCCESS", Colors.GREEN)
                time_ms = metrics.get("execution_time_ms", 0)
                candidates = metrics.get("candidates_added", 0)
                cost = metrics.get("cost_usd", 0.0)

                # Format row with proper spacing (accounting for ANSI codes)
                lines.append(f"{connector_name:<20} {status:<24} {time_ms:<12} {candidates:<12} {cost:<12.4f}")
            else:
                status = colorize("✗ FAILED", Colors.RED)
                time_ms = metrics.get("execution_time_ms", 0)
                error = metrics.get("error", "Unknown error")

                lines.append(f"{connector_name:<20} {status:<24} {time_ms:<12} {'N/A':<12} {'N/A':<12}")
                lines.append(colorize(f"  Error: {error}", Colors.RED))
    else:
        lines.append(colorize("  No connectors executed", Colors.YELLOW))

    lines.append("")

    # Errors section with color
    if report['errors'] or report.get('persistence_errors'):
        lines.append(colorize("Errors:", Colors.BOLD + Colors.RED))
        lines.append(colorize("-" * 80, Colors.GRAY))
        for error in report['errors']:
            connector = error.get("connector", "Unknown")
            error_msg = error.get("error", "Unknown error")
            lines.append(colorize(f"  [{connector}] {error_msg}", Colors.RED))

        # Add persistence errors if present
        if report.get('persistence_errors'):
            for error in report['persistence_errors']:
                source = error.get("source", "Unknown")
                error_msg = error.get("error", "Unknown error")
                entity_name = error.get("entity_name", "N/A")
                lines.append(colorize(f"  [Persistence/{source}] {error_msg} (entity: {entity_name})", Colors.RED))

        lines.append("")

    # Footer with color
    lines.append(colorize("=" * 80, Colors.CYAN))

    return "\n".join(lines)


def main():
    """
    CLI entry point for orchestration.

    Usage:
        python -m engine.orchestration.cli run "tennis courts Edinburgh"
    """
    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Intelligent Ingestion Orchestration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # run command
    run_parser = subparsers.add_parser("run", help="Run orchestrated ingestion")
    run_parser.add_argument("query", type=str, help="Search query string")
    run_parser.add_argument(
        "--mode",
        type=str,
        choices=["discover_many", "resolve_one"],
        default="discover_many",
        help="Ingestion mode (default: discover_many)",
    )
    run_parser.add_argument(
        "--persist",
        action="store_true",
        help="Persist accepted entities to database (default: False)",
    )

    # Parse arguments
    args = parser.parse_args()

    # Validate command
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "run":
        # Create ingestion request
        ingestion_mode = IngestionMode.DISCOVER_MANY
        if args.mode == "resolve_one":
            ingestion_mode = IngestionMode.RESOLVE_ONE

        request = IngestRequest(
            ingestion_mode=ingestion_mode,
            query=args.query,
            persist=args.persist,
        )

        # Execute orchestration (async)
        report = asyncio.run(orchestrate(request))

        # Format and print report
        formatted = format_report(report)
        print(formatted)

        # Exit successfully
        sys.exit(0)


if __name__ == "__main__":
    main()
