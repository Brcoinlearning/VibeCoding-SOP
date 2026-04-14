---
name: sop-trigger-blind-review
description: Use after TDD gates pass to run isolated blind review with independent LLM session and persist structured review reports to 40-review directory.
---

# SOP Trigger Blind Review

在本地执行链中，执行独立盲审并产出结构化报告。

## 触发条件

当以下情况时使用此技能：
- TDD 门禁已通过
- 需要进行独立的代码审查
- 准备进入发布裁决前的审查

## 调用方式

### 独立调用（无门禁）
```bash
python3 cli.py blind-review TASK-001 --workspace .
```

### 通过总控调用（强门禁）
当通过 `development_phase_orchestrator` 调用时，会自动检查：
- dev-tdd 阶段是否通过
- TDD 执行证据是否存在

## 核心特性

### 1. 上下文隔离
- 使用全新的 LLM 会话
- Builder 的上下文完全不会传递给 Reviewer
- 确保审查的独立性

### 2. 权限隔离
- 使用文件锁防止并发冲突
- 独立的文件系统写入

### 3. 信息降维
- 完整报告落盘到 `40-review/` 目录
- CLI 只返回极简结果（PASS/REJECTED/ERROR）

## 输入参数

- `task_id`: 任务编号（必填）
- `--workspace`: 工作目录（可选，默认 "."）
- `--api-key`: API 密钥（可选，默认读取 `ANTHROPIC_API_KEY`）

## 输出产物

1. **结构化报告**：`40-review/{task_id}.json`
2. **人类可读报告**：`40-review/{task_id}.md`
3. **CLI 返回**：`PASS` / `REJECTED` / `ERROR`

## 完整示例

```bash
# 标准盲审
python3 cli.py blind-review TASK-001 --workspace .

# 使用自定义 API Key
python3 cli.py blind-review TASK-001 --workspace . --api-key "sk-ant-..."
```

## 返回值

### PASS（通过）
```json
{
  "success": true,
  "result": "PASS",
  "task_id": "TASK-001",
  "summary": "代码质量良好，测试覆盖充分，可以进入发布裁决",
  "report_file": "40-review/TASK-001.md"
}
```

### REJECTED（拒绝）
```json
{
  "success": false,
  "result": "REJECTED",
  "task_id": "TASK-001",
  "summary": "发现以下问题需要修复：...",
  "issues": [
    {
      "severity": "high",
      "description": "测试覆盖率不足"
    }
  ],
  "report_file": "40-review/TASK-001.md"
}
```

### ERROR（错误）
```json
{
  "success": false,
  "result": "ERROR",
  "task_id": "TASK-001",
  "error": "审查过程中发生错误：..."
}
```

### BLOCKED（门禁拦截）
```json
{
  "success": false,
  "status": "BLOCKED",
  "message": "前置阶段 dev-tdd 未通过",
  "missing_dependencies": ["dev-tdd"]
}
```

## 门禁规则

1. TDD 门禁未通过时，不允许执行盲审
2. 盲审结果为 REJECTED 或 ERROR 时，必须回到 Builder 修复并重试
3. 盲审结果为 PASS 时，才允许调用 `submit_to_owner`
4. 报告文件缺失或不可解析时，按失败处理

## 审查标准

盲审会检查以下方面：
- 代码质量与可维护性
- 测试覆盖充分性
- 需求实现完整性
- 文档与注释质量
- 安全性问题
- 性能问题

## 注意事项

1. 盲审使用对抗性 System Prompt，确保审查的严格性
2. 独立调用时不会检查门禁，适合快速审查
3. 总控调用时会强制检查前置条件
4. 只有 PASS 状态才能进入发布裁决阶段
