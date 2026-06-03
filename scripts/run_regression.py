#!/usr/bin/env python3
"""Run Phase 2 regression suite against the API."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests" / "regression"))

from report import run_regression  # noqa: E402


def main() -> None:
    api_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    cases_dir = ROOT / "tests" / "regression" / "cases"
    report = run_regression(api_url, cases_dir)
    print(report.format_summary())
    sys.exit(0 if report.passes_targets() else 1)


if __name__ == "__main__":
    main()
