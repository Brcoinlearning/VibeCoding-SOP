# 技术选型文档

## 本轮实现边界

> 本轮仅做 **基于 superpowers 既有结构的文档化优化与 SKILL.md 编排增强**。  
> 明确禁止：脱离 `superpowers` 运行骨架另起一套运行时、编排器或平台层实现。  
> 允许产物：`SKILL.md`、需求/选型/架构/任务/契约/进度文档，以及为这些文档服务的轻量说明。

## 项目概述

**项目名称**：Superpowers 深度定制版

**基于**：业务规则备忘录（10-requirements/business_rules_memo.md）

**选型目标**：在不偏离原项目运行方式的前提下，给 superpowers 增加更强的需求分析前置、审查隔离约束与过程透明度。

## 基线原则

### 原项目优先原则

- 运行骨架优先沿用 `superpowers/README.md` 中已经验证过的后半执行能力：`using-git-worktrees -> subagent-driven-development / executing-plans -> test-driven-development -> requesting-code-review -> finishing-a-development-branch`
- 组织载体优先沿用 `superpowers/skills/*/SKILL.md` 的技能体系，而不是新增独立编排平台
- 交互入口优先沿用 skill 触发和已有命令语义，不把主流程迁移到 Python orchestrator 或独立脚本系统
- 定制目标是“补前置阶段、加约束、提透明度”，不是替换原项目的主干执行链

### 本次定制的增强位点

- 以前置四阶段分析资产沉淀替代原前半设计/计划主链
- 在 `subagent-driven-development` / `test-driven-development` 的既有流程上增加透明度和隔离门禁要求
- 在已有 `skills` 体系下做增量 skill 或 project override，不引入一套新的运行时抽象

## 技术选型总览

| 组件 | 选型 | 决策理由 |
|------|------|----------|
| 工作流主骨架 | 直接沿用 superpowers skills 工作流 | 原项目已验证，符合“沿用并增强” |
| 需求前置阶段 | 新增/整理需求分析类 skill 文档编排 | 补 superpowers 原版在需求分析深度上的不足 |
| 计划执行 | 由 `Architecture` 直接产出 task，并沿用 `subagent-driven-development` / `executing-plans` 落地 | 保留原项目执行习惯，但不再依赖 `writing-plans` 作为主链 |
| TDD 执行 | 沿用 `test-driven-development` | 保持原项目强约束，不另起流程 |
| 审查机制 | 沿用子 Agent 双阶段审查，增加隔离要求 | 与原项目 `subagent-driven-development` 对齐 |
| 透明化 | 通过 skill 指令层增加信息来源声明、改动预览、进度播报 | 不新增平台，直接增强现有交互协议 |
| 文档格式 | Markdown | 与原项目完全一致 |
| 状态记录 | 沿用文档 frontmatter + 轻量状态断言，不引入新状态机系统 | 保守增强，避免系统漂移 |

## 运行结构选型

### 选型结论

**选型**：以 `superpowers` 原生 skill 驱动工作流作为唯一主运行结构。

**不采用**：Clean Architecture 平台化重建、自定义 orchestrator 主导、独立 CLI 主导的流程迁移。

### 选择理由

- `superpowers` 的核心能力本来就不是运行时框架，而是一组可自动触发的 workflow skills
- 原项目已经明确了从设计、计划、执行、审查到收尾的闭环
- 本次需求真正缺的是“前置需求分析深度”和“执行可见性/隔离约束”，不是缺一层新架构
- 如果把需求写成独立平台，后续实现会天然偏向重造而不是复用

## Skill 组织方式选型

### 选型结论

**选型**：延续 `superpowers/skills/<skill-name>/SKILL.md` 这一组织模式，以新增 skill 和局部增强 skill 为主。

### 组织原则

- 原项目 skill 能表达的能力，优先通过复用或 project override 实现
- 只有当原项目没有对应能力时，才新增本地 skill
- 新增 skill 的命名、说明、触发条件、执行边界应与 superpowers 现有风格保持一致
- skill 之间通过文档产物衔接，而不是通过新平台对象模型衔接

### 对原项目 skill 的映射

| 目标能力 | 优先映射到的原项目能力 | 定制方式 |
|------|--------------------|----------|
| 需求澄清/方案讨论 | `brainstorming` | 不再作为本目标流程主链，必要时仅作补充参考 |
| 工作树隔离 | `using-git-worktrees` | 原样沿用 |
| 实施计划 | `20-architecture/tasks.md` | 由 `Architecture` 阶段直接承担 task 来源职责 |
| 子 Agent 执行 | `subagent-driven-development` | 增加透明度与隔离门禁 |
| 批处理执行 | `executing-plans` | 原样保留为备选执行路径 |
| TDD | `test-driven-development` | 增加文档期/透明化边界约束 |
| 代码审查 | `requesting-code-review` / 双阶段 review | 原样沿用，增强输入证据约束 |
| 结束收尾 | `finishing-a-development-branch` | 原样沿用 |

## 四阶段规划流程的接入方式

### 选型结论

**选型**：把四阶段规划流程作为 `superpowers` 标准开发链之前的前置分析链，而不是替代原有实现链。

### 阶段与原流程的关系

| 定制阶段 | 目标 | 与 superpowers 的衔接 |
|------|------|--------------------|
| 1. 边界收敛 | 形成业务规则备忘录 | 作为后续阶段的稳定输入 |
| 2. 技术选型 | 明确技术约束与复用策略 | 约束后续架构与实现边界 |
| 3. 架构拆解 | 形成任务边界与依赖 | 直接产出正式开发使用的 task 分解 |
| 4. 契约固化 | 形成可测验收契约 | 为 `test-driven-development` 和审查提供依据 |

### 接入原则

- 四阶段产物是当前目标流程的正式前置输入，而不是为 `writing-plans` 预热的过渡材料
- `Architecture` 阶段直接输出正式开发所消费的 task 文档
- `subagent-driven-development` 仍然负责逐任务调度与双阶段审查
- `test-driven-development` 仍然是实现阶段唯一的编码纪律

## Agent 隔离机制选型

### 选型结论

**主选方案**：沿用 `subagent-driven-development` 已有的“每任务 fresh subagent + 两阶段 review”模式，并把“隔离”定义为项目级强约束。

### 采用方式

- 实现阶段使用 fresh subagent 执行任务，保持上下文隔离
- 审查继续分为 spec compliance review 和 code quality review 两道门
- 对于需要更强隔离的场景，文档中只保留“未来可升级为独立 API reviewer”的扩展位，不将其定义为本轮主方案

### 不采用的方向

- 不把独立 API 审查定义为当前主干实现依赖
- 不把文件传递机制包装成新的主运行架构
- 不把隔离机制设计成新的平台对象层

### 选择理由

- 原项目已经把“fresh subagent per task”作为核心质量手段
- 这与当前需求中的“防止高负荷上下文导致审核放水”高度一致
- 在原模式上增加门禁，比另起系统的风险更低、兼容性更好

## 透明化机制选型

### 选型结论

**选型**：通过 skill 指令层增强实现透明化，不新增独立通知系统。

### 透明化范围

- 阶段开始/完成时的简明进度播报
- 子 Agent 启动前声明预期信息来源
- 子 Agent 执行时确认实际读取文档
- 文件修改前展示改动预览并等待确认
- 审查时明确最小证据输入集

### 载体

- 会话内文本输出
- 进度文档或轻量状态文件，仅作为辅助记录
- 需求/架构/契约文档中的审计信息

### 不采用的方向

- 不建设独立通知服务
- 不定义新的事件总线或进度中心
- 不为透明化单独引入平台基础设施

## Skill 来源策略

### 选型结论

**选型**：优先复用仓库内已有 `superpowers/skills`，本项目仅补缺口 skill，不做大规模外部 skill 搬运依赖。

### 原则

- `superpowers` 仓库内已有 skill，直接作为主参考对象
- 本项目新增 skill 时，优先放在项目 `skills/` 目录，以便版本化管理
- 外部 skill 仅在确实缺失且无法由现有 skill 承载时再引入

### 这样做的原因

- 本次任务明确要求“高度参考原项目的运行结构与 skill 方式”
- 如果大量依赖外部全局 skill，设计重心会偏出 `superpowers` 主体
- 项目内版本化更利于后续审查“哪些增强是真正相对原项目新增的”

## 文档与状态载体选型

### 文档格式

**选型**：Markdown

**理由**：

- 与 `superpowers` 文档、计划、skill 体系一致
- 可直接被 agent 与人类共同消费
- 适合沉淀四阶段产物和审查证据摘要

### 状态记录

**选型**：轻量记录，避免平台化

**理由**：

- 原项目核心不是依赖复杂状态机，而是依赖技能流程约束
- 当前需求只需要“Owner 可见”和“过程可追溯”，并不需要引入新的执行内核
- 以文档 frontmatter 作为阶段状态的唯一权威来源即可，不必额外建设状态服务

### 文件命名与 frontmatter 选型

**选型**：固定产物文件名 + 统一 frontmatter

**固定文件名**：
- `10-requirements/business_rules_memo.md`
- `15-tech-selection/tech-selection.md`
- `20-architecture/architecture.md`
- `20-architecture/tasks.md`
- `25-contract/test_contract.md`

**frontmatter 关键字段**：

```yaml
doc_id: "business_rules_memo|tech_selection|architecture|tasks|test_contract"
phase: "boundary-convergence|tech-selection|architecture-and-tasking|contract-solidification"
artifact: "business_rules_memo|tech_selection|architecture|tasks|test_contract"
status: "draft|in_review|approved|superseded"
derived_from: []
updated_at: "YYYY-MM-DD"
```

**采用理由**：
- 比 `<topic>` 占位路径更稳定
- 便于阶段间显式断言上游是否已 `approved`
- 不需要引入独立状态机或 Python orchestrator

### 上下文读取策略选型

**选型**：摘要优先读取，而不是默认读取上游全文。

**规则**：
- 先读 frontmatter
- 再读摘要或关键章节
- 只在当前问题需要时展开读取正文

**采用理由**：
- 控制上下文膨胀
- 保持纯 Prompt / 文档方案的轻量化
- 不必为了这一问题提前引入检索系统

## 待确认事项

1. 哪些增强应直接改写原有 `superpowers` skill，哪些应以新增本地 skill 承载。
2. 是否还需要为“补充 brainstorming”单独写一条非主链使用边界，避免后续误触发。
3. 透明化输出是否需要沉淀到固定模板文档，还是只保留会话协议要求。
4. 是否需要为“高风险任务”单独定义更强审查模式，但这不应改变当前主运行骨架。
5. 是否需要在全局规则中再补一条“正式开发必须遵循 transparency protocol”的总原则，以进一步减少遗忘风险。

## 结论

本项目的技术选型结论不是“做一个新的 Agent 开发平台”，而是：

- **以 superpowers 的 skill 工作流为主骨架**
- **以前置四阶段分析链补足需求与架构输入质量**
- **以透明化和隔离门禁增强执行与审查质量**
- **全程避免脱离原项目结构的系统性重构**

---

**生成时间**：2026-04-15
**状态**：revised-draft
**版本**：v4
