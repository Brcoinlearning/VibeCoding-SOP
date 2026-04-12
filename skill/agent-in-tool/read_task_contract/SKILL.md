---
name: read-task-contract
description: Use when Builder Agent needs to read task requirements before starting development. Reads task specification from 20-planning/ directory and returns structured requirement information. This is the first step in the development workflow.
---

# Read Task Contract

## Overview

需求读取工具 - Builder Agent开始工作前的第一步。

从 `20-planning/` 目录读取任务需求文档，返回结构化的需求信息。

## When to Use

```
    收到开发指令
         |
         v
   调用本Skill
         |
         v
  获取需求详情
         |
         v
   开始编码工作
```

**触发条件:**
- Builder Agent接到新任务
- 需要确认具体的开发需求
- 需要了解验收标准

## Quick Reference

| 功能 | 说明 |
|------|------|
| 读取路径 | `20-planning/{task_id}.md` |
| 返回格式 | 结构化JSON |
| 包含信息 | 标题、描述、验收标准、依赖 |

## Implementation

```python
from pathlib import Path
import json
import re
from typing import Dict, Optional

def read_task_contract(task_id: str, workspace_path: str = None) -> Dict:
    """
    读取任务需求文档

    Args:
        task_id: 任务ID (如 "TASK-001")
        workspace_path: 工作区路径 (默认为当前目录)

    Returns:
        {
            "task_id": str,
            "title": str,
            "description": str,
            "acceptance_criteria": List[str],
            "dependencies": List[str],
            "priority": str,
            "status": str
        }
    """
    if workspace_path is None:
        workspace_path = "."

    planning_dir = Path(workspace_path) / "20-planning"
    task_file = planning_dir / f"{task_id}.md"

    if not task_file.exists():
        return {
            "task_id": task_id,
            "error": f"Task file not found: {task_file}",
            "status": "NOT_FOUND"
        }

    content = task_file.read_text(encoding='utf-8')

    # 解析Markdown
    return parse_task_markdown(task_id, content)


def parse_task_markdown(task_id: str, content: str) -> Dict:
    """
    解析任务Markdown文档
    """
    # 提取标题 (第一个 # 标题)
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else task_id

    # 提取描述 (标题后的第一段)
    description_match = re.search(r'^#\s+.+?\n\n(.+?)\n\n', content, re.DOTALL)
    description = description_match.group(1).strip() if description_match else ""

    # 提取验收标准
    acceptance_criteria = []
    criteria_section = re.search(r'## 验收标准|## Acceptance Criteria(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if criteria_section:
        criteria_matches = re.findall(r'^-\s+(.+)$', criteria_section.group(1), re.MULTILINE)
        acceptance_criteria = [m.strip() for m in criteria_matches]

    # 提取依赖
    dependencies = []
    dep_section = re.search(r'## 依赖|## Dependencies(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if dep_section:
        dep_matches = re.findall(r'^-\s+(TASK-\d+)', dep_section.group(1), re.MULTILINE)
        dependencies = list(set(dep_matches))

    # 提取优先级
    priority = "medium"
    priority_match = re.search(r'优先级[：:]\s*(\w+)', content)
    if priority_match:
        priority = priority_match.group(1).lower()

    return {
        "task_id": task_id,
        "title": title,
        "description": description,
        "acceptance_criteria": acceptance_criteria,
        "dependencies": dependencies,
        "priority": priority,
        "status": "READY"
    }
```

## Standalone CLI 调用

```bash
python3 cli.py read-task TASK-001 --workspace .
```

## Usage Example

```python
# Builder调用
result = read_task_contract("TASK-001")

# 返回
{
    "task_id": "TASK-001",
    "title": "实现用户登录功能",
    "description": "开发基于JWT的用户认证系统",
    "acceptance_criteria": [
        "支持邮箱+密码登录",
        "返回有效JWT token",
        "错误处理完善"
    ],
    "dependencies": [],
    "priority": "high",
    "status": "READY"
}
```

## Files Structure

```
read_task_contract/
├── SKILL.md              # 本文件
└── scripts/
    └── task_reader.py    # 实现代码
```
