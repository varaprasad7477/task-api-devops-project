import os
import tempfile
import pytest
from app.database import (
    init_db,
    insert_run,
    get_runs,
    get_run_by_id,
    get_summary_stats,
    get_quality_gate_config,
    update_quality_gate_config
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_init_and_config(temp_db):
    cfg = get_quality_gate_config(temp_db)
    assert cfg["min_coverage_pct"] == 80.0
    assert cfg["max_failed_tests"] == 0

    updated = update_quality_gate_config(
        min_coverage_pct=85.0,
        max_failed_tests=1,
        max_duration_seconds=120.0,
        slack_webhook_url="https://hooks.slack.com/services/test",
        db_path=temp_db
    )
    assert updated["min_coverage_pct"] == 85.0
    assert updated["max_failed_tests"] == 1
    assert updated["slack_webhook_url"] == "https://hooks.slack.com/services/test"


def test_insert_and_get_runs(temp_db):
    run_data = {
        "github_run_id": 101,
        "workflow_name": "task-api-ci-cd",
        "branch": "main",
        "commit_sha": "abc1234",
        "commit_message": "Add test endpoint",
        "author": "Tester",
        "status": "success",
        "duration_seconds": 25.4,
        "tests_passed": 8,
        "tests_failed": 0,
        "coverage_pct": 95.0,
        "quality_gate_passed": True,
        "quality_gate_reason": "All quality standards met."
    }

    run_id = insert_run(run_data, db_path=temp_db)
    assert run_id > 0

    run = get_run_by_id(run_id, db_path=temp_db)
    assert run is not None
    assert run["branch"] == "main"
    assert run["coverage_pct"] == 95.0
    assert run["quality_gate_passed"] is True

    # Test update existing by github_run_id
    run_data["coverage_pct"] = 96.5
    updated_run_id = insert_run(run_data, db_path=temp_db)
    assert updated_run_id == run_id

    run_updated = get_run_by_id(run_id, db_path=temp_db)
    assert run_updated["coverage_pct"] == 96.5


def test_get_runs_filtering(temp_db):
    # Insert multiple runs
    insert_run({
        "workflow_name": "ci", "branch": "main", "status": "success",
        "coverage_pct": 90.0, "quality_gate_passed": True
    }, db_path=temp_db)

    insert_run({
        "workflow_name": "ci", "branch": "feature/auth", "status": "failure",
        "coverage_pct": 65.0, "quality_gate_passed": False
    }, db_path=temp_db)

    # All runs
    runs, total = get_runs(db_path=temp_db)
    assert total == 2
    assert len(runs) == 2

    # Filter by branch
    main_runs, main_total = get_runs(branch="main", db_path=temp_db)
    assert main_total == 1
    assert main_runs[0]["branch"] == "main"

    # Filter by status
    fail_runs, fail_total = get_runs(status="failure", db_path=temp_db)
    assert fail_total == 1
    assert fail_runs[0]["status"] == "failure"

    # Filter by quality gate
    tripped_runs, tripped_total = get_runs(quality_gate_passed=False, db_path=temp_db)
    assert tripped_total == 1
    assert tripped_runs[0]["quality_gate_passed"] is False


def test_summary_stats(temp_db):
    # Empty DB
    summary_empty = get_summary_stats(db_path=temp_db)
    assert summary_empty["total_runs"] == 0

    # Populate runs
    insert_run({
        "workflow_name": "ci", "branch": "main", "status": "success",
        "duration_seconds": 20.0, "coverage_pct": 90.0, "quality_gate_passed": True
    }, db_path=temp_db)

    insert_run({
        "workflow_name": "ci", "branch": "main", "status": "failure",
        "duration_seconds": 30.0, "coverage_pct": 70.0, "quality_gate_passed": False
    }, db_path=temp_db)

    summary = get_summary_stats(days=30, db_path=temp_db)
    assert summary["total_runs"] == 2
    assert summary["success_rate_pct"] == 50.0
    assert summary["failure_rate_pct"] == 50.0
    assert summary["avg_coverage_pct"] == 80.0
    assert summary["avg_duration_seconds"] == 25.0
    assert summary["quality_gate_pass_rate_pct"] == 50.0
    assert summary["latest_run"] is not None
