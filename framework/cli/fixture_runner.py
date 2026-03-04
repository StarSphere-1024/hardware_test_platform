#!/usr/bin/env python3
"""
Command-line interface for running fixture tests.

Usage:
    python -m framework.cli.fixture_runner <fixture_file> [options]

Examples:
    python -m framework.cli.fixture_runner fixtures/examples/smoke_test.json
    python -m framework.cli.fixture_runner fixtures/examples/full_hardware_test.json --verbose
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Run hardware test fixtures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s fixtures/examples/smoke_test.json
  %(prog)s fixtures/examples/full_hardware_test.json --verbose
  %(prog)s fixtures/examples/stress_test.json --loop-count 5
        """
    )

    parser.add_argument(
        "fixture",
        type=Path,
        help="Path to fixture JSON file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--cases-dir",
        type=Path,
        default=Path("cases"),
        help="Directory containing case files (default: cases/)"
    )
    parser.add_argument(
        "--functions-dir",
        type=Path,
        default=Path("functions"),
        help="Directory containing test functions (default: functions/)"
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=Path("fixtures"),
        help="Directory containing fixture files (default: fixtures/)"
    )
    parser.add_argument(
        "--loop-count",
        type=int,
        default=None,
        help="Override fixture loop count"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports"),
        help="Directory for output reports (default: reports/)"
    )

    args = parser.parse_args()

    # Validate fixture file exists
    if not args.fixture.exists():
        print(f"Error: Fixture file not found: {args.fixture}")
        sys.exit(1)

    # Import and run
    from framework.core.fixture_runner import FixtureRunner

    print(f"Loading fixture: {args.fixture}")

    runner = FixtureRunner(
        functions_dir=str(args.functions_dir),
        cases_dir=str(args.cases_dir),
        fixtures_dir=str(args.fixtures_dir),
    )

    # Load fixture configuration
    fixture_config = runner.load_fixture(str(args.fixture))

    if not fixture_config:
        print(f"Error: Failed to load fixture configuration")
        sys.exit(1)

    # Override loop count if specified
    if args.loop_count is not None:
        fixture_config["loop"] = True
        fixture_config["loop_count"] = args.loop_count

    # Run the fixture
    result = runner.run(fixture_config)

    if result:
        print(f"\n{'='*60}")
        print(f"Fixture: {result.fixture_name}")
        print(f"Status: {result.status.upper()}")
        print(f"Duration: {result.duration:.2f}s")
        print(f"Passed: {result.total_pass}, Failed: {result.total_fail}")

        if result.error:
            print(f"Error: {result.error}")

        # Exit with appropriate code
        sys.exit(0 if result.success else 1)
    else:
        print("Failed to run fixture")
        sys.exit(1)


if __name__ == "__main__":
    main()
