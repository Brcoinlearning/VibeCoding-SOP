#!/usr/bin/env python3
"""
skill_forge_contract: Forge requirements contract artifacts for SOP stages.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


def _extract_acceptance(raw_requirement: str) -> list[str]:
    lines = [line.strip() for line in raw_requirement.splitlines() if line.strip()]
    candidates: list[str] = []
    for line in lines:
        if line.startswith("- ") or line.startswith("* "):
            candidates.append(line[2:].strip())
    if candidates:
        return candidates[:10]
    return [
        "必须具备至少一条可执行的验收路径",
        "关键边界流必须可验证",
        "输出产物必须可追溯并可交接",
    ]


def _write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_artifact(
    base_path: Path,
    artifact_type: str,
    task_id: str,
    stage: str,
    status: str,
    content: str,
) -> str:
    route = {
        "requirement_contract": "20-planning",
        "execution_evidence": "30-build",
        "review_report": "40-review",
        "go_no_go_record": "50-release",
    }[artifact_type]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    filename = f"{task_id}-{artifact_type}-{timestamp}.md"
    full = base_path / route / filename
    md = f"""---
type: {artifact_type}
task_id: {task_id}
stage: {stage}
status: {status}
created_at: {datetime.now().isoformat()}
---

{content}
"""
    _write_markdown(full, md)
    return str(full)


def skill_forge_contract(
    task_id: str,
    raw_requirement: str,
    workspace_path: str = ".",
    requirement_type: str = "new_feature",
    risk_level: str = "medium",
    in_scope: Optional[str] = None,
    out_scope: Optional[str] = None,
) -> Dict:
    """
    Generate requirement artifacts:
    - 10-requirements/{task_id}.md
    - 20-planning/{task_id}.md
    - 20-planning/{task_id}-requirement_contract-*.md (frontmatter artifact)
    """
    workspace = Path(workspace_path)
    now = datetime.now().isoformat()
    acceptance = _extract_acceptance(raw_requirement)
    in_scope_text = in_scope or "待补充"
    out_scope_text = out_scope or "待补充"

    req_md = f"""# {task_id} 需求分析启动卡

- 需求类型：{requirement_type}
- 风险等级：{risk_level}
- 时间戳：{now}

## 原始需求
{raw_requirement}

## 初始验收条件
{chr(10).join([f"- {x}" for x in acceptance])}
"""
    plan_md = f"""# {task_id} 需求契约包

## 目标
{raw_requirement}

## In Scope
{in_scope_text}

## Out of Scope
{out_scope_text}

## 验收条件（可测试）
{chr(10).join([f"- {x}" for x in acceptance])}

## 风险与假设
- 风险等级：{risk_level}
- 未决问题：待补充
"""

    req_file = workspace / "10-requirements" / f"{task_id}.md"
    plan_file = workspace / "20-planning" / f"{task_id}.md"
    _write_markdown(req_file, req_md)
    _write_markdown(plan_file, plan_md)
    artifact_file = _write_artifact(
        base_path=workspace,
        artifact_type="requirement_contract",
        task_id=task_id,
        stage="planning",
        status="ready",
        content=plan_md,
    )

    return {
        "success": True,
        "task_id": task_id,
        "requirement_file": str(req_file),
        "planning_file": str(plan_file),
        "artifact_file": artifact_file,
        "acceptance_count": len(acceptance),
    }
