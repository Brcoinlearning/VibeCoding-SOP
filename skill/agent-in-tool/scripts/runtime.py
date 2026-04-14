#!/usr/bin/env python3
"""
Standalone runtime for Agent-in-Tool skills (no MCP dependency).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict

from scripts.blind_reviewer import BlindReviewer
from scripts.contract_forger import skill_forge_contract
from scripts.development_orchestrator import ensure_development_stage_ready, mark_development_stage
from scripts.tdd_enforcer import skill_tdd_enforcer


async def trigger_blind_review(
    task_id: str,
    workspace_path: str = ".",
    api_key: str | None = None,
) -> Dict:
    """触发独立盲审。"""
    gate = ensure_development_stage_ready(task_id, "dev-review", workspace_path)
    if not gate["success"]:
        return {
            "status": "BLOCKED",
            "message": gate["message"],
            "missing_dependencies": gate.get("missing_dependencies", []),
            "action": "COMPLETE_PREVIOUS_STAGE",
        }

    reviewer = BlindReviewer(api_key=api_key)
    result = await reviewer.review(task_id, workspace_path)
    if result.get("status") == "PASS":
        mark_development_stage(
            task_id,
            "dev-review",
            "pass",
            workspace_path=workspace_path,
            evidence=result.get("report_file", ""),
            note="blind review passed",
        )
    elif result.get("status") in {"REJECTED", "ERROR"}:
        mark_development_stage(
            task_id,
            "dev-review",
            "fail",
            workspace_path=workspace_path,
            evidence=result.get("report_file", ""),
            note=result.get("message", "blind review failed"),
        )
    return result


def show_confirmation_dialog(task_id: str, workspace: str) -> bool:
    """显示原生确认框。"""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()

        review_file = Path(workspace) / "40-review" / f"{task_id}.json"
        if review_file.exists():
            with open(review_file, "r", encoding="utf-8") as f:
                review = json.load(f)
            summary = f"状态: {review.get('status', 'UNKNOWN')}"
        else:
            summary = "审查报告未找到"

        message = f"""代码审查通过，是否批准发布？

任务: {task_id}
{summary}

点击「是」批准发布 (Go)
点击「否」返回修复 (No-Go)
"""
        root.attributes("-topmost", True)
        result = messagebox.askyesno(f"发布确认 - {task_id}", message)
        root.destroy()
        return result
    except ImportError:
        print(f"\n{'='*60}")
        print(f"代码审查通过 - {task_id}")
        print(f"{'='*60}")
        response = input("是否批准发布？ (yes/no): ").strip().lower()
        return response in {"yes", "y"}


async def execute_release(task_id: str, workspace: str) -> Dict:
    """执行发布流程。"""
    workspace_path = Path(workspace)

    try:
        subprocess.run(["git", "add", "."], cwd=workspace_path, check=True, capture_output=True)
        commit_message = f"feat: {task_id} - Approved by owner\n\n[Agent-in-Tool Workflow]"
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=workspace_path,
            check=True,
            capture_output=True,
        )
        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace_path,
            check=True,
            capture_output=True,
            text=True,
        )
        commit_hash = hash_result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"❌ Git提交失败: {e}"}

    release_dir = workspace_path / "50-release"
    release_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    release_name = f"{task_id}_{timestamp}"
    release_path = release_dir / release_name
    release_path.mkdir(exist_ok=True)

    files_to_copy = [("src", "src"), ("40-review", "review_report"), ("20-planning", "requirement")]
    for src_name, dst_name in files_to_copy:
        src = workspace_path / src_name
        dst = release_path / dst_name
        if src.exists():
            if src.is_dir():
                shutil.copytree(src, dst / src_name, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

    manifest = {
        "task_id": task_id,
        "release_name": release_name,
        "timestamp": datetime.now().isoformat(),
        "commit_hash": commit_hash,
        "files": [str(f.relative_to(release_path)) for f in release_path.rglob("*")],
    }
    with open(release_path / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "message": f"""✅ 代码已批准并发布！

发布位置: 50-release/{release_name}
Commit: {commit_hash}
时间: {timestamp}

任务完成！""",
    }


async def submit_to_owner(
    task_id: str,
    workspace_path: str = ".",
    non_interactive: bool = False,
    approval: str = "auto",
) -> Dict:
    """提交人类裁决。"""
    gate = ensure_development_stage_ready(task_id, "dev-owner", workspace_path)
    if not gate["success"]:
        return {
            "success": False,
            "message": gate["message"],
            "missing_dependencies": gate.get("missing_dependencies", []),
        }

    if non_interactive:
        if approval == "no-go":
            mark_development_stage(
                task_id,
                "dev-owner",
                "fail",
                workspace_path=workspace_path,
                note="owner no-go (non-interactive)",
            )
            return {
                "success": False,
                "message": "❌ 配置为拒绝放行 (No-Go)\n\n请根据反馈继续修复代码。",
            }
        result = await execute_release(task_id, workspace_path)
        if result.get("success"):
            mark_development_stage(
                task_id,
                "dev-owner",
                "pass",
                workspace_path=workspace_path,
                note="owner go (non-interactive)",
            )
            mark_development_stage(
                task_id,
                "released",
                "pass",
                workspace_path=workspace_path,
                note="release completed",
            )
        return result

    approved = show_confirmation_dialog(task_id, workspace_path)
    if not approved:
        mark_development_stage(
            task_id,
            "dev-owner",
            "fail",
            workspace_path=workspace_path,
            note="owner no-go",
        )
        return {
            "success": False,
            "message": "❌ 人类拒绝放行 (No-Go)\n\n请根据反馈继续修复代码。",
        }
    result = await execute_release(task_id, workspace_path)
    if result.get("success"):
        mark_development_stage(
            task_id,
            "dev-owner",
            "pass",
            workspace_path=workspace_path,
            note="owner go",
        )
        mark_development_stage(
            task_id,
            "released",
            "pass",
            workspace_path=workspace_path,
            note="release completed",
        )
    return result


__all__ = [
    "skill_forge_contract",
    "skill_tdd_enforcer",
    "trigger_blind_review",
    "submit_to_owner",
]
