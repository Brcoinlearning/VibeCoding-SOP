# 软件开发 SOP

## 项目定位

本项目不是从零重建一套新的 Agent 开发平台，而是以 [superpowers](/Users/mr.hu/Desktop/开发项目/软件开发SOP/superpowers/README.md) 为主参考对象，对其进行面向个人通用业务开发场景的流程优化。

当前工作的核心目标是：

- 保留 `superpowers` 已经验证过的后半执行骨架
- 用新的前置四阶段准备链替代原项目前半主链
- 在正式开发阶段补强透明度与 reviewer 隔离
- 通过文档、skills、prompts 先把流程协议收敛清楚，再决定后续整体架构如何调整

换句话说，这个仓库当前首先是在做一套**沿用并增强 superpowers 的开发流程协议**，而不是先做新的运行时系统。

## 相对 superpowers 的核心优化

### 1. 前置主链被替换为四阶段准备链

相对 `superpowers` 默认的前半设计/计划路径，本项目当前采用：

```text
Boundary Convergence
  -> Tech Selection
  -> Architecture and Tasking
  -> Contract Solidification
```

这四个阶段分别负责：

- 边界收敛：把模糊需求压缩成业务规则、范围和边界条件
- 技术选型：明确技术路线、复用策略、排除项和外部开源参考
- 架构拆解：同时完成架构边界设计与 task 合理拆解
- 契约固化：把正式开发前必须满足的验收条件、透明度门禁、review 隔离要求固化下来

其中，`Architecture and Tasking` 不只是画架构，还直接承担正式开发 task 来源职责，这一点是相对原流程的重要调整。

### 2. 正式开发仍沿用 superpowers 后半骨架

本项目没有抛弃 `superpowers` 的核心执行能力，而是保留并增强以下部分：

- `using-git-worktrees`
- `subagent-driven-development`
- `test-driven-development`
- `requesting-code-review`
- `finishing-a-development-branch`

当前定义的正式开发主线是：

```text
四阶段准备链完成
  -> using-git-worktrees
  -> task execution
  -> isolated review per task
  -> finishing
```

也就是说，本项目优化的重点不是重造执行骨架，而是把前置输入质量和执行期护栏做得更强。

### 3. 增加面向 Owner 的透明度协议

相对原流程，本项目把“Agent 不得闷头推进”定义成显式规则。

在当前方案里，主控 agent 和子 agent 在关键节点都必须让 Owner 看见：

- 读了哪些前置文档
- 当前要完成什么
- 预计会改哪些文件或文件类型
- 接下来准备调用哪个 subagent
- review 何时开始、由谁执行、结果如何

对于高风险或大范围改动，还要求先预览、后写入。

### 4. 增加 reviewer 隔离

本项目把 reviewer 隔离从“最佳实践”上升为流程要求：

- implementer 只负责实现，不得自审自放行
- spec reviewer 必须是独立 fresh reviewer subagent
- code quality reviewer 必须是独立 fresh reviewer subagent
- 修复后的重新审查仍需重新 fresh dispatch reviewer
- final review 若执行，也必须显式对 Owner 可见

这项优化的目的，是尽量减少“实现者自己放水”或“Owner 无法确认 review 是否真的发生”的情况。

### 5. 文档与产物采用固定命名协议

为了让阶段交接更稳定，本项目当前采用固定产物命名，而不是按 topic 动态拼路径：

- `10-requirements/business_rules_memo.md`
- `15-tech-selection/tech-selection.md`
- `20-architecture/architecture.md`
- `20-architecture/tasks.md`
- `25-contract/test_contract.md`

这些文档统一带 frontmatter，用来表达：

- `doc_id`
- `phase`
- `artifact`
- `status`
- `derived_from`
- `updated_at`

下一阶段开始前，需要先检查上游文档是否已经达到 `status: approved`。

## 当前实现边界

当前仓库已经完成的主要是：

- 需求、技术、架构、契约文档的重新收敛
- 四阶段 skills 的首版实现
- 正式开发透明度协议的首版实现
- 对 `superpowers` 关键 skills 和 reviewer prompts 的项目级增强

当前仓库**尚未**引入：

- 新的 Python orchestrator
- 独立 runtime 审批系统
- 代码级硬拦截式状态机

这意味着本项目现在落地的是**文档 / skill / prompt 级强约束**，而不是更重的运行时系统。

## 关键文档索引

如果要理解当前方案，建议优先看这些文档：

- [10-requirements/business_rules_memo.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/10-requirements/business_rules_memo.md)
- [15-tech-selection/tech-selection.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/15-tech-selection/tech-selection.md)
- [20-architecture/architecture.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/20-architecture/architecture.md)
- [20-architecture/superpowers-deep-customization-skill-map.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/20-architecture/superpowers-deep-customization-skill-map.md)
- [25-contract/test_contract.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/25-contract/test_contract.md)

与流程直接相关的 skills 在这里：

- [skills/boundary-convergence/SKILL.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/skills/boundary-convergence/SKILL.md)
- [skills/tech-selection/SKILL.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/skills/tech-selection/SKILL.md)
- [skills/architecture-and-tasking/SKILL.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/skills/architecture-and-tasking/SKILL.md)
- [skills/contract-solidification/SKILL.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/skills/contract-solidification/SKILL.md)
- [skills/development-transparency-protocol/SKILL.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/skills/development-transparency-protocol/SKILL.md)

相对 `superpowers` 的关键改写点在这里：

- [superpowers/skills/using-git-worktrees/SKILL.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/superpowers/skills/using-git-worktrees/SKILL.md)
- [superpowers/skills/subagent-driven-development/SKILL.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/superpowers/skills/subagent-driven-development/SKILL.md)
- [superpowers/skills/test-driven-development/SKILL.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/superpowers/skills/test-driven-development/SKILL.md)
- [superpowers/skills/requesting-code-review/SKILL.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/superpowers/skills/requesting-code-review/SKILL.md)
- [superpowers/skills/executing-plans/SKILL.md](/Users/mr.hu/Desktop/开发项目/软件开发SOP/superpowers/skills/executing-plans/SKILL.md)

## 后续方向

当前这份 README 只负责回答两件事：

- 这个项目相对 `superpowers` 做了什么优化
- 当前方案落到了哪些文档和 skills 上

具体如何安装、如何触发、如何运行，暂时不在这里展开，因为后续整体架构仍可能继续调整。
