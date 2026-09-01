import os
import tempfile
from unittest.mock import patch, MagicMock
from scripts.ci_quality_gate import main


def test_ci_quality_gate_script_pass():
    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w+", delete=False) as junit_f, \
         tempfile.NamedTemporaryFile(suffix=".json", mode="w+", delete=False) as cov_f, \
         tempfile.NamedTemporaryFile(suffix=".md", mode="w+", delete=False) as summary_f:

        junit_f.write("""<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" tests="5" failures="0" skipped="0" time="0.3"></testsuite>""")
        junit_f.flush()

        cov_f.write("""{
            "totals": {"percent_covered": 95.0, "num_statements": 50, "covered_lines": 48}
        }""")
        cov_f.flush()

        with patch("sys.argv", [
            "ci_quality_gate.py",
            "--junitxml", junit_f.name,
            "--coverage-json", cov_f.name,
            "--min-coverage", "80.0",
            "--max-failures", "0"
        ]), patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": summary_f.name}):
            # Should not raise SystemExit
            main()

        # Check summary was written
        with open(summary_f.name, "r", encoding="utf-8") as f:
            content = f.read()
            assert "CI Quality Gate & Metrics Report" in content
            assert "95.00%" in content

    for p in [junit_f.name, cov_f.name, summary_f.name]:
        if os.path.exists(p):
            os.remove(p)


def test_ci_quality_gate_script_post_dashboard():
    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w+", delete=False) as junit_f, \
         tempfile.NamedTemporaryFile(suffix=".json", mode="w+", delete=False) as cov_f:

        junit_f.write("""<testsuite name="pytest" tests="2" failures="0" time="0.1"></testsuite>""")
        junit_f.flush()
        cov_f.write("""{"totals": {"percent_covered": 85.0}}""")
        cov_f.flush()

        with patch("sys.argv", [
            "ci_quality_gate.py",
            "--junitxml", junit_f.name,
            "--coverage-json", cov_f.name,
            "--dashboard-url", "http://localhost:5000"
        ]), patch("scripts.ci_quality_gate.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 201
            mock_post.return_value = mock_resp

            main()
            mock_post.assert_called_once()

    for p in [junit_f.name, cov_f.name]:
        if os.path.exists(p):
            os.remove(p)
