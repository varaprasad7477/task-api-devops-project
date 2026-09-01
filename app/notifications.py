import json
import logging
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


def send_quality_gate_alert(
    webhook_url: str,
    run_data: Dict[str, Any],
    reasons: List[str],
    timeout: int = 5
) -> bool:
    """
    Sends a formatted Slack or generic Webhook alert when a Quality Gate trips.
    Returns True if sent successfully (HTTP 200/204), False otherwise.
    """
    if not webhook_url:
        return False

    workflow_name = run_data.get("workflow_name", "task-api-ci-cd")
    branch = run_data.get("branch", "main")
    commit_sha = (run_data.get("commit_sha") or "unknown")[:7]
    author = run_data.get("author", "CI Pipeline")
    coverage_pct = run_data.get("coverage_pct", 0.0)
    tests_passed = run_data.get("tests_passed", 0)
    tests_failed = run_data.get("tests_failed", 0)
    duration_seconds = run_data.get("duration_seconds", 0.0)
    github_run_id = run_data.get("github_run_id")

    reasons_text = "\n".join(f"• {r}" for r in reasons) if reasons else "• Quality gate standards threshold breached."

    # Format Slack Blocks payload
    payload = {
        "text": f":rotating_light: *Quality Gate Tripped* for `{workflow_name}` on `{branch}` ({commit_sha})",
        "attachments": [
            {
                "color": "#e11d48",  # Rose/Red
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*Quality Gate Failed for {workflow_name}*\n"
                                f"*Branch:* `{branch}` | *Commit:* `{commit_sha}` | *Author:* {author}\n"
                                f"*Status:* Tests ({tests_passed} passed, {tests_failed} failed) | "
                                f"*Coverage:* {coverage_pct}% | *Duration:* {duration_seconds}s"
                            )
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Triggered Policies:*\n{reasons_text}"
                        }
                    }
                ]
            }
        ]
    }

    if github_run_id:
        payload["attachments"][0]["blocks"].append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"GitHub Actions Run ID: *{github_run_id}*"
                }
            ]
        })

    try:
        resp = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout)
        if resp.status_code in (200, 204):
            logger.info("Quality gate alert sent successfully to webhook.")
            return True
        logger.warning(f"Webhook returned status code {resp.status_code}: {resp.text}")
        return False
    except Exception as e:
        logger.error(f"Failed to send webhook alert: {str(e)}")
        return False
