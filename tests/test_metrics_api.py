import os
import tempfile
import pytest
from app.main import create_app


@pytest.fixture
def client_with_db():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    app = create_app(db_path=db_path)
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client

    if os.path.exists(db_path):
        os.remove(db_path)


def test_dashboard_page_render(client_with_db):
    res = client_with_db.get("/")
    assert res.status_code == 200
    assert b"Quality Gate" in res.data

    res2 = client_with_db.get("/dashboard")
    assert res2.status_code == 200


def test_ingest_and_get_runs_api(client_with_db):
    payload = {
        "workflow_name": "task-api-ci-cd",
        "branch": "main",
        "commit_sha": "1234567",
        "commit_message": "Test commit",
        "author": "CI Runner",
        "status": "success",
        "duration_seconds": 22.1,
        "tests_passed": 8,
        "tests_failed": 0,
        "coverage_pct": 94.0
    }

    res_post = client_with_db.post("/api/runs", json=payload)
    assert res_post.status_code == 201
    body = res_post.get_json()
    assert body["status"] == "ok"
    assert body["run"]["quality_gate_passed"] is True
    assert body["run"]["coverage_pct"] == 94.0

    # Get runs
    res_get = client_with_db.get("/api/runs")
    assert res_get.status_code == 200
    runs_data = res_get.get_json()
    assert runs_data["total_count"] == 1
    assert len(runs_data["runs"]) == 1

    # Get single run
    run_id = body["run_id"]
    res_single = client_with_db.get(f"/api/runs/{run_id}")
    assert res_single.status_code == 200
    assert res_single.get_json()["run"]["id"] == run_id

    # Non-existent run
    res_404 = client_with_db.get("/api/runs/99999")
    assert res_404.status_code == 404


def test_summary_api(client_with_db):
    # Ingest 1 pass, 1 tripped
    client_with_db.post("/api/runs", json={
        "workflow_name": "task-api-ci-cd", "branch": "main", "status": "success",
        "tests_passed": 8, "tests_failed": 0, "coverage_pct": 90.0, "duration_seconds": 20.0
    })
    client_with_db.post("/api/runs", json={
        "workflow_name": "task-api-ci-cd", "branch": "feature/test", "status": "success",
        "tests_passed": 8, "tests_failed": 0, "coverage_pct": 70.0, "duration_seconds": 25.0
    })

    res = client_with_db.get("/api/summary")
    assert res.status_code == 200
    summary = res.get_json()
    assert summary["total_runs"] == 2
    assert summary["avg_coverage_pct"] == 80.0
    assert summary["quality_gate_pass_rate_pct"] == 50.0
    assert len(summary["branches"]) == 2


def test_quality_gate_config_api(client_with_db):
    res = client_with_db.get("/api/quality-gate/config")
    assert res.status_code == 200
    cfg = res.get_json()
    assert cfg["min_coverage_pct"] == 80.0

    update_payload = {
        "min_coverage_pct": 88.0,
        "max_failed_tests": 0,
        "max_duration_seconds": 180.0,
        "slack_webhook_url": "https://hooks.slack.com/services/abc"
    }
    res_put = client_with_db.put("/api/quality-gate/config", json=update_payload)
    assert res_put.status_code == 200
    updated_cfg = res_put.get_json()
    assert updated_cfg["min_coverage_pct"] == 88.0
    assert updated_cfg["slack_webhook_url"] == "https://hooks.slack.com/services/abc"


def test_test_webhook_api_error_when_no_url(client_with_db):
    res = client_with_db.post("/api/quality-gate/test-webhook", json={})
    assert res.status_code == 400


def test_test_webhook_api_success(client_with_db):
    from unittest.mock import patch
    with patch("app.main.send_quality_gate_alert", return_value=True):
        res = client_with_db.post("/api/quality-gate/test-webhook", json={"webhook_url": "https://hooks.slack.com/test"})
        assert res.status_code == 200
        assert res.get_json()["status"] == "success"


def test_sync_api_endpoint(client_with_db):
    from unittest.mock import patch, MagicMock
    with patch("app.sync_service.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"workflow_runs": []}
        mock_get.return_value = mock_resp

        res = client_with_db.post("/api/sync", json={"owner": "test", "repo": "test", "count": 5})
        assert res.status_code == 200
        assert res.get_json()["status"] == "success"


def test_analyze_and_repositories_endpoints(client_with_db):
    from unittest.mock import patch, MagicMock

    with patch("app.sync_service.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "workflow_runs": [
                {
                    "id": 9911,
                    "name": "CI",
                    "head_branch": "main",
                    "status": "completed",
                    "conclusion": "success",
                    "created_at": "2026-08-31T10:00:00Z",
                    "updated_at": "2026-08-31T10:00:20Z"
                }
            ],
            "description": "FastAPI framework",
            "stargazers_count": 75000,
            "forks_count": 6000,
            "language": "Python",
            "default_branch": "master"
        }
        mock_get.return_value = mock_resp

        # Analyze
        res_analyze = client_with_db.post("/api/analyze", json={"url": "https://github.com/tiangolo/fastapi"})
        assert res_analyze.status_code == 200
        data = res_analyze.get_json()
        assert data["repo_name"] == "tiangolo/fastapi"
        assert data["synced_count"] == 1

        # List repositories
        res_repos = client_with_db.get("/api/repositories")
        assert res_repos.status_code == 200
        repos_data = res_repos.get_json()
        assert any(r["repo_name"] == "tiangolo/fastapi" for r in repos_data["repositories"])


def test_get_report_api(client_with_db):
    # Ingest a sample run
    client_with_db.post("/api/runs", json={
        "repo_name": "test/report-repo",
        "workflow_name": "CI",
        "branch": "main",
        "status": "success",
        "tests_passed": 15,
        "tests_failed": 0,
        "coverage_pct": 89.5,
        "duration_seconds": 32.0
    })

    # JSON report
    res_json = client_with_db.get("/api/report?repo=test/report-repo")
    assert res_json.status_code == 200
    report = res_json.get_json()
    assert report["repo_name"] == "test/report-repo"
    assert report["overall_verdict"] == "PASSED"
    assert report["health_score"] >= 80

    # Markdown report
    res_md = client_with_db.get("/api/report?repo=test/report-repo&format=markdown")
    assert res_md.status_code == 200
    assert b"# \xf0\x9f\x9b\xa1\xef\xb8\x8f CI/CD Quality Gate Audit Report" in res_md.data or b"Quality Gate Audit Report" in res_md.data

