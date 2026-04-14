#!/usr/bin/env python3
"""
Requirement phase orchestrator state machine.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

STATE_DIR = ".sop_state"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

REQ_STAGES = ["req-boundary", "req-architecture", "req-contract", "req-complete"]
REQ_DEPS = {
    "req-boundary": [],
    "req-architecture": ["req-boundary"],
    "req-contract": ["req-architecture"],
    "req-complete": ["req-contract"],
}


def _now() -> str:
    return datetime.now().strftime(TIME_FORMAT)


def _state_file(task_id: str, workspace_path: str) -> Path:
    return Path(workspace_path) / STATE_DIR / f"requirements-{task_id}.json"


def _handoff_file(task_id: str, workspace_path: str) -> Path:
    return Path(workspace_path) / "20-planning" / f"{task_id}-requirements_handoff.json"


def init_requirements_state(task_id: str, workspace_path: str = ".", overwrite: bool = False) -> Dict:
    path = _state_file(task_id, workspace_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        return {"success": False, "message": f"状态文件已存在: {path}"}

    now = _now()
    stages = {
        stage: {"status": "pending", "updated_at": now, "evidence": "", "note": ""}
        for stage in REQ_STAGES
    }
    data = {
        "task_id": task_id,
        "phase": "requirements",
        "created_at": now,
        "updated_at": now,
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
    return [dep for dep in REQ_DEPS[stage_id] if data["stages"].get(dep, {}).get("status") != "pass"]


def mark_requirements_stage(
    task_id: str,
    stage_id: str,
    result: str,
    workspace_path: str = ".",
    evidence: str = "",
    note: str = "",
) -> Dict:
    if stage_id not in REQ_STAGES:
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


def get_requirements_status(task_id: str, workspace_path: str = ".") -> Dict:
    loaded = _load(task_id, workspace_path)
    if not loaded["success"]:
        return loaded
    data = loaded["data"]
    next_stage = None
    stages = []
    for stage in REQ_STAGES:
        deps_ok = len(_missing(data, stage)) == 0
        status = data["stages"][stage]["status"]
        stages.append({"id": stage, "status": status, "deps_ok": deps_ok, "updated_at": data["stages"][stage]["updated_at"]})
        if next_stage is None and status == "pending" and deps_ok:
            next_stage = stage
    return {"success": True, "task_id": task_id, "phase": "requirements", "next_stage": next_stage, "stages": stages}


def create_requirements_handoff(task_id: str, workspace_path: str = ".", force: bool = False) -> Dict:
    loaded = _load(task_id, workspace_path)
    if not loaded["success"]:
        return loaded
    data = loaded["data"]
    if data["stages"]["req-contract"]["status"] != "pass" and not force:
        return {"success": False, "message": "req-contract 未通过，不能生成交接产物"}

    workspace = Path(workspace_path)
    planning_file = workspace / "20-planning" / f"{task_id}.md"
    contracts = sorted((workspace / "20-planning").glob(f"{task_id}-requirement_contract-*.md"))
    handoff = {
        "task_id": task_id,
        "created_at": _now(),
        "source": "requirements_orchestrator",
        "requirement_state_file": str(loaded["path"]),
        "planning_file": str(planning_file) if planning_file.exists() else "",
        "contract_artifact": str(contracts[-1]) if contracts else "",
        "status": "ready",
    }
    handoff_file = _handoff_file(task_id, workspace_path)
    handoff_file.parent.mkdir(parents=True, exist_ok=True)
    handoff_file.write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding="utf-8")

    mark_requirements_stage(
        task_id,
        "req-complete",
        "pass",
        workspace_path=workspace_path,
        evidence=str(handoff_file),
        note="requirements handoff created",
    )
    return {"success": True, "task_id": task_id, "handoff_file": str(handoff_file)}

