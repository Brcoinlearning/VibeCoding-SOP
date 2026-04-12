---
name: fetch-and-trim-evidence
description: Use when performing code review workflows that require collecting git diffs, test results, and evidence packaging. Triggered by test failures, review requests, or when Builder Agent needs to prepare evidence for Reviewer Agent. Automatically captures git status, parses test reports (pytest_results.json, test-results.xml), trims oversized logs, and packages into reviewer_input template.
---

# Fetch and Trim Evidence

## Overview

证据采集与裁剪工具 - 将MCP Server的监听器(Listener)、裁剪器(Trimmer)和封装器(Packager)功能转换为被动工具。

当测试失败或需要审查时，Agent主动调用此工具执行Git Diff获取、测试报告读取和日志裁剪。

## When to Use

```
                    收到审查请求
                          |
            +-------------+-------------+
            |                           |
       测试失败                     人工触发
            |                           |
            v                           v
    需要准备审查证据            需要代码变更快照
            |                           |
            +-------------+-------------+
                          |
                  调用此Skill
```

**触发条件:**
- pytest测试运行后，有失败用例
- 需要进行代码审查前
- Git提交需要review时
- CI/CD流程中收集证据阶段

**输出:** 规范化的reviewer_input模板，包含裁剪后的diff、测试结果和关键错误栈

## Core Pattern

### Before (MCP Event-Driven)
```python
# 被动监听 - 系统自动触发
class GitListener:
    async def on_push(self, event):
        evidence = await self.collect()
        await queue.route(evidence)
```

### After (Skill Tool-Driven)
```python
# 主动调用 - Agent控制流程
def fetch_and_trim_evidence(repo_path, commit=None):
    """Agent主动调用收集证据"""
    git_info = capture_git_status(repo_path, commit)
    test_results = parse_test_reports(repo_path)
    trimmed = trim_logs_and_diffs(git_info, test_results)
    return package_reviewer_input(trimmed)
```

## Quick Reference

| 功能 | 原MCP组件 | Skill实现 |
|------|----------|----------|
| Git状态捕获 | `Listener.git_poller` | `capture_git_status()` |
| 测试结果解析 | `Listener.test_watcher` | `parse_test_reports()` |
| 日志裁剪 | `Trimmer.trim_build_output()` | `trim_logs_and_diffs()` |
| 证据封装 | `Packager.create_reviewer_input()` | `package_reviewer_input()` |

## Implementation

### Scripts Location
所有可执行脚本位于 `scripts/` 目录:
- `git_capture.py` - Git状态和diff获取
- `test_parser.py` - 测试结果解析
- `log_trimmer.py` - 日志和diff裁剪
- `evidence_packager.py` - 证据封装

### Key Functions

```python
# scripts/git_capture.py
def capture_git_status(repo_path: Path, commit: str = None) -> dict:
    """
    捕获Git状态信息

    Returns:
        {
            "commit_hash": str,
            "branch": str,
            "changed_files": List[str],
            "diff_summary": str,
            "full_diff": str
        }
    """

# scripts/test_parser.py
def parse_test_reports(repo_path: Path) -> dict:
    """
    解析测试报告文件

    查找顺序:
    1. pytest_results.json
    2. test-results.xml
    3. .pytest_cache/results.json

    Returns:
        {
            "passed": bool,
            "total_tests": int,
            "failed_tests": int,
            "test_summary": str,
            "coverage_percent": float,
            "failed_test_cases": List[dict]
        }
    """

# scripts/log_trimmer.py
def trim_logs_and_diffs(
    build_log: str,
    diff_content: str,
    max_log_lines: int = 100,
    max_diff_chars: int = 50000
) -> tuple[str, str]:
    """
    裁剪日志和diff以控制上下文大小

    保留策略:
    - 日志: 保留错误栈，移除重复信息
    - Diff: 保留变更统计，裁剪大文件

    Returns:
        (trimmed_log, trimmed_diff)
    """

# scripts/evidence_packager.py
def package_reviewer_input(
    task_id: str,
    git_info: dict,
    test_results: dict,
    trimmed_diff: str,
    trimmed_log: str
) -> dict:
    """
    封装为reviewer_input模板

    Returns:
        {
            "task_id": str,
            "metadata": {...},
            "content": str,  # Markdown格式
            "artifacts": {...}
        }
    """
```

## Usage Flow

```python
# Agent调用示例
from scripts.git_capture import capture_git_status
from scripts.test_parser import parse_test_reports
from scripts.log_trimmer import trim_logs_and_diffs
from scripts.evidence_packager import package_reviewer_input

# 1. 收集证据
repo_path = Path("/path/to/repo")
git_info = capture_git_status(repo_path)
test_results = parse_test_reports(repo_path)

# 2. 裁剪数据
trimmed_log, trimmed_diff = trim_logs_and_diffs(
    build_log="",
    diff_content=git_info["full_diff"]
)

# 3. 封装证据
evidence = package_reviewer_input(
    task_id="T-001",
    git_info=git_info,
    test_results=test_results,
    trimmed_diff=trimmed_diff,
    trimmed_log=trimmed_log
)

# 4. 返回给Agent使用
return evidence
```

## Log Trimming Logic

### 关键: 必须保留原有限幅逻辑

原始MCP系统中的日志裁剪逻辑必须完整保留，防止上下文超载：

```python
def trim_build_output(build_log: str, diff_content: str) -> tuple:
    """
    裁剪构建输出

    策略:
    1. 提取关键错误栈 (Traceback, ERROR, FATAL)
    2. 移除重复的进度信息
    3. 保留最后N行 (通常包含最终状态)
    4. 限制总字符数
    """

    # 提取错误栈
    error_lines = []
    for line in build_log.split('\n'):
        if any(keyword in line for keyword in ['Traceback', 'ERROR', 'FATAL', 'Failed']):
            error_lines.append(line)

    # 限制行数
    log_summary = '\n'.join(error_lines[-100:])  # 最后100行错误

    # 裁剪diff
    if len(diff_content) > 50000:
        # 保留文件统计
        lines = diff_content.split('\n')
        summary_lines = []
        for line in lines:
            if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
                summary_lines.append(line)
            elif line.startswith('+') or line.startswith('-'):
                summary_lines.append(line)

        diff_summary = '\n'.join(summary_lines[:1000])  # 前1000行变更
    else:
        diff_summary = diff_content

    return log_summary, diff_summary
```

## Test Result Parsing

支持多种测试报告格式：

### pytest_results.json
```json
{
    "summary": {
        "passed": 45,
        "failed": 3,
        "total": 48,
        "duration": 12.5
    },
    "tests": [
        {
            "name": "test_user_login",
            "outcome": "failed",
            "traceback": "AssertionError: ..."
        }
    ],
    "coverage": {
        "percent_covered": 78.5
    }
}
```

### test-results.xml
```xml
<testsuites>
    <testsuite tests="48" failures="3" errors="0">
        <testcase name="test_user_login">
            <failure>AssertionError: ...</failure>
        </testcase>
    </testsuite>
</testsuites>
```

## Common Mistakes

| 错误 | 原因 | 修复 |
|------|------|------|
| 上下文超载 | 未裁剪日志/大文件diff | 必须调用`trim_logs_and_diffs()` |
| 缺少测试信息 | 只获取git信息 | 同时解析测试报告 |
| 格式不统一 | 每次自定义格式 | 使用`package_reviewer_input()` |
| 缺少关键错误 | 裁剪策略过于激进 | 保留完整错误栈 |

## Real-World Impact

**原始MCP系统问题:**
- 异步事件循环复杂
- 调试困难(需追踪EventBus)
- 依赖后台守护进程

**转换为Skill后:**
- 简单函数调用
- 直接查看调用栈
- 按需执行，无需常驻
- 代码量减少60%+

## Files Structure

```
fetch_and_trim_evidence/
├── SKILL.md                    # 本文件
└── scripts/
    ├── git_capture.py          # Git状态捕获
    ├── test_parser.py          # 测试结果解析
    ├── log_trimmer.py          # 日志裁剪
    └── evidence_packager.py    # 证据封装
```

## Integration with Other Skills

此Skill是审查工作流的第一步:

```
fetch_and_trim_evidence (本Skill)
         ↓
execute_structured_review (下一个Skill)
         ↓
archive_review_artifact (最后一步)
```

**输出格式** 确保与 `execute_structured_review` Skill的输入schema兼容。
