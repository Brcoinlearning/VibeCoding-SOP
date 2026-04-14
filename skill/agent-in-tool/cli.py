#!/usr/bin/env python3
"""
Standalone CLI entry for Agent-in-Tool skills (no MCP required).
"""
from __future__ import annotations

import argparse
import asyncio
import json

from scripts.development_orchestrator import (
    ensure_development_stage_ready,
    get_development_status,
    init_development_state,
    mark_development_stage,
)
from scripts.requirements_orchestrator import (
    create_requirements_handoff,
    get_requirements_status,
    init_requirements_state,
    mark_requirements_stage,
)
from scripts.requirements_subagent_dispatcher import (
    dispatch_requirements_phase,
)
from scripts.runtime import (
    skill_forge_contract,
    skill_tdd_enforcer,
    submit_to_owner,
    trigger_blind_review,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent-in-Tool standalone CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_review = sub.add_parser("blind-review", help="触发盲审")
    p_review.add_argument("task_id")
    p_review.add_argument("--workspace", default=".")
    p_review.add_argument("--api-key", default=None)

    p_submit = sub.add_parser("submit-owner", help="提交人类裁决")
    p_submit.add_argument("task_id")
    p_submit.add_argument("--workspace", default=".")
    p_submit.add_argument("--non-interactive", action="store_true")
    p_submit.add_argument("--approval", choices=["auto", "go", "no-go"], default="auto")

    p_forge = sub.add_parser("forge-contract", help="skill_forge_contract：锻造需求契约")
    p_forge.add_argument("task_id")
    p_forge.add_argument("raw_requirement")
    p_forge.add_argument("--workspace", default=".")
    p_forge.add_argument("--requirement-type", default="new_feature")
    p_forge.add_argument("--risk-level", default="medium")
    p_forge.add_argument("--in-scope", default=None)
    p_forge.add_argument("--out-scope", default=None)

    p_tdd = sub.add_parser("tdd-enforce", help="skill_tdd_enforcer：执行TDD门禁")
    p_tdd.add_argument("task_id")
    p_tdd.add_argument("--workspace", default=".")
    p_tdd.add_argument("--test-command", default="pytest -q")
    p_tdd.add_argument("--skip-red", action="store_true")
    p_tdd.add_argument("--skip-green", action="store_true")
    p_tdd.add_argument("--skip-refactor", action="store_true")

    p_req_init = sub.add_parser("req-init", help="初始化需求分析总控状态")
    p_req_init.add_argument("task_id")
    p_req_init.add_argument("--workspace", default=".")
    p_req_init.add_argument("--overwrite", action="store_true")

    p_req_status = sub.add_parser("req-status", help="查看需求分析阶段状态")
    p_req_status.add_argument("task_id")
    p_req_status.add_argument("--workspace", default=".")

    p_req_mark = sub.add_parser("req-mark", help="标记需求阶段结果")
    p_req_mark.add_argument("task_id")
    p_req_mark.add_argument("stage_id", choices=["req-boundary", "req-architecture", "req-contract", "req-complete"])
    p_req_mark.add_argument("result", choices=["pass", "fail"])
    p_req_mark.add_argument("--workspace", default=".")
    p_req_mark.add_argument("--evidence", default="")
    p_req_mark.add_argument("--note", default="")

    p_req_handoff = sub.add_parser("req-handoff", help="生成需求->开发交接产物")
    p_req_handoff.add_argument("task_id")
    p_req_handoff.add_argument("--workspace", default=".")
    p_req_handoff.add_argument("--force", action="store_true")

    p_req_dispatch = sub.add_parser("req-dispatch", help="多Agent调度：执行完整需求分析阶段")
    p_req_dispatch.add_argument("task_id")
    p_req_dispatch.add_argument("raw_requirement")
    p_req_dispatch.add_argument("--workspace", default=".")
    p_req_dispatch.add_argument("--api-key", default=None)

    p_dev_init = sub.add_parser("dev-init", help="初始化开发流程总控状态")
    p_dev_init.add_argument("task_id")
    p_dev_init.add_argument("--workspace", default=".")
    p_dev_init.add_argument("--overwrite", action="store_true")
    p_dev_init.add_argument("--no-require-handoff", action="store_true")

    p_dev_status = sub.add_parser("dev-status", help="查看开发阶段状态")
    p_dev_status.add_argument("task_id")
    p_dev_status.add_argument("--workspace", default=".")

    p_dev_mark = sub.add_parser("dev-mark", help="手动标记开发阶段结果")
    p_dev_mark.add_argument("task_id")
    p_dev_mark.add_argument("stage_id", choices=["dev-forge", "dev-tdd", "dev-review", "dev-owner", "released"])
    p_dev_mark.add_argument("result", choices=["pass", "fail"])
    p_dev_mark.add_argument("--workspace", default=".")
    p_dev_mark.add_argument("--evidence", default="")
    p_dev_mark.add_argument("--note", default="")

    args = parser.parse_args()

    if args.command == "blind-review":
        result = asyncio.run(trigger_blind_review(args.task_id, args.workspace, args.api_key))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "forge-contract":
        gate = ensure_development_stage_ready(args.task_id, "dev-forge", args.workspace)
        if not gate["success"]:
            print(
                json.dumps(
                    {
                        "success": False,
                        "status": "BLOCKED",
                        "message": gate["message"],
                        "missing_dependencies": gate.get("missing_dependencies", []),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        result = skill_forge_contract(
            task_id=args.task_id,
            raw_requirement=args.raw_requirement,
            workspace_path=args.workspace,
            requirement_type=args.requirement_type,
            risk_level=args.risk_level,
            in_scope=args.in_scope,
            out_scope=args.out_scope,
        )
        if result.get("success"):
            mark_development_stage(
                args.task_id,
                "dev-forge",
                "pass",
                workspace_path=args.workspace,
                evidence=result.get("artifact_file", ""),
                note="forge contract done",
            )
        else:
            mark_development_stage(
                args.task_id,
                "dev-forge",
                "fail",
                workspace_path=args.workspace,
                note="forge contract failed",
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "tdd-enforce":
        gate = ensure_development_stage_ready(args.task_id, "dev-tdd", args.workspace)
        if not gate["success"]:
            print(
                json.dumps(
                    {
                        "success": False,
                        "status": "BLOCKED",
                        "message": gate["message"],
                        "missing_dependencies": gate.get("missing_dependencies", []),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        result = skill_tdd_enforcer(
            task_id=args.task_id,
            workspace_path=args.workspace,
            test_command=args.test_command,
            run_red=not args.skip_red,
            run_green=not args.skip_green,
            run_refactor_check=not args.skip_refactor,
        )
        mark_development_stage(
            args.task_id,
            "dev-tdd",
            "pass" if result.get("success") else "fail",
            workspace_path=args.workspace,
            evidence=result.get("summary_file", ""),
            note=result.get("status", ""),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "submit-owner":
        result = asyncio.run(
            submit_to_owner(
                args.task_id,
                workspace_path=args.workspace,
                non_interactive=args.non_interactive,
                approval=args.approval,
            )
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "req-init":
        result = init_requirements_state(args.task_id, args.workspace, overwrite=args.overwrite)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "req-status":
        result = get_requirements_status(args.task_id, args.workspace)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "req-mark":
        result = mark_requirements_stage(
            args.task_id,
            args.stage_id,
            args.result,
            workspace_path=args.workspace,
            evidence=args.evidence,
            note=args.note,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "req-handoff":
        result = create_requirements_handoff(args.task_id, args.workspace, force=args.force)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "req-dispatch":
        result = asyncio.run(dispatch_requirements_phase(
            task_id=args.task_id,
            raw_requirement=args.raw_requirement,
            workspace=args.workspace,
            api_key=args.api_key
        ))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "dev-init":
        result = init_development_state(
            args.task_id,
            args.workspace,
            overwrite=args.overwrite,
            require_handoff=not args.no_require_handoff,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "dev-status":
        result = get_development_status(args.task_id, args.workspace)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "dev-mark":
        result = mark_development_stage(
            args.task_id,
            args.stage_id,
            args.result,
            workspace_path=args.workspace,
            evidence=args.evidence,
            note=args.note,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return


if __name__ == "__main__":
    main()
