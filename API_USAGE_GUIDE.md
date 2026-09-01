# 🚀 GatePulse API & Usage Examples

> Quick reference for using GatePulse APIs with real examples

---

## 📡 API Overview

GatePulse provides a comprehensive REST API for task management, CI metrics, and quality gate operations.

### Base URL
```
http://localhost:5000
```

### Authentication
Currently no authentication required (assumes secure network).

---

## 🏥 Health & Status Endpoints

### Check Service Health
```bash
curl http://localhost:5000/health
```

**Response** (200 OK):
```json
{
  "status": "ok"
}
```

---

## ✅ Task Management API

### 1️⃣ List All Tasks
```bash
curl -X GET http://localhost:5000/tasks
```

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "title": "Set up Docker",
    "description": "Containerize the API",
    "done": true
  },
  {
    "id": 2,
    "title": "Write CI pipeline",
    "description": "Run pytest on every push",
    "done": false
  }
]
```

---

### 2️⃣ Create a New Task
```bash
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Add API documentation",
    "description": "Write Swagger/OpenAPI spec",
    "done": false
  }'
```

**Request Body**:
```json
{
  "title": "Add API documentation",      // Required, non-empty string
  "description": "Write Swagger spec",   // Optional, string
  "done": false                          // Optional, boolean
}
```

**Response** (201 Created):
```json
{
  "id": 3,
  "title": "Add API documentation",
  "description": "Write Swagger spec",
  "done": false
}
```

**Error Response** (400 Bad Request):
```json
{
  "error": "title is required"
}
```

---

### 3️⃣ Update a Task
```bash
curl -X PUT http://localhost:5000/tasks/2 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Write GitHub Actions CI pipeline",
    "done": true
  }'
```

**Request Body** (at least one field required):
```json
{
  "title": "Updated title",              // Optional string (non-empty)
  "description": "Updated description",  // Optional string
  "done": true                           // Optional boolean
}
```

**Response** (200 OK):
```json
{
  "id": 2,
  "title": "Write GitHub Actions CI pipeline",
  "description": "Run pytest on every push",
  "done": true
}
```

**Error Responses**:
```json
// Task not found (404)
{"error": "Task with id 999 not found"}

// No fields provided (400)
{"error": "at least one field must be provided"}

// Invalid done field (400)
{"error": "done must be a boolean"}
```

---

## 📊 Metrics & Telemetry API

### 4️⃣ Ingest a CI Run Result
Typically called by GitHub Actions or CI/CD pipeline after tests complete.

```bash
curl -X POST http://localhost:5000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "Test Suite",
    "branch": "main",
    "commit_sha": "abc123def456",
    "commit_message": "Fix bug in sync_service",
    "author": "varaprasad7477",
    "status": "success",
    "duration_seconds": 45.5,
    "tests_passed": 46,
    "tests_failed": 0,
    "tests_skipped": 2,
    "tests_total": 48,
    "coverage_pct": 89.3
  }'
```

**Request Body**:
```json
{
  "workflow_name": "Test Suite",           // Required
  "branch": "main",                        // Required
  "commit_sha": "abc123...",               // Required
  "commit_message": "Fix bug",             // Required
  "author": "username",                    // Required
  "status": "success|failure|cancelled",   // Required
  "duration_seconds": 45.5,                // Required (float)
  "tests_passed": 46,                      // Required (int)
  "tests_failed": 0,                       // Required (int)
  "tests_skipped": 2,                      // Required (int)
  "tests_total": 48,                       // Required (int)
  "coverage_pct": 89.3                     // Required (float 0-100)
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "github_run_id": null,
  "repo_name": "varaprasad7477/task-api-devops-project",
  "workflow_name": "Test Suite",
  "branch": "main",
  "commit_sha": "abc123def456",
  "commit_message": "Fix bug in sync_service",
  "author": "varaprasad7477",
  "status": "success",
  "duration_seconds": 45.5,
  "tests_passed": 46,
  "tests_failed": 0,
  "tests_skipped": 2,
  "tests_total": 48,
  "coverage_pct": 89.3,
  "quality_gate_passed": 1,                    // 1=passed, 0=tripped
  "quality_gate_reason": "Quality Gate: PASSED",
  "created_at": "2026-09-01T12:34:56Z"
}
```

---

### 5️⃣ Get All Runs (Paginated & Filtered)

```bash
# Get all runs
curl http://localhost:5000/api/runs

# With filters
curl "http://localhost:5000/api/runs?limit=10&branch=main&quality_gate_passed=1"

# Specific run
curl http://localhost:5000/api/runs/1
```

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 30 | Number of results |
| `offset` | int | 0 | Pagination offset |
| `branch` | string | - | Filter by branch |
| `status` | string | - | Filter by status (success/failure) |
| `quality_gate_passed` | int (0/1) | - | Filter by gate status |
| `repo_name` | string | - | Filter by repository |

**Response** (200 OK):
```json
{
  "runs": [
    {
      "id": 1,
      "workflow_name": "Test Suite",
      "branch": "main",
      "commit_sha": "abc123def456",
      "status": "success",
      "duration_seconds": 45.5,
      "tests_passed": 46,
      "tests_failed": 0,
      "coverage_pct": 89.3,
      "quality_gate_passed": 1,
      "created_at": "2026-09-01T12:34:56Z"
    }
  ],
  "total_count": 100,
  "limit": 30,
  "offset": 0
}
```

---

### 6️⃣ Get Single Run Details
```bash
curl http://localhost:5000/api/runs/1
```

**Response** (200 OK):
```json
{
  "id": 1,
  "github_run_id": null,
  "repo_name": "varaprasad7477/task-api-devops-project",
  "workflow_name": "Test Suite",
  "branch": "main",
  "commit_sha": "abc123def456",
  "commit_message": "Fix bug in sync_service",
  "author": "varaprasad7477",
  "status": "success",
  "duration_seconds": 45.5,
  "tests_passed": 46,
  "tests_failed": 0,
  "tests_skipped": 2,
  "tests_total": 48,
  "coverage_pct": 89.3,
  "quality_gate_passed": 1,
  "quality_gate_reason": "Quality Gate: PASSED",
  "created_at": "2026-09-01T12:34:56Z",
  "raw_details": "{...}"  // Extended JSON data
}
```

---

### 7️⃣ Get Summary Statistics
Aggregate metrics for dashboards and reporting.

```bash
curl http://localhost:5000/api/summary
```

**Response** (200 OK):
```json
{
  "total_runs": 100,
  "pass_rate_pct": 95.0,
  "failure_count": 5,
  "avg_coverage_pct": 87.5,
  "avg_duration_seconds": 48.3,
  "quality_gate_pass_pct": 93.0,
  "last_30_days": {
    "runs": 30,
    "failures": 2,
    "avg_coverage_pct": 88.2,
    "trend": "improving"
  },
  "by_branch": {
    "main": {
      "runs": 60,
      "pass_rate_pct": 98.0,
      "avg_coverage_pct": 89.5
    },
    "develop": {
      "runs": 40,
      "pass_rate_pct": 87.5,
      "avg_coverage_pct": 84.0
    }
  }
}
```

---

## ⚙️ Quality Gate Configuration API

### 8️⃣ Get Quality Gate Config
```bash
curl http://localhost:5000/api/quality-gate
```

**Response** (200 OK):
```json
{
  "min_coverage_pct": 80.0,
  "max_failed_tests": 0,
  "max_duration_seconds": 300.0,
  "slack_webhook_url": "https://hooks.slack.com/services/..."
}
```

---

### 9️⃣ Update Quality Gate Config
```bash
curl -X PUT http://localhost:5000/api/quality-gate \
  -H "Content-Type: application/json" \
  -d '{
    "min_coverage_pct": 85.0,
    "max_failed_tests": 0,
    "max_duration_seconds": 600.0,
    "slack_webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  }'
```

**Request Body** (all optional, only provided fields are updated):
```json
{
  "min_coverage_pct": 85.0,              // Optional, float 0-100
  "max_failed_tests": 0,                 // Optional, int ≥ 0
  "max_duration_seconds": 600.0,         // Optional, float ≥ 0
  "slack_webhook_url": "https://hooks..." // Optional, valid URL
}
```

**Response** (200 OK):
```json
{
  "min_coverage_pct": 85.0,
  "max_failed_tests": 0,
  "max_duration_seconds": 600.0,
  "slack_webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
}
```

---

## 🔍 Repository Analysis API

### 🔟 Analyze Any Public GitHub Repository
Fetches recent workflow runs from any public GitHub repository via GitHub Actions API.

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/tiangolo/fastapi"
  }'
```

**Request Body**:
```json
{
  "repo_url": "https://github.com/owner/repo"  // Required, public repo
}
```

**Response** (200 OK):
```json
{
  "owner": "tiangolo",
  "repo": "fastapi",
  "runs_synced": 12,
  "quality_gate_passed": 10,
  "avg_coverage_pct": 92.5,
  "recent_runs": [
    {
      "workflow_name": "test",
      "branch": "master",
      "status": "success",
      "coverage_pct": 93.0,
      "quality_gate_passed": 1
    }
  ]
}
```

---

### 1️⃣1️⃣ Get Tracked Repositories
```bash
curl http://localhost:5000/api/repositories
```

**Response** (200 OK):
```json
{
  "repositories": [
    {
      "repo_name": "tiangolo/fastapi",
      "total_runs": 50,
      "quality_gate_pass_pct": 98.0,
      "avg_coverage_pct": 92.5,
      "last_sync": "2026-09-01T10:00:00Z"
    },
    {
      "repo_name": "varaprasad7477/task-api-devops-project",
      "total_runs": 100,
      "quality_gate_pass_pct": 93.0,
      "avg_coverage_pct": 87.5,
      "last_sync": "2026-09-01T11:30:00Z"
    }
  ]
}
```

---

## 📝 Reports & Export API

### 1️⃣2️⃣ Get Quality Report (Multiple Formats)

**JSON Format**:
```bash
curl "http://localhost:5000/api/report?format=json"
```

**Markdown Format** (for GitHub, Slack):
```bash
curl "http://localhost:5000/api/report?format=markdown"
```

**Response - JSON** (200 OK):
```json
{
  "health_score": 87,
  "grade": "B+",
  "compliance": {
    "coverage": {
      "value": 89.3,
      "required": 80.0,
      "status": "PASS"
    },
    "test_failures": {
      "value": 0,
      "required": 0,
      "status": "PASS"
    },
    "duration": {
      "value": 45.5,
      "required": 300.0,
      "status": "PASS"
    },
    "status": {
      "value": "success",
      "required": "success",
      "status": "PASS"
    }
  },
  "recommendations": [
    "Maintain code coverage above 80%",
    "Consider optimizing build duration"
  ],
  "generated_at": "2026-09-01T12:34:56Z"
}
```

**Response - Markdown**:
```markdown
# Quality Gate Audit Report

## Health Score: 87/100 (Grade: B+)

### Compliance Matrix
| Rule | Value | Required | Status |
|------|-------|----------|--------|
| Code Coverage | 89.3% | ≥80% | ✅ PASS |
| Test Failures | 0 | 0 | ✅ PASS |
| Build Duration | 45.5s | ≤300s | ✅ PASS |
| Status | success | success | ✅ PASS |

### Overall Result: ✅ QUALITY GATE: PASSED

### Recommendations
- Maintain code coverage above 80%
- Consider optimizing build duration

---
Generated: 2026-09-01 12:34:56 UTC
```

---

## 🌐 Frontend Routes

### Dashboard UI
```
GET http://localhost:5000/dashboard
GET http://localhost:5000/
```
Interactive dashboard with:
- Trend charts (coverage, pass rate, duration)
- Quality gate status banner
- Filterable runs table
- Repository search & analysis

### Executive Audit Report UI
```
GET http://localhost:5000/report
GET http://localhost:5000/audit
```
Printable/exportable quality audit report with:
- Health score gauge
- Compliance matrix
- Risk assessment
- Recommendations
- Export options (JSON, Markdown, PDF)

---

## 🛡️ Error Handling

All endpoints return standard HTTP status codes:

| Status | Meaning | Example |
|--------|---------|---------|
| 200 | Success | Task retrieved |
| 201 | Created | Run ingested successfully |
| 400 | Bad Request | Missing required field |
| 404 | Not Found | Task ID doesn't exist |
| 422 | Unprocessable | Invalid data type |
| 500 | Server Error | Database connection failed |

**Error Response Format**:
```json
{
  "error": "Detailed error message",
  "status": 400
}
```

---

## 📚 Integration Examples

### Python - Ingest Run Result
```python
import requests

url = "http://localhost:5000/api/runs"
run_data = {
    "workflow_name": "CI/CD Pipeline",
    "branch": "main",
    "commit_sha": "abc123",
    "commit_message": "Add feature X",
    "author": "username",
    "status": "success",
    "duration_seconds": 60.0,
    "tests_passed": 100,
    "tests_failed": 0,
    "tests_skipped": 5,
    "tests_total": 105,
    "coverage_pct": 88.5
}

response = requests.post(url, json=run_data)
result = response.json()
print(f"Run ID: {result['id']}")
print(f"Quality Gate: {'PASSED' if result['quality_gate_passed'] else 'TRIPPED'}")
```

### Bash - GitHub Actions Workflow
```bash
#!/bin/bash
# .github/workflows/quality-gate.yml

- name: Report Metrics to GatePulse
  run: |
    curl -X POST http://gatepulse:5000/api/runs \
      -H "Content-Type: application/json" \
      -d '{
        "workflow_name": "Tests",
        "branch": "${{ github.ref_name }}",
        "commit_sha": "${{ github.sha }}",
        "commit_message": "${{ github.event.head_commit.message }}",
        "author": "${{ github.actor }}",
        "status": "success",
        "duration_seconds": 60.0,
        "tests_passed": 100,
        "tests_failed": 0,
        "tests_skipped": 5,
        "tests_total": 105,
        "coverage_pct": 89.3
      }'
```

### JavaScript/Node - Check Quality Gate
```javascript
const fetch = require('node-fetch');

async function checkQualityGate(runId) {
  const response = await fetch(`http://localhost:5000/api/runs/${runId}`);
  const run = await response.json();
  
  if (run.quality_gate_passed) {
    console.log("✅ Quality Gate PASSED");
  } else {
    console.log(`❌ Quality Gate TRIPPED: ${run.quality_gate_reason}`);
    process.exit(1);
  }
}

checkQualityGate(1);
```

---

## 🧪 Testing the API

### Using curl (Command Line)
```bash
# Test health
curl http://localhost:5000/health

# List tasks
curl http://localhost:5000/tasks

# Create task
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Task"}'
```

### Using Postman
1. Import the API endpoints above
2. Create a collection for GatePulse
3. Test each endpoint
4. Export collection for team use

### Using Python
```bash
pip install requests
python -c "import requests; print(requests.get('http://localhost:5000/health').json())"
```

---

## 🚀 Quick Start Examples

### 1. Start the application
```bash
python app/main.py
```

### 2. Test with curl
```bash
# Health check
curl http://localhost:5000/health

# Get tasks
curl http://localhost:5000/tasks

# Create task
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"New Task","done":false}'
```

### 3. Ingest CI metrics
```bash
curl -X POST http://localhost:5000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name":"Tests",
    "branch":"main",
    "commit_sha":"abc123",
    "commit_message":"Fix bug",
    "author":"developer",
    "status":"success",
    "duration_seconds":45,
    "tests_passed":46,
    "tests_failed":0,
    "tests_skipped":2,
    "tests_total":48,
    "coverage_pct":89.3
  }'
```

### 4. View dashboard
```
Open: http://localhost:5000/dashboard
```

---

**Last Updated**: September 1, 2026  
**API Version**: 1.0.0  
**Environment**: Python 3.10+ | Flask 3.0.3
