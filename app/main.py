import os
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, jsonify, render_template, request, Response

from app.database import (
    get_quality_gate_config,
    get_run_by_id,
    get_runs,
    get_summary_stats,
    get_tracked_repositories,
    init_db,
    insert_run,
    update_quality_gate_config,
)
from app.notifications import send_quality_gate_alert
from app.quality_gate import evaluate_quality_gate
from app.report_generator import generate_quality_report
from app.sync_service import GitHubActionsSync, parse_github_url

DEFAULT_TASKS = [
    {"id": 1, "title": "Set up Docker", "description": "Containerize the API", "done": True},
    {"id": 2, "title": "Write CI pipeline", "description": "Run pytest on every push", "done": False},
]


def create_app(db_path: Optional[str] = None) -> Flask:
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    app = Flask(__name__, template_folder=template_dir)
    app.config["TASKS"] = deepcopy(DEFAULT_TASKS)
    app.config["DB_PATH"] = db_path

    # Initialize SQLite database schema
    init_db(db_path)

    # -------------------------------------------------------------
    # 1. CORE TASK REST API
    # -------------------------------------------------------------
    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.get("/tasks")
    def list_tasks():
        return jsonify(app.config["TASKS"]), 200

    @app.post("/tasks")
    def create_task():
        payload = request.get_json(silent=True) or {}
        title = str(payload.get("title", "")).strip()
        if not title:
            return jsonify(error="title is required"), 400

        tasks = app.config["TASKS"]
        new_task = {
            "id": (tasks[-1]["id"] + 1) if tasks else 1,
            "title": title,
            "description": str(payload.get("description", "")).strip(),
            "done": bool(payload.get("done", False)),
        }
        tasks.append(new_task)
        return jsonify(new_task), 201

    @app.put("/tasks/<int:task_id>")
    def update_task(task_id: int):
        payload = request.get_json(silent=True) or {}
        title = payload.get("title")
        description = payload.get("description")
        done = payload.get("done")

        if title is None and description is None and done is None:
            return jsonify(error="at least one field must be provided"), 400

        for task in app.config["TASKS"]:
            if task["id"] != task_id:
                continue

            if title is not None:
                title = str(title).strip()
                if not title:
                    return jsonify(error="title cannot be empty"), 400
                task["title"] = title

            if description is not None:
                task["description"] = str(description).strip()

            if done is not None:
                if not isinstance(done, bool):
                    return jsonify(error="done must be a boolean"), 400
                task["done"] = done

            return jsonify(task), 200

        return jsonify(error="task not found"), 404

    # -------------------------------------------------------------
    # 2. DASHBOARD & EXECUTIVE REPORT WEB UI
    # -------------------------------------------------------------
    @app.get("/")
    @app.get("/dashboard")
    def dashboard_page():
        return render_template("dashboard.html")

    @app.get("/report")
    @app.get("/audit")
    def report_page():
        return render_template("report.html")


    # -------------------------------------------------------------
    # 3. METRICS & QUALITY GATE TELEMETRY API
    # -------------------------------------------------------------
    @app.get("/api/runs")
    def get_runs_api():
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        repo_name = request.args.get("repo")
        branch = request.args.get("branch")
        status = request.args.get("status")
        qg_raw = request.args.get("quality_gate_passed")
        qg_passed = (qg_raw.lower() == "true") if qg_raw is not None else None

        runs_list, total_count = get_runs(
            limit=limit,
            offset=offset,
            repo_name=repo_name,
            branch=branch,
            status=status,
            quality_gate_passed=qg_passed,
            db_path=app.config.get("DB_PATH"),
        )
        return jsonify(runs=runs_list, total_count=total_count, limit=limit, offset=offset), 200

    @app.get("/api/runs/<int:run_id>")
    def get_run_detail(run_id: int):
        run = get_run_by_id(run_id, db_path=app.config.get("DB_PATH"))
        if not run:
            return jsonify(error="Run not found"), 404
        return jsonify(run=run), 200

    @app.post("/api/runs")
    def ingest_run():
        payload = request.get_json(silent=True) or {}
        if not payload:
            return jsonify(error="Invalid JSON payload"), 400

        # Evaluate quality gate policies
        passed, reasons, reason_summary = evaluate_quality_gate(
            payload, notify=True, db_path=app.config.get("DB_PATH")
        )
        payload["quality_gate_passed"] = passed
        payload["quality_gate_reason"] = reason_summary
        if not payload.get("created_at"):
            payload["created_at"] = datetime.now(timezone.utc).isoformat()

        run_id = insert_run(payload, db_path=app.config.get("DB_PATH"))
        inserted_run = get_run_by_id(run_id, db_path=app.config.get("DB_PATH"))
        return jsonify(status="ok", run_id=run_id, run=inserted_run), 201

    @app.get("/api/summary")
    def get_summary():
        repo_name = request.args.get("repo")
        days = int(request.args.get("days", 30))
        summary = get_summary_stats(repo_name=repo_name, days=days, db_path=app.config.get("DB_PATH"))
        return jsonify(summary), 200

    @app.get("/api/repositories")
    def list_repositories():
        repos = get_tracked_repositories(db_path=app.config.get("DB_PATH"))
        return jsonify(repositories=repos), 200

    @app.post("/api/analyze")
    @app.post("/api/sync")
    def analyze_repository():
        try:
            payload = request.get_json(silent=True) or {}
            url_or_slug = payload.get("url") or payload.get("repo_url") or ""
            owner = payload.get("owner")
            repo = payload.get("repo")

            if url_or_slug:
                owner, repo = parse_github_url(url_or_slug)
            elif not owner or not repo:
                owner, repo = "varaprasad7477", "task-api-devops-project"

            token = payload.get("token")
            count = int(payload.get("count", 40))

            syncer = GitHubActionsSync(owner=owner, repo=repo, token=token, db_path=app.config.get("DB_PATH"))
            result = syncer.sync_runs(count=count)
            return jsonify(result), 200
        except Exception as e:
            error_msg = str(e)
            if "rate limit" in error_msg.lower():
                return jsonify({
                    "error": "GitHub API rate limit exceeded. Please try again later or provide a GitHub token for higher rate limits.",
                    "details": error_msg
                }), 429
            else:
                return jsonify({
                    "error": "Failed to analyze repository",
                    "details": error_msg
                }), 500

    @app.get("/api/report")
    def get_report_api():
        repo_name = request.args.get("repo")
        if not repo_name:
            repos = get_tracked_repositories(db_path=app.config.get("DB_PATH"))
            repo_name = repos[0]["repo_name"] if repos else "varaprasad7477/task-api-devops-project"

        days = int(request.args.get("days", 30))
        fmt = request.args.get("format", "json").lower()

        report_data = generate_quality_report(repo_name=repo_name, days=days, db_path=app.config.get("DB_PATH"))

        if fmt in ("markdown", "md"):
            return Response(report_data.get("markdown_report", ""), mimetype="text/markdown")
        return jsonify(report_data), 200

    @app.get("/api/quality-gate/config")
    def get_config():
        cfg = get_quality_gate_config(db_path=app.config.get("DB_PATH"))
        return jsonify(cfg), 200

    @app.put("/api/quality-gate/config")
    def update_config():
        payload = request.get_json(silent=True) or {}
        min_cov = float(payload.get("min_coverage_pct", 80.0))
        max_fails = int(payload.get("max_failed_tests", 0))
        max_dur = float(payload.get("max_duration_seconds", 300.0))
        slack_url = payload.get("slack_webhook_url")

        updated = update_quality_gate_config(
            min_coverage_pct=min_cov,
            max_failed_tests=max_fails,
            max_duration_seconds=max_dur,
            slack_webhook_url=slack_url,
            db_path=app.config.get("DB_PATH"),
        )
        return jsonify(updated), 200

    @app.post("/api/quality-gate/test-webhook")
    def test_webhook():
        payload = request.get_json(silent=True) or {}
        webhook_url = payload.get("webhook_url")
        if not webhook_url:
            cfg = get_quality_gate_config(db_path=app.config.get("DB_PATH"))
            webhook_url = cfg.get("slack_webhook_url")

        if not webhook_url:
            return jsonify(status="error", message="No webhook URL provided"), 400

        mock_run = {
            "workflow_name": "CI Quality Check",
            "branch": "main",
            "commit_sha": "abc1234",
            "author": "Quality Gate Alert Bot",
            "coverage_pct": 74.5,
            "tests_passed": 7,
            "tests_failed": 1,
            "duration_seconds": 28.4,
            "github_run_id": 9999999,
        }
        mock_reasons = [
            "Coverage 74.5% is below the required 80.0% threshold",
            "1 test failure detected (allowed: 0)",
        ]
        success = send_quality_gate_alert(webhook_url, mock_run, mock_reasons)
        if success:
            return jsonify(status="success", message="Test alert dispatched successfully"), 200
        return jsonify(status="error", message="Failed to deliver alert payload to webhook"), 502

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

