from unittest.mock import patch, MagicMock
from app.notifications import send_quality_gate_alert


def test_send_alert_empty_url():
    assert send_quality_gate_alert("", {}, []) is False


@patch("requests.post")
def test_send_alert_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    run_data = {
        "workflow_name": "task-api-ci-cd",
        "branch": "main",
        "commit_sha": "abc123456",
        "author": "Vara Prasad",
        "coverage_pct": 74.0,
        "tests_passed": 7,
        "tests_failed": 1,
        "duration_seconds": 25.0,
        "github_run_id": 888888
    }
    reasons = ["Coverage 74.0% is below 80.0%", "1 test failure"]

    result = send_quality_gate_alert("https://hooks.slack.com/services/test", run_data, reasons)
    assert result is True
    mock_post.assert_called_once()


@patch("requests.post")
def test_send_alert_http_failure(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    mock_post.return_value = mock_resp

    run_data = {"workflow_name": "task-api-ci-cd"}
    result = send_quality_gate_alert("https://hooks.slack.com/services/test", run_data, ["Reason"])
    assert result is False


@patch("requests.post")
def test_send_alert_exception(mock_post):
    mock_post.side_effect = Exception("Network connection timeout")

    run_data = {"workflow_name": "task-api-ci-cd"}
    result = send_quality_gate_alert("https://hooks.slack.com/services/test", run_data, ["Reason"])
    assert result is False
