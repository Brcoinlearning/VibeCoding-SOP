---
name: tech-selection
description: Use when producing phase 2 technology selection document from business rules memo
---

# Tech Selection

## Scope

This skill is documentation-only in current phase.

- Allowed: produce decision documents
- Not allowed: implement scripts, CLIs, orchestrators, runtime services

## Input

- `10-requirements/{task_id}_business_rules_memo.md`

## Output

- `15-tech-selection/{task_id}_tech_selection.md`

## Required Content

1. Candidate options and tradeoffs
2. Compatibility and dependency analysis
3. Reuse-first decisions (prefer existing superpowers skills)
4. Chosen approach with rationale
5. Explicit current-phase boundary statement

## Process

1. Map business requirements to technical concerns.
2. Compare alternatives with pros/cons.
3. Select approach favoring existing skills and low implementation risk.
4. Record deferred items as "后续代码化阶段可选".

## Quality Gates

- Must align with requirement memo boundaries.
- Must not prescribe immediate Python/script implementation in current phase.
