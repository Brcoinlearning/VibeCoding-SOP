#!/usr/bin/env python3
"""
Report Generator Module
生成结构化的审查报告
"""
from datetime import datetime
from typing import Dict, Any, Optional
from .review_validator import validate_review_input, check_severity_consistency
from .flaw_detector import generate_flaw_report


def execute_structured_review(
    evidence: Dict,
    review_data: Dict,
    reviewer_id: Optional[str] = None
) -> Dict:
    """
    执行结构化审查

    Args:
        evidence: 来自fetch_and_trim_evidence的输出
        review_data: Agent填写的审查结果
        reviewer_id: 审查者ID

    Returns:
        审查报告
    """
    # 验证输入
    is_valid, error_message, warnings = validate_review_input(review_data)

    if not is_valid:
        raise ValueError(f"Invalid review input: {error_message}")

    # 检查严重级别一致性
    if "lethal_flaw" in review_data and "severity" in review_data:
        consistent, consistency_msg = check_severity_consistency(
            review_data["lethal_flaw"],
            review_data["severity"]
        )
        if not consistent:
            # 添加为警告而非错误
            warnings.append(consistency_msg)

    # 生成报告
    report = {
        "task_id": evidence.get("task_id", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "reviewer_id": reviewer_id or "unknown",
        "evidence_metadata": evidence.get("metadata", {}),
        "review": review_data,
        "warnings": warnings,
        "status": "completed"
    }

    return report


def format_review_as_markdown(report: Dict) -> str:
    """
    将审查报告格式化为Markdown

    Args:
        report: 审查报告

    Returns:
        Markdown格式的报告
    """
    review = report["review"]

    md = f"""# Code Review Report

## Task Information
- **Task ID**: {report['task_id']}
- **Timestamp**: {report['timestamp']}
- **Reviewer**: {report.get('reviewer_id', 'N/A')}

---

## Review Summary

### Severity: {review.get('severity', 'N/A').upper()}

"""

    # 严重级别图标
    severity_icons = {
        "critical": "🔴",
        "major": "🟠",
        "minor": "🟡",
        "info": "🔵"
    }
    severity = review.get("severity", "info")
    icon = severity_icons.get(severity, "⚪")
    md += f"**Status**: {icon} {severity.upper()}\n\n"

    # 致命缺陷
    md += f"""### Lethal Flaw
{review.get('lethal_flaw', 'None identified')}

### Exploit Path
```{review.get('exploit_path', 'N/A')}
```

### Evidence

"""

    # 证据信息
    evidence = review.get("evidence", {})
    md += f"""| Field | Value |
|-------|-------|
| **Test Case** | `{evidence.get('test_case', 'N/A')}` |
| **File** | `{evidence.get('file_path', 'N/A')}` |
| **Line** | {evidence.get('line_number', 'N/A')} |
"""

    if evidence.get('code_snippet'):
        md += f"""| **Code** | ```{evidence.get('code_snippet')}``` |\n"""

    if evidence.get('test_output'):
        md += f"""| **Test Output** | ```{evidence.get('test_output')[:200]}...``` |\n"""

    # 建议
    md += f"""

---

## Recommendation: {review.get('recommendation', 'N/A').upper()}

"""

    recommendation = review.get("recommendation", "")
    if recommendation == "go":
        md += "✅ **APPROVED** - Code is ready to merge\n"
    elif recommendation == "no-go":
        md += "❌ **REJECTED** - Code must be fixed before merging\n"
    else:
        md += "⚠️ **CONDITIONAL** - Address the conditions before merging\n"

    # 修复建议
    remediation = review.get("remediation", "")
    if remediation:
        md += f"""

### Remediation
{remediation}
"""

    # 警告
    warnings = report.get("warnings", [])
    if warnings:
        md += "\n### Warnings\n"
        for warning in warnings:
            md += f"- ⚠️ {warning}\n"

    # Git信息
    git_info = report.get("evidence_metadata", {}).get("git", {})
    if git_info:
        md += f"""

---

## Git Information
| Field | Value |
|-------|-------|
| **Commit** | `{git_info.get('commit_hash', 'N/A')}` |
| **Branch** | {git_info.get('branch', 'N/A')} |
| **Files Changed** | {git_info.get('changed_files_count', 0)} |
"""

    # 测试信息
    test_info = report.get("evidence_metadata", {}).get("test", {})
    if test_info:
        md += f"""

## Test Information
| Field | Value |
|-------|-------|
| **Status** | {'✅ PASSED' if test_info.get('passed') else '❌ FAILED'} |
| **Total Tests** | {test_info.get('total_tests', 0)} |
| **Failed Tests** | {test_info.get('failed_tests', 0)} |
"""

        coverage = test_info.get('coverage_percent')
        if coverage is not None:
            md += f"| **Coverage** | {coverage:.1f}% |\n"

    return md


def save_report_to_file(report: Dict, output_path: str) -> None:
    """
    保存报告到文件

    Args:
        report: 审查报告
        output_path: 输出文件路径
    """
    import json
    from pathlib import Path

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # 保存JSON格式
    json_path = output.with_suffix('.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 保存Markdown格式
    md_path = output.with_suffix('.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(format_review_as_markdown(report))


def create_review_summary(report: Dict) -> str:
    """
    创建审查摘要 (用于通知)

    Args:
        report: 审查报告

    Returns:
        摘要文本
    """
    review = report["review"]
    severity = review.get("severity", "info")
    recommendation = review.get("recommendation", "pending")

    summary = f"""📋 Code Review Complete

Task: {report['task_id']}
Severity: {severity.upper()}
Decision: {recommendation.upper()}
"""

    if review.get("lethal_flaw"):
        summary += f"\nIssue: {review['lethal_flaw'][:100]}..."

    return summary


if __name__ == "__main__":
    # 测试代码
    test_evidence = {
        "task_id": "T-001",
        "metadata": {
            "git": {
                "commit_hash": "abc123",
                "branch": "main",
                "changed_files_count": 2
            },
            "test": {
                "passed": False,
                "total_tests": 15,
                "failed_tests": 2
            }
        }
    }

    test_review = {
        "severity": "critical",
        "lethal_flaw": "SQL注入漏洞: 用户登录接口未做参数化查询",
        "exploit_path": "步骤1: 访问 /api/login\n步骤2: 输入 username=admin'--\n步骤3: 成功绕过认证",
        "evidence": {
            "test_case": "test_login_sql_injection",
            "file_path": "auth/login.py",
            "line_number": 42,
            "code_snippet": "query = f\"SELECT * FROM users WHERE username='{username}'\""
        },
        "recommendation": "no-go",
        "remediation": "使用参数化查询: cursor.execute(\"SELECT * FROM users WHERE username=%s\", (username,))"
    }

    report = execute_structured_review(test_evidence, test_review, "reviewer-1")
    print(format_review_as_markdown(report))
