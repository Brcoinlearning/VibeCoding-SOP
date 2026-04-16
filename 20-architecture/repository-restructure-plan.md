# 单一主仓库重组方案

## 文档定位

本文档只回答一件事：**当前项目如何从“外层仓库 + 内层 superpowers 仓库”的割裂结构，收敛为单一主仓库结构。**

它定义的是仓库治理与目录重组方案，不直接执行迁移操作，也不在本轮完成所有文件移动。

## 背景与问题定义

当前仓库存在以下结构性问题：

1. 外层仓库保存了四阶段 skills、需求/架构/契约文档与项目级 README。
2. 内层 `superpowers/` 仍是一个独立仓库，里面保存了原项目 skills 与部分已被本项目改写的技能。
3. 当前目标物语义上已经是一个整体工作流产品，但目录与 git 边界仍然割裂。
4. `brainstorming`、`writing-plans` 已不再是本项目主链步骤，但它们仍然存在于上游默认结构中。
5. 正式开发阶段实际依赖的 skills 一部分在外层 `skills/`，一部分在内层 `superpowers/skills/`，这会持续放大维护成本。

因此，当前结构适合调研，不适合长期演化。

## 重组结论

### 核心结论

本项目后续应被定义为：

**基于 superpowers 演化出的定制分叉版，并以外层仓库作为唯一主仓库。**

这意味着：

- 外层仓库成为唯一正式产品仓库
- `superpowers/` 不再继续作为长期运行中的内层独立仓库存在
- 所有正式参与运行的 skills 最终都要收敛到同一套主 `skills/` 目录中
- 上游 `superpowers` 在语义上转为“参考来源”与“差异对照对象”，而不再是运行边界

### 为什么不是增强层项目

本项目已经不只是新增若干补充 skill，而是在重写主流程：

- 前半主链已被四阶段准备链替换
- `Architecture` 已直接承担 task 来源职责
- 正式开发透明度与 reviewer 隔离已成为项目级硬规则
- `brainstorming` 与 `writing-plans` 已明确不再作为主链步骤

这类变化已经超出轻量 overlay 的合理边界，更符合“单一主仓库下的定制分叉版”。

## 重组目标

本次重组的最终目标是：

1. 仓库语义统一
2. skill 载体统一
3. 默认主流程统一
4. git 管理边界统一
5. 上游关系表达清晰

展开来说：

- 以后打开仓库的人，应当看到一个完整目标物，而不是“产品层 + 内嵌参考仓库”的混合物
- 正式运行时，应只认一套主 `skills/`
- README、架构文档、skill 变更映射、契约文档都应围绕同一仓库结构表达
- 外层仓库与内层仓库分开提交、分开追踪的状态应被终结

## 目标目录结构

建议的目标结构如下：

```text
软件开发SOP/
├── README.md
├── 10-requirements/
├── 15-tech-selection/
├── 20-architecture/
├── 25-contract/
├── docs/
│   ├── upstream-diff/
│   └── decisions/
├── skills/
│   ├── boundary-convergence/
│   ├── tech-selection/
│   ├── architecture-and-tasking/
│   ├── contract-solidification/
│   ├── development-transparency-protocol/
│   ├── using-git-worktrees/
│   ├── subagent-driven-development/
│   ├── test-driven-development/
│   ├── requesting-code-review/
│   ├── executing-plans/
│   ├── finishing-a-development-branch/
│   └── ...
└── .git
```

这个结构表达的是：

- 根目录就是产品本体
- `skills/` 是唯一主技能目录
- 文档目录只承担说明、架构、差异记录职责
- 不再保留运行语义上的 `superpowers/` 内层仓库边界

## Skill 目录治理原则

### 原则 1：只保留一个主 `skills/`

后续正式运行时，所有主流程 skills 都应收敛到根目录 `skills/`。

这意味着：

- 外层 `skills/` 是未来唯一主技能目录
- 当前 `superpowers/skills/` 中仍被正式使用的能力，需要迁移进主 `skills/`
- 不允许长期保持“两套都算正式技能目录”的状态

### 原则 2：新增 skill 与改写 skill 不再分仓表达

无论 skill 是：

- 本项目新增
- 从 `superpowers` 继承
- 基于 `superpowers` 改写

最终都应进入统一的主技能目录，并通过文档说明其来源，而不是继续通过目录边界表达来源。

### 原则 3：来源通过文档表达，不通过嵌套仓库表达

skill 的来源关系，应记录在差异文档中，而不是依赖 `superpowers/` 这个内层仓库去提醒维护者“这是上游来的”。

## Skill 分类与处置策略

### A 类：当前主链必需 skill

以下 skills 应进入主 `skills/`，并成为后续正式主线的一部分：

- `boundary-convergence`
- `tech-selection`
- `architecture-and-tasking`
- `contract-solidification`
- `development-transparency-protocol`
- `using-git-worktrees`
- `subagent-driven-development`
- `test-driven-development`
- `requesting-code-review`
- `executing-plans`
- `finishing-a-development-branch`

### B 类：保留但降级为非主链参考 skill

以下 skills 当前不再作为默认主链步骤，但仍可能保留为参考或补充能力：

- `brainstorming`
- `writing-plans`

对它们的建议处理方式：

1. 不立即删除
2. 不再在 README 和主流程文档中把它们写成默认入口
3. 在 skill 内或差异文档中标记为“本项目非主链能力 / legacy reference”

### C 类：暂不纳入首轮主仓库技能集合

对当前目标物没有直接作用的上游技能，不必在首轮全部迁移进来。

处理原则：

- 如果当前主流程不依赖，就不优先迁移
- 如果未来需要，再从上游参考资产中选择性吸收

## `superpowers/` 目录的退场策略

### 当前角色

当前 `superpowers/` 的实际角色是：

- 上游参考资产容器
- 已改写 skills 的旧存放位置
- 造成运行边界割裂的主要来源

### 目标角色

重组完成后，`superpowers/` 不应再作为运行目录存在。

可接受的最终状态只有两种：

1. 完全移除
2. 临时改名为纯参考目录，并在迁移完成后删除

### 不建议的状态

以下状态不应长期存在：

- `superpowers/` 继续作为内层独立 git 仓库
- 外层 `skills/` 与内层 `superpowers/skills/` 同时承担正式运行职责
- 主流程文档写一套，目录结构继续按另一套存在

## Git 治理原则

### 原则 1：外层仓库是唯一正式仓库

后续正式开发、提交、发布，都应基于外层仓库进行。

### 原则 2：终结 nested repo 状态

`superpowers/.git` 不应在最终结构中继续保留。

### 原则 3：上游关系通过文档与差异记录维护

与上游 `superpowers` 的关系，应通过以下方式表达：

- README 中的来源说明
- 差异映射文档
- 必要时记录上游参考版本

而不是通过继续保留一个运行中的内层仓库来表达。

## 迁移阶段设计

### 阶段 1：文档确认阶段

目标：先把重组方案定清楚，不急于一次性搬迁全部内容。

本阶段完成标准：

- 明确单一主仓库方向
- 明确主 `skills/` 唯一化目标
- 明确 `brainstorming` / `writing-plans` 的降级处理策略
- 明确 `superpowers/` 的退场方向

### 阶段 2：主技能目录收拢阶段

目标：把当前主流程真正依赖的 skills 收拢到统一主 `skills/`。

本阶段重点：

- 迁移 `using-git-worktrees`
- 迁移 `subagent-driven-development`
- 迁移 `test-driven-development`
- 迁移 `requesting-code-review`
- 迁移 `executing-plans`
- 迁移 `finishing-a-development-branch`
- 一并迁移它们依赖的 prompt 与 reference 文件

完成标准：

- 当前主流程运行不再依赖 `superpowers/skills/`

### 阶段 3：非主链技能降级与标注阶段

目标：处理不再属于默认主链的上游技能。

本阶段重点：

- `brainstorming` 标注为非主链参考能力
- `writing-plans` 标注为非主链参考能力
- 修正 README、架构文档、skill map 中的残留默认表述

### 阶段 4：内层仓库退场阶段

目标：彻底结束 `superpowers/` 作为内层独立仓库的状态。

本阶段重点：

- 清理 nested git 关系
- 移除或归档 `superpowers/` 目录
- 补齐上游差异说明文档

完成标准：

- 外层仓库成为唯一产品仓库
- 运行目录与 git 目录边界一致

## 风险与控制策略

### 风险 1：一次性大搬迁导致路径全部失效

控制策略：

- 分阶段迁移
- 每迁移一类 skills 就同步修正 README、skill map、相关引用

### 风险 2：删掉 `brainstorming` / `writing-plans` 太早，失去参考价值

控制策略：

- 先降级，不立刻删除
- 待新主链稳定后再决定是否彻底移除

### 风险 3：上游关系消失，后续无法判断哪些内容来自 `superpowers`

控制策略：

- 补 `docs/upstream-diff/` 文档
- 对关键 skill 记录“保留 / 改写 / 替换”关系

### 风险 4：迁移后 README 与架构文档再次失配

控制策略：

- 每次结构迁移后，都必须同步检查：README、架构文档、skill map、execution-progress、test contract

## 与现有文档的关系

本文档补充的是**仓库重组设计**，不是替代以下文档：

- `README.md`：项目总览
- `20-architecture/architecture.md`：目标流程架构
- `20-architecture/superpowers-deep-customization-skill-map.md`：skill 改写与映射关系
- `20-architecture/execution-progress.md`：当前执行进度

它负责回答“目录和仓库边界应该怎么重组”，而不是“流程本身是什么”。

## 当前阶段结论

当前已经达成的共识是：

1. 本项目后续按**单一主仓库**方向推进。
2. 当前结构中的 `superpowers/` 只是过渡性参考载体，不应长期保留为内层运行仓库。
3. 后续正式运行应只认一套主 `skills/`。
4. `brainstorming` 与 `writing-plans` 不再是本项目默认主链步骤。
5. 重组任务应在后续单独实施，不与当前文档收敛工作混做。

---

**生成时间**：2026-04-16
**状态**：draft
**版本**：v1
