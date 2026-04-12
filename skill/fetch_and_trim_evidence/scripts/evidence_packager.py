#!/usr/bin/env python3
"""
Evidence Packager Module
将收集的证据封装为reviewer_input模板
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def package_reviewer_input(
    task_id: str,
    git_info: Dict,
    test_results: Dict,
    trimmed_diff: str,
    trimmed_log: str,
    additional_context: Optional[Dict] = None
) -> Dict:
    """
    封装为reviewer_input模板

    Args:
        task_id: 任务ID
        git_info: Git信息 (来自git_capture)
        test_results: 测试结果 (来自test_parser)
        trimmed_diff: 裁剪后的diff
        trimmed_log: 裁剪后的日志
        additional_context: 额外上下文

    Returns:
        {
            "task_id": str,
            "metadata": Dict,
            "content": str,  # Markdown格式
            "artifacts": Dict
        }
    """
    # 构建元数据
    metadata = {
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
        "git": {
            "commit_hash": git_info.get("commit_hash"),
            "branch": git_info.get("branch"),
            "changed_files_count": len(git_info.get("changed_files", [])),
            "diff_summary": git_info.get("diff_summary", "")
        },
        "test": {
            "passed": test_results.get("passed"),
            "total_tests": test_results.get("total_tests"),
            "failed_tests": test_results.get("failed_tests"),
            "coverage_percent": test_results.get("coverage_percent")
        }
    }

    # 添加额外上下文
    if additional_context:
        metadata.update(additional_context)

    # 构建Markdown内容
    content = format_reviewer_input_markdown(
        task_id=task_id,
        git_info=git_info,
        test_results=test_results,
        trimmed_diff=trimmed_diff,
        trimmed_log=trimmed_log
    )

    # 构建artifacts
    artifacts = {
        "git_diff": trimmed_diff,
        "test_results": test_results,
        "build_log": trimmed_log,
        "changed_files": git_info.get("changed_files", [])
    }

    return {
        "task_id": task_id,
        "metadata": metadata,
        "content": content,
        "artifacts": artifacts
    }


def format_reviewer_input_markdown(
    task_id: str,
    git_info: Dict,
    test_results: Dict,
    trimmed_diff: str,
    trimmed_log: str
) -> str:
    """
    将审查输入格式化为Markdown
    """
    md = f"""# Code Review Request

## Task Information
- **Task ID**: {task_id}
- **Timestamp**: {datetime.now().isoformat()}

## Git Information

### Commit Details
- **Commit Hash**: `{git_info.get("commit_hash", "N/A")}`
- **Branch**: {git_info.get("branch", "N/A")}

### Changed Files
"""

    # 添加变更文件列表
    changed_files = git_info.get("changed_files", [])
    if changed_files:
        md += f"\nTotal changes: **{len(changed_files)}** files\n\n"
        for file_path in changed_files[:20]:  # 最多显示20个文件
            md += f"- `{file_path}`\n"
        if len(changed_files) > 20:
            md += f"- ... and {len(changed_files) - 20} more files\n"
    else:
        md += "\nNo files changed or git info unavailable.\n"

    # 添加diff摘要
    diff_summary = git_info.get("diff_summary", "")
    if diff_summary:
        md += f"\n### Diff Summary\n```\n{diff_summary}\n```\n"

    # 添加测试结果
    md += "\n## Test Results\n\n"

    test_passed = test_results.get("passed", True)
    test_icon = "✅" if test_passed else "❌"

    md += f"### Status: {test_icon} **{'PASSED' if test_passed else 'FAILED'}**\n\n"

    total_tests = test_results.get("total_tests", 0)
    failed_tests = test_results.get("failed_tests", 0)
    passed_tests = total_tests - failed_tests

    md += f"- **Total Tests**: {total_tests}\n"
    md += f"- **Passed**: {passed_tests}\n"
    md += f"- **Failed**: {failed_tests}\n"

    if test_results.get("skipped_tests", 0) > 0:
        md += f"- **Skipped**: {test_results.get('skipped_tests')}\n"

    coverage = test_results.get("coverage_percent")
    if coverage is not None:
        md += f"- **Coverage**: {coverage:.1f}%\n"

    # 添加测试摘要
    test_summary = test_results.get("test_summary", "")
    if test_summary:
        md += f"\n**Summary**: {test_summary}\n"

    # 添加失败的测试用例
    failed_cases = test_results.get("failed_test_cases", [])
    if failed_cases:
        md += "\n### Failed Test Cases\n\n"
        for i, case in enumerate(failed_cases[:10], 1):  # 最多显示10个
            md += f"#### {i}. {case.get('name', 'unknown')}\n"
            if case.get('nodeid'):
                md += f"**Location**: `{case.get('nodeid')}`\n"
            if case.get('traceback'):
                md += f"```\n{case.get('traceback')[:500]}\n```\n"  # 限制traceback长度
        if len(failed_cases) > 10:
            md += f"\n... and {len(failed_cases) - 10} more failed tests\n"

    # 添加代码diff
    if trimmed_diff:
        md += "\n## Code Diff\n\n"
        md += "```diff\n"
        md += trimmed_diff
        md += "\n```\n"

    # 添加构建日志
    if trimmed_log:
        md += "\n## Build/Test Log\n\n"
        md += "```\n"
        md += trimmed_log
        md += "\n```\n"

    # 添加审查指导
    md += """
## Review Guidance

Please review the above changes and test results:

1. **Code Quality**: Check for bugs, security issues, and code smells
2. **Test Coverage**: Ensure tests cover critical paths
3. **Documentation**: Verify comments and docstrings are clear
4. **Best Practices**: Follow language-specific conventions

### Required Output Format

Your review must include:
- **Severity**: critical | major | minor | info
- **Lethal Flaw**: Detailed description of any critical issues
- **Exploit Path**: Step-by-step reproduction for security issues
- **Evidence**: Reference to specific test cases or code lines
- **Recommendation**: go | no-go | conditional
"""

    return md


def save_evidence_to_file(evidence: Dict, output_path: Path) -> None:
    """
    将证据保存到文件

    Args:
        evidence: 封装后的证据
        output_path: 输出文件路径
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(evidence["content"])


def load_evidence_from_file(input_path: Path) -> Dict:
    """
    从文件加载证据

    Args:
        input_path: 输入文件路径

    Returns:
        证据字典
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return {
        "task_id": "unknown",
        "content": content,
        "source_file": str(input_path)
    }


if __name__ == "__main__":
    # 测试代码
    import sys

    # 模拟数据
    git_info = {
        "commit_hash": "abc123",
        "branch": "main",
        "changed_files": ["src/main.py", "tests/test_main.py"],
        "diff_summary": "2 files changed, 10 insertions(+), 5 deletions(-)"
    }

    test_results = {
        "passed": False,
        "total_tests": 15,
        "failed_tests": 2,
        "skipped_tests": 1,
        "test_summary": "12 passed, 2 failed, 1 skipped",
        "coverage_percent": 85.5,
        "failed_test_cases": [
            {
                "name": "test_login",
                "nodeid": "tests/test_auth.py::test_login",
                "traceback": "AssertionError: Expected 200, got 401"
            }
        ]
    }

    evidence = package_reviewer_input(
        task_id="T-001",
        git_info=git_info,
        test_results=test_results,
        trimmed_diff="+ def new_function():\n- old code",
        trimmed_log="Running tests...\nERROR: test failed"
    )

    print(evidence["content"])
