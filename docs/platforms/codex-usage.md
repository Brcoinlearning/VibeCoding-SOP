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

## Codex Subagent Dispatch Notes

本节只描述 Codex 平台中的 subagent 调用落地注意事项，不定义通用工作流。

### 分层原则

- `subagent-driven-development` 负责定义流程门禁、透明度要求与 reviewer 隔离
- Codex 平台文档负责定义当前平台中 subagent 调用如何正确落地

不要把 `spawn_agent` 的底层 payload 规则写回通用 workflow skill。

### 当前已知行为

在当前 Codex 环境中，`spawn_agent` / `send_input` 的输入必须严格满足“二选一输入通道”规则：

- 要么使用 `message`
- 要么使用 `items`

如果请求结构中同时出现两者，工具会拒绝执行。

当前已确认的一个关键细节是：

- 对某些会话或调用封装来说，只要请求结构里出现了 `items` 键，即使它是空数组，也可能被判定为“同时提供了 `message` 与 `items`”

因此，若要走 `message` 通道，推荐做法是：

- 请求结构中只保留 `message`
- 请求结构中彻底不出现 `items` 键

### 失败时如何表述

如果 subagent 调用因为 Codex 平台输入形状被拒绝，应这样表述：

- 这是当前会话中的 subagent dispatch layer 被阻塞
- implementer / reviewer 实际尚未启动
- 任务本身尚未进入标准 SDD 执行态

不要把这种情况表述成：

- 任务已经开始编码
- reviewer 已经实际运行
- SDD 已经成功进入实现阶段

### 这不代表什么

这类失败不自动说明：

- Codex 平台不支持 subagent
- Codex 不适配 SDD
- 任务方案、代码或环境本身有问题

更准确的判断通常是：

- 当前会话中的 subagent 调用落地方式，没有和 Codex 工具接口成功对齐
