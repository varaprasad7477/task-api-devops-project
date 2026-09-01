from typing import Any, Dict, List, Optional, Tuple
from app.database import get_quality_gate_config
from app.notifications import send_quality_gate_alert


def evaluate_quality_gate(
    run_data: Dict[str, Any],
    config_override: Optional[Dict[str, Any]] = None,
    notify: bool = True,
    db_path: Optional[str] = None
) -> Tuple[bool, List[str], str]:
    """
    Evaluates a CI run against quality gate rules.
    Returns:
      (passed: bool, reasons: List[str], reason_summary: str)
    """
    config = config_override or get_quality_gate_config(db_path)
    min_cov = float(config.get("min_coverage_pct", 80.0))
    max_fails = int(config.get("max_failed_tests", 0))
    max_dur = float(config.get("max_duration_seconds", 300.0))
    webhook_url = config.get("slack_webhook_url")

    cov_pct = float(run_data.get("coverage_pct", 0.0))
    failed_tests = int(run_data.get("tests_failed", 0))
    status = run_data.get("status", "success")
    duration = float(run_data.get("duration_seconds", 0.0))

    reasons: List[str] = []

    # Rule 1: Code Coverage
    if cov_pct < min_cov:
        reasons.append(f"Coverage {cov_pct:.1f}% is below required threshold {min_cov:.1f}%")

    # Rule 2: Test Failures
    if failed_tests > max_fails:
        reasons.append(f"{failed_tests} test failure(s) detected (allowed max: {max_fails})")

    # Rule 3: Workflow status
    if status != "success":
        reasons.append(f"Workflow status is '{status}' (expected 'success')")

    # Rule 4: Max execution duration
    if duration > max_dur:
        reasons.append(f"Duration {duration:.1f}s exceeded limit of {max_dur:.1f}s")

    passed = len(reasons) == 0
    reason_summary = "All quality standards met." if passed else " | ".join(reasons)

    if not passed and notify and webhook_url:
        send_quality_gate_alert(webhook_url, run_data, reasons)

    return passed, reasons, reason_summary
