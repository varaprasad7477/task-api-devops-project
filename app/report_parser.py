import json
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional


def parse_junit_xml(source: str) -> Dict[str, Any]:
    """
    Parses a JUnit XML report (from file path or raw XML string).
    Returns a dict with test metrics: total, passed, failed, errors, skipped, duration.
    """
    if not source:
        return {
            "tests_total": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_errors": 0,
            "tests_skipped": 0,
            "duration_seconds": 0.0,
            "test_cases": []
        }

    try:
        if os.path.exists(source):
            tree = ET.parse(source)
            root = tree.getroot()
        else:
            root = ET.fromstring(source)
    except Exception as e:
        return {
            "error": f"Failed to parse JUnit XML: {str(e)}",
            "tests_total": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_errors": 0,
            "tests_skipped": 0,
            "duration_seconds": 0.0,
            "test_cases": []
        }

    # Handle both <testsuites> wrapper and single <testsuite> root
    testsuites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    if not testsuites and root.tag != "testsuite":
        # Maybe root is testsuites but has no children or attributes on root
        testsuites = [root]

    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    total_time = 0.0
    test_cases = []

    for suite in testsuites:
        try:
            total_tests += int(suite.attrib.get("tests", 0))
            total_failures += int(suite.attrib.get("failures", 0))
            total_errors += int(suite.attrib.get("errors", 0))
            total_skipped += int(suite.attrib.get("skipped", 0))
            total_time += float(suite.attrib.get("time", 0.0))
        except (ValueError, TypeError):
            pass

        for case in suite.findall("testcase"):
            name = case.attrib.get("name", "unknown")
            classname = case.attrib.get("classname", "")
            time_sec = float(case.attrib.get("time", 0.0))
            failure = case.find("failure")
            error = case.find("error")
            skipped = case.find("skipped")

            status = "passed"
            message = ""
            if failure is not None:
                status = "failed"
                message = failure.attrib.get("message", failure.text or "Test failed")
            elif error is not None:
                status = "error"
                message = error.attrib.get("message", error.text or "Test error")
            elif skipped is not None:
                status = "skipped"
                message = skipped.attrib.get("message", skipped.text or "Test skipped")

            test_cases.append({
                "name": name,
                "classname": classname,
                "time_seconds": time_sec,
                "status": status,
                "message": message
            })

    # If suite attributes were 0/missing, infer from test_cases
    if total_tests == 0 and test_cases:
        total_tests = len(test_cases)
        total_failures = sum(1 for c in test_cases if c["status"] == "failed")
        total_errors = sum(1 for c in test_cases if c["status"] == "error")
        total_skipped = sum(1 for c in test_cases if c["status"] == "skipped")
        total_time = sum(c["time_seconds"] for c in test_cases)

    failed_and_errors = total_failures + total_errors
    passed = max(0, total_tests - failed_and_errors - total_skipped)

    return {
        "tests_total": total_tests,
        "tests_passed": passed,
        "tests_failed": failed_and_errors,
        "tests_errors": total_errors,
        "tests_skipped": total_skipped,
        "duration_seconds": round(total_time, 3),
        "test_cases": test_cases
    }


def parse_coverage_report(source: str) -> Dict[str, Any]:
    """
    Parses a coverage report from file path or raw string.
    Supports coverage JSON format or coverage XML (Cobertura format).
    """
    if not source:
        return {"coverage_pct": 0.0, "lines_total": 0, "lines_covered": 0}

    # Attempt JSON parsing first
    try:
        content = ""
        if os.path.exists(source):
            with open(source, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = source

        data = json.loads(content)
        totals = data.get("totals", {})
        cov_pct = float(totals.get("percent_covered", 0.0))
        lines_total = int(totals.get("num_statements", 0))
        lines_covered = int(totals.get("covered_lines", 0))
        return {
            "coverage_pct": round(cov_pct, 2),
            "lines_total": lines_total,
            "lines_covered": lines_covered,
            "files": {
                k: round(v.get("summary", {}).get("percent_covered", 0.0), 2)
                for k, v in data.get("files", {}).items()
            }
        }
    except Exception:
        pass

    # Attempt XML Cobertura parsing
    try:
        if os.path.exists(source):
            tree = ET.parse(source)
            root = tree.getroot()
        else:
            root = ET.fromstring(source)

        line_rate = root.attrib.get("line-rate")
        lines_valid = root.attrib.get("lines-valid", 0)
        lines_covered = root.attrib.get("lines-covered", 0)

        if line_rate is not None:
            cov_pct = round(float(line_rate) * 100.0, 2)
        elif int(lines_valid) > 0:
            cov_pct = round((int(lines_covered) / int(lines_valid)) * 100.0, 2)
        else:
            cov_pct = 0.0

        return {
            "coverage_pct": cov_pct,
            "lines_total": int(lines_valid),
            "lines_covered": int(lines_covered)
        }
    except Exception as e:
        return {
            "error": f"Failed to parse coverage report: {str(e)}",
            "coverage_pct": 0.0,
            "lines_total": 0,
            "lines_covered": 0
        }
