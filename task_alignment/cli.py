#!/usr/bin/env python3
"""CLI interface for Task Alignment System."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .checker import check_task_alignment
from .models import AlignmentStatus


def main():
    parser = argparse.ArgumentParser(
        description="Task Alignment System - Validate tasks against sources of truth",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check a task against all sources
  python -m task_alignment "Implement Dissent Language Pattern Matcher"

  # Check with verbose output
  python -m task_alignment -v "Add interruption detection to analytics"

  # Check only specific sources
  python -m task_alignment --checks blueprint,codebase "Create new API endpoint"

  # Output as JSON
  python -m task_alignment --json "Fix tone shift detector"

  # Specify custom repo path
  python -m task_alignment --repo /path/to/repo "Update frontend component"
        """
    )

    parser.add_argument(
        "task",
        help="Task description to validate"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed progress"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of markdown"
    )

    parser.add_argument(
        "--checks",
        type=str,
        help="Comma-separated list of checks to run: blueprint,codebase,roadmap,requirements,coherence"
    )

    parser.add_argument(
        "--repo",
        type=str,
        help="Path to local code repository"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Write output to file"
    )

    args = parser.parse_args()

    checks = None
    if args.checks:
        checks = [c.strip() for c in args.checks.split(",")]

    repo_path = Path(args.repo) if args.repo else None

    try:
        report = check_task_alignment(
            task_description=args.task,
            repo_path=repo_path,
            checks=checks,
            verbose=args.verbose,
        )

        if args.json:
            output = json.dumps(report.to_dict(), indent=2)
        else:
            output = report.to_markdown()

        if args.output:
            Path(args.output).write_text(output)
            print(f"Report written to: {args.output}")
        else:
            print(output)

        if report.overall_status == AlignmentStatus.CONFLICTS:
            sys.exit(1)
        elif report.overall_status == AlignmentStatus.MISSING_INFO:
            sys.exit(2)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()
