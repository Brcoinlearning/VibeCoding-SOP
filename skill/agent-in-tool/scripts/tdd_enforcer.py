#!/usr/bin/env python3
"""
skill_tdd_enforcer: Enforce RED->GREEN->REFACTOR evidence for current task.
"""
from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict


def _run(command: str, cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        text=True,
        capture_output=True,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _summary(log: str, limit: int = 120) -> str:
    lines = [line for line in log.splitlines() if line.strip()]
    return "\n".join(lines[-limit:])


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def skill_tdd_enforcer(
    task_id: str,
    workspace_path: str = ".",
    test_command: str = "pytest -q",
    run_red: bool = True,
    run_green: bool = True,
    run_refactor_check: bool = True,
) -> Dict:
    """
    Run TDD gates and persist evidence under 30-build/.
    """
    workspace = Path(workspace_path)
    t = datetime.now().strftime("%Y%m%d-%H%M")
    evidence_dir = workspace / "30-build"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    red_ok = True
    red_log = ""
    if run_red:
        rc, out = _run(test_command, workspace)
        red_ok = rc != 0
        red_log = out
        _write(evidence_dir / f"{task_id}-red-{t}.log", out)

    green_ok = True
    green_log = ""
    if run_green:
        rc, out = _run(test_command, workspace)
        green_ok = rc == 0
        green_log = out
        _write(evidence_dir / f"{task_id}-green-{t}.log", out)

    refactor_ok = True
    refactor_log = ""
    if run_refactor_check:
        rc, out = _run(test_command, workspace)
        refactor_ok = rc == 0
        refactor_log = out
        _write(evidence_dir / f"{task_id}-refactor-{t}.log", out)

    passed = red_ok and green_ok and refactor_ok
    summary_md = f"""---
type: execution_evidence
task_id: {task_id}
stage: build
status: {"ready" if passed else "rejected"}
created_at: {datetime.now().isoformat()}
---

# TDD Evidence for {task_id}

- RED gate: {"PASS" if red_ok else "FAIL"}
- GREEN gate: {"PASS" if green_ok else "FAIL"}
- REFACTOR gate: {"PASS" if refactor_ok else "FAIL"}
- command: `{test_command}`

## RED Summary
```
{_summary(red_log)}
```

## GREEN Summary
```
{_summary(green_log)}
```

## REFACTOR Summary
```
{_summary(refactor_log)}
```
"""
    summary_file = evidence_dir / f"{task_id}-execution_evidence-{t}.md"
    _write(summary_file, summary_md)

    return {
        "success": passed,
        "task_id": task_id,
        "status": "PASS" if passed else "REJECTED",
        "summary_file": str(summary_file),
        "red": red_ok,
        "green": green_ok,
        "refactor": refactor_ok,
    }
