from unittest.mock import patch
from app.quality_gate import evaluate_quality_gate


def test_quality_gate_passed():
    run_data = {
        "status": "success",
        "coverage_pct": 92.0,
        "tests_failed": 0,
        "duration_seconds": 35.0
    }
    config = {
        "min_coverage_pct": 80.0,
        "max_failed_tests": 0,
        "max_duration_seconds": 300.0
    }
    passed, reasons, summary = evaluate_quality_gate(run_data, config_override=config, notify=False)
    assert passed is True
    assert len(reasons) == 0
    assert summary == "All quality standards met."


def test_quality_gate_tripped_by_coverage():
    run_data = {
        "status": "success",
        "coverage_pct": 74.5,
        "tests_failed": 0,
        "duration_seconds": 30.0
    }
    config = {
        "min_coverage_pct": 80.0,
        "max_failed_tests": 0,
        "max_duration_seconds": 300.0
    }
    passed, reasons, summary = evaluate_quality_gate(run_data, config_override=config, notify=False)
    assert passed is False
    assert any("Coverage 74.5% is below required threshold" in r for r in reasons)


def test_quality_gate_tripped_by_failures_and_status():
    run_data = {
        "status": "failure",
        "coverage_pct": 85.0,
        "tests_failed": 2,
        "duration_seconds": 30.0
    }
    config = {
        "min_coverage_pct": 80.0,
        "max_failed_tests": 0,
        "max_duration_seconds": 300.0
    }
    passed, reasons, summary = evaluate_quality_gate(run_data, config_override=config, notify=False)
    assert passed is False
    assert len(reasons) == 2
    assert any("2 test failure(s) detected" in r for r in reasons)
    assert any("Workflow status is 'failure'" in r for r in reasons)


def test_quality_gate_tripped_by_duration():
    run_data = {
        "status": "success",
        "coverage_pct": 85.0,
        "tests_failed": 0,
        "duration_seconds": 450.0
    }
    config = {
        "min_coverage_pct": 80.0,
        "max_failed_tests": 0,
        "max_duration_seconds": 300.0
    }
    passed, reasons, summary = evaluate_quality_gate(run_data, config_override=config, notify=False)
    assert passed is False
    assert any("Duration 450.0s exceeded limit" in r for r in reasons)


@patch("app.quality_gate.send_quality_gate_alert")
def test_quality_gate_notification_trigger(mock_alert):
    run_data = {
        "status": "success",
        "coverage_pct": 60.0,
        "tests_failed": 0,
        "duration_seconds": 20.0
    }
    config = {
        "min_coverage_pct": 80.0,
        "max_failed_tests": 0,
        "max_duration_seconds": 300.0,
        "slack_webhook_url": "https://hooks.slack.com/services/mock"
    }
    passed, _, _ = evaluate_quality_gate(run_data, config_override=config, notify=True)
    assert passed is False
    mock_alert.assert_called_once()
