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
from engine.orchestration.execution_context import ExecutionContext
from engine.lenses.loader import VerticalLens, LensConfigError

import os


def bootstrap_lens(lens_id: str) -> ExecutionContext:
    """
    Bootstrap: Load and validate lens configuration ONCE at CLI entry point.

    Per docs/target-architecture.md 3.2: "Lens loading occurs only during engine bootstrap."
    This function enforces the bootstrap boundary by loading the lens exactly
    once and creating an ExecutionContext for runtime use.

    Args:
        lens_id: The lens identifier (e.g., "edinburgh_finds")

    Returns:
        ExecutionContext with validated lens contract

    Raises:
        LensConfigError: If lens validation fails (fail-fast per architecture)
        FileNotFoundError: If lens file doesn't exist
    """
    # Load lens from disk
    lens_path = Path(__file__).parent.parent / "lenses" / lens_id / "lens.yaml"

    if not lens_path.exists():
        raise FileNotFoundError(
            f"Lens file not found: {lens_path}\n"
            f"Available lenses should be in: engine/lenses/<lens_id>/lens.yaml"
        )

    # Load and validate lens (fail-fast on validation errors)
    vertical_lens = VerticalLens(lens_path)

    # Extract compiled, immutable lens contract (plain dict)
    # Shallow copy for defensive programming
    lens_contract = {
        "mapping_rules": list(vertical_lens.mapping_rules),
        "module_triggers": list(vertical_lens.module_triggers),
        "modules": dict(vertical_lens.domain_modules),
        "facets": dict(vertical_lens.facets),
        "values": list(vertical_lens.values),
        "confidence_threshold": vertical_lens.confidence_threshold,
    }

    # Compute deterministic content hash for reproducibility
    import hashlib
    import json
    canonical_contract = json.dumps(lens_contract, sort_keys=True)
    lens_hash = hashlib.sha256(canonical_contract.encode("utf-8")).hexdigest()

    # Create and return ExecutionContext with lens metadata per docs/target-architecture.md 3.6
    return ExecutionContext(
        lens_id=lens_id,
        lens_contract=lens_contract,
        lens_hash=lens_hash
    )


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
    run_parser.add_argument(
        "--lens",
        type=str,
        default=None,
        help="Lens ID to use (default: from LENS_ID environment variable)",
    )
    run_parser.add_argument(
        "--allow-default-lens",
        action="store_true",
        default=False,
        help="Allow fallback to default lens 'edinburgh_finds' for dev/test (default: False)",
    )

    # Parse arguments
    args = parser.parse_args()

    # Validate command
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "run":
        # Bootstrap: Load lens configuration ONCE at entry point
        # Per docs/target-architecture.md 3.2: Lens loading occurs only during bootstrap
        # Lens resolution precedence per docs/target-architecture.md 3.1:
        # 1. CLI override (--lens)
        # 2. Environment variable (LENS_ID)
        # 3. Application config (engine/config/app.yaml → default_lens)
        # 4. Dev/Test fallback (LR-002 - not implemented yet)

        lens_id = args.lens or os.getenv("LENS_ID")

        # Level 3: Load from config file if not resolved
        if not lens_id:
            config_path = Path(__file__).parent.parent / "config" / "app.yaml"
            if config_path.exists():
                try:
                    # Local import to avoid mandatory dependency
                    import yaml
                    with open(config_path, "r") as f:
                        config = yaml.safe_load(f)
                        if config and isinstance(config, dict):
                            lens_id = config.get("default_lens")
                except Exception as e:
                    print(colorize(f"ERROR: Failed to load config file: {config_path}", Colors.RED))
                    print(f"YAML parsing error: {e}")
                    sys.exit(1)

        # Level 4: Dev/Test fallback (LR-002)
        # Per docs/target-architecture.md 3.1: "Must be explicitly enabled with --allow-default-lens"
        if not lens_id:
            if args.allow_default_lens:
                # Use fallback lens with prominent warning
                lens_id = "edinburgh_finds"
                warning_msg = colorize(
                    "WARNING: Using fallback lens 'edinburgh_finds' (dev/test only)",
                    Colors.YELLOW
                )
                print(warning_msg, file=sys.stderr)
            else:
                # No fallback allowed - fail fast per Invariant 6
                print(colorize("ERROR: No lens specified", Colors.RED))
                print("Provide lens via --lens argument or LENS_ID environment variable")
                print("Example: python -m engine.orchestration.cli run --lens edinburgh_finds \"your query\"")
                sys.exit(1)

        try:
            # Bootstrap lens and create ExecutionContext
            ctx = bootstrap_lens(lens_id)
        except LensConfigError as e:
            print(colorize(f"ERROR: Lens validation failed: {e}", Colors.RED))
            sys.exit(1)
        except FileNotFoundError as e:
            print(colorize(f"ERROR: {e}", Colors.RED))
            sys.exit(1)

        # Create ingestion request
        ingestion_mode = IngestionMode.DISCOVER_MANY
        if args.mode == "resolve_one":
            ingestion_mode = IngestionMode.RESOLVE_ONE

        request = IngestRequest(
            ingestion_mode=ingestion_mode,
            query=args.query,
            persist=args.persist,
        )

        # Execute orchestration with bootstrapped context (async)
        report = asyncio.run(orchestrate(request, ctx=ctx))

        # Format and print report
        formatted = format_report(report)
        print(formatted)

        # Exit successfully
        sys.exit(0)


if __name__ == "__main__":
    main()
