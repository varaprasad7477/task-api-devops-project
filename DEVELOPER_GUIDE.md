# 📖 GatePulse Developer Quick Reference Guide

> A quick guide to understanding and contributing to the GatePulse project

---

## 🗂️ Project Structure at a Glance

```
task-api-devops-project/
├── app/                          # Main application code
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # Flask app & REST endpoints (276 lines)
│   ├── database.py              # SQLite operations (384 lines)
│   ├── quality_gate.py          # Quality gate evaluation logic (51 lines)
│   ├── notifications.py         # Slack alerts (31 lines)
│   ├── report_generator.py      # Report & health score generation (155 lines)
│   ├── report_parser.py         # JUnit & coverage XML parsing (166 lines)
│   ├── sync_service.py          # GitHub Actions API integration (397 lines)
│   └── templates/               # HTML templates
│       ├── dashboard.html       # Interactive telemetry dashboard
│       └── report.html          # Executive audit report
│
├── tests/                        # Test suite (46 tests, 100% pass)
│   ├── conftest.py             # Pytest fixtures
│   ├── test_main.py            # Task API tests (8 tests)
│   ├── test_database.py        # Database tests (4 tests)
│   ├── test_metrics_api.py     # Metrics endpoint tests (9 tests)
│   ├── test_notifications.py   # Alert notification tests (4 tests)
│   ├── test_quality_gate.py    # Quality gate logic tests (5 tests)
│   ├── test_report_generator.py # Report generation tests (4 tests)
│   ├── test_report_parser.py   # Parser tests (6 tests)
│   ├── test_sync.py            # Sync service tests (4 tests)
│   └── test_ci_script.py       # CI script tests (2 tests)
│
├── scripts/                      # Utility scripts
│   ├── ci_quality_gate.py      # CLI quality gate enforcement
│   └── seed_metrics.py         # Sample data seeding
│
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container image
├── docker-compose.yml           # Container orchestration
├── README.md                    # Project documentation
└── PROJECT_VALIDATION_REPORT.md # This validation report
```

---

## 🔄 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           USER / EXTERNAL SYSTEM                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┬─────────────────┐
        │                             │                 │
    ┌───▼────┐              ┌────────▼──────┐    ┌─────▼──────┐
    │ POST   │              │  GitHub       │    │  Dashboard │
    │/api/   │              │  Repo Link    │    │  UI        │
    │runs    │              │  Analysis     │    │            │
    └───┬────┘              └────────┬──────┘    └─────┬──────┘
        │                           │                 │
        └───────────────┬───────────┴─────────────────┘
                        │
           ┌────────────▼────────────┐
           │  sync_service.py        │
           │  - Fetch GitHub API     │
           │  - Download artifacts   │
           │  - Parse metrics        │
           └────────────┬────────────┘
                        │
        ┌───────────────▼───────────────┐
        │  report_parser.py             │
        │  - Parse JUnit XML            │
        │  - Parse coverage.json/.xml   │
        │  - Extract metrics            │
        └───────────────┬───────────────┘
                        │
        ┌───────────────▼───────────────┐
        │  Run Data (Standardized)      │
        │  {                            │
        │    tests_passed: int          │
        │    tests_failed: int          │
        │    coverage_pct: float        │
        │    duration_seconds: float    │
        │    status: "success"          │
        │  }                            │
        └───────────────┬───────────────┘
                        │
           ┌────────────▼────────────┐
           │  quality_gate.py        │
           │  - Evaluate rules       │
           │  - Determine: PASS/TRIP │
           └────────────┬────────────┘
                        │
           ┌────────────▼────────────┐
           │  database.py            │
           │  - Store run in SQLite  │
           │  - Track history        │
           │  - Generate stats       │
           └────────────┬────────────┘
                        │
        ┌───────────────┴─────────────────┐
        │                                 │
    ┌───▼────────────┐        ┌──────────▼───┐
    │  Slack Alert   │        │  Dashboard   │
    │  Notification  │        │  Display     │
    │  (if tripped)  │        │  - Trends    │
    └────────────────┘        │  - Charts    │
                              │  - Reports   │
                              └──────────────┘
```

---

## 🎯 Module Reference

### 1. **main.py** - Flask Application & REST API
**Purpose**: Define Flask app, REST endpoints, and HTML routes

**Key Functions**:
- `create_app(db_path)` → Initialize Flask application
- `health()` → Service status (GET /health)
- `list_tasks()` → Get all tasks (GET /tasks)
- `create_task()` → Create new task (POST /tasks)
- `update_task(task_id)` → Update task (PUT /tasks/<id>)
- `dashboard()` → Render dashboard UI (GET /dashboard)
- `ingest_runs()` → Ingest run results (POST /api/runs)
- `analyze_github_repo()` → Fetch & analyze any GitHub repo

**When to Modify**:
- Adding new REST endpoints
- Changing request/response formats
- Modifying template rendering logic

---

### 2. **database.py** - SQLite Data Persistence
**Purpose**: All database operations (CRUD, schema management)

**Key Functions**:
- `init_db(db_path)` → Create schema & tables
- `get_db_connection(db_path)` → Get SQLite connection
- `insert_run(run_data, db_path)` → Store run results
- `get_runs(filters, db_path)` → Query runs with filtering
- `get_summary_stats(db_path)` → Calculate aggregate statistics
- `get_quality_gate_config(db_path)` → Retrieve gate config

**Important Details**:
- Uses `sqlite3.Row` for dict-like access
- Stores JSON data in `raw_details` column for extensibility
- Default database: `metrics.db` (configurable via `METRICS_DB_PATH` env var)

**When to Modify**:
- Adding new database fields
- Changing query logic or filters
- Adding new statistics calculations

---

### 3. **quality_gate.py** - Quality Gate Logic
**Purpose**: Evaluate CI runs against quality standards

**Key Functions**:
- `evaluate_quality_gate(run_data, config_override, notify, db_path)` 
  → Returns: `(passed: bool, reasons: List[str], reason_summary: str)`

**Quality Gate Rules** (configurable):
- ✅ Code Coverage ≥ 80% (default)
- ✅ Test Failures ≤ 0 (zero tolerance)
- ✅ Build Duration ≤ 300 seconds
- ✅ Workflow Status = "success"

**When to Modify**:
- Changing quality gate rules
- Adding new evaluation criteria
- Adjusting threshold values

---

### 4. **notifications.py** - Alert Integration
**Purpose**: Send alerts to external services (Slack, webhooks)

**Key Functions**:
- `send_quality_gate_alert(run_data, reason_summary, webhook_url)`
  → POST alert message to webhook

**Supported Webhooks**:
- Slack (fully supported)
- Generic HTTP webhooks (compatible)

**When to Modify**:
- Adding support for new notification channels
- Changing alert message format
- Adding retry logic

---

### 5. **report_parser.py** - Metrics Extraction
**Purpose**: Parse JUnit XML & coverage reports from CI artifacts

**Key Functions**:
- `parse_junit_xml(xml_content)` → Extract test metrics
  - Returns: `{tests_passed, tests_failed, tests_skipped, tests_total}`
- `parse_coverage_json(json_content)` → Parse coverage JSON
  - Returns: Coverage percentage
- `parse_coverage_xml(xml_content)` → Parse Cobertura XML
  - Returns: Coverage percentage

**Supported Formats**:
- JUnit XML (pytest output)
- Coverage JSON (pytest-cov)
- Cobertura XML (coverage.py)

**When to Modify**:
- Supporting new test frameworks (NUnit, TestNG, etc.)
- Parsing additional metrics
- Changing report format expectations

---

### 6. **report_generator.py** - Report & Score Calculation
**Purpose**: Generate executive reports and health scores

**Key Functions**:
- `calculate_health_score(run_data)` → Compute 0-100 health score
- `generate_quality_report(runs, config)` → Create comprehensive audit report
- `format_report_as_json()` → JSON export
- `format_report_as_markdown()` → Markdown export (for GitHub/Slack)

**Scoring Algorithm**:
- Coverage: 40% weight (target: ≥80%)
- Test Pass Rate: 30% weight (target: 100%)
- Build Duration: 20% weight (target: ≤300s)
- Trend: 10% weight (improving/stable/declining)

**When to Modify**:
- Changing health score algorithm
- Adjusting metric weights
- Adding new report sections

---

### 7. **sync_service.py** - GitHub Actions Integration
**Purpose**: Fetch CI data from any public GitHub repository via GitHub Actions REST API

**Key Functions**:
- `GitHubActionsSync.sync_repository(owner/repo)` → Orchestrate full sync
- `fetch_workflow_runs(owner, repo)` → GET recent workflow runs
- `fetch_artifacts(run_id)` → Download run artifacts
- `parse_github_url(url)` → Extract owner/repo from URL

**Flow**:
1. Parse GitHub URL → Extract owner & repo
2. Fetch workflow runs via GitHub Actions API
3. Download artifacts (report.xml, coverage.json)
4. Parse metrics
5. Store in database

**When to Modify**:
- Changing GitHub API endpoints
- Adding artifact filters
- Handling new GitHub API responses

**Note**: Requires public repository access (no auth token needed)

---

## 🧪 Testing Strategy

### Test Organization

| Test File | Focus | Coverage |
|-----------|-------|----------|
| `test_main.py` | Task CRUD, Flask routes | 95% |
| `test_database.py` | SQLite operations | 97% |
| `test_metrics_api.py` | REST API endpoints | ~90% |
| `test_quality_gate.py` | Quality gate rules | 100% |
| `test_report_parser.py` | XML/JSON parsing | 84% |
| `test_report_generator.py` | Report generation | 88% |
| `test_notifications.py` | Webhook alerts | 100% |
| `test_sync.py` | GitHub API sync | 79% |

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_quality_gate.py -v

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run single test
pytest tests/test_main.py::test_create_task -v

# Run tests matching pattern
pytest -k "quality_gate" -v
```

### Key Testing Principles

1. **Mocking**: External dependencies (GitHub API, Slack) are mocked
2. **Edge Cases**: Tests cover empty inputs, invalid data, error scenarios
3. **Integration**: API tests verify end-to-end workflows
4. **Fixtures**: `conftest.py` provides reusable test data

---

## 🚀 Common Development Tasks

### Adding a New API Endpoint

1. **Define Route** in `main.py`:
   ```python
   @app.get("/api/custom")
   def custom_endpoint():
       data = get_data()
       return jsonify(data), 200
   ```

2. **Add Logic** in appropriate module (e.g., `database.py`)

3. **Write Test** in `tests/test_main.py`:
   ```python
   def test_custom_endpoint(client):
       response = client.get("/api/custom")
       assert response.status_code == 200
   ```

4. **Update Documentation** in README.md

### Modifying Quality Gate Rules

1. **Edit Configuration** in `database.py` (defaults):
   ```python
   min_coverage_pct: 80.0  # Adjust threshold
   ```

2. **Add Validation Logic** in `quality_gate.py`:
   ```python
   if new_metric < threshold:
       reasons.append("New metric failed")
   ```

3. **Test** with `test_quality_gate.py`

4. **Update README** with new rules

### Adding Support for New Report Format

1. **Create Parser** in `report_parser.py`:
   ```python
   def parse_new_format(content):
       # Extract metrics
       return {...}
   ```

2. **Add Detection Logic** to identify format

3. **Test** in `test_report_parser.py`

4. **Update `sync_service.py`** to use new parser

---

## 🔍 Debugging Tips

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Database locked error | Multiple processes | Use `check_same_thread=False` (already set) |
| Empty coverage data | Parser not matching format | Check XML/JSON structure in test data |
| Slack alert not sent | Invalid webhook URL | Validate URL in config, check network |
| GitHub API rate limit | Too many requests | Add caching, implement exponential backoff |
| Test fails intermittently | Race condition | Ensure database fixtures cleanup properly |

### Debug Mode

```python
# Add to main.py
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)  # Auto-reload on code changes
```

### Logging

```python
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Quality gate result: {passed}")
```

---

## 📚 Key Concepts

### Quality Gate (Def)
A set of automated rules that must pass before code is merged/deployed. If any rule fails, the gate "trips" and blocks the build.

### CI/CD Metrics (Def)
Quantifiable measurements of code quality: test pass rate, code coverage %, build duration, deployment success.

### Telemetry (Def)
Collection and analysis of data about system behavior. In GatePulse: tracking CI metrics over time.

### Webhook (Def)
HTTP callback that sends data to external service (Slack, Teams, etc.) when an event occurs.

### Artifacts (Def)
Files generated during CI run: test reports (JUnit XML), coverage reports (JSON/XML), build logs.

---

## 🤝 Contributing Guide

### Before Submitting Code

1. ✅ Run tests: `pytest -v`
2. ✅ Check coverage: `pytest --cov=app --cov-report=term-missing`
3. ✅ Format code: Follow existing style
4. ✅ Update tests: Add tests for new features
5. ✅ Update README: Document new endpoints/features
6. ✅ Update this guide: If adding major features

### Code Style

- Follow PEP 8 conventions
- Use type hints for all functions
- Write docstrings for classes and public functions
- Keep lines under 100 characters
- Use meaningful variable names

### Commit Message Format

```
[FEATURE/FIX/DOCS] Brief description

- Detailed change 1
- Detailed change 2

Closes #123
```

---

## 📞 Getting Help

1. **Check README.md** for project overview
2. **Check this guide** for architecture & modules
3. **Review tests** for usage examples
4. **Look at docstrings** for function documentation
5. **Search code** for similar implementations

---

**Last Updated**: September 1, 2026  
**Maintained By**: GatePulse Team
