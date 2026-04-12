#!/usr/bin/env python3
"""
Standalone CLI entry for Agent-in-Tool skills (no MCP required).
"""
from __future__ import annotations

import argparse
import asyncio
import json

from scripts.runtime import (
    read_task_contract,
    skill_forge_contract,
    skill_tdd_enforcer,
    submit_to_owner,
    trigger_blind_review,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent-in-Tool standalone CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_read = sub.add_parser("read-task", help="读取任务需求")
    p_read.add_argument("task_id")
    p_read.add_argument("--workspace", default=".")

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

    args = parser.parse_args()

    if args.command == "read-task":
        result = read_task_contract(args.task_id, args.workspace)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "blind-review":
        result = asyncio.run(trigger_blind_review(args.task_id, args.workspace, args.api_key))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "forge-contract":
        result = skill_forge_contract(
            task_id=args.task_id,
            raw_requirement=args.raw_requirement,
            workspace_path=args.workspace,
            requirement_type=args.requirement_type,
            risk_level=args.risk_level,
            in_scope=args.in_scope,
            out_scope=args.out_scope,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "tdd-enforce":
        result = skill_tdd_enforcer(
            task_id=args.task_id,
            workspace_path=args.workspace,
            test_command=args.test_command,
            run_red=not args.skip_red,
            run_green=not args.skip_green,
            run_refactor_check=not args.skip_refactor,
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


if __name__ == "__main__":
    main()
