# Codex Usage Notes

## 文档定位

本文档只回答一个问题：**当前仓库接入 Codex 后，实际是如何运行的。**

## 当前运行方式

当前 Codex 接入方式基于：

1. 仓库根级 `skills/` 目录
2. `using-superpowers` 作为总入口 skill
3. Codex 自身的 skill 发现与调用能力

也就是说，当前仓库在 Codex 中的运行方式仍然是：

- 基于 skill 的软编排
- 基于 prompt / hook / skill 描述的流程约束
- 不是显式代码 orchestrator

## 这意味着什么

接入 Codex 后，当前仓库可以：

- 让 Codex 发现并使用根级 `skills/`
- 按当前 skill 体系执行四阶段准备链与正式开发后半骨架
- 使用透明度协议与 reviewer 隔离相关 skill 约束流程

但当前仓库仍然没有：

- 独立 runtime 审批系统
- 代码级硬状态机
- 显式 orchestrator 进程

因此，当前主控逻辑仍主要存在于：

- `using-superpowers`
- 各 `SKILL.md` 的触发条件与流程描述
- Codex 的会话内自我编排

## 当前建议

如果当前目标只是“先让仓库在 Codex 中可用”，那么现有结构已经足够支撑接入。

如果后续目标升级为：

- 强制阶段顺序
- 硬审批准入
- 可验证的 reviewer dispatch

那就需要后续再考虑显式 orchestrator 或更硬的状态门禁实现。
