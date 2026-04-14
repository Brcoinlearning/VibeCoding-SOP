---
name: sop-development-phase-orchestrator
description: Use after requirements handoff is complete to control development, TDD gates, blind review, and owner release with strict stage progression and artifact validation.
---

# SOP Development Phase Orchestrator

开发与发布阶段总控 Skill，承接需求阶段交接产物，驱动开发四步链路。

## 触发条件

当以下情况时使用此技能：
- 需求分析阶段已完成，存在 `20-planning/{task_id}-requirements_handoff.json`
- 准备开始开发实现
- 需要执行 TDD 门禁、代码审查、发布裁决

## 前置条件

默认要求存在需求交接产物：
```bash
# 检查交接文件是否存在
ls 20-planning/{task_id}-requirements_handoff.json
```

如需临时跳过（不推荐）：
```bash
python3 cli.py dev-init TASK-001 --workspace . --no-require-handoff
```

## 阶段流程

### 阶段 1：需求锻造 (dev-forge)
**命令**：`python3 cli.py forge-contract TASK-001 "原始需求" --workspace .`

**作用**：将需求锻造成可执行契约

**输出**：
- `10-requirements/{task_id}.md`
- `20-planning/{task_id}.md`
- `20-planning/{task_id}-requirement_contract-*.md`

**门禁**：前置阶段必须 pass

### 阶段 2：TDD 门禁 (dev-tdd)
**命令**：`python3 cli.py tdd-enforce TASK-001 --workspace . --test-command "pytest -q"`

**作用**：执行 RED → GREEN → REFACTOR 三门禁

**输出**：
- `30-build/{task_id}-red-*.log`
- `30-build/{task_id}-green-*.log`
- `30-build/{task_id}-refactor-*.log`
- `30-build/{task_id}-execution_evidence-*.md`

**门禁**：dev-forge 必须 pass

### 阶段 3：独立盲审 (dev-review)
**命令**：`python3 cli.py blind-review TASK-001 --workspace .`

**作用**：执行物理隔离的独立盲审

**输出**：
- `40-review/{task_id}.json`
- `40-review/{task_id}.md`

**门禁**：dev-tdd 必须 pass

### 阶段 4：Owner 裁决 (dev-owner)
**命令**：`python3 cli.py submit-owner TASK-001 --workspace .`

**作用**：发布前的最终 Go/No-Go 裁决

**输出**：
- Go：Git 提交并归档到 `50-release/{task_id}_{timestamp}/`
- No-Go：返回修复流程

**门禁**：dev-review 必须 PASS

## CLI 命令

```bash
# 初始化开发流程状态（会检查交接产物）
python3 cli.py dev-init TASK-001 --workspace .

# 查看开发阶段状态
python3 cli.py dev-status TASK-001 --workspace .

# 手动标记阶段结果（一般情况下不需要，过程命令会自动标记）
python3 cli.py dev-mark TASK-001 dev-forge pass --workspace .
```

## 门禁规则

1. 任一阶段未通过前，不允许进入下一阶段
2. 过程命令（forge-contract, tdd-enforce 等）会自动检查前置状态
3. 前置未满足时返回 BLOCKED 状态

## 最小门禁要求

1. 未生成 `20-planning/{task_id}.md`：不得进入编码
2. `tdd-enforce` 非 PASS：不得进入盲审
3. 盲审结果非 PASS：不得进入 Owner 裁决
4. Owner 未 Go：不得进入 `50-release/`

## 完整开发流程

```bash
# 1. 初始化（自动检查交接产物）
python3 cli.py dev-init TASK-001 --workspace .

# 2. 执行四步链（自动门禁）
python3 cli.py forge-contract TASK-001 "需求描述" --workspace .
python3 cli.py tdd-enforce TASK-001 --workspace . --test-command "pytest -q"
python3 cli.py blind-review TASK-001 --workspace .
python3 cli.py submit-owner TASK-001 --workspace .

# 3. 查看状态
python3 cli.py dev-status TASK-001 --workspace .
```
