#!/usr/bin/env python3
"""
Test Parser Module
解析测试报告文件
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional


def parse_test_reports(repo_path: Path) -> Dict:
    """
    解析测试报告文件

    查找顺序:
    1. pytest_results.json
    2. test-results.xml
    3. .pytest_cache/results.json

    Args:
        repo_path: 仓库路径

    Returns:
        {
            "passed": bool,
            "total_tests": int,
            "failed_tests": int,
            "test_summary": str,
            "coverage_percent": Optional[float],
            "failed_test_cases": List[Dict]
        }
    """
    # 定义查找路径
    test_paths = [
        repo_path / "pytest_results.json",
        repo_path / "test-results.xml",
        repo_path / ".pytest_cache" / "results.json",
        repo_path / "coverage.json",
    ]

    for test_path in test_paths:
        if test_path.exists():
            if test_path.suffix == ".json":
                return parse_json_report(test_path)
            elif test_path.suffix == ".xml":
                return parse_xml_report(test_path)

    # 未找到测试报告
    return {
        "passed": True,
        "total_tests": 0,
        "failed_tests": 0,
        "test_summary": "No test results found",
        "coverage_percent": None,
        "failed_test_cases": []
    }


def parse_json_report(report_path: Path) -> Dict:
    """
    解析JSON格式的测试报告

    支持格式:
    - pytest_results.json
    - coverage.json
    """
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 判断是pytest还是coverage
        if "summary" in data or "tests" in data:
            return parse_pytest_json(data)
        elif "percent_covered" in data or "coverage" in data:
            return parse_coverage_json(data)
        else:
            return parse_generic_json(data)

    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in {report_path}: {e}")


def parse_pytest_json(data: Dict) -> Dict:
    """
    解析pytest JSON结果
    """
    summary = data.get("summary", {})
    tests = data.get("tests", [])

    total_tests = summary.get("total", len(tests))
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)

    # 提取失败的测试用例
    failed_test_cases = []
    for test in tests:
        if test.get("outcome") == "failed":
            failed_test_cases.append({
                "name": test.get("name", "unknown"),
                "nodeid": test.get("nodeid", ""),
                "traceback": test.get("call", {}).get("traceback", ""),
                "duration": test.get("duration", 0)
            })

    return {
        "passed": failed == 0,
        "total_tests": total_tests,
        "failed_tests": failed,
        "skipped_tests": skipped,
        "test_summary": f"Ran {total_tests} tests: {passed} passed, {failed} failed, {skipped} skipped",
        "coverage_percent": summary.get("coverage"),
        "failed_test_cases": failed_test_cases
    }


def parse_coverage_json(data: Dict) -> Dict:
    """
    解析coverage JSON结果
    """
    # 安全获取coverage百分比，处理None值
    percent = data.get("percent_covered") or data.get("coverage", {}).get("percent")

    # 格式化summary，处理None情况
    if percent is not None:
        test_summary = f"Coverage: {percent:.1f}%"
    else:
        test_summary = "Coverage: N/A"

    return {
        "passed": True,
        "total_tests": 0,
        "failed_tests": 0,
        "test_summary": test_summary,
        "coverage_percent": percent,
        "failed_test_cases": []
    }


def parse_generic_json(data: Dict) -> Dict:
    """
    解析通用JSON结果
    """
    passed = data.get("passed", data.get("success", True))
    total = data.get("total", data.get("tests", 0))
    failed = data.get("failed", data.get("errors", 0))

    return {
        "passed": passed,
        "total_tests": total,
        "failed_tests": failed,
        "test_summary": data.get("summary", f"{total} tests, {failed} failed"),
        "coverage_percent": data.get("coverage"),
        "failed_test_cases": data.get("failures", [])
    }


def parse_xml_report(report_path: Path) -> Dict:
    """
    解析XML格式的测试报告 (JUnit格式)
    """
    try:
        tree = ET.parse(report_path)
        root = tree.getroot()

        total_tests = 0
        failed_tests = 0
        skipped_tests = 0
        failed_test_cases = []

        # 遍历testsuites
        for testsuite in root.iter("testsuite"):
            total_tests += int(testsuite.get("tests", 0))
            failed_tests += int(testsuite.get("failures", 0))
            skipped_tests += int(testsuite.get("skipped", 0))

            # 提取失败的测试用例
            for testcase in testsuite.iter("testcase"):
                failure = testcase.find("failure")
                if failure is not None:
                    failed_test_cases.append({
                        "name": testcase.get("name", "unknown"),
                        "classname": testcase.get("classname", ""),
                        "traceback": failure.text or ""
                    })

        return {
            "passed": failed_tests == 0,
            "total_tests": total_tests,
            "failed_tests": failed_tests,
            "skipped_tests": skipped_tests,
            "test_summary": f"Ran {total_tests} tests: {total_tests - failed_tests} passed, {failed_tests} failed, {skipped_tests} skipped",
            "coverage_percent": None,
            "failed_test_cases": failed_test_cases
        }

    except ET.ParseError as e:
        raise Exception(f"Invalid XML in {report_path}: {e}")


def extract_error_stack(traceback: str, max_lines: int = 50) -> str:
    """
    从traceback中提取关键错误栈

    Args:
        traceback: 完整traceback
        max_lines: 最大行数

    Returns:
        裁剪后的错误栈
    """
    if not traceback:
        return ""

    lines = traceback.split('\n')

    # 保留关键行 (包含Error, Traceback, File等)
    key_lines = []
    for line in lines:
        if any(keyword in line for keyword in ['Traceback', 'Error', 'File', 'line', 'AssertionError', 'Exception']):
            key_lines.append(line)

    # 如果关键行太少,保留最后N行
    if len(key_lines) < 10:
        return '\n'.join(lines[-max_lines:])

    return '\n'.join(key_lines[-max_lines:])


if __name__ == "__main__":
    # 测试代码
    import sys

    if len(sys.argv) > 1:
        repo_path = Path(sys.argv[1])
    else:
        repo_path = Path.cwd()

    try:
        test_results = parse_test_reports(repo_path)
        print("Test Results:")
        print(f"  Passed: {test_results['passed']}")
        print(f"  Total: {test_results['total_tests']}")
        print(f"  Failed: {test_results['failed_tests']}")
        print(f"  Summary: {test_results['test_summary']}")
        if test_results['coverage_percent']:
            print(f"  Coverage: {test_results['coverage_percent']}%")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
