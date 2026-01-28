#!/usr/bin/env python
"""
Live Smoke Test for Orchestration System

This script performs manual verification of the orchestration system with real queries.
Use this to verify the system is working end-to-end with actual API calls.

Usage:
    python scripts/test_orchestration_live.py [--persist] [--verbose]

Options:
    --persist    Persist results to database (default: False)
    --verbose    Show detailed output for each test (default: False)

Prerequisites:
    - API keys configured (SERPER_API_KEY, GOOGLE_PLACES_API_KEY, etc.)
    - Database connection available (if using --persist)
    - Internet connection for API calls

Test Cases:
    1. Category search (broad): "padel courts Edinburgh"
    2. Specific place (high-precision): "Oriam Scotland"
    3. Domain-specific (sports): "swimming pools Edinburgh"
    4. Budget-aware (multiple connectors): "restaurants Edinburgh"

Expected Behavior:
    - All tests should complete without errors
    - Candidates should be found for each query
    - Deduplication should reduce candidate count
    - Connector metrics should show reasonable latency and costs
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass

# Add project root to Python path so we can import engine modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engine.orchestration.planner import orchestrate
from engine.orchestration.types import IngestRequest, IngestionMode


@dataclass
class TestCase:
    """A single test case for smoke testing."""
    name: str
    query: str
    expected_connectors: List[str]
    min_candidates: int
    description: str


# Define test cases
TEST_CASES = [
    TestCase(
        name="Category Search (Broad)",
        query="padel courts Edinburgh",
        expected_connectors=["serper", "google_places", "openstreetmap"],
        min_candidates=5,
        description="Should trigger broad discovery with multiple connectors"
    ),
    TestCase(
        name="Specific Place (High-Precision)",
        query="Oriam Scotland",
        expected_connectors=["google_places"],
        min_candidates=1,
        description="Should use high-precision connector for specific place"
    ),
    TestCase(
        name="Domain-Specific (Sports)",
        query="swimming pools Edinburgh",
        expected_connectors=["sport_scotland", "google_places"],
        min_candidates=3,
        description="Should include domain-specific connector for sports"
    ),
    TestCase(
        name="Multi-Connector Query",
        query="tennis clubs Edinburgh",
        expected_connectors=["serper", "google_places", "sport_scotland"],
        min_candidates=5,
        description="Should trigger multiple connectors with budget awareness"
    ),
]


def run_test_case(test_case: TestCase, persist: bool, verbose: bool) -> Dict[str, Any]:
    """
    Run a single test case.

    Args:
        test_case: The test case to run
        persist: Whether to persist results to database
        verbose: Whether to show detailed output

    Returns:
        Test result dict with status and details
    """
    print(f"\n{'='*80}")
    print(f"Running Test: {test_case.name}")
    print(f"Query: {test_case.query}")
    print(f"Description: {test_case.description}")
    print(f"{'='*80}")

    try:
        # Create ingestion request
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query=test_case.query,
            persist=persist,
        )

        # Execute orchestration
        report = orchestrate(request)

        # Verify results
        result = {
            "test_name": test_case.name,
            "status": "PASS",
            "details": []
        }

        # Check candidates found
        if report['accepted_entities'] < test_case.min_candidates:
            result["status"] = "WARN"
            result["details"].append(
                f"Expected at least {test_case.min_candidates} candidates, "
                f"got {report['accepted_entities']}"
            )

        # Check connectors executed
        executed_connectors = [
            name for name, metrics in report['connectors'].items()
            if metrics.get('executed', False)
        ]

        if verbose:
            print(f"\nExecuted Connectors: {', '.join(executed_connectors)}")
            print(f"Candidates Found: {report['candidates_found']}")
            print(f"Accepted Entities: {report['accepted_entities']}")
            if persist:
                print(f"Persisted to DB: {report.get('persisted_count', 0)}")

        # Check for errors
        if report['errors']:
            result["status"] = "FAIL"
            result["details"].append(f"Errors occurred: {len(report['errors'])} error(s)")
            if verbose:
                for error in report['errors']:
                    print(f"  Error [{error.get('connector')}]: {error.get('error')}")

        # Report status
        status_symbol = "✓" if result["status"] == "PASS" else "✗"
        print(f"\n{status_symbol} Status: {result['status']}")

        if result["details"]:
            print("Details:")
            for detail in result["details"]:
                print(f"  - {detail}")

        return result

    except Exception as e:
        print(f"\n✗ Status: FAIL")
        print(f"Exception: {str(e)}")
        return {
            "test_name": test_case.name,
            "status": "FAIL",
            "details": [f"Exception: {str(e)}"]
        }


def main():
    """Main entry point for smoke test."""
    parser = argparse.ArgumentParser(
        description="Live smoke test for orchestration system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--persist",
        action="store_true",
        help="Persist results to database (default: False)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output for each test (default: False)"
    )

    args = parser.parse_args()

    # Print header
    print("="*80)
    print("ORCHESTRATION SYSTEM - LIVE SMOKE TEST")
    print("="*80)
    print(f"Mode: {'PERSIST' if args.persist else 'DRY-RUN'}")
    print(f"Verbose: {'ON' if args.verbose else 'OFF'}")
    print(f"Test Cases: {len(TEST_CASES)}")

    # Run all test cases
    results = []
    for test_case in TEST_CASES:
        result = run_test_case(test_case, args.persist, args.verbose)
        results.append(result)

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for r in results if r["status"] == "PASS")
    warned = sum(1 for r in results if r["status"] == "WARN")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    print(f"Total Tests: {len(results)}")
    print(f"✓ Passed: {passed}")
    print(f"⚠ Warnings: {warned}")
    print(f"✗ Failed: {failed}")

    # Exit with appropriate code
    if failed > 0:
        print("\n⚠ Some tests failed. Review the output above.")
        sys.exit(1)
    elif warned > 0:
        print("\n⚠ All tests passed with warnings. Review the output above.")
        sys.exit(0)
    else:
        print("\n✓ All tests passed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
