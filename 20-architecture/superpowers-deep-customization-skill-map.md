# Superpowers 深度定制版 - Skill 变更映射

## 文档定位

本文档只回答一件事：**为了实现当前目标流程，需要新增或改写哪些 skill。**

它不描述未来脚本系统，也不引入独立 orchestrator。这里的“编排”只指基于文档与 `SKILL.md` 的流程协议。

## 目标流程回顾

当前目标流程为：

```text
Boundary Convergence
  -> Tech Selection
  -> Architecture
  -> Contract Solidification
  -> using-git-worktrees
  -> subagent-driven-development
  -> isolated review per task
  -> finishing-a-development-branch
```

其中：
- 前四阶段替代原 `brainstorming` / `writing-plans` 前半主链。
- 正式开发仍沿用 `superpowers` 的后半执行骨架。
- 重点增强点只有两类：透明度、reviewer 隔离。

## 变更策略

### 策略 1：沿用原 skill 名称优先

只要原 skill 能承载当前目标，就优先在原 skill 上增强，而不是新造平行 skill。

### 策略 2：新增只补前半链缺口

新增 skill 只用于承接四阶段准备链，以及补充透明度协议这类原项目未显式表达的规则。

### 策略 3：review 协议显式化

review 相关要求不能只停留在口头约定，必须落到 `SKILL.md` 与 reviewer prompt。

## Skill 变更总表

| 类型 | Skill / 文档 | 处理方式 | 责任 |
|------|--------------|----------|------|
| 改写 | `superpowers/skills/using-git-worktrees` | 增强 | 接入四阶段放行门禁，成为正式开发入口 |
| 改写 | `superpowers/skills/subagent-driven-development` | 增强 | 承载 task 执行、Owner 对齐、fresh implementer / fresh reviewer 隔离 |
| 改写 | `superpowers/skills/test-driven-development` | 增强 | 保留 TDD 核心纪律，同时服从 Owner 可见性门禁 |
| 改写 | `superpowers/skills/executing-plans` | 增强 | 作为 fallback 执行路径时仍服从透明度与独立 review 规则 |
| 改写 | `superpowers/skills/requesting-code-review` | 增强 | 明确 reviewer 必须独立、fresh，且调用前对 Owner 可见 |
| 改写 | `superpowers/skills/subagent-driven-development/implementer-prompt.md` | 增强 | 约束 implementer 的声明、预览、汇报格式 |
| 改写 | `superpowers/skills/subagent-driven-development/spec-reviewer-prompt.md` | 增强 | 明确独立 reviewer、对抗性审查、禁止放水 |
| 改写 | `superpowers/skills/subagent-driven-development/code-quality-reviewer-prompt.md` | 增强 | 明确独立 reviewer 与质量审查口径 |
| 新增 | `skills/boundary-convergence` | 新建 | 前置阶段 1：边界收敛 |
| 新增 | `skills/tech-selection` | 新建 | 前置阶段 2：技术选型 |
| 新增 | `skills/architecture-and-tasking` | 新建 | 前置阶段 3：架构设计与 task 拆解 |
| 新增 | `skills/contract-solidification` | 新建 | 前置阶段 4：契约固化 |
| 新增 | `skills/development-transparency-protocol` | 新建 | 透明度声明模板与高风险预览门禁 |

## 改写项说明

### 1. `using-git-worktrees`

**保留部分**：
- worktree 目录选择
- 忽略校验
- 基线验证

**增强部分**：
- 明确四阶段全部通过后才能进入
- 明确它是正式开发入口
- 明确进入前要读取 `10/15/20/25` 产物

### 2. `subagent-driven-development`

**保留部分**：
- fresh subagent per task
- 逐 task 执行
- task 后 review

**增强部分**：
- task 开始前必须向 Owner 声明所读文档、目标、预计改动范围
- implementer 启动前必须得到 Owner 对齐
- reviewer 调用必须对 Owner 显式可见
- implementer 不得自审自放行
- spec reviewer 与 code quality reviewer 都必须是 fresh reviewer subagent
- 修复后重新审查时不得复用旧 reviewer session
- final review 若执行，也必须显式告知 Owner 并使用 fresh reviewer
- 每个 task 结束后先汇报再进入下一 task

### 2.1 `implementer-prompt.md`

**增强点**：
- implementer 只能实现，不具备 review 放行权
- 必须显式交回 review handoff
- 高风险或大范围改动先返回预览，不得直接写入

### 2.2 `spec-reviewer-prompt.md`

**增强点**：
- reviewer 必须先执行 Isolation Check
- 必须确认自己不是 implementer
- 必须确认自己是当前 review pass 的 fresh reviewer
- 必须确认 Owner 已被告知当前 review 调用

### 2.3 `code-quality-reviewer-prompt.md`

**增强点**：
- reviewer 必须先执行 Isolation Check
- 与 spec reviewer 一样要求 fresh reviewer 和 Owner 可见性
- 输出中明确包含 Isolation Check 结果

### 3. `test-driven-development`

**保留部分**：
- RED-GREEN-REFACTOR
- failing test first
- 不允许先写 production code

**增强部分**：
- 将透明度门禁嵌入开始写入前
- 高风险改动下要求先给 Owner 看预览
- 强调 TDD 是 implementer 的内部纪律，不替代 reviewer 隔离

### 4. `executing-plans`

**保留部分**：
- 作为无 subagent 优势场景下的 fallback 执行路径
- 批次执行与阶段性汇报

**增强部分**：
- 进入前仍需确认四阶段与 `using-git-worktrees` 已完成
- 每个 task 或 batch 仍需向 Owner 说明读取文档、目标与预计改动范围
- 不得因 fallback 路径而跳过独立 review 与透明度协议

### 5. `requesting-code-review`

**保留部分**：
- 继续沿用原项目 code reviewer 能力

**增强部分**：
- review 调用前必须对 Owner 可见
- reviewer 必须不是 implementer
- 修复后重新 review 时也必须 fresh dispatch

## 新增项说明

### 1. `boundary-convergence`

**输入**：用户目标、现有参考项目、已有需求线索。

**输出**：
- 边界、范围、非目标
- 核心业务规则
- 异常/歧义清单

**放行标准**：需求边界足够稳定，后续阶段不再依赖编码期临时补定义。

### 2. `tech-selection`

**输入**：边界收敛产物、原项目结构、复用约束。

**输出**：
- 技术选择
- 复用策略
- 与 `superpowers` 的映射关系

**放行标准**：后续架构设计不需要在实现期临时更换技术路线。

### 3. `architecture-and-tasking`

**输入**：需求与技术产物。

**输出**：
- 架构边界
- 模块职责
- task 列表
- 依赖关系
- 并行/串行关系
- 风险 task 标记

**放行标准**：task 粒度合理，依赖闭合，不需要靠实现期假设推进。

### 4. `contract-solidification`

**输入**：前 3 阶段产物。

**输出**：
- 测试契约
- review 约束
- 透明度门禁契约

**放行标准**：正式开发可以直接据此验收，不必再补新的流程定义。

### 5. `development-transparency-protocol`

**职责**：为正式开发链提供统一声明模板。

**至少包含**：
- task 启动说明模板
- implementer 调用说明模板
- reviewer 调用说明模板
- task 完成汇报模板
- 高风险预览后写入规则

## 本轮推荐实施顺序

```text
1. 改 using-git-worktrees
2. 改 subagent-driven-development
3. 改 test-driven-development
4. 改 implementer / reviewer prompt
5. 改 executing-plans 与 requesting-code-review 两条旁路
6. 补 development-transparency-protocol
7. 再补四阶段 skill
```

## 当前实现状态

- `using-git-worktrees`：已补正式开发入口与四阶段门禁
- `subagent-driven-development`：已补 Owner 对齐、fresh reviewer、final review 可见性
- `test-driven-development`：已补透明度预览门禁
- `executing-plans`：已补 fallback 路径透明度与独立 review 约束
- `requesting-code-review`：已补 Owner 可见与 reviewer 独立约束
- implementer / reviewer prompts：已补 isolation check 与 review handoff
- 四阶段 skills：已完成首版
- `development-transparency-protocol`：已完成首版

## 本轮不做

- 不实现 Python orchestrator
- 不实现独立 runtime 审批系统
- 不把 review 调度变成单独服务
- 不要求本轮先把所有自动化脚本写完

---

**生成时间**：2026-04-15
**状态**：draft
**版本**：v1
