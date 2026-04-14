---
name: sop-forge-requirements
description: Use to forge raw requirements into executable contract artifacts with 10-requirements and 20-planning outputs. Can be called standalone or through development-phase-orchestrator.
---

# SOP Forge Requirements

将原始需求锻造成可执行契约，并落盘为 SOP 标准产物。

## 触发条件

当以下情况时使用此技能：
- 有原始需求需要转化为结构化契约
- 需要生成需求文档和规划文档
- 准备开始开发实现前

## 调用方式

### 独立调用（无门禁）
```bash
python3 cli.py forge-contract TASK-001 "实现用户登录并记录审计日志" --workspace .
```

### 通过总控调用（强门禁）
当通过 `development_phase_orchestrator` 调用时，会自动检查：
- 交接产物是否存在
- 前置阶段是否通过

## 输入参数

- `task_id`: 任务编号（必填）
- `raw_requirement`: 原始需求文本（必填）
- `--workspace`: 工作目录（可选，默认 "."）
- `--requirement-type`: 需求类型（可选，默认 "new_feature"）
- `--risk-level`: 风险等级（可选，默认 "medium"）
- `--in-scope`: 范围内内容（可选）
- `--out-scope`: 范围外内容（可选）

## 输出产物

1. **需求文档**：`10-requirements/{task_id}.md`
2. **规划文档**：`20-planning/{task_id}.md`
3. **契约文档**：`20-planning/{task_id}-requirement_contract-*.md`

## 完整示例

```bash
python3 cli.py forge-contract \
  TASK-001 \
  "实现用户登录功能，包括邮箱登录、密码验证、审计日志记录" \
  --workspace . \
  --requirement-type new_feature \
  --risk-level high \
  --in-scope "登录、验证、审计" \
  --out-scope "第三方登录、短信验证"
```

## 返回值

成功时返回：
```json
{
  "success": true,
  "task_id": "TASK-001",
  "artifact_file": "20-planning/TASK-001-requirement_contract-20250413.md",
  "outputs": [
    "10-requirements/TASK-001.md",
    "20-planning/TASK-001.md",
    "20-planning/TASK-001-requirement_contract-20250413.md"
  ]
}
```

失败时返回：
```json
{
  "success": false,
  "error": "错误原因"
}
```

## 注意事项

1. 独立调用时不会检查门禁，适合快速生成契约
2. 总控调用时会检查前置条件，不满足时返回 BLOCKED
3. 生成的契约文档将作为后续 TDD 和审查的依据
