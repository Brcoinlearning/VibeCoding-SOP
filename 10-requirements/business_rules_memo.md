# 业务规则备忘录

## 核心概念定义

**Superpowers 深度定制版**是什么：
- 基于 [superpowers](/Users/mr.hu/Desktop/开发项目/软件开发SOP/superpowers) 做流程级优化的开发工作流
- 前置以四阶段准备链替代原项目的 `brainstorming`
- 正式开发阶段仍高度参考原项目的 worktree、subagent、TDD、review、分支收尾方式
- 在原后半执行链上增强透明度和 reviewer 隔离

**四阶段准备链**的定义：
- `Boundary Convergence`：把模糊想法收敛成业务规则和范围边界
- `Tech Selection`：把技术约束、复用策略、技术取舍明确下来
- `Architecture`：形成架构边界、依赖关系、任务拆解与粒度控制
- `Contract Solidification`：把需求和架构转成可验证契约，作为正式开发输入

**透明度机制**的定义：
- 在阶段切换、task 启动、subagent 调用、准备修改文件时，agent 必须先说明再执行
- Owner 必须能看见“读了什么、准备做什么、准备调用谁、预计改哪里”
- 对高风险或大范围改动，必须先预览后写入

**阶段门禁状态**的定义：
- 四阶段产物采用固定文件命名，不再依赖 topic 变量拼装路径
- 每份阶段文档都必须带 frontmatter，并显式包含 `doc_id`、`phase`、`artifact`、`status`、`derived_from`、`updated_at`
- 下一阶段开始前，agent 必须先展示上游文档的关键 frontmatter，确认 `status: approved` 后才允许放行

**review 隔离**的定义：
- implementer subagent 只负责实现，不得对自己的结果做最终放行
- reviewer 必须是独立 fresh subagent，并使用专门 reviewer prompt
- 每个 task 完成后立即触发 reviewer，而不是等全部任务结束后一次性审查

## 需求概述

**项目名称**：Superpowers 深度定制版

**目标**：在保持原项目 skill 组织方式和后半执行骨架的前提下，补足前置需求准备深度，并显著提高执行阶段的可见性与审查可靠性。

**背景**：
- 原项目前半段更偏设计/计划导向，不完全符合当前需要的四阶段准备方式
- 实际开发中，即使流程上存在 reviewer，也可能出现 Owner 无法确认 reviewer 是否真的被调用的问题
- agent 在 CLI 中容易“闷头工作”，缺少与 Owner 的持续对齐点
- task 分解如果不合理，会直接导致实现阶段依赖混乱、假设过多、review 失效

## 目标用户描述

**最终用户**：软件开发者、项目经理、技术负责人、Owner

**主要关注点**：

| 角色 | 关注点 |
|------|--------|
| 开发者 | 前置输入完整、task 合理、实现阶段不反复返工 |
| 项目经理 | 需求流转透明、阶段状态可见、问题能及时暴露 |
| 技术负责人 | 架构边界清晰、依赖合理、review 不放水 |
| Owner | 每个关键阶段和关键 task 都能对齐，不被 agent 黑箱推进 |

## 用户场景

- 场景 1：用户提出一个新需求，系统先进入四阶段准备链，而不是直接 brainstorm 或直接写计划
- 场景 2：四阶段完成后，系统进入 worktree 中正式开发，并按 task 逐项推进
- 场景 3：每个 task 开始前，Owner 能看到本轮读取的前置文档、目标和预期改动范围
- 场景 4：每个 task 完成后，独立 reviewer 立即接手审查，Owner 能明确看到调用与结果

## 核心价值说明

**价值主张**：
Superpowers 深度定制版不是重建一套新平台，而是在原项目后半执行链基础上，通过**四阶段准备链**、**透明度检查点**和**对抗性 reviewer 隔离**，让需求准备更充分、执行过程更可见、审查结果更可信。

**与原项目的关系**：

| 维度 | 原项目 | 本次目标物 |
|------|--------|------------|
| 前置准备 | `brainstorming` + `writing-plans` 为主 | 四阶段准备链替代前半主链 |
| worktree 使用 | 保留 | 保留 |
| task 执行 | 保留 | 保留 |
| TDD 纪律 | 保留 | 保留 |
| review 结构 | 保留但需强化可见性与对抗性 | 保留并增强 |
| Owner 可见性 | 相对隐式 | 明确加入强制检查点 |

## 功能需求

**FR-1：四阶段准备链替代前半主链**
- 使用 `Boundary Convergence -> Tech Selection -> Architecture -> Contract Solidification`
- 四阶段完成后才进入 `using-git-worktrees`
- `brainstorming` 和 `writing-plans` 不再作为主链必经步骤

**FR-2：Architecture 阶段负责架构与 task 分解**
- 输出不只是架构说明，还必须包含合理的 task 拆解
- task 拆解必须覆盖依赖关系、粒度控制、并行/串行关系、风险标记
- 如果 task 拆解不满足验收标准，不得进入正式开发

**FR-3：正式开发阶段保留原后半执行骨架**
- 从 `using-git-worktrees` 开始进入正式执行
- 逐 task 执行、逐 task review、最后进入分支收尾
- 保留原项目的 subagent、TDD、review、finishing 思路

**FR-4：透明度检查点**
- 每个 task 开始前必须声明：读取了哪些前置文档、本轮要完成什么、预计改哪些文件、将调用哪个 subagent
- implementer 开始前必须征求 Owner 同意
- reviewer 调用前必须显式通知 Owner 将调用哪个 reviewer 做什么
- task 完成后必须先展示改动摘要和结果，再进入下一个 task
- 对高风险或大范围改动，必须先展示改动预览并获得确认后再写入

**FR-5：review 隔离与可见性**
- implementer 不得兼任 reviewer
- 每个 task 完成后立即触发 reviewer
- reviewer 必须是 fresh subagent，并使用专门 reviewer prompt
- Owner 必须能看见 reviewer 将被调用以及调用结果

## 非功能需求

**可见性**：
- 阶段切换、task 启动、review 调用、task 完成必须有明确文本说明
- Owner 不应通过猜测来判断流程是否真实发生

**一致性**：
- 需求、技术选型、架构、契约四阶段产物之间不得互相冲突
- 正式开发阶段必须消费四阶段产物，而不是脱离其重新假设

**可追溯性**：
- 每个阶段的输入、输出、放行条件必须能回溯
- 每个 task 的 review 调用与结果必须可追踪

**兼容性**：
- 组织方式、skill 表达方式、后半执行骨架应与原项目风格一致
- 不要求在本轮引入独立 runtime orchestrator

## 业务规则

**BR-1：主流程替换规则**
- 四阶段准备链替代原项目前半主链
- 完成四阶段后进入 `using-git-worktrees`

**BR-2：后半执行继承规则**
- worktree、逐 task 执行、TDD、review、分支收尾仍参考原项目
- 优化重点只在透明度和 reviewer 隔离

**BR-3：task 放行规则**
- task 开始前未完成文档读取声明和 Owner 对齐，不得开始实施
- task 完成后未完成 reviewer 调用，不得标记完成

**BR-4：高风险改动规则**
- 高风险、大范围或关键文件改动必须先预览后写入
- 普通 task 至少要做到“开始前说明、完成后汇报”

**BR-5：Architecture 放行规则**
- Architecture 阶段必须同时完成架构边界设计和 task 合理化拆解
- task 粒度或依赖关系不合格时，不得进入正式开发

## 边界条件

**范围内**：
- 四阶段准备链的流程定义与产物要求
- `using-git-worktrees` 之后的透明度增强
- reviewer subagent 的显式调用与隔离增强
- task 分解合理性与放行门禁

**范围外**：
- 在本轮把流程实现为独立 Python orchestrator
- 脱离原项目 skill 方式重建新的主运行平台
- 先行定义所有未来代码化扩展

## 异常处理

**阶段失败**：
- 任一前置阶段不达标，不得进入下一阶段
- 应明确告诉 Owner 失败原因、缺口和需要补齐的内容

**透明度失效**：
- 若未声明前置文档、未说明 subagent 调用、未做完成汇报，则该 task 视为流程不合格

**review 隔离失效**：
- 若 implementer 与 reviewer 未被显式区分，或 reviewer 调用对 Owner 不可见，则该次 review 无效

## 数据规范

**需求文档（10）**：描述目标、范围、规则、边界、透明度和隔离要求

**技术选型文档（15）**：描述技术约束、复用策略、与原项目结构的映射关系

**架构文档（20）**：描述流程结构、阶段衔接、task 拆解原则、review 与透明度门禁

**测试契约文档（25）**：描述如何验证四阶段产物、task 透明度、review 隔离和正式开发链是否符合要求

**固定产物命名规范**：
- `10-requirements/business_rules_memo.md`
- `15-tech-selection/tech-selection.md`
- `20-architecture/architecture.md`
- `20-architecture/tasks.md`
- `25-contract/test_contract.md`

**统一 frontmatter 关键字段**：

```yaml
doc_id: "business_rules_memo|tech_selection|architecture|tasks|test_contract"
phase: "boundary-convergence|tech-selection|architecture-and-tasking|contract-solidification"
artifact: "business_rules_memo|tech_selection|architecture|tasks|test_contract"
status: "draft|in_review|approved|superseded"
derived_from: []
updated_at: "YYYY-MM-DD"
```

## 待确认事项

1. 哪些改动应定义为高风险 task，从而触发“预览后写入”强门禁。
2. reviewer prompt 的具体风格边界如何定义，既保持对抗性又避免无意义挑错。
3. Architecture 阶段当前拟采用的 skill 组合是否足以稳定产出合格的 task 分解，需要在后续验收中验证。

---

**生成时间**：2026-04-15
**状态**：revised-draft
**版本**：v3
