"""
Quality Gate Audit Report Generator
Generates comprehensive, accurate CI/CD quality and reliability assessment reports
for any tracked repository, including composite health scores, rule-by-rule compliance,
risk factors, actionable recommendations, and formatted Markdown exports.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from app.database import get_quality_gate_config, get_runs, get_summary_stats


def calculate_health_score(summary: Dict[str, Any], config: Dict[str, Any]) -> Tuple[int, str]:
    """
    Calculates a 0-100 composite CI/CD health score and letter grade.
    Weights:
      - Build Success Rate: 35%
      - Code Coverage vs Threshold: 30%
      - Quality Gate Compliance: 25%
      - Duration Efficiency: 10%
    """
    total_runs = summary.get("total_runs", 0)
    if total_runs == 0:
        return 0, "N/A"

    success_rate = float(summary.get("success_rate_pct", 0.0))
    avg_cov = float(summary.get("avg_coverage_pct", 0.0))
    min_cov = float(config.get("min_coverage_pct", 80.0))
    qg_compliance = float(summary.get("quality_gate_pass_rate_pct", 0.0))
    avg_dur = float(summary.get("avg_duration_seconds", 0.0))
    max_dur = float(config.get("max_duration_seconds", 300.0))

    # 1. Success rate score (0-35)
    s_score = (success_rate / 100.0) * 35.0

    # 2. Coverage score (0-30)
    cov_ratio = min(1.0, avg_cov / max(1.0, min_cov)) if min_cov > 0 else 1.0
    c_score = cov_ratio * 30.0

    # 3. Quality gate compliance score (0-25)
    q_score = (qg_compliance / 100.0) * 25.0

    # 4. Duration score (0-10)
    if avg_dur <= (max_dur * 0.5):
        d_score = 10.0
    elif avg_dur <= max_dur:
        d_score = 10.0 - ((avg_dur - (max_dur * 0.5)) / (max_dur * 0.5)) * 5.0
    else:
        d_score = max(0.0, 5.0 - ((avg_dur - max_dur) / max_dur) * 5.0)

    total_score = max(0, min(100, int(round(s_score + c_score + q_score + d_score))))

    if total_score >= 95:
        grade = "A+"
    elif total_score >= 90:
        grade = "A"
    elif total_score >= 80:
        grade = "B"
    elif total_score >= 70:
        grade = "C"
    elif total_score >= 60:
        grade = "D"
    else:
        grade = "F"

    return total_score, grade


def generate_quality_report(
    repo_name: str,
    days: int = 30,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a full structured quality report and GitHub-flavored markdown export
    for a given repository.
    """
    summary = get_summary_stats(repo_name=repo_name, days=days, db_path=db_path)
    config = get_quality_gate_config(db_path=db_path)
    runs, total_runs = get_runs(limit=15, offset=0, repo_name=repo_name, db_path=db_path)

    health_score, health_grade = calculate_health_score(summary, config)

    min_cov = float(config.get("min_coverage_pct", 80.0))
    max_fails = int(config.get("max_failed_tests", 0))
    max_dur = float(config.get("max_duration_seconds", 300.0))

    latest_run = summary.get("latest_run")
    overall_passed = bool(latest_run and latest_run.get("quality_gate_passed")) if latest_run else False

    # Rule-by-rule evaluation
    rule_evaluations = []
    if latest_run:
        # Rule 1: Coverage
        latest_cov = float(latest_run.get("coverage_pct", 0.0))
        cov_passed = latest_cov >= min_cov
        rule_evaluations.append({
            "rule": "Minimum Code Coverage",
            "required": f">= {min_cov:.1f}%",
            "actual": f"{latest_cov:.1f}%",
            "status": "PASSED" if cov_passed else "TRIPPED",
            "details": f"Coverage is {latest_cov:.1f}% vs threshold {min_cov:.1f}%"
        })

        # Rule 2: Test Failures
        latest_fails = int(latest_run.get("tests_failed", 0))
        fails_passed = latest_fails <= max_fails
        rule_evaluations.append({
            "rule": "Zero Test Failures",
            "required": f"<= {max_fails} failed tests",
            "actual": f"{latest_fails} failed tests",
            "status": "PASSED" if fails_passed else "TRIPPED",
            "details": f"{latest_run.get('tests_passed', 0)} passed, {latest_fails} failed out of {latest_run.get('tests_total', 0)} total"
        })

        # Rule 3: Execution Duration
        latest_dur = float(latest_run.get("duration_seconds", 0.0))
        dur_passed = latest_dur <= max_dur
        rule_evaluations.append({
            "rule": "Pipeline Duration Limit",
            "required": f"<= {max_dur:.1f}s",
            "actual": f"{latest_dur:.1f}s",
            "status": "PASSED" if dur_passed else "TRIPPED",
            "details": f"Execution finished in {latest_dur:.1f}s"
        })

        # Rule 4: Workflow Status
        latest_status = str(latest_run.get("status", "success"))
        status_passed = latest_status == "success"
        rule_evaluations.append({
            "rule": "Workflow Exit Status",
            "required": "success",
            "actual": latest_status,
            "status": "PASSED" if status_passed else "TRIPPED",
            "details": f"CI run completed with status '{latest_status}'"
        })

    # Risk Assessment & Recommendations
    risks: List[str] = []
    recommendations: List[str] = []

    if summary.get("avg_coverage_pct", 0.0) < min_cov:
        risks.append(f"Average code coverage ({summary.get('avg_coverage_pct')}%) is below the {min_cov}% threshold.")
        recommendations.append("Increase unit and integration test suite breadth to reach minimum 80% coverage standard.")

    if summary.get("last_30_days_failure_rate_pct", 0.0) > 15.0:
        risks.append(f"High 30-day pipeline failure rate ({summary.get('last_30_days_failure_rate_pct')}%).")
        recommendations.append("Investigate flaky test cases or build environment instabilities to lower CI failure rate.")

    if summary.get("avg_duration_seconds", 0.0) > (max_dur * 0.7):
        risks.append(f"Average pipeline execution time ({summary.get('avg_duration_seconds')}s) is approaching the {max_dur}s threshold.")
        recommendations.append("Implement dependency caching (pip/npm cache) and parallelize test execution to optimize build speed.")

    if not risks:
        risks.append("No critical quality risks identified. Pipeline meets enterprise reliability standards.")
        recommendations.append("Maintain strict branch protection rules and continuous quality gate telemetry in CI.")

    # Generate Markdown representation
    repo_meta = summary.get("repo_meta") or {}
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    md_lines = [
        f"# 🛡️ CI/CD Quality Gate Audit Report: `{repo_name}`",
        f"*Generated on: {now_iso}*",
        "",
        "## 📊 Executive Summary",
        "",
        f"- **Repository:** [{repo_name}]({repo_meta.get('html_url', f'https://github.com/{repo_name}')})",
        f"- **Primary Language:** {repo_meta.get('language', 'General')}",
        f"- **Overall Quality Gate Verdict:** **{'✅ PASSED' if overall_passed else '❌ TRIPPED'}**",
        f"- **Composite Health Score:** **{health_score}/100 (Grade: {health_grade})**",
        f"- **Total Analyzed Runs:** {total_runs}",
        f"- **Build Success Rate:** {summary.get('success_rate_pct', 0.0)}%",
        f"- **Average Code Coverage:** {summary.get('avg_coverage_pct', 0.0)}% (Target: >= {min_cov:.1f}%)",
        f"- **Quality Gate Compliance:** {summary.get('quality_gate_pass_rate_pct', 0.0)}%",
        f"- **Average Pipeline Duration:** {summary.get('avg_duration_seconds', 0.0)}s",
        "",
        "## 🔍 Rule-by-Rule Quality Gate Evaluation",
        "",
        "| Rule | Required Standard | Latest Run Actual | Verdict | Diagnostic Details |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]

    for r in rule_evaluations:
        badge = "✅ PASSED" if r["status"] == "PASSED" else "❌ TRIPPED"
        md_lines.append(f"| **{r['rule']}** | `{r['required']}` | `{r['actual']}` | {badge} | {r['details']} |")

    md_lines.extend([
        "",
        "## ⚠️ Risk Assessment & DevOps Recommendations",
        "",
        "### Identified Risk Factors:",
    ])
    for risk in risks:
        md_lines.append(f"- ⚠️ {risk}")

    md_lines.extend([
        "",
        "### Actionable Recommendations:",
    ])
    for rec in recommendations:
        md_lines.append(f"- 💡 {rec}")

    md_lines.extend([
        "",
        "## 📋 Recent Pipeline Telemetry (Last 10 Runs)",
        "",
        "| Run ID | Branch | Status | Quality Gate | Tests (P/F) | Coverage | Duration | Date |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ])

    for r in runs[:10]:
        qg_badge = "✅ PASS" if r.get("quality_gate_passed") else "❌ TRIPPED"
        status_badge = "Success" if r.get("status") == "success" else r.get("status")
        md_lines.append(
            f"| #{r.get('id')} | `{r.get('branch')}` | {status_badge} | {qg_badge} | "
            f"{r.get('tests_passed')}/{r.get('tests_failed')} | {r.get('coverage_pct', 0):.1f}% | "
            f"{r.get('duration_seconds', 0):.1f}s | {r.get('created_at', '')[:10]} |"
        )

    md_content = "\n".join(md_lines)

    return {
        "repo_name": repo_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "repo_meta": repo_meta,
        "config": config,
        "health_score": health_score,
        "health_grade": health_grade,
        "overall_verdict": "PASSED" if overall_passed else "TRIPPED",
        "rule_evaluations": rule_evaluations,
        "risks": risks,
        "recommendations": recommendations,
        "recent_runs": runs[:10],
        "markdown_report": md_content
    }
