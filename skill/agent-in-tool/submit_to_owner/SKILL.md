---
name: submit-to-owner
description: Use when Builder Agent receives PASS from blind review and requests human Go/No-Go decision. Displays native confirmation dialog to human owner. On Go approval, automatically commits code and routes artifacts to 50-release/ directory.
---

# Submit to Owner

## Overview

人类裁决工具 - 当盲审通过后，请求人类最终放行。

弹出原生确认框，人类输入Go/No-Go：
- **Go** → 自动commit并路由到 `50-release/`
- **No-Go** → 返回给Builder继续修复

## When to Use

```
   Blind Review PASS
         |
         v
   调用本Skill
         |
         v
  人类确认框
    /     \
  Go     No-Go
   |       |
   v       v
 Commit   返回修复
```

**触发条件:**
- `trigger_blind_review` 返回 PASS
- 需要人类最终验收
- 准备发布代码

## Quick Reference

| 功能 | 说明 |
|------|------|
| 交互方式 | 原生确认框 |
| Go操作 | Git commit + 路由到50-release/ |
| No-Go操作 | 返回Builder继续修复 |
| 文件处理 | 自动整理发布包 |

## Implementation

```python
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict

# 原生确认框实现
def show_confirmation_dialog(task_id: str, review_summary: str) -> bool:
    """
    显示原生确认框

    Args:
        task_id: 任务ID
        review_summary: 审查摘要

    Returns:
        True (Go) / False (No-Go)
    """
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    title = f"代码审查通过 - {task_id}"
    message = f"""审查已通过，是否批准发布？

任务: {task_id}
审查摘要: {review_summary}

点击「是」批准发布 (Go)
点击「否」返回修复 (No-Go)
"""

    # 置顶窗口
    root.attributes('-topmost', True)
    result = messagebox.askyesno(title, message)

    root.destroy()
    return result


async def submit_to_owner(
    task_id: str,
    workspace_path: str = None,
    auto_commit: bool = True
) -> Dict:
    """
    提交人类裁决

    Args:
        task_id: 任务ID
        workspace_path: 工作区路径
        auto_commit: 是否自动commit

    Returns:
        裁决结果
    """
    if workspace_path is None:
        workspace_path = "."

    # 1. 读取审查报告
    review_report = load_review_report(task_id, workspace_path)

    # 2. 显示确认框
    review_summary = format_review_summary(review_report)
    approved = show_confirmation_dialog(task_id, review_summary)

    if not approved:
        return {
            "status": "NO-GO",
            "message": "❌ 人类拒绝放行。请根据反馈继续修复代码。",
            "action": "CONTINUE_FIXING"
        }

    # 3. Go - 执行发布流程
    if auto_commit:
        commit_result = await commit_changes(task_id, workspace_path)
        if not commit_result["success"]:
            return {
                "status": "ERROR",
                "message": f"❌ 提交失败: {commit_result['error']}",
                "action": "RETRY"
            }

    # 4. 路由到发布目录
    route_result = await route_to_release(task_id, workspace_path)

    return {
        "status": "GO",
        "message": f"✅ 代码已批准并发布到 50-release/ 目录",
        "release_path": route_result["release_path"],
        "commit_hash": commit_result.get("commit_hash") if auto_commit else None,
        "action": "COMPLETED"
    }


def load_review_report(task_id: str, workspace: str) -> Dict:
    """加载审查报告"""
    import json

    report_file = Path(workspace) / "40-review" / f"{task_id}.json"

    if not report_file.exists():
        return {"status": "PASS", "findings": []}

    with open(report_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_review_summary(report: Dict) -> str:
    """格式化审查摘要"""
    if report.get("status") == "PASS":
        findings_count = len(report.get("findings", []))
        return f"✅ 审查通过，发现 {findings_count} 个非阻断性问题"
    else:
        return f"⚠️ 发现 {report.get('severity', 'unknown')} 级别问题"


async def commit_changes(task_id: str, workspace: str) -> Dict:
    """提交代码变更"""
    try:
        # 添加所有变更
        subprocess.run(
            ["git", "add", "."],
            cwd=workspace,
            check=True,
            capture_output=True
        )

        # 提交
        commit_message = f"feat: {task_id} - Approved by owner\n\n[auto-commit from Agent-in-Tool workflow]"
        result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=workspace,
            check=True,
            capture_output=True,
            text=True
        )

        # 获取commit hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace,
            check=True,
            capture_output=True,
            text=True
        )

        return {
            "success": True,
            "commit_hash": hash_result.stdout.strip()
        }

    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": str(e)
        }


async def route_to_release(task_id: str, workspace: str) -> Dict:
    """路由到发布目录"""
    release_dir = Path(workspace) / "50-release"
    release_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    release_name = f"{task_id}_{timestamp}"

    # 创建发布包
    release_path = release_dir / release_name
    release_path.mkdir(exist_ok=True)

    # 复制代码文件
    code_src = Path(workspace) / "src"
    if code_src.exists():
        shutil.copytree(code_src, release_path / "src")

    # 复制审查报告
    review_src = Path(workspace) / "40-review" / f"{task_id}.md"
    if review_src.exists():
        shutil.copy2(review_src, release_path / "review_report.md")

    # 复制需求文档
    requirement_src = Path(workspace) / "20-planning" / f"{task_id}.md"
    if requirement_src.exists():
        shutil.copy2(requirement_src, release_path / "requirement.md")

    # 生成发布清单
    manifest = {
        "task_id": task_id,
        "release_name": release_name,
        "timestamp": datetime.now().isoformat(),
        "files": list(release_path.rglob("*"))
    }

    with open(release_path / "manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)

    return {
        "release_path": str(release_path),
        "release_name": release_name
    }
```

## Non-Interactive Mode

对于CI/CD环境，提供非交互模式：

```python
async def submit_to_owner_non_interactive(
    task_id: str,
    workspace_path: str = None,
    approval: str = "auto"  # auto | go | no-go
) -> Dict:
    """
    非交互模式提交

    Args:
        approval: "auto" (自动通过), "go" (批准), "no-go" (拒绝)

    Returns:
        裁决结果
    """
    if approval == "no-go":
        return {
            "status": "NO-GO",
            "message": "❌ 配置为拒绝放行",
            "action": "CONTINUE_FIXING"
        }

    # auto 或 go 都执行发布
    return await submit_to_owner(task_id, workspace_path, auto_commit=True)
```

## Standalone CLI 调用

```bash
# 交互式
python3 cli.py submit-owner TASK-001 --workspace .

# 非交互（CI）
python3 cli.py submit-owner TASK-001 --workspace . --non-interactive --approval go
```

## Complete Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    Builder Agent Workflow                    │
└─────────────────────────────────────────────────────────────┘
                              |
                              v
                    read_task_contract("TASK-001")
                              |
                              v
                    [读取需求文档]
                              |
                              v
                    [编写代码...]
                              |
                              v
                    trigger_blind_review("TASK-001")
                              |
        +---------------------+---------------------+
        |                                           |
        v                                           v
[后台Agent-in-Tool]                        [Builder等待]
        |                                           |
        +-> collect_evidence()                      |
        |                                           |
        +-> spawn_independent_llm()                 |
        |                                           |
        +-> save_report(40-review/)                 |
        |                                           |
        v                                           v
[返回极简结果] <-----------------------------------+
        |
        v
    "❌ 审查未通过" OR "✅ 审查通过"
        |
        v
submit_to_owner("TASK-001")
        |
        v
[人类确认框]
    /       \
  Go      No-Go
   |         |
   v         v
[Commit] [返回修复]
   |
   v
[路由到50-release/]
   |
   v
✅ 发布完成
```

## Environment Setup

```bash
# 安装依赖
pip install tkinter filelock

# macOS上tkinter通常已安装
# Linux上可能需要: sudo apt-get install python3-tk

# 配置
export GIT_AUTHOR_NAME="Agent-in-Tool Bot"
export GIT_AUTHOR_EMAIL="bot@example.com"
```

## Files Structure

```
submit_to_owner/
├── SKILL.md                    # 本文件
└── scripts/
    ├── owner_dialog.py         # 确认框实现
    ├── release_manager.py      # 发布管理
    └── git_operations.py       # Git操作
```

## Security Considerations

1. **Commit权限**: 确保当前 CLI 运行账号有 Git 仓库写入权限
2. **文件锁**: 使用文件锁防止并发冲突
3. **路径验证**: 验证workspace_path防止路径遍历
4. **权限控制**: 限制release目录写入权限
