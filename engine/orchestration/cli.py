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
import sys
from typing import Dict, Any

from engine.orchestration.planner import orchestrate
from engine.orchestration.types import IngestRequest, IngestionMode


def format_report(report: Dict[str, Any]) -> str:
    """
    Format orchestration report for CLI output.

    Creates a human-readable report with:
    - Query echo
    - Summary statistics
    - Per-connector metrics table
    - Errors (if any)

    Args:
        report: The orchestration report dict

    Returns:
        Formatted string for CLI display
    """
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("INTELLIGENT INGESTION ORCHESTRATION REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Query
    lines.append(f"Query: {report['query']}")
    lines.append("")

    # Summary
    lines.append("Summary:")
    lines.append(f"  Candidates Found:    {report['candidates_found']}")
    lines.append(f"  Accepted Entities:   {report['accepted_entities']}")
    deduped = report['candidates_found'] - report['accepted_entities']
    lines.append(f"  Duplicates Removed:  {deduped}")

    # Add persistence info if available
    if "persisted_count" in report:
        lines.append(f"  Persisted to DB:     {report['persisted_count']}")

    lines.append("")

    # Connector Metrics
    lines.append("Connector Metrics:")
    lines.append("-" * 80)

    if report['connectors']:
        # Table header
        lines.append(f"{'Connector':<20} {'Status':<10} {'Time (ms)':<12} {'Candidates':<12} {'Cost (USD)':<12}")
        lines.append("-" * 80)

        # Table rows
        for connector_name, metrics in report['connectors'].items():
            if metrics.get("executed", False):
                status = "SUCCESS"
                time_ms = metrics.get("execution_time_ms", 0)
                candidates = metrics.get("candidates_added", 0)
                cost = metrics.get("cost_usd", 0.0)

                lines.append(f"{connector_name:<20} {status:<10} {time_ms:<12} {candidates:<12} {cost:<12.4f}")
            else:
                status = "FAILED"
                time_ms = metrics.get("execution_time_ms", 0)
                error = metrics.get("error", "Unknown error")

                lines.append(f"{connector_name:<20} {status:<10} {time_ms:<12} {'N/A':<12} {'N/A':<12}")
                lines.append(f"  Error: {error}")
    else:
        lines.append("  No connectors executed")

    lines.append("")

    # Errors
    if report['errors'] or report.get('persistence_errors'):
        lines.append("Errors:")
        lines.append("-" * 80)
        for error in report['errors']:
            connector = error.get("connector", "Unknown")
            error_msg = error.get("error", "Unknown error")
            lines.append(f"  [{connector}] {error_msg}")

        # Add persistence errors if present
        if report.get('persistence_errors'):
            for error in report['persistence_errors']:
                source = error.get("source", "Unknown")
                error_msg = error.get("error", "Unknown error")
                entity_name = error.get("entity_name", "N/A")
                lines.append(f"  [Persistence/{source}] {error_msg} (entity: {entity_name})")

        lines.append("")

    # Footer
    lines.append("=" * 80)

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

        # Execute orchestration
        report = orchestrate(request)

        # Format and print report
        formatted = format_report(report)
        print(formatted)

        # Exit successfully
        sys.exit(0)


if __name__ == "__main__":
    main()
