---
name: sop-enforce-tdd
description: Use during build stage to enforce RED->GREEN->REFACTOR TDD gates and persist execution evidence. Can be called standalone or through development-phase-orchestrator for strict gating.
---

# SOP Enforce TDD

执行 TDD 三门禁（RED → GREEN → REFACTOR），并生成可追溯证据。

## 触发条件

当以下情况时使用此技能：
- 准备开始编写代码实现
- 需要执行测试驱动开发流程
- 需要生成 TDD 执行证据

## 调用方式

### 独立调用（无门禁）
```bash
python3 cli.py tdd-enforce TASK-001 --workspace . --test-command "pytest -q"
```

### 通过总控调用（强门禁）
当通过 `development_phase_orchestrator` 调用时，会自动检查：
- dev-forge 阶段是否通过
- 契约文档是否存在

## 输入参数

- `task_id`: 任务编号（必填）
- `--workspace`: 工作目录（可选，默认 "."）
- `--test-command`: 测试命令（可选，默认 "pytest -q"）
- `--skip-red`: 跳过 RED 阶段（可选）
- `--skip-green`: 跳过 GREEN 阶段（可选）
- `--skip-refactor`: 跳过 REFACTOR 阶段（可选）

## TDD 三门禁流程

### 1. RED 阶段
**目标**：编写失败的测试

**执行**：运行测试命令（预期失败）

**输出**：`30-build/{task_id}-red-*.log`

### 2. GREEN 阶段
**目标**：编写最小实现使测试通过

**执行**：运行测试命令（预期通过）

**输出**：`30-build/{task_id}-green-*.log`

### 3. REFACTOR 阶段
**目标**：重构代码，保持测试通过

**执行**：运行测试命令 + 代码质量检查

**输出**：`30-build/{task_id}-refactor-*.log`

## 输出产物

1. **阶段日志**：
   - `30-build/{task_id}-red-*.log`
   - `30-build/{task_id}-green-*.log`
   - `30-build/{task_id}-refactor-*.log`

2. **执行证据**：`30-build/{task_id}-execution_evidence-*.md`

## 完整示例

```bash
# 标准 TDD 流程
python3 cli.py tdd-enforce TASK-001 --workspace . --test-command "pytest -q"

# 使用自定义测试命令
python3 cli.py tdd-enforce TASK-001 --workspace . --test-command "npm test"

# 跳过某些阶段（不推荐）
python3 cli.py tdd-enforce TASK-001 --workspace . --skip-red
```

## 返回值

成功时返回：
```json
{
  "success": true,
  "task_id": "TASK-001",
  "status": "PASS",
  "stages": {
    "red": "passed",
    "green": "passed",
    "refactor": "passed"
  },
  "summary_file": "30-build/TASK-001-execution_evidence-20250413.md"
}
```

失败时返回：
```json
{
  "success": false,
  "task_id": "TASK-001",
  "status": "FAIL",
  "failed_stage": "red",
  "error": "测试失败：..."
}
```

被门禁拦截时返回：
```json
{
  "success": false,
  "status": "BLOCKED",
  "message": "前置阶段 dev-forge 未通过",
  "missing_dependencies": ["dev-forge"]
}
```

## 注意事项

1. 标准 TDD 流程应按 RED → GREEN → REFACTOR 顺序执行
2. 独立调用时不会检查门禁，适合快速测试
3. 总控调用时会强制执行三门禁，任一阶段失败则整体失败
4. 生成的执行证据将作为盲审的依据
