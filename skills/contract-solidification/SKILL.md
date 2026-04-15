---
name: contract-solidification
description: Use when producing phase 4 test contract from architecture and tasks documents
---

# Contract Solidification

## Scope

This skill defines acceptance contracts and scenarios only.

- Allowed: Gherkin contract and acceptance criteria updates
- Not allowed: runtime code, import scripts, orchestrator implementation

## Input

- `20-architecture/{task_id}_architecture.md`
- `20-architecture/{task_id}_tasks.md`
- `10-requirements/{task_id}_business_rules_memo.md` (if needed for rules)

## Output

- `25-contract/{task_id}_contract.md`

## Required Scenario Types

1. Happy path
2. Boundary cases
3. Error cases
4. Scope-guard cases (prevent phase drift to runtime coding)

## Process

1. Extract enforceable behaviors from upstream docs.
2. Convert behaviors to Gherkin scenarios with clear Given/When/Then.
3. Add explicit scenarios for transparency gates and isolation failure blocking.
4. Verify contract language is testable and unambiguous.

## Quality Gates

- Contract must be executable as acceptance criteria.
- Must include scenarios that block unauthorized runtime implementation in current phase.
