---
name: archive-review-artifact
description: Use when completing code review workflows and need to persist review results to filesystem. Automatically generates timestamps, creates properly formatted filenames, parses Frontmatter metadata, and routes to correct archive directories. Use after Reviewer Agent produces report and Owner Agent approves Go/No-Go decision. Handles file naming conflicts and maintains audit trail.
---

# Archive Review Artifact

## Overview

产物路由与状态归档工具 - 将MCP Server的路由器(Router)和Owner裁决逻辑转换为文件系统归档工具。

在完成代码审查或人类确认放行(Go)后，调用此工具将审查结论写入本地文件系统。

## When to Use

```
        审查完成
            |
    +-------+-------+
    |               |
 审查报告已生成   Go/No-Go决策
    |               |
    v               v
 调用此Skill → 文件系统归档
            |
    +-------+-------+
    |               |
 归档成功        归档失败
    |               |
    v               v
 更新状态      返回错误信息
```

**触发条件:**
- Reviewer Agent完成审查并生成报告
- Owner Agent做出Go/No-Go决策
- 需要持久化审查结论
- 需要维护审计追踪

**前置要求:** 必须先完成 `execute_structured_review` 并获得审查结果

## Core Pattern

### Before (Event Router)
```python
# MCP: 事件驱动路由
class Router:
    async def route(self, event):
        destination = self.determine_route(event)
        await self.send_to_queue(event, destination)

# 复杂的队列管理和状态跟踪
```

### After (Direct File Write)
```python
# Skill: 直接文件写入
def archive_review_artifact(review_result: dict, decision: str):
    """Agent直接调用归档"""
    filename = generate_filename(review_result)
    filepath = determine_archive_path(decision)
    write_with_frontmatter(filepath, review_result)
    return filepath
```

## Quick Reference

| 功能 | 原MCP组件 | Skill实现 |
|------|----------|----------|
| 路径计算 | `Router.determine_route()` | `determine_archive_path()` |
| 文件命名 | `Router.generate_name()` | `generate_filename()` |
| Frontmatter解析 | `Router.parse_metadata()` | `parse_frontmatter()` |
| 状态归档 | `Router.update_status()` | `write_to_filesystem()` |

## Implementation

### Directory Structure

```
archive/
├── reviews/           # 所有审查报告
│   ├── pending/       # 待决策
│   ├── approved/      # Go (已批准)
│   └── rejected/      # No-Go (已拒绝)
└── artifacts/         # 附加产物
    ├── diffs/         # 代码差异
    └── test_results/  # 测试结果
```

### Core Functions

```python
# scripts/archiver.py

def determine_archive_path(decision: str, base_path: Path = None) -> Path:
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

    return decision_map.get(decision, base_path / "pending")

def generate_filename(review_result: dict) -> str:
    """
    生成归档文件名

    格式: {task_id}_{timestamp}_{decision}.md
    示例: T-001_20250412_103000_go.md
    """
    task_id = review_result.get("task_id", "UNKNOWN")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    decision = review_result.get("recommendation", "pending")

    return f"{task_id}_{timestamp}_{decision}.md"

def parse_frontmatter(content: str) -> dict:
    """
    解析Frontmatter元数据

    支持YAML格式:
    ---
    key: value
    ---
    """
    import re
    import yaml

    frontmatter_pattern = r'^---\n(.*?)\n---'
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if match:
        try:
            return yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            return {}

    return {}

def write_with_frontmatter(filepath: Path, content: str, metadata: dict):
    """
    写入带有Frontmatter的文件

    Args:
        filepath: 文件路径
        content: 文件内容
        metadata: Frontmatter元数据
    """
    import yaml

    # 确保目录存在
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # 生成Frontmatter
    frontmatter = yaml.dump(metadata, default_flow_style=False)
    full_content = f"---\n{frontmatter}---\n\n{content}"

    # 写入文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_content)

def archive_review_artifact(
    review_result: dict,
    decision: str,
    additional_metadata: dict = None
) -> dict:
    """
    归档审查产物

    Args:
        review_result: 来自execute_structured_review的输出
        decision: Go/No-Go决策
        additional_metadata: 额外元数据

    Returns:
        {
            "success": bool,
            "filepath": str,
            "archive_id": str
        }
    """
    try:
        # 确定归档路径
        archive_dir = determine_archive_path(decision)

        # 生成文件名
        filename = generate_filename(review_result)
        filepath = archive_dir / filename

        # 准备元数据
        metadata = {
            "task_id": review_result.get("task_id"),
            "timestamp": datetime.now().isoformat(),
            "decision": decision,
            "severity": review_result.get("review", {}).get("severity"),
            "reviewer": review_result.get("reviewer_id", "unknown"),
            "archive_id": f"{review_result.get('task_id')}_{int(datetime.now().timestamp())}"
        }

        if additional_metadata:
            metadata.update(additional_metadata)

        # 生成Markdown内容
        content = format_review_as_markdown(review_result, decision)

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
            "error": str(e)
        }

def format_review_as_markdown(review_result: dict, decision: str) -> str:
    """
    将审查结果格式化为Markdown
    """
    review = review_result.get("review", {})

    md = f"""# Code Review Report

## Task Information
- **Task ID**: {review_result.get("task_id")}
- **Timestamp**: {review_result.get("timestamp")}
- **Decision**: {decision.upper()}

## Review Summary

### Severity: {review.get("severity", "N/A").upper()}

### Lethal Flaw
{review.get("lethal_flaw", "None identified")}

### Exploit Path
```
{review.get("exploit_path", "N/A")}
```

### Evidence
- **Test Case**: {review.get("evidence", {}).get("test_case", "N/A")}
- **File**: {review.get("evidence", {}).get("file_path", "N/A")}
- **Line**: {review.get("evidence", {}).get("line_number", "N/A")}

### Recommendation
{review.get("recommendation", "N/A")}

### Remediation
{review.get("remediation", "None provided")}
"""
    return md
```

## Frontmatter Schema

归档文件使用YAML Frontmatter存储元数据:

```yaml
---
task_id: T-001
timestamp: "2025-04-12T10:30:00Z"
decision: go
severity: major
reviewer: reviewer-agent
archive_id: T-001_1723456789
commit_hash: abc123def
branch: feature/user-auth
changed_files:
  - auth/login.py
  - tests/test_login.py
test_passed: false
failed_tests: 2
---
```

## Archive Workflow

```
         审查完成
              |
              v
    execute_structured_review
              |
              v
         [审查报告]
              |
         +----+----+
         |         |
      人类决策    自动决策
      (Go/No-Go)  (根据规则)
         |         |
         +----+----+
              |
              v
    archive_review_artifact (本Skill)
         - 确定路径
         - 生成文件名
         - 解析/生成Frontmatter
         - 写入文件
              |
              v
         [归档完成]
              |
              v
         返回文件路径
```

## Usage Examples

### Example 1: Approved Review
```python
review_result = {
    "task_id": "T-001",
    "timestamp": "2025-04-12T10:30:00Z",
    "review": {
        "severity": "minor",
        "lethal_flaw": "未处理异常",
        "exploit_path": "N/A",
        "evidence": {"test_case": "test_exception.py"},
        "recommendation": "go"
    }
}

decision = "go"  # 人类批准

result = archive_review_artifact(review_result, decision)
# => archive/reviews/approved/T-001_20250412_103000_go.md
```

### Example 2: Rejected Review
```python
decision = "no-go"  # 人类拒绝

result = archive_review_artifact(review_result, decision)
# => archive/reviews/rejected/T-001_20250412_103000_no-go.md
```

### Example 3: With Additional Metadata
```python
additional_metadata = {
    "commit_hash": "abc123def",
    "branch": "feature/new-auth",
    "changed_files": ["auth/login.py", "tests/test_login.py"],
    "test_passed": False,
    "failed_tests": 2
}

result = archive_review_artifact(review_result, decision, additional_metadata)
```

## File Naming Conventions

### Review Reports
```
{task_id}_{timestamp}_{decision}.md
示例: T-001_20250412_103000_go.md
```

### Diffs
```
{task_id}_{timestamp}_diff.patch
示例: T-001_20250412_103000_diff.patch
```

### Test Results
```
{task_id}_{timestamp}_test_results.json
示例: T-001_20250412_103000_test_results.json
```

## Common Mistakes

| 错误 | 原因 | 修复 |
|------|------|------|
| 路径覆盖 | 文件名冲突 | 使用时间戳避免冲突 |
| 编码问题 | 未指定UTF-8 | 写入时指定encoding='utf-8' |
| 目录不存在 | 未创建父目录 | 使用`mkdir(parents=True)` |
| Frontmatter格式错误 | YAML缩进问题 | 使用yaml.dump()自动格式化 |

## Integration with Other Skills

```
fetch_and_trim_evidence
       ↓
execute_structured_review
       ↓
   [审查报告 + 人类决策]
       ↓
archive_review_artifact (本Skill)
       ↓
   [文件系统归档]
```

## Files Structure

```
archive_review_artifact/
├── SKILL.md              # 本文件
└── scripts/
    ├── archiver.py       # 归档核心逻辑
    ├── frontmatter.py    # Frontmatter处理
    └── path_resolver.py  # 路径解析
```

## Real-World Impact

**对比MCP Router:**

| 方面 | MCP Router | Skill Archive |
|------|-----------|---------------|
| 复杂度 | 事件队列、状态机 | 简单文件操作 |
| 调试 | 需追踪事件流 | 直接查看文件 |
| 可维护性 | 高耦合 | 低耦合 |
| 透明度 | 隐藏在队列中 | 直接文件访问 |

**优势:**
- ✅ 简单直接，易于调试
- ✅ 文件即审计追踪
- ✅ 无需后台进程
- ✅ 易于备份和迁移
