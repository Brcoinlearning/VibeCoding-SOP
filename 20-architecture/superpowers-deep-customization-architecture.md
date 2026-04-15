# Superpowers 深度定制版 - 架构设计文档

## 本轮实现边界

> 本轮仅做 **沿用 superpowers 后半执行骨架的文档与 skill 编排增强**。  
> 明确禁止：把本项目架构设计成独立于 `superpowers` 之外的新平台、新编排器或新运行时。  
> 本文只定义“目标流程如何组织”，不预设独立 runtime orchestrator。

## 项目概述

**项目名称**：Superpowers 深度定制版

**基于**：
- 业务规则备忘录 v3（10-requirements/superpowers-deep-customization-business_rules_memo.md）
- 技术选型文档 v4（15-tech-selection/superpowers-deep-customization-tech-selection.md）

**架构目标**：
- 用四阶段准备链替代原项目前半主链
- 在 `using-git-worktrees` 之后进入正式开发
- 沿用原项目后半执行骨架，只增强透明度与 reviewer 隔离
- 让后续文档和 skills 都围绕当前目标物收敛，而不是滑向平台化重建

## 架构结论

### 核心结论

本项目的架构不是一个新的平台架构，而是一套**基于 superpowers skill 组织方式的目标流程架构**。

本次定制明确分成两段：

1. **前半链替换**：
   `Boundary Convergence -> Tech Selection -> Architecture -> Contract Solidification`
2. **后半链继承并增强**：
   `using-git-worktrees -> task execution -> isolated review -> finishing`

其中：
- `brainstorming` 不再是主链步骤。
- `writing-plans` 不再是主链步骤。
- 正式开发从 `using-git-worktrees` 开始。
- 正式开发期仍保留原项目的 task、subagent、TDD、review、finishing 思路。

### 明确不采用

- 不采用新的 Python orchestrator 作为主调度中心。
- 不采用以独立服务或脚本为核心的运行时模型。
- 不采用“文档之外另有一套平台对象层”的表达方式。
- 不把 `brainstorming` 和 `writing-plans` 以“兜底主链”的方式偷偷保留回架构主流程。

## 参考骨架

### 原项目值得继承的部分

依据 [README.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/superpowers/README.md) 与相关 skills，原项目真正值得继承的是后半执行骨架：

1. **工作树隔离**：通过 `using-git-worktrees` 建立安全的正式开发环境。
2. **逐 task 执行**：通过 task 粒度推进实施，而不是一次性完成整个需求。
3. **subagent 执行**：通过 fresh subagent 降低上下文污染。
4. **TDD 纪律**：通过 `test-driven-development` 保持 RED-GREEN-REFACTOR。
5. **review 与收尾**：通过 review 和分支收尾技能形成闭环。

本次定制保留的就是这部分骨架，而不是原项目前半的默认 design/plan 入口。

## 目标流程

### 完整流程

```text
用户提出需求
  -> Boundary Convergence
  -> Tech Selection
  -> Architecture
  -> Contract Solidification
  -> using-git-worktrees
  -> 按 Architecture 产物逐 task 执行
  -> implementer subagent 执行
  -> 独立 reviewer subagent 审查
  -> task 完成后进入下一 task
  -> finishing-a-development-branch
```

### 流程含义

- 前四阶段负责把模糊需求变成稳定输入。
- `Architecture` 阶段不仅给出架构，还要给出正式开发的 task 来源。
- 四阶段全部通过后，正式开发才开始。
- 正式开发的第一个动作是 `using-git-worktrees`。
- 进入 worktree 后，按 task 逐项推进、逐项 review、最后收尾。

## 模块划分

### 模块 1：四阶段准备链

**职责**：在正式开发前，生成稳定、可交接、可验证的输入资产。

**阶段组成**：
- `Boundary Convergence`
- `Tech Selection`
- `Architecture`
- `Contract Solidification`

**核心产物**：
- `10-requirements/` 业务规则备忘录
- `15-tech-selection/` 技术选型文档
- `20-architecture/` 架构设计与任务拆解文档
- `25-contract/` 测试契约文档

**放行规则**：
- 任一阶段不通过，不得进入下一阶段。
- 四阶段全部通过前，不得进入 `using-git-worktrees`。
- 阶段放行以文档 frontmatter 中的 `status: approved` 为准。
- 下一阶段开始前，必须向 Owner 显式展示上游文档的关键 frontmatter 字段。

### 模块 2：正式开发执行链

**职责**：在 worktree 中消费四阶段产物并完成实际实施。

**执行骨架**：
- `using-git-worktrees`
- 逐 task 执行
- implementer subagent
- reviewer subagent
- finishing-a-development-branch

**架构要求**：
- 不重新引入 `brainstorming` 与 `writing-plans` 作为主链依赖。
- task 来源直接来自 `Architecture` 阶段产物。
- 契约约束直接来自 `Contract Solidification` 阶段产物。

### 模块 3：透明度与隔离增强层

**职责**：在正式开发执行链上叠加刚性门禁。

**增强点**：
- task 开始前必须声明前置文档、目标、预计改动范围、即将调用的 subagent
- implementer 开始前必须征求 Owner 同意
- reviewer 调用前必须显式通知 Owner
- task 完成后必须先汇报改动摘要和结果
- 高风险 task 必须预览后写入
- reviewer 必须是独立 fresh subagent，并使用专门 reviewer prompt

**统一载体**：
- 正式开发期的说明模板统一收敛到 `skills/development-transparency-protocol/SKILL.md`
- `subagent-driven-development` 与 `test-driven-development` 只负责引用和执行，不再各自维护一套独立话术体系

## 四阶段准备链的架构职责

### 1. Boundary Convergence

**职责**：把模糊需求收敛成业务规则、边界、异常和范围。

**输出要求**：
- 业务规则备忘录
- 范围与边界明确
- 不再依赖正式开发时临时补需求

### 2. Tech Selection

**职责**：明确技术约束、复用策略和技术选择依据。

**输出要求**：
- 技术约束清晰
- 与原项目结构的映射关系清晰
- 为后续架构和实施提供技术边界

### 3. Architecture

**职责**：定义结构边界，并生成正式开发的 task 来源。

**输出要求**：
- 架构边界
- 模块职责
- task 列表
- task 依赖关系
- 并行/串行关系
- 风险 task 标记

**关键说明**：
- `Architecture` 阶段不是单纯“画架构”。
- 它还必须替代原 `writing-plans` 的 task 来源职责。
- 如果 task 粒度、依赖关系或串并行关系不合理，不得进入正式开发。

### 4. Contract Solidification

**职责**：把前面三阶段的产物转成正式开发期可消费的契约。

**输出要求**：
- 可验证的测试契约
- 对正式开发与 review 的约束
- 对高风险改动和透明度门禁的契约表达

## 正式开发执行链的架构职责

### 1. using-git-worktrees

**职责**：正式开发入口。

**规则**：
- 四阶段通过后才能进入。
- 进入后才允许开始逐 task 实施。

### 2. implementer subagent

**职责**：负责某个 task 的实施与 TDD 循环。

**规则**：
- implementer 只负责实现。
- 不得兼任 reviewer。
- 必须在 task 开始前完成透明度说明。

### 3. reviewer subagent

**职责**：对每个 task 做独立审查。

**规则**：
- 每个 task 完成后立即触发。
- reviewer 必须是独立 fresh subagent。
- reviewer 必须使用专门 reviewer prompt。
- Owner 必须能看见 reviewer 即将被调用以及调用结果。

### 4. finishing-a-development-branch

**职责**：在所有 task 完成后做正式收尾。

**规则**：
- 只有当前面 task 链与 review 链都完成时才进入。
- 继续沿用原项目的分支收尾思路。

## 目录结构设计

| 目录 | 角色 |
|------|------|
| `superpowers/` | 原项目参考实现 |
| `10-requirements/` | 边界收敛产物 |
| `15-tech-selection/` | 技术选型产物 |
| `20-architecture/` | 架构与任务拆解产物 |
| `25-contract/` | 契约固化产物 |
| `skills/` | 本项目新增或增强的 skills |

## 固定产物命名

四阶段产物统一采用固定文件名：

- `10-requirements/business_rules_memo.md`
- `15-tech-selection/tech-selection.md`
- `20-architecture/architecture.md`
- `20-architecture/tasks.md`
- `25-contract/test_contract.md`

这样做的目的不是支持同目录并行多个需求实例，而是让当前这一轮目标物的阶段输入输出路径稳定、可预测、可断言。

## Frontmatter 状态门禁

每份阶段文档都应带统一 frontmatter，至少包含：

```yaml
doc_id: "business_rules_memo|tech_selection|architecture|tasks|test_contract"
phase: "boundary-convergence|tech-selection|architecture-and-tasking|contract-solidification"
artifact: "business_rules_memo|tech_selection|architecture|tasks|test_contract"
status: "draft|in_review|approved|superseded"
derived_from: []
updated_at: "YYYY-MM-DD"
```

架构上的定位是：
- 这是轻量状态断言，不是独立状态机服务
- 它用于阶段放行前的显式检查
- 它不能替代 Owner 审阅，但能显著降低流程跳转的随意性

## 数据与交接关系

```text
10-requirements
  -> 15-tech-selection
  -> 20-architecture
  -> 25-contract
  -> using-git-worktrees
  -> task execution
  -> review
  -> finishing
```

**交接原则**：
- 文档是主交接介质。
- `Architecture` 提供 task 来源。
- `Contract` 提供验收与执行约束。
- 正式开发不应脱离四阶段产物重新假设需求。

## 门禁设计

### 前置门禁

- 四阶段未全部通过，不得进入 `using-git-worktrees`。
- `Architecture` 的 task 分解不合格，不得放行。
- `Contract` 不可验证，不得放行。
- 上游文档未达到 `status: approved`，不得放行下一阶段。

### 执行门禁

- task 开始前未完成 Owner 对齐，不得实施。
- 未显式说明 implementer subagent 调用，不得实施。
- 高风险 task 未完成预览确认，不得写入。

### review 门禁

- implementer 不得为自己放行。
- 未显式说明 reviewer 调用，不得视为已审查。
- reviewer 未使用专门 prompt，则该 review 无效。

## 这份架构文档应表达什么

- 前半链如何被四阶段准备链替代。
- 正式开发为何从 `using-git-worktrees` 开始。
- `Architecture` 如何承担 task 来源职责。
- 透明度和 reviewer 隔离如何作为执行门禁叠加到原后半骨架上。

## 这份架构文档不应表达什么

- 不表达独立 runtime orchestrator 如何实现。
- 不表达未来 Python 脚本、事件总线、状态机服务如何建设。
- 不再把 `brainstorming` / `writing-plans` 写回主流程。

## 结论

本次架构的正确口径是：

- **前半链替换**：四阶段准备链取代原 `brainstorming` / `writing-plans` 主链职责。
- **后半链继承**：从 `using-git-worktrees` 开始沿用原项目正式开发骨架。
- **门禁增强**：透明度检查点和 reviewer 隔离成为正式开发期的硬规则。
- **实现克制**：当前只建立 skill-based orchestration protocol，不预设独立 runtime orchestrator。

---

**生成时间**：2026-04-15
**状态**：revised-draft
**版本**：v5
