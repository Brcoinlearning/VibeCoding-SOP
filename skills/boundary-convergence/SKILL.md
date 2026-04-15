---
name: boundary-convergence
description: Use when converting raw request into structured business rules memo for phase 1
---

# Boundary Convergence

## Scope

This skill is for documentation output only in the current project phase.

- Allowed: requirement analysis documents
- Not allowed: runtime code, scripts, orchestrator implementation

## Input

- Raw requirement text
- Optional background constraints

## Output

- `10-requirements/{task_id}_business_rules_memo.md`

## Required Sections

1. 核心概念定义
2. 需求概述
3. 目标用户描述
4. 核心价值说明
5. 功能需求
6. 非功能需求
7. 业务规则
8. 边界条件
9. 异常处理
10. 数据规范

## Process

1. Detect ambiguous points across function/data/user/tech/business dimensions.
2. Ask clarifying questions in rounds.
3. Consolidate confirmed answers into the memo.
4. Ensure output is complete and consistent with project boundaries.

## Quality Gates

- Output path and filename must match phase conventions.
- No implementation code generation.
- No references requiring `scripts/*` or `orchestrator/*`.
