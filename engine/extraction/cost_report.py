"""
LLM cost report CLI.

Provides a command-line interface for viewing LLM usage and cost breakdown
from the global usage tracker.
"""

import argparse

from engine.extraction.llm_cost import get_usage_tracker, format_cost_report


def main() -> int:
    """
    CLI entry point for LLM cost report.

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="View LLM usage and cost report for extraction engine"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset usage tracker after displaying report",
    )

    args = parser.parse_args()

    try:
        tracker = get_usage_tracker()
        report = format_cost_report(tracker)
        print(report)

        if args.reset:
            # Reset tracker by clearing records
            tracker.usage_records.clear()
            print("\nUsage tracker has been reset.")

        return 0

    except Exception as exc:
        print(f"Error generating cost report: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
