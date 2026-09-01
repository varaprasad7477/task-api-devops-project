import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

DATABASE_FILE = os.environ.get("METRICS_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "metrics.db"))
DEFAULT_REPO_NAME = "varaprasad7477/task-api-devops-project"


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Returns a SQLite connection with dict-like row factory."""
    path = db_path or DATABASE_FILE
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes SQLite database tables and default quality gate configuration."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Create runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            github_run_id INTEGER,
            repo_name TEXT DEFAULT 'varaprasad7477/task-api-devops-project',
            workflow_name TEXT NOT NULL,
            branch TEXT NOT NULL,
            commit_sha TEXT,
            commit_message TEXT,
            author TEXT,
            status TEXT NOT NULL,
            duration_seconds REAL DEFAULT 0.0,
            tests_passed INTEGER DEFAULT 0,
            tests_failed INTEGER DEFAULT 0,
            tests_skipped INTEGER DEFAULT 0,
            tests_total INTEGER DEFAULT 0,
            coverage_pct REAL DEFAULT 0.0,
            quality_gate_passed INTEGER DEFAULT 1,
            quality_gate_reason TEXT,
            created_at TEXT NOT NULL,
            raw_details TEXT
        )
    """)

    # Check if repo_name column exists in runs (migration for existing DBs)
    cursor.execute("PRAGMA table_info(runs)")
    columns = [row["name"] for row in cursor.fetchall()]
    if "repo_name" not in columns:
        cursor.execute("ALTER TABLE runs ADD COLUMN repo_name TEXT DEFAULT 'varaprasad7477/task-api-devops-project'")

    # Create repositories metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repositories (
            repo_name TEXT PRIMARY KEY,
            owner TEXT NOT NULL,
            repo TEXT NOT NULL,
            description TEXT,
            stars_count INTEGER DEFAULT 0,
            forks_count INTEGER DEFAULT 0,
            language TEXT,
            default_branch TEXT DEFAULT 'main',
            html_url TEXT,
            total_runs_count INTEGER DEFAULT 0,
            last_analyzed_at TEXT NOT NULL
        )
    """)

    # Create quality gate config table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quality_gate_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            min_coverage_pct REAL DEFAULT 80.0,
            max_failed_tests INTEGER DEFAULT 0,
            max_duration_seconds REAL DEFAULT 300.0,
            slack_webhook_url TEXT,
            updated_at TEXT NOT NULL
        )
    """)

    # Insert default config if empty
    cursor.execute("SELECT COUNT(*) FROM quality_gate_configs")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO quality_gate_configs (
                min_coverage_pct, max_failed_tests, max_duration_seconds, slack_webhook_url, updated_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (80.0, 0, 300.0, None, now_str))

    # Insert default repository entry if empty
    cursor.execute("SELECT COUNT(*) FROM repositories")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO repositories (
                repo_name, owner, repo, description, stars_count, forks_count,
                language, default_branch, html_url, total_runs_count, last_analyzed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            DEFAULT_REPO_NAME, "varaprasad7477", "task-api-devops-project",
            "Task API with Dockerized CI/CD & Quality Gate Dashboard", 0, 0,
            "Python", "main", "https://github.com/varaprasad7477/task-api-devops-project", 0, now_str
        ))

    conn.commit()
    conn.close()


def upsert_repository_metadata(meta: Dict[str, Any], db_path: Optional[str] = None) -> None:
    """Inserts or updates metadata for a tracked repository."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    repo_name = meta.get("repo_name") or f"{meta.get('owner')}/{meta.get('repo')}"
    owner = meta.get("owner", "")
    repo = meta.get("repo", "")
    description = meta.get("description", "")
    stars_count = int(meta.get("stars_count", 0))
    forks_count = int(meta.get("forks_count", 0))
    language = meta.get("language", "Python")
    default_branch = meta.get("default_branch", "main")
    html_url = meta.get("html_url", f"https://github.com/{repo_name}")
    total_runs_count = int(meta.get("total_runs_count", 0))
    last_analyzed_at = meta.get("last_analyzed_at") or datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        INSERT INTO repositories (
            repo_name, owner, repo, description, stars_count, forks_count,
            language, default_branch, html_url, total_runs_count, last_analyzed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(repo_name) DO UPDATE SET
            description = excluded.description,
            stars_count = excluded.stars_count,
            forks_count = excluded.forks_count,
            language = excluded.language,
            default_branch = excluded.default_branch,
            html_url = excluded.html_url,
            total_runs_count = excluded.total_runs_count,
            last_analyzed_at = excluded.last_analyzed_at
    """, (
        repo_name, owner, repo, description, stars_count, forks_count,
        language, default_branch, html_url, total_runs_count, last_analyzed_at
    ))

    conn.commit()
    conn.close()


def get_tracked_repositories(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns all tracked repositories ordered by most recently analyzed."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repositories ORDER BY last_analyzed_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_quality_gate_config(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Fetches the active quality gate configuration."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quality_gate_configs ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return {
        "min_coverage_pct": 80.0,
        "max_failed_tests": 0,
        "max_duration_seconds": 300.0,
        "slack_webhook_url": None,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


def update_quality_gate_config(
    min_coverage_pct: float,
    max_failed_tests: int,
    max_duration_seconds: float,
    slack_webhook_url: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Updates the quality gate configuration."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        UPDATE quality_gate_configs
        SET min_coverage_pct = ?,
            max_failed_tests = ?,
            max_duration_seconds = ?,
            slack_webhook_url = ?,
            updated_at = ?
        WHERE id = (SELECT id FROM quality_gate_configs ORDER BY id DESC LIMIT 1)
    """, (min_coverage_pct, max_failed_tests, max_duration_seconds, slack_webhook_url, now_str))

    conn.commit()
    conn.close()
    return get_quality_gate_config(db_path)


def insert_run(run_data: Dict[str, Any], db_path: Optional[str] = None) -> int:
    """Inserts a run record or updates if (github_run_id, repo_name) exists."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    github_run_id = run_data.get("github_run_id")
    repo_name = run_data.get("repo_name", DEFAULT_REPO_NAME)
    workflow_name = run_data.get("workflow_name", "CI")
    branch = run_data.get("branch", "main")
    commit_sha = run_data.get("commit_sha", "")
    commit_message = run_data.get("commit_message", "")
    author = run_data.get("author", "")
    status = run_data.get("status", "success")
    duration_seconds = float(run_data.get("duration_seconds", 0.0))
    tests_passed = int(run_data.get("tests_passed", 0))
    tests_failed = int(run_data.get("tests_failed", 0))
    tests_skipped = int(run_data.get("tests_skipped", 0))
    tests_total = int(run_data.get("tests_total", tests_passed + tests_failed + tests_skipped))
    coverage_pct = float(run_data.get("coverage_pct", 0.0))
    quality_gate_passed = 1 if run_data.get("quality_gate_passed", True) else 0
    quality_gate_reason = run_data.get("quality_gate_reason", "")
    created_at = run_data.get("created_at") or datetime.now(timezone.utc).isoformat()
    raw_details = run_data.get("raw_details")
    if isinstance(raw_details, dict):
        raw_details = json.dumps(raw_details)

    if github_run_id:
        cursor.execute("SELECT id FROM runs WHERE github_run_id = ? AND repo_name = ?", (github_run_id, repo_name))
        existing = cursor.fetchone()
        if existing:
            run_id = existing["id"]
            cursor.execute("""
                UPDATE runs SET
                    workflow_name = ?,
                    branch = ?,
                    commit_sha = ?,
                    commit_message = ?,
                    author = ?,
                    status = ?,
                    duration_seconds = ?,
                    tests_passed = ?,
                    tests_failed = ?,
                    tests_skipped = ?,
                    tests_total = ?,
                    coverage_pct = ?,
                    quality_gate_passed = ?,
                    quality_gate_reason = ?,
                    created_at = ?,
                    raw_details = ?
                WHERE id = ?
            """, (
                workflow_name, branch, commit_sha, commit_message, author, status,
                duration_seconds, tests_passed, tests_failed, tests_skipped,
                tests_total, coverage_pct, quality_gate_passed, quality_gate_reason,
                created_at, raw_details, run_id
            ))
            conn.commit()
            conn.close()
            return run_id

    # Use INSERT OR IGNORE to handle duplicate github_run_ids gracefully
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO runs (
                github_run_id, repo_name, workflow_name, branch, commit_sha, commit_message, author,
                status, duration_seconds, tests_passed, tests_failed, tests_skipped,
                tests_total, coverage_pct, quality_gate_passed, quality_gate_reason,
                created_at, raw_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            github_run_id, repo_name, workflow_name, branch, commit_sha, commit_message, author,
            status, duration_seconds, tests_passed, tests_failed, tests_skipped,
            tests_total, coverage_pct, quality_gate_passed, quality_gate_reason,
            created_at, raw_details
        ))

        # Get the ID of inserted or existing run
        cursor.execute("SELECT id FROM runs WHERE github_run_id = ? AND repo_name = ?", (github_run_id, repo_name))
        result = cursor.fetchone()
        run_id = result["id"] if result else cursor.lastrowid
        
        conn.commit()
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            # Retry after brief wait
            import time
            time.sleep(0.5)
            conn.close()
            return insert_run(run_data, db_path)  # Recursive retry
        raise
    finally:
        conn.close()
    
    return run_id


def get_runs(
    limit: int = 50,
    offset: int = 0,
    repo_name: Optional[str] = None,
    branch: Optional[str] = None,
    status: Optional[str] = None,
    quality_gate_passed: Optional[bool] = None,
    db_path: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves a paginated list of runs with optional repo/branch/status filters and total count."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    query = "SELECT * FROM runs WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM runs WHERE 1=1"
    params: List[Any] = []

    if repo_name:
        query += " AND repo_name = ?"
        count_query += " AND repo_name = ?"
        params.append(repo_name)

    if branch:
        query += " AND branch = ?"
        count_query += " AND branch = ?"
        params.append(branch)

    if status:
        query += " AND status = ?"
        count_query += " AND status = ?"
        params.append(status)

    if quality_gate_passed is not None:
        val = 1 if quality_gate_passed else 0
        query += " AND quality_gate_passed = ?"
        count_query += " AND quality_gate_passed = ?"
        params.append(val)

    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]

    query += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    runs_list = []
    for r in rows:
        d = dict(r)
        d["quality_gate_passed"] = bool(d["quality_gate_passed"])
        runs_list.append(d)

    return runs_list, total_count


def get_run_by_id(run_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single run by database ID."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    d = dict(row)
    d["quality_gate_passed"] = bool(d["quality_gate_passed"])
    if d.get("raw_details"):
        try:
            d["raw_details"] = json.loads(d["raw_details"])
        except Exception:
            pass
    return d


def get_summary_stats(repo_name: Optional[str] = None, days: int = 30, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Calculates summary statistics for a given repository (or overall) across history and 30-day window."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    repo_filter = " WHERE repo_name = ?" if repo_name else ""
    params = [repo_name] if repo_name else []

    cursor.execute(f"SELECT COUNT(*) FROM runs{repo_filter}", params)
    total_runs = cursor.fetchone()[0]

    # Fetch repository metadata
    repo_meta = None
    if repo_name:
        cursor.execute("SELECT * FROM repositories WHERE repo_name = ?", (repo_name,))
        r_row = cursor.fetchone()
        if r_row:
            repo_meta = dict(r_row)

    if total_runs == 0:
        conn.close()
        return {
            "repo_name": repo_name or DEFAULT_REPO_NAME,
            "repo_meta": repo_meta,
            "total_runs": 0,
            "success_rate_pct": 0.0,
            "failure_rate_pct": 0.0,
            "avg_coverage_pct": 0.0,
            "avg_duration_seconds": 0.0,
            "quality_gate_pass_rate_pct": 0.0,
            "last_30_days_runs": 0,
            "last_30_days_failure_rate_pct": 0.0,
            "latest_run": None,
            "branches": []
        }

    # Latest run for this repo
    cursor.execute(f"SELECT * FROM runs{repo_filter} ORDER BY created_at DESC, id DESC LIMIT 1", params)
    latest_row = cursor.fetchone()
    latest_run = dict(latest_row) if latest_row else None
    if latest_run:
        latest_run["quality_gate_passed"] = bool(latest_run["quality_gate_passed"])

    # Overall aggregates for this repo
    cursor.execute(f"""
        SELECT
            AVG(coverage_pct) as avg_cov,
            AVG(duration_seconds) as avg_dur,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_cnt,
            SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) as fail_cnt,
            SUM(CASE WHEN quality_gate_passed = 1 THEN 1 ELSE 0 END) as qg_pass_cnt
        FROM runs{repo_filter}
    """, params)
    overall = cursor.fetchone()

    avg_cov = round(float(overall["avg_cov"] or 0.0), 2)
    avg_dur = round(float(overall["avg_dur"] or 0.0), 2)
    success_cnt = overall["success_cnt"] or 0
    fail_cnt = overall["fail_cnt"] or 0
    qg_pass_cnt = overall["qg_pass_cnt"] or 0

    success_rate = round((success_cnt / total_runs) * 100.0, 1) if total_runs > 0 else 0.0
    failure_rate = round((fail_cnt / total_runs) * 100.0, 1) if total_runs > 0 else 0.0
    qg_pass_rate = round((qg_pass_cnt / total_runs) * 100.0, 1) if total_runs > 0 else 0.0

    # 30 days calculation
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    t_query = "SELECT COUNT(*) as total_30, SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) as fail_30, AVG(coverage_pct) as avg_cov_30, AVG(duration_seconds) as avg_dur_30 FROM runs WHERE created_at >= ?"
    t_params = [cutoff_date]
    if repo_name:
        t_query += " AND repo_name = ?"
        t_params.append(repo_name)

    cursor.execute(t_query, t_params)
    thirty = cursor.fetchone()

    total_30 = thirty["total_30"] or 0
    fail_30 = thirty["fail_30"] or 0
    failure_rate_30 = round((fail_30 / total_30) * 100.0, 1) if total_30 > 0 else 0.0
    avg_cov_30 = round(float(thirty["avg_cov_30"] or 0.0), 2) if total_30 > 0 else avg_cov

    # Distinct branches for this repo
    b_query = "SELECT DISTINCT branch FROM runs WHERE branch IS NOT NULL"
    if repo_name:
        b_query += " AND repo_name = ?"
    b_query += " ORDER BY branch"
    cursor.execute(b_query, params)
    branches = [row[0] for row in cursor.fetchall()]

    conn.close()

    return {
        "repo_name": repo_name or DEFAULT_REPO_NAME,
        "repo_meta": repo_meta,
        "total_runs": total_runs,
        "success_rate_pct": success_rate,
        "failure_rate_pct": failure_rate,
        "avg_coverage_pct": avg_cov,
        "avg_duration_seconds": avg_dur,
        "quality_gate_pass_rate_pct": qg_pass_rate,
        "last_30_days_runs": total_30,
        "last_30_days_failure_rate_pct": failure_rate_30,
        "last_30_days_avg_coverage_pct": avg_cov_30,
        "latest_run": latest_run,
        "branches": branches
    }
