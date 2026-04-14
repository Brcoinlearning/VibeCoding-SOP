#!/usr/bin/env python3
"""
SOP orchestrator state machine for requirement -> delivery workflow.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

STATE_DIR = ".sop_state"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


@dataclass(frozen=True)
class Stage:
    id: str
    label: str
    executor: str
    dependencies: List[str]


STAGES: List[Stage] = [
    Stage("req-boundary", "需求阶段1：边界收敛", "external-skill", []),
    Stage("req-architecture", "需求阶段2：架构拆解", "external-skill", ["req-boundary"]),
    Stage("req-contract", "需求阶段3：契约固化", "external-skill", ["req-architecture"]),
    Stage("local-forge", "本地：forge_requirements", "local-skill", ["req-contract"]),
    Stage("local-tdd", "本地：enforce_tdd", "local-skill", ["local-forge"]),
    Stage("local-review", "本地：trigger_blind_review", "local-skill", ["local-tdd"]),
    Stage("owner-decision", "本地：submit_to_owner", "owner", ["local-review"]),
    Stage("released", "发布归档完成", "system", ["owner-decision"]),
]

STAGE_MAP = {stage.id: stage for stage in STAGES}


def _now() -> str:
    return datetime.now().strftime(TIME_FORMAT)


def _state_file(task_id: str, workspace_path: str) -> Path:
    return Path(workspace_path) / STATE_DIR / f"{task_id}.json"


def _init_stage_data() -> Dict[str, Dict[str, str]]:
    now = _now()
    data: Dict[str, Dict[str, str]] = {}
    for stage in STAGES:
        data[stage.id] = {
            "status": "pending",
            "updated_at": now,
            "evidence": "",
            "note": "",
            "executor": stage.executor,
        }
    return data


def init_workflow_state(task_id: str, workspace_path: str = ".", overwrite: bool = False) -> Dict:
    path = _state_file(task_id, workspace_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        return {"success": False, "message": f"状态文件已存在: {path}"}

    now = _now()
    data = {
        "task_id": task_id,
        "created_at": now,
        "updated_at": now,
        "version": 1,
        "stages": _init_stage_data(),
        "history": [
            {"at": now, "stage": "init", "result": "success", "note": "workflow initialized"}
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "state_file": str(path)}


def load_workflow_state(task_id: str, workspace_path: str = ".") -> Dict:
    path = _state_file(task_id, workspace_path)
    if not path.exists():
        return {"success": False, "message": f"状态文件不存在: {path}"}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"success": True, "state_file": str(path), "data": data}


def _save_state(path: Path, data: Dict) -> None:
    data["updated_at"] = _now()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _missing_dependencies(data: Dict, stage_id: str) -> List[str]:
    stage = STAGE_MAP[stage_id]
    missing: List[str] = []
    for dep in stage.dependencies:
        if data["stages"].get(dep, {}).get("status") != "pass":
            missing.append(dep)
    return missing


def mark_stage_result(
    task_id: str,
    stage_id: str,
    result: str,
    workspace_path: str = ".",
    evidence: str = "",
    note: str = "",
) -> Dict:
    if stage_id not in STAGE_MAP:
        return {"success": False, "message": f"未知阶段: {stage_id}"}
    if result not in {"pass", "fail"}:
        return {"success": False, "message": "result 必须是 pass 或 fail"}

    loaded = load_workflow_state(task_id, workspace_path)
    if not loaded["success"]:
        return loaded

    path = Path(loaded["state_file"])
    data = loaded["data"]

    if result == "pass":
        missing = _missing_dependencies(data, stage_id)
        if missing:
            return {
                "success": False,
                "message": f"阶段 {stage_id} 前置条件未满足",
                "missing_dependencies": missing,
            }

    stage_data = data["stages"][stage_id]
    stage_data["status"] = result
    stage_data["updated_at"] = _now()
    stage_data["evidence"] = evidence
    stage_data["note"] = note
    data["history"].append(
        {"at": _now(), "stage": stage_id, "result": result, "evidence": evidence, "note": note}
    )
    _save_state(path, data)

    return {
        "success": True,
        "task_id": task_id,
        "stage": stage_id,
        "result": result,
        "state_file": str(path),
    }


def ensure_stage_ready(task_id: str, stage_id: str, workspace_path: str = ".") -> Dict:
    if stage_id not in STAGE_MAP:
        return {"success": False, "message": f"未知阶段: {stage_id}"}

    loaded = load_workflow_state(task_id, workspace_path)
    if not loaded["success"]:
        # 没有状态文件时不强制阻断，兼容旧流程
        return {"success": True, "enforced": False, "message": "未初始化SOP状态，跳过强制门禁"}

    data = loaded["data"]
    missing = _missing_dependencies(data, stage_id)
    if missing:
        return {
            "success": False,
            "enforced": True,
            "message": f"阶段 {stage_id} 前置条件未满足",
            "missing_dependencies": missing,
        }
    return {"success": True, "enforced": True}


def get_workflow_status(task_id: str, workspace_path: str = ".") -> Dict:
    loaded = load_workflow_state(task_id, workspace_path)
    if not loaded["success"]:
        return loaded

    data = loaded["data"]
    stages_view = []
    next_stage = None
    for stage in STAGES:
        stage_data = data["stages"][stage.id]
        deps_ok = not _missing_dependencies(data, stage.id)
        stages_view.append(
            {
                "id": stage.id,
                "label": stage.label,
                "executor": stage.executor,
                "status": stage_data["status"],
                "deps_ok": deps_ok,
                "updated_at": stage_data["updated_at"],
            }
        )
        if next_stage is None and stage_data["status"] == "pending" and deps_ok:
            next_stage = stage.id

    return {
        "success": True,
        "task_id": task_id,
        "state_file": loaded["state_file"],
        "next_stage": next_stage,
        "stages": stages_view,
    }

