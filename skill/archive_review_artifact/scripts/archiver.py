#!/usr/bin/env python3
"""
Archiver Module
归档审查产物到文件系统
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import yaml


def format_review_as_markdown_inline(report_result: dict) -> str:
    """
    将审查报告格式化为Markdown (内联实现，避免跨目录导入)

    Args:
        report_result: 审查报告字典

    Returns:
        Markdown格式的内容
    """
    review = report_result.get("review", {})

    md = f"""# Code Review Report

## Task Information
- **Task ID**: {report_result.get('task_id', 'N/A')}
- **Timestamp**: {report_result.get('timestamp', 'N/A')}
- **Reviewer**: {report_result.get('reviewer_id', 'N/A')}

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
```
{review.get('exploit_path', 'N/A')}
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
        snippet = str(evidence.get('code_snippet', ''))[:100]
        md += f"| **Code** | ```{snippet}``` |\n"

    if evidence.get('test_output'):
        output = str(evidence.get('test_output', ''))[:200]
        md += f"| **Test Output** | ```{output}...``` |\n"

    # 建议
    md += """

---

## Recommendation: """ + review.get('recommendation', 'N/A').upper() + """

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

    # Git信息
    evidence_metadata = report_result.get("evidence_metadata", {})
    git_info = evidence_metadata.get("git", {})
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
    test_info = evidence_metadata.get("test", {})
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


def determine_archive_path(
    decision: str,
    base_path: Optional[Path] = None
) -> Path:
    """
    根据决策确定归档路径

    Args:
        decision: "go", "no-go", "conditional"
        base_path: 基础路径

    Returns:
        归档目录路径
    """
    if base_path is None:
        base_path = Path("archive/reviews")

    decision_map = {
        "go": base_path / "approved",
        "no-go": base_path / "rejected",
        "conditional": base_path / "pending",
        "pending": base_path / "pending"
    }

    return decision_map.get(decision.lower(), base_path / "pending")


def generate_filename(review_result: Dict) -> str:
    """
    生成归档文件名

    格式: {task_id}_{timestamp}_{decision}.md
    示例: T-001_20250412_103000_go.md
    """
    task_id = review_result.get("task_id", "UNKNOWN")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    recommendation = review_result.get("review", {}).get("recommendation", "pending")

    return f"{task_id}_{timestamp}_{recommendation}.md"


def write_with_frontmatter(
    filepath: Path,
    content: str,
    metadata: Dict
) -> None:
    """
    写入带有Frontmatter的文件

    Args:
        filepath: 文件路径
        content: 文件内容
        metadata: Frontmatter元数据
    """
    # 确保目录存在
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # 生成Frontmatter
    frontmatter = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)
    full_content = f"---\n{frontmatter}---\n\n{content}"

    # 写入文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_content)


def parse_frontmatter(content: str) -> Dict:
    """
    解析Frontmatter元数据

    Args:
        content: 文件内容

    Returns:
        元数据字典
    """
    import re

    frontmatter_pattern = r'^---\n(.*?)\n---'
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if match:
        try:
            return yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            return {}

    return {}


def archive_review_artifact(
    review_result: Dict,
    decision: str,
    additional_metadata: Optional[Dict] = None,
    base_path: Optional[Path] = None
) -> Dict:
    """
    归档审查产物

    Args:
        review_result: 来自execute_structured_review的输出
        decision: Go/No-Go决策
        additional_metadata: 额外元数据
        base_path: 基础归档路径

    Returns:
        {
            "success": bool,
            "filepath": str,
            "archive_id": str,
            "error": str (如果失败)
        }
    """
    try:
        # 确定归档路径
        archive_dir = determine_archive_path(decision, base_path)

        # 生成文件名
        filename = generate_filename(review_result)
        filepath = archive_dir / filename

        # 准备元数据
        metadata = {
            "task_id": review_result.get("task_id"),
            "timestamp": datetime.now().isoformat(),
            "decision": decision,
            "severity": review_result.get("review", {}).get("severity"),
            "recommendation": review_result.get("review", {}).get("recommendation"),
            "reviewer": review_result.get("reviewer_id", "unknown"),
            "archive_id": f"{review_result.get('task_id')}_{int(datetime.now().timestamp())}"
        }

        # 添加Git和测试信息
        evidence_metadata = review_result.get("evidence_metadata", {})
        if evidence_metadata.get("git"):
            metadata["git"] = evidence_metadata["git"]
        if evidence_metadata.get("test"):
            metadata["test"] = evidence_metadata["test"]

        # 添加额外元数据
        if additional_metadata:
            metadata.update(additional_metadata)

        # 生成Markdown内容 (内联实现，避免跨目录导入)
        content = format_review_as_markdown_inline(review_result)

        # 写入文件
        write_with_frontmatter(filepath, content, metadata)

        return {
            "success": True,
            "filepath": str(filepath),
            "archive_id": metadata["archive_id"]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "filepath": None,
            "archive_id": None
        }


def archive_diff_artifact(
    task_id: str,
    diff_content: str,
    base_path: Optional[Path] = None
) -> Dict:
    """
    归档代码diff

    Args:
        task_id: 任务ID
        diff_content: diff内容
        base_path: 基础归档路径

    Returns:
        归档结果
    """
    try:
        if base_path is None:
            base_path = Path("archive/artifacts/diffs")

        base_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{task_id}_{timestamp}_diff.patch"
        filepath = base_path / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(diff_content)

        return {
            "success": True,
            "filepath": str(filepath)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def archive_test_results(
    task_id: str,
    test_results: Dict,
    base_path: Optional[Path] = None
) -> Dict:
    """
    归档测试结果

    Args:
        task_id: 任务ID
        test_results: 测试结果字典
        base_path: 基础归档路径

    Returns:
        归档结果
    """
    import json

    try:
        if base_path is None:
            base_path = Path("archive/artifacts/test_results")

        base_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{task_id}_{timestamp}_test_results.json"
        filepath = base_path / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)

        return {
            "success": True,
            "filepath": str(filepath)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def list_archived_reviews(
    base_path: Optional[Path] = None,
    decision: Optional[str] = None
) -> list:
    """
    列出已归档的审查

    Args:
        base_path: 基础归档路径
        decision: 过滤决策类型

    Returns:
        归档列表
    """
    if base_path is None:
        base_path = Path("archive/reviews")

    if decision:
        search_path = determine_archive_path(decision, base_path.parent)
    else:
        search_path = base_path

    if not search_path.exists():
        return []

    reviews = []
    for file_path in search_path.glob("*.md"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                metadata = parse_frontmatter(content)

            reviews.append({
                "filepath": str(file_path),
                "filename": file_path.name,
                "metadata": metadata
            })
        except Exception:
            continue

    # 按时间戳排序 (最新的在前)
    reviews.sort(
        key=lambda x: x["metadata"].get("timestamp", ""),
        reverse=True
    )

    return reviews


def get_review_stats(base_path: Optional[Path] = None) -> Dict:
    """
    获取归档统计信息

    Args:
        base_path: 基础归档路径

    Returns:
        统计信息
    """
    if base_path is None:
        base_path = Path("archive/reviews")

    stats = {
        "total": 0,
        "approved": 0,
        "rejected": 0,
        "pending": 0,
        "by_severity": {
            "critical": 0,
            "major": 0,
            "minor": 0,
            "info": 0
        }
    }

    for decision in ["approved", "rejected", "pending"]:
        decision_path = determine_archive_path(decision, base_path)

        if decision_path.exists():
            files = list(decision_path.glob("*.md"))
            stats[decision] = len(files)
            stats["total"] += len(files)

            # 统计严重级别
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        metadata = parse_frontmatter(f.read())

                    severity = metadata.get("severity", "info")
                    if severity in stats["by_severity"]:
                        stats["by_severity"][severity] += 1
                except Exception:
                    continue

    return stats


if __name__ == "__main__":
    # 测试代码
    test_review = {
        "task_id": "T-001",
        "timestamp": datetime.now().isoformat(),
        "reviewer_id": "reviewer-1",
        "review": {
            "severity": "critical",
            "lethal_flaw": "SQL注入漏洞",
            "exploit_path": "步骤1: ...\n步骤2: ...",
            "evidence": {"test_case": "test_sql_injection"},
            "recommendation": "no-go",
            "remediation": "使用参数化查询"
        },
        "evidence_metadata": {
            "git": {
                "commit_hash": "abc123",
                "branch": "main"
            },
            "test": {
                "passed": False,
                "total_tests": 15
            }
        }
    }

    result = archive_review_artifact(test_review, "no-go")
    if result["success"]:
        print(f"Archived to: {result['filepath']}")
        print(f"Archive ID: {result['archive_id']}")
    else:
        print(f"Error: {result['error']}")
