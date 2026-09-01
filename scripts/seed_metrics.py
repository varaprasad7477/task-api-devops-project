#!/usr/bin/env python3
"""
Seed script to populate SQLite database with realistic historical CI run data.
Demonstrates trend lines, pass/fail ratios, coverage progression, and quality gate triggers.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import init_db, insert_run, get_db_connection
from app.quality_gate import evaluate_quality_gate

SAMPLE_RUNS = [
    {
        "days_ago": 28,
        "branch": "main",
        "commit_sha": "a1b2c3d",
        "commit_message": "Initial commit of Task API",
        "author": "Vara Prasad",
        "status": "success",
        "duration_seconds": 38.2,
        "tests_passed": 4,
        "tests_failed": 0,
        "tests_skipped": 0,
        "coverage_pct": 68.0,
    },
    {
        "days_ago": 25,
        "branch": "feature/docker",
        "commit_sha": "b2c3d4e",
        "commit_message": "Add Dockerfile and Compose setup",
        "author": "Vara Prasad",
        "status": "success",
        "duration_seconds": 42.1,
        "tests_passed": 5,
        "tests_failed": 0,
        "tests_skipped": 0,
        "coverage_pct": 72.5,
    },
    {
        "days_ago": 22,
        "branch": "main",
        "commit_sha": "c3d4e5f",
        "commit_message": "Merge pull request #1 from docker-setup",
        "author": "Vara Prasad",
        "status": "success",
        "duration_seconds": 35.6,
        "tests_passed": 5,
        "tests_failed": 0,
        "tests_skipped": 0,
        "coverage_pct": 73.0,
    },
    {
        "days_ago": 18,
        "branch": "feature/validation",
        "commit_sha": "d4e5f6a",
        "commit_message": "Add request validation for title and boolean done",
        "author": "Vara Prasad",
        "status": "failure",
        "duration_seconds": 30.4,
        "tests_passed": 6,
        "tests_failed": 1,
        "tests_skipped": 0,
        "coverage_pct": 82.0,
    },
    {
        "days_ago": 17,
        "branch": "feature/validation",
        "commit_sha": "e5f6a7b",
        "commit_message": "Fix validation edge case for whitespace strings",
        "author": "Vara Prasad",
        "status": "success",
        "duration_seconds": 31.8,
        "tests_passed": 7,
        "tests_failed": 0,
        "tests_skipped": 0,
        "coverage_pct": 84.5,
    },
    {
        "days_ago": 15,
        "branch": "main",
        "commit_sha": "f6a7b8c",
        "commit_message": "Merge pull request #2: validation logic",
        "author": "Vara Prasad",
        "status": "success",
        "duration_seconds": 29.4,
        "tests_passed": 7,
        "tests_failed": 0,
        "tests_skipped": 0,
        "coverage_pct": 84.5,
    },
    {
        "days_ago": 12,
        "branch": "feature/ghcr-deploy",
        "commit_sha": "a7b8c9d",
        "commit_message": "Configure GHCR publish step in GitHub Actions",
        "author": "Vara Prasad",
        "status": "success",
        "duration_seconds": 54.2,
        "tests_passed": 7,
        "tests_failed": 0,
        "tests_skipped": 0,
        "coverage_pct": 84.5,
    },
    {
        "days_ago": 9,
        "branch": "main",
        "commit_sha": "b8c9d0e",
        "commit_message": "Publish docker image on main push",
        "author": "Vara Prasad",
        "status": "success",
        "duration_seconds": 48.0,
        "tests_passed": 7,
        "tests_failed": 0,
        "tests_skipped": 0,
        "coverage_pct": 84.5,
    },
    {
        "days_ago": 6,
        "branch": "feature/uncovered-endpoint",
        "commit_sha": "c9d0e1f",
        "commit_message": "Add experimental task export without full tests",
        "author": "Vara Prasad",
        "status": "success",
        "duration_seconds": 26.5,
        "tests_passed": 7,
        "tests_failed": 0,
        "tests_skipped": 0,
        "coverage_pct": 74.0,  # Quality Gate Tripped!
    },
    {
        "days_ago": 4,
        "branch": "feature/quality-gate",
        "commit_sha": "d0e1f2a",
        "commit_message": "Implement comprehensive test suite for all endpoints",
        "author": "Vara Prasad",
        "status": "success",
        "duration_seconds": 24.1,
        "tests_passed": 8,
        "tests_failed": 0,
        "tests_skipped": 0,
        "coverage_pct": 94.0,
    },
    {
        "days_ago": 2,
        "branch": "feature/quality-gate",
        "commit_sha": "e1f2a3b",
        "commit_message": "Add pytest-cov, JUnit report generation, and metrics sync",
        "author": "Vara Prasad",
        "status": "success",
        "duration_seconds": 22.8,
        "tests_passed": 8,
        "tests_failed": 0,
        "tests_skipped": 0,
        "coverage_pct": 98.2,
    },
    {
        "days_ago": 0,
        "branch": "main",
        "commit_sha": "f2a3b4c",
        "commit_message": "Merge pull request #3: CI/CD Quality Gate & Metrics Dashboard",
        "author": "Vara Prasad",
        "status": "success",
        "duration_seconds": 21.5,
        "tests_passed": 8,
        "tests_failed": 0,
        "tests_skipped": 0,
        "coverage_pct": 100.0,
    },
]


def seed(db_path=None, force=False):
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    if not force:
        cursor.execute("SELECT COUNT(*) FROM runs")
        if cursor.fetchone()[0] > 0:
            print("Database already contains records. Use force=True or run seed directly with --force to overwrite.")
            conn.close()
            return

    cursor.execute("DELETE FROM runs")
    conn.commit()
    conn.close()

    now = datetime.now(timezone.utc)
    base_run_id = 9001000

    print(f"Seeding {len(SAMPLE_RUNS)} sample CI runs into database...")
    for idx, item in enumerate(SAMPLE_RUNS):
        created_dt = now - timedelta(days=item["days_ago"], hours=idx * 2)
        run_data = {
            "github_run_id": base_run_id + idx,
            "workflow_name": "task-api-ci-cd",
            "branch": item["branch"],
            "commit_sha": item["commit_sha"],
            "commit_message": item["commit_message"],
            "author": item["author"],
            "status": item["status"],
            "duration_seconds": item["duration_seconds"],
            "tests_passed": item["tests_passed"],
            "tests_failed": item["tests_failed"],
            "tests_skipped": item["tests_skipped"],
            "tests_total": item["tests_passed"] + item["tests_failed"] + item["tests_skipped"],
            "coverage_pct": item["coverage_pct"],
            "created_at": created_dt.isoformat(),
            "raw_details": {
                "run_number": idx + 1,
                "html_url": f"https://github.com/varaprasad7477/task-api-devops-project/actions/runs/{base_run_id + idx}"
            }
        }

        # Evaluate quality gate
        qg_passed, qg_reasons, qg_summary = evaluate_quality_gate(run_data, notify=False, db_path=db_path)
        run_data["quality_gate_passed"] = qg_passed
        run_data["quality_gate_reason"] = qg_summary

        insert_run(run_data, db_path=db_path)

    print("[SUCCESS] Seed completed successfully!")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    force_flag = "--force" in sys.argv
    seed(force=force_flag)
