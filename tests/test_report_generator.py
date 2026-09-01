import os
import tempfile
from datetime import datetime, timezone
import pytest

from app.database import init_db, insert_run
from app.report_generator import calculate_health_score, generate_quality_report


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_calculate_health_score_empty():
    score, grade = calculate_health_score({}, {"min_coverage_pct": 80.0, "max_duration_seconds": 300.0})
    assert score == 0
    assert grade == "N/A"


def test_calculate_health_score_high_performance():
    summary = {
        "total_runs": 20,
        "success_rate_pct": 100.0,
        "avg_coverage_pct": 95.0,
        "quality_gate_pass_rate_pct": 100.0,
        "avg_duration_seconds": 25.0
    }
    config = {"min_coverage_pct": 80.0, "max_duration_seconds": 300.0}
    score, grade = calculate_health_score(summary, config)
    assert score >= 95
    assert grade == "A+"


def test_calculate_health_score_low_performance():
    summary = {
        "total_runs": 10,
        "success_rate_pct": 40.0,
        "avg_coverage_pct": 50.0,
        "quality_gate_pass_rate_pct": 30.0,
        "avg_duration_seconds": 450.0
    }
    config = {"min_coverage_pct": 80.0, "max_duration_seconds": 300.0}
    score, grade = calculate_health_score(summary, config)
    assert score < 60
    assert grade == "F"


def test_generate_quality_report_structured(temp_db):
    # Insert sample runs
    insert_run({
        "repo_name": "test-owner/test-repo",
        "branch": "main",
        "commit_sha": "abc1234",
        "commit_message": "Add test quality check",
        "author": "Alice",
        "status": "success",
        "duration_seconds": 22.0,
        "tests_passed": 12,
        "tests_failed": 0,
        "coverage_pct": 92.0,
        "quality_gate_passed": True,
        "quality_gate_reason": "All quality standards met."
    }, db_path=temp_db)

    report = generate_quality_report("test-owner/test-repo", days=30, db_path=temp_db)

    assert report["repo_name"] == "test-owner/test-repo"
    assert report["overall_verdict"] == "PASSED"
    assert report["health_score"] > 80
    assert len(report["rule_evaluations"]) == 4
    assert len(report["recent_runs"]) == 1
    assert "CI/CD Quality Gate Audit Report" in report["markdown_report"]
    assert "# 🛡️" in report["markdown_report"]
