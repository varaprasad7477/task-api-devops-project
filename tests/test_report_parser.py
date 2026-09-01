import json
from app.report_parser import parse_coverage_report, parse_junit_xml

SAMPLE_JUNIT_XML_PASS = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="8" time="0.450">
    <testcase classname="tests.test_main" name="test_health" time="0.05" />
    <testcase classname="tests.test_main" name="test_list_tasks" time="0.06" />
    <testcase classname="tests.test_main" name="test_create_task" time="0.08" />
  </testsuite>
</testsuites>
"""

SAMPLE_JUNIT_XML_FAIL = """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" errors="0" failures="1" skipped="1" tests="4" time="0.620">
  <testcase classname="tests.test_main" name="test_health" time="0.05" />
  <testcase classname="tests.test_main" name="test_fail" time="0.10">
    <failure message="AssertionError: assert 500 == 200">Traceback details</failure>
  </testcase>
  <testcase classname="tests.test_main" name="test_skip" time="0.00">
    <skipped message="reason: skipped test" />
  </testcase>
</testsuite>
"""

SAMPLE_COVERAGE_JSON = json.dumps({
    "totals": {
        "covered_lines": 85,
        "num_statements": 100,
        "percent_covered": 85.0
    },
    "files": {
        "app/main.py": {
            "summary": {"percent_covered": 92.5}
        }
    }
})

SAMPLE_COVERAGE_XML = """<?xml version="1.0" ?>
<coverage version="7.5.0" timestamp="1725000000" lines-valid="50" lines-covered="44" line-rate="0.88">
  <packages>
    <package name="app" line-rate="0.88" />
  </packages>
</coverage>
"""


def test_parse_junit_xml_success():
    res = parse_junit_xml(SAMPLE_JUNIT_XML_PASS)
    assert res["tests_total"] == 8
    assert res["tests_passed"] == 8
    assert res["tests_failed"] == 0
    assert res["duration_seconds"] == 0.45


def test_parse_junit_xml_with_failures():
    res = parse_junit_xml(SAMPLE_JUNIT_XML_FAIL)
    assert res["tests_total"] == 4
    assert res["tests_failed"] == 1
    assert res["tests_skipped"] == 1
    assert res["tests_passed"] == 2
    assert len(res["test_cases"]) == 3
    failed_case = next(c for c in res["test_cases"] if c["name"] == "test_fail")
    assert failed_case["status"] == "failed"
    assert "AssertionError" in failed_case["message"]


def test_parse_junit_xml_empty_or_invalid():
    empty_res = parse_junit_xml("")
    assert empty_res["tests_total"] == 0

    invalid_res = parse_junit_xml("not valid xml content <<<")
    assert invalid_res["tests_total"] == 0
    assert "error" in invalid_res


def test_parse_coverage_json():
    res = parse_coverage_report(SAMPLE_COVERAGE_JSON)
    assert res["coverage_pct"] == 85.0
    assert res["lines_total"] == 100
    assert res["lines_covered"] == 85
    assert "app/main.py" in res["files"]


def test_parse_coverage_xml():
    res = parse_coverage_report(SAMPLE_COVERAGE_XML)
    assert res["coverage_pct"] == 88.0
    assert res["lines_total"] == 50
    assert res["lines_covered"] == 44


def test_parse_coverage_empty_or_invalid():
    empty_res = parse_coverage_report("")
    assert empty_res["coverage_pct"] == 0.0

    invalid_res = parse_coverage_report("invalid coverage text <<<")
    assert invalid_res["coverage_pct"] == 0.0
