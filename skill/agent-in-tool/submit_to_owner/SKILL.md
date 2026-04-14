---
name: sop-submit-to-owner
description: Use only after blind review PASS to request owner Go/No-Go decision and complete release routing with git commit and archival to 50-release directory.
---

# SOP Submit to Owner

发布前的唯一裁决入口，负责 Owner 的 Go/No-Go 决策与发布归档。

## 触发条件

当以下情况时使用此技能：
- 盲审结果为 PASS
- `40-review/{task_id}.json` 和 `40-review/{task_id}.md` 已生成
- 准备进行最终的发布决策

## 调用方式

### 交互式调用（默认）
```bash
python3 cli.py submit-owner TASK-001 --workspace .
```
会提示 Owner 进行 Go/No-Go 决策。

### 非交互式调用（CI/CD）
```bash
python3 cli.py submit-owner TASK-001 --workspace . --non-interactive --approval go
```
适用于自动化流程。

## 输入参数

- `task_id`: 任务编号（必填）
- `--workspace`: 工作目录（可选，默认 "."）
- `--non-interactive`: 非交互模式（可选）
- `--approval`: 决策结果（可选，非交互模式下生效）
  - `auto`: 自动决策
  - `go`: 批准发布
  - `no-go`: 拒绝发布

## 决策流程

### Go（批准）
1. 执行 Git 提交
2. 归档所有产物到 `50-release/{task_id}_{timestamp}/`
3. 生成 `manifest.json`
4. 更新状态为 `released`

### No-Go（拒绝）
1. 返回修复流程
2. 不进入发布目录
3. 保持当前状态，允许修复后重新提交

## 输出产物

### Go 时
- `50-release/{task_id}_{timestamp}/`
  - 所有阶段产物（需求、规划、构建、审查）
  - `manifest.json`（发布清单）
  - Git 提交记录

### No-Go 时
- 返回修复建议
- 不生成发布目录

## 完整示例

```bash
# 交互式决策
python3 cli.py submit-owner TASK-001 --workspace .

# 非交互式 - 批准
python3 cli.py submit-owner TASK-001 --workspace . --non-interactive --approval go

# 非交互式 - 拒绝
python3 cli.py submit-owner TASK-001 --workspace . --non-interactive --approval no-go
```

## 返回值

### Go（批准）
```json
{
  "success": true,
  "decision": "go",
  "task_id": "TASK-001",
  "release_dir": "50-release/TASK-001_20250413_153000",
  "git_commit": "abc123",
  "manifest": "50-release/TASK-001_20250413_153000/manifest.json",
  "artifacts": [
    "10-requirements/TASK-001.md",
    "20-planning/TASK-001.md",
    "30-build/TASK-001-execution_evidence-20250413.md",
    "40-review/TASK-001.md"
  ]
}
```

### No-Go（拒绝）
```json
{
  "success": false,
  "decision": "no-go",
  "task_id": "TASK-001",
  "reason": "Owner 拒绝发布",
  "feedback": "需要修复以下问题：...",
  "next_steps": "回到开发阶段修复问题后重新提交"
}
```

## 门禁规则

1. 盲审结果非 PASS 不得调用本技能
2. Owner 选择 No-Go 必须回退修复，不得绕过
3. 发布目录与 `manifest.json` 未生成视为发布失败

## 发布清单 (manifest.json)

```json
{
  "task_id": "TASK-001",
  "release_date": "2025-04-13T15:30:00",
  "decision": "go",
  "stages": {
    "requirements": "pass",
    "forge": "pass",
    "tdd": "pass",
    "review": "pass",
    "owner": "go"
  },
  "artifacts": [
    "10-requirements/TASK-001.md",
    "20-planning/TASK-001.md",
    "30-build/TASK-001-execution_evidence-20250413.md",
    "40-review/TASK-001.md"
  ],
  "git_commit": "abc123"
}
```

## 注意事项

1. 这是发布流程的最后一环，必须谨慎决策
2. Go 决策会执行 Git 提交，确保代码已准备好
3. 发布归档后，任务状态变为 `released`
4. No-Go 后需要修复问题并重新走审查流程
5. 非交互模式适用于 CI/CD 场景，但建议关键发布使用交互式
