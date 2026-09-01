import io
import os
import tempfile
import zipfile
from unittest.mock import MagicMock, patch
import pytest

from app.database import init_db, get_runs
from app.sync_service import GitHubActionsSync


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_sync_workflow_runs_mock(temp_db):
    mock_runs_response = {
        "workflow_runs": [
            {
                "id": 123456,
                "name": "task-api-ci-cd",
                "head_branch": "main",
                "head_sha": "f1e2d3c",
                "head_commit": {
                    "message": "Add quality gate check",
                    "author": {"name": "Vara Prasad"}
                },
                "status": "completed",
                "conclusion": "success",
                "created_at": "2026-08-30T10:00:00Z",
                "updated_at": "2026-08-30T10:00:30Z",
                "run_started_at": "2026-08-30T10:00:00Z",
                "html_url": "https://github.com/varaprasad7477/task-api-devops-project/actions/runs/123456"
            }
        ]
    }

    syncer = GitHubActionsSync(owner="varaprasad7477", repo="task-api-devops-project", db_path=temp_db)

    with patch("requests.get") as mock_get:
        # Mock runs list response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_runs_response
        mock_get.return_value = mock_resp

        result = syncer.sync_runs(count=5)
        assert result["status"] == "success"
        assert result["synced_count"] == 1

    runs, total = get_runs(db_path=temp_db)
    assert total == 1
    assert runs[0]["github_run_id"] == 123456
    assert runs[0]["branch"] == "main"
    assert runs[0]["quality_gate_passed"] is True


def test_fetch_artifacts_mock(temp_db):
    syncer = GitHubActionsSync(token="fake-token", db_path=temp_db)

    # Create in-memory zip with report.xml and coverage.xml
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("report.xml", """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" tests="8" failures="0" skipped="0" time="0.5">
</testsuite>""")
        z.writestr("coverage.xml", """<?xml version="1.0" ?>
<coverage lines-valid="50" lines-covered="45" line-rate="0.90"></coverage>""")
    zip_bytes = buf.getvalue()

    with patch("requests.get") as mock_get:
        # 1. Artifacts list response
        mock_list_resp = MagicMock()
        mock_list_resp.status_code = 200
        mock_list_resp.json.return_value = {
            "artifacts": [
                {"name": "test-and-coverage-reports", "archive_download_url": "https://api.github.com/download/123"}
            ]
        }

        # 2. Download zip response
        mock_dl_resp = MagicMock()
        mock_dl_resp.status_code = 200
        mock_dl_resp.content = zip_bytes

        mock_get.side_effect = [mock_list_resp, mock_dl_resp]

        metrics = syncer.fetch_run_artifacts(123456)
        assert metrics.get("tests_passed") == 8
        assert metrics.get("coverage_pct") == 90.0


def test_parse_github_url():
    from app.sync_service import parse_github_url

    assert parse_github_url("https://github.com/pallets/flask") == ("pallets", "flask")
    assert parse_github_url("https://github.com/tiangolo/fastapi.git") == ("tiangolo", "fastapi")
    assert parse_github_url("https://github.com/psf/requests/actions") == ("psf", "requests")
    assert parse_github_url("https://github.com/django/django/tree/main") == ("django", "django")
    assert parse_github_url("https://github.com/facebook/react?tab=readme-ov-file#intro") == ("facebook", "react")
    assert parse_github_url("encode/uvicorn") == ("encode", "uvicorn")
    assert parse_github_url("git@github.com:django/django.git") == ("django", "django")
    assert parse_github_url("task-api-devops-project") == ("varaprasad7477", "task-api-devops-project")
    assert parse_github_url("") == ("varaprasad7477", "task-api-devops-project")


def test_sync_commits_fallback_when_no_runs(temp_db):
    syncer = GitHubActionsSync(owner="test", repo="no-actions-repo", db_path=temp_db)

    with patch.object(syncer, "fetch_workflow_runs", return_value=[]), \
         patch.object(syncer, "fetch_recent_commits", return_value=[
             {
                 "sha": "a1b2c3d4e5",
                 "commit": {
                     "message": "Initial commit",
                     "author": {"name": "Dev", "date": "2026-08-31T10:00:00Z"}
                 },
                 "html_url": "https://github.com/test/no-actions-repo/commit/a1b2c3d4e5"
             }
         ]):
        result = syncer.sync_runs(count=5)
        assert result["status"] == "success"
        assert result["synced_count"] == 1

    runs, total = get_runs(repo_name="test/no-actions-repo", db_path=temp_db)
    assert total == 1
    assert runs[0]["commit_sha"] == "a1b2c3d"

