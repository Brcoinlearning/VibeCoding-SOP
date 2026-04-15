# Superpowers 深度定制版 - 任务拆解文档

## 文档定位

本文档只回答一件事：**为了得到当前目标物，需要按什么顺序改哪些文档和 skills。**

它不再承担“平台迁移路线图”职责，也不描述未来 Python orchestrator、独立 runtime、脚本系统如何建设。

## 当前目标物

当前目标物是一套**基于 skill 的显式流程协议**，核心包含：

1. 四阶段准备链替代 `brainstorming` / `writing-plans` 前半主链。
2. 四阶段完成后进入 `using-git-worktrees`。
3. 正式开发阶段保留原项目后半执行骨架。
4. 在后半执行链中增强透明度检查点与 reviewer 隔离。

## 任务拆解原则

### 原则 1：先改口径，再改连接
- 先统一 `10/15/20/25` 文档口径
- 再定义哪些 skill 需要新增，哪些 skill 需要 project override

### 原则 2：先改流程协议，再谈代码化
- 本轮优先落文档、SKILL.md、门禁规则
- 不把未来脚本化、服务化实现混进当前主任务

### 原则 3：先保证任务来源可靠
- `Architecture` 阶段必须能稳定输出可执行 task 列表
- task 来源不稳定时，不进入正式开发链设计细化

## 主任务列表

### Task 1：统一需求与架构口径

**目标**：让需求、技术、架构、契约文档都反映同一条主流程。

**涉及内容**：
- 业务规则备忘录
- 技术选型文档
- 架构设计文档
- 测试契约文档

**完成标准**：
- 明确四阶段准备链替代 `brainstorming`
- 明确 `writing-plans` 不再作为主链必经步骤
- 明确正式开发从 `using-git-worktrees` 开始
- 明确优化点只集中在透明度与 reviewer 隔离

**依赖**：无

### Task 2：定义四阶段准备链的职责与验收

**目标**：明确四阶段各自产出什么、如何交接、何时放行。

**子任务**：
- 定义 `Boundary Convergence` 的输入、输出、验收标准
- 定义 `Tech Selection` 的输入、输出、验收标准
- 定义 `Architecture` 的输入、输出、验收标准
- 定义 `Contract Solidification` 的输入、输出、验收标准

**重点要求**：
- `Architecture` 必须包含架构边界和 task 合理化分解
- `Contract Solidification` 必须形成可直接约束正式开发的契约

**完成标准**：
- 四阶段之间的交接关系清晰
- 任一阶段未通过时，无法模糊放行下一阶段

**依赖**：Task 1

### Task 3：定义正式开发阶段的透明度协议

**目标**：把 Owner 可见性要求写成显式规则，而不是依赖 agent 自觉。

**子任务**：
- 定义 task 开始前必须读取和声明哪些前置文档
- 定义 implementer 启动前对 Owner 的说明模板
- 定义 reviewer 调用前对 Owner 的说明模板
- 定义 task 完成后的改动摘要与结果汇报模板
- 定义高风险 task 的“预览后写入”规则

**完成标准**：
- 任何 task 都至少满足“开始前说明、review 调用说明、完成后汇报”
- 高风险 task 满足“预览后写入”

**依赖**：Task 2

### Task 4：定义 reviewer 隔离协议

**目标**：在保留原项目后半 review 结构的前提下，强化 reviewer 独立性和可见性。

**子任务**：
- 明确 implementer 与 reviewer 的职责边界
- 明确保留 spec review 与 code quality review 两道门
- 明确 reviewer 必须是 fresh subagent
- 明确 reviewer 必须使用专门 reviewer prompt
- 明确 Owner 必须可见 reviewer 调用与结果

**完成标准**：
- implementer 不再具备自我放行空间
- Owner 能确认 review 确实发生

**依赖**：Task 3

### Task 5：确定需要新增或改写的 skills

**目标**：按当前目标物识别真正需要变动的 skill 集合。

**候选范围**：
- 前置四阶段相关 skills
- `using-git-worktrees` 的接入说明
- `subagent-driven-development` 的透明度和 reviewer 协议增强
- `test-driven-development` 的 task 内透明度边界
- reviewer prompt 相关文档

**完成标准**：
- 列出“新增 skill”与“改写已有 skill”的清单
- 每个 skill 的职责、触发条件、与主流程关系明确

**依赖**：Task 4

### Task 6：回写测试契约

**目标**：确保测试契约验证的是当前目标流程，而不是未来平台实现。

**子任务**：
- 删除依赖独立 runtime 的场景
- 补充四阶段放行场景
- 补充透明度检查点场景
- 补充 reviewer 隔离与显式调用场景
- 补充 Architecture task 分解质量场景

**完成标准**：
- 契约可以直接作为当前目标物的验收基线

**依赖**：Task 5

## 建议执行顺序

```text
Task 1
  -> Task 2
  -> Task 3
  -> Task 4
  -> Task 5
  -> Task 6
```

## 不纳入本轮主任务的内容

- Python orchestrator 代码实现
- 独立 blind review runtime 的代码化重建
- 事件总线、状态机服务、通知服务等平台能力
- 面向未来扩展的自动导入脚本或统一 CLI 设计

## 架构阶段的额外验收要求

由于 `Architecture` 阶段承担正式开发 task 来源，它必须额外满足以下检查项：

1. 每个 task 都有明确目标。
2. 每个 task 都有明确前置依赖。
3. task 粒度不过大也不过碎。
4. 不存在需要靠实现期临时假设才能成立的依赖关系。
5. 能明确区分可以并行与必须串行的任务。

若以上任一项不满足，则 `Architecture` 阶段不得放行。

---

**生成时间**：2026-04-15
**状态**：revised-draft
**版本**：v2
