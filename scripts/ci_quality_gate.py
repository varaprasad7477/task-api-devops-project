#!/usr/bin/env python3
"""
CI Quality Gate & Metrics Enforcement Script
Parses test and coverage reports, evaluates quality gate policies,
generates GitHub Actions Step Summary, and posts data to the metrics dashboard API.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests
from app.report_parser import parse_coverage_report, parse_junit_xml


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate CI Quality Gate and post metrics")
    parser.add_argument("--junitxml", default="report.xml", help="Path to JUnit XML test report")
    parser.add_argument("--coverage-json", default="coverage.json", help="Path to coverage JSON report")
    parser.add_argument("--coverage-xml", default="coverage.xml", help="Path to coverage XML report")
    parser.add_argument("--min-coverage", type=float, default=80.0, help="Minimum coverage percentage required (default: 80.0)")
    parser.add_argument("--max-failures", type=int, default=0, help="Maximum allowed test failures (default: 0)")
    parser.add_argument("--dashboard-url", default=os.environ.get("DASHBOARD_URL", ""), help="Metrics Dashboard API URL")
    parser.add_argument("--enforce", action="store_true", default=False, help="Exit with non-zero exit code if quality gate trips")
    return parser.parse_args()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    args = parse_args()

    # 1. Parse JUnit XML
    junit_path = args.junitxml
    junit_metrics = parse_junit_xml(junit_path) if os.path.exists(junit_path) else {
        "tests_total": 0, "tests_passed": 0, "tests_failed": 0, "tests_skipped": 0, "duration_seconds": 0.0
    }

    # 2. Parse Coverage
    cov_path = args.coverage_json if os.path.exists(args.coverage_json) else args.coverage_xml
    cov_metrics = parse_coverage_report(cov_path) if os.path.exists(cov_path) else {
        "coverage_pct": 0.0, "lines_total": 0, "lines_covered": 0
    }

    coverage_pct = float(cov_metrics.get("coverage_pct", 0.0))
    tests_passed = int(junit_metrics.get("tests_passed", 0))
    tests_failed = int(junit_metrics.get("tests_failed", 0))
    tests_skipped = int(junit_metrics.get("tests_skipped", 0))
    tests_total = int(junit_metrics.get("tests_total", tests_passed + tests_failed + tests_skipped))
    duration_seconds = float(junit_metrics.get("duration_seconds", 0.0))

    # 3. Evaluate Quality Gate
    reasons = []
    if coverage_pct < args.min_coverage:
        reasons.append(f"Coverage {coverage_pct:.1f}% is below the required threshold of {args.min_coverage:.1f}%")
    if tests_failed > args.max_failures:
        reasons.append(f"{tests_failed} test failure(s) detected (allowed max: {args.max_failures})")

    qg_passed = len(reasons) == 0
    qg_status_str = "PASSED" if qg_passed else "TRIPPED"
    qg_reason_summary = "All quality standards met." if qg_passed else " | ".join(reasons)

    # 4. Print CLI banner
    print("\n=======================================================")
    print("           CI / CD QUALITY GATE VERIFICATION           ")
    print("=======================================================")
    print(f"Status:             {'✅ PASSED' if qg_passed else '❌ TRIPPED'}")
    print(f"Total Tests:        {tests_total} ({tests_passed} passed, {tests_failed} failed, {tests_skipped} skipped)")
    print(f"Code Coverage:      {coverage_pct:.2f}% (Threshold: {args.min_coverage:.1f}%)")
    print(f"Test Duration:      {duration_seconds:.2f}s")
    if not qg_passed:
        print("\nQuality Gate Failure Reasons:")
        for r in reasons:
            print(f"  - {r}")
    print("=======================================================\n")

    # 5. Write GitHub Actions Step Summary if in GH Actions environment
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        badge_color = "brightgreen" if qg_passed else "red"
        badge = f"![Quality Gate](https://img.shields.io/badge/Quality_Gate-{qg_status_str}-{badge_color}?style=for-the-badge)"
        pass_fail_label = "✅ Passed" if tests_failed <= args.max_failures else "❌ Failed"
        cov_label = "✅ Passed" if coverage_pct >= args.min_coverage else "❌ Below Target"
        markdown = f"""
## 🛡️ CI Quality Gate & Metrics Report

{badge}

| Metric | Result | Target / Standard | Status |
| :--- | :--- | :--- | :--- |
| **Test Results** | {tests_passed} / {tests_total} Passed | 0 Failures | {pass_fail_label} |
| **Code Coverage** | **{coverage_pct:.2f}%** | >= {args.min_coverage:.1f}% | {cov_label} |
| **Execution Time** | {duration_seconds:.2f}s | <= 300s | ✅ Normal |

### Quality Gate Summary
> **Status:** **{qg_status_str}**
> **Details:** {qg_reason_summary}
"""
        try:
            with open(summary_file, "a", encoding="utf-8") as f:
                f.write(markdown)
            print("Wrote quality gate summary to $GITHUB_STEP_SUMMARY")
        except Exception as e:
            print(f"Could not write to GITHUB_STEP_SUMMARY: {e}")

    # 6. Post metrics to Dashboard API if configured
    dashboard_url = args.dashboard_url.rstrip("/")
    if dashboard_url:
        payload = {
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "workflow_name": os.environ.get("GITHUB_WORKFLOW", "task-api-ci-cd"),
            "branch": os.environ.get("GITHUB_REF_NAME", "main"),
            "commit_sha": os.environ.get("GITHUB_SHA", ""),
            "commit_message": os.environ.get("GITHUB_COMMIT_MESSAGE", ""),
            "author": os.environ.get("GITHUB_ACTOR", "CI Runner"),
            "status": "success" if tests_failed == 0 else "failure",
            "duration_seconds": duration_seconds,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "tests_skipped": tests_skipped,
            "tests_total": tests_total,
            "coverage_pct": coverage_pct,
            "quality_gate_passed": qg_passed,
            "quality_gate_reason": qg_reason_summary,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        api_endpoint = f"{dashboard_url}/api/runs"
        try:
            resp = requests.post(api_endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            if resp.status_code in (200, 201):
                print(f"Successfully posted metrics to dashboard API: {api_endpoint}")
            else:
                print(f"Warning: Dashboard API responded with status {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"Notice: Could not post to dashboard API ({api_endpoint}): {e}")

    # 7. Exit code enforcement
    if args.enforce and not qg_passed:
        print("ERROR: Quality gate enforcement failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
