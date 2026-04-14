#!/usr/bin/env python3
"""
Development phase orchestrator state machine.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

STATE_DIR = ".sop_state"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

DEV_STAGES = ["dev-forge", "dev-tdd", "dev-review", "dev-owner", "released"]
DEV_DEPS = {
    "dev-forge": [],
    "dev-tdd": ["dev-forge"],
    "dev-review": ["dev-tdd"],
    "dev-owner": ["dev-review"],
    "released": ["dev-owner"],
}


def _now() -> str:
    return datetime.now().strftime(TIME_FORMAT)


def _state_file(task_id: str, workspace_path: str) -> Path:
    return Path(workspace_path) / STATE_DIR / f"development-{task_id}.json"


def _handoff_file(task_id: str, workspace_path: str) -> Path:
    return Path(workspace_path) / "20-planning" / f"{task_id}-requirements_handoff.json"


def init_development_state(
    task_id: str,
    workspace_path: str = ".",
    overwrite: bool = False,
    require_handoff: bool = True,
) -> Dict:
    handoff = _handoff_file(task_id, workspace_path)
    if require_handoff and not handoff.exists():
        return {"success": False, "message": f"需求交接产物不存在: {handoff}"}

    path = _state_file(task_id, workspace_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        return {"success": False, "message": f"状态文件已存在: {path}"}

    now = _now()
    stages = {
        stage: {"status": "pending", "updated_at": now, "evidence": "", "note": ""}
        for stage in DEV_STAGES
    }
    data = {
        "task_id": task_id,
        "phase": "development",
        "created_at": now,
        "updated_at": now,
        "handoff_file": str(handoff) if handoff.exists() else "",
        "stages": stages,
        "history": [{"at": now, "stage": "init", "result": "success"}],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "state_file": str(path)}


def _load(task_id: str, workspace_path: str = ".") -> Dict:
    path = _state_file(task_id, workspace_path)
    if not path.exists():
        return {"success": False, "message": f"状态文件不存在: {path}"}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"success": True, "path": path, "data": data}


def _save(path: Path, data: Dict) -> None:
    data["updated_at"] = _now()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _missing(data: Dict, stage_id: str) -> List[str]:
    return [dep for dep in DEV_DEPS[stage_id] if data["stages"].get(dep, {}).get("status") != "pass"]


def ensure_development_stage_ready(task_id: str, stage_id: str, workspace_path: str = ".") -> Dict:
    if stage_id not in DEV_STAGES:
        return {"success": False, "message": f"未知阶段: {stage_id}"}
    loaded = _load(task_id, workspace_path)
    if not loaded["success"]:
        return {"success": True, "enforced": False, "message": "未初始化开发状态，跳过强制门禁"}
    data = loaded["data"]
    missing = _missing(data, stage_id)
    if missing:
        return {"success": False, "enforced": True, "message": f"阶段 {stage_id} 前置条件未满足", "missing_dependencies": missing}
    return {"success": True, "enforced": True}


def mark_development_stage(
    task_id: str,
    stage_id: str,
    result: str,
    workspace_path: str = ".",
    evidence: str = "",
    note: str = "",
) -> Dict:
    if stage_id not in DEV_STAGES:
        return {"success": False, "message": f"未知阶段: {stage_id}"}
    if result not in {"pass", "fail"}:
        return {"success": False, "message": "result 必须是 pass 或 fail"}
    loaded = _load(task_id, workspace_path)
    if not loaded["success"]:
        return loaded
    path = loaded["path"]
    data = loaded["data"]
    if result == "pass":
        missing = _missing(data, stage_id)
        if missing:
            return {"success": False, "message": f"阶段 {stage_id} 前置条件未满足", "missing_dependencies": missing}
    data["stages"][stage_id]["status"] = result
    data["stages"][stage_id]["updated_at"] = _now()
    data["stages"][stage_id]["evidence"] = evidence
    data["stages"][stage_id]["note"] = note
    data["history"].append({"at": _now(), "stage": stage_id, "result": result, "evidence": evidence, "note": note})
    _save(path, data)
    return {"success": True, "task_id": task_id, "stage": stage_id, "result": result, "state_file": str(path)}


def get_development_status(task_id: str, workspace_path: str = ".") -> Dict:
    loaded = _load(task_id, workspace_path)
    if not loaded["success"]:
        return loaded
    data = loaded["data"]
    next_stage = None
    stages = []
    for stage in DEV_STAGES:
        deps_ok = len(_missing(data, stage)) == 0
        status = data["stages"][stage]["status"]
        stages.append({"id": stage, "status": status, "deps_ok": deps_ok, "updated_at": data["stages"][stage]["updated_at"]})
        if next_stage is None and status == "pending" and deps_ok:
            next_stage = stage
    return {"success": True, "task_id": task_id, "phase": "development", "next_stage": next_stage, "stages": stages, "handoff_file": data.get("handoff_file", "")}

