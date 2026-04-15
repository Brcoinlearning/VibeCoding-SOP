---
name: architecture-and-tasking
description: 用于四阶段准备链的第 3 阶段，在技术选型完成后同时完成架构边界设计与 task 合理拆解，产出正式开发可直接消费的架构与任务文档，并决定是否允许进入 Contract Solidification
---

# Architecture and Tasking

## 技能定位

这是当前项目四阶段准备链的第 3 阶段 skill。

本阶段同时承担两件事：

1. 定义当前目标物的结构边界
2. 生成正式开发可以直接消费的 task 来源

它不是单纯“画架构”，也不是把若干任务随手列出来，而是要把后续开发期赖以推进的结构边界、模块职责、task 粒度、依赖关系和风险信息一次性压实。

这也是当前流程中用于替代原 `writing-plans` 主链职责的关键阶段。

## 本阶段的唯一目标

形成一份可交接的《架构与任务拆解文档》，并明确：

- 当前目标物的结构边界是什么
- 各模块或能力块分别负责什么
- 正式开发应该按哪些 task 推进
- 哪些 task 可以并行，哪些必须串行
- 哪些 task 风险较高，需要更强门禁
- 是否已经具备进入 `Contract Solidification` 的条件

## 不做什么

本阶段禁止混入以下内容：

- 直接开始编码或进入 worktree
- 把测试契约细节提前写完
- 把 review 流程细节提前混入架构说明
- 只给宏观架构，不给可执行 task 来源
- 只给 task 列表，不说明结构边界和依赖关系

如果讨论开始滑向实现细节，要回到“边界、职责、拆解、依赖”这四类核心问题。

## 输入

至少包含：

- `Boundary Convergence` 阶段产出的 `10-requirements/business_rules_memo.md`
- `Tech Selection` 阶段产出的 `15-tech-selection/tech-selection.md`
- `superpowers` 原项目的运行骨架与 skill 组织方式

可选输入：

- 已知 demo
- 已知风险点
- 用户对 task 粒度、并行策略、结构风格的额外偏好

读取规则：

- 启动时先检查前两阶段文档是否存在
- 先读取它们的 frontmatter 和摘要，再按需读取关键章节
- 仅当两份文档的 `status` 都为 `approved` 时才允许进入本阶段
- 不要默认把所有上游正文全文放入上下文

启动本阶段时，必须先向 Owner 显式展示你读到的上游 frontmatter 关键字段，例如：

```text
准备进入阶段：架构拆解（Architecture and Tasking）

上游文档检查结果：
- 10-requirements/business_rules_memo.md
  - doc_id：business_rules_memo
  - status：approved
- 15-tech-selection/tech-selection.md
  - doc_id：tech_selection
  - status：approved

若以上任一关键字段不符合要求，则本阶段不得开始。
```

## 输出

输出文件：

- `20-architecture/architecture.md`
- `20-architecture/tasks.md`

这两份文档都必须包含统一 frontmatter：

```yaml
---
doc_id: "architecture" | "tasks"
phase: "architecture-and-tasking"
artifact: "architecture" | "tasks"
status: "draft|in_review|approved|superseded"
derived_from:
  - "business_rules_memo"
  - "tech_selection"
updated_at: "YYYY-MM-DD"
---
```

输出内容至少必须覆盖：

### 架构文档部分

1. 本轮架构目标
2. 本轮明确不采用的方向
3. 结构边界
4. 模块职责
5. 依赖方向
6. 与 `superpowers` 原骨架的衔接方式
7. 风险点与控制策略

### task 文档部分

1. task 列表
2. 每个 task 的目标
3. 每个 task 的输入依赖
4. 每个 task 的输出结果
5. 串行/并行关系
6. 风险 task 标记
7. 不允许进入实现期临时假设的说明

## 核心方法

本阶段直接吸收两类成熟方法，但不要求显式调用外部 skill：

- 架构边界设计方法
- task 拆解与依赖排序方法

重点是把有效方法内化进当前项目协议，而不是把 skill 调用链拉长。

### 方法 1：先定边界，再拆任务

不得先列 task 再补架构理由。

正确顺序是：

1. 先明确目标物的结构边界
2. 再明确模块职责和依赖方向
3. 再基于这些边界拆 task

如果边界未清就开始拆 task，后续实现极易依赖假设推进。

### 方法 2：依赖方向必须显式

架构文档必须说明：

- 哪些模块依赖哪些模块
- 哪些依赖关系被明确禁止
- 哪些边界不允许在实现期被穿透

如果依赖方向说不清，task 依赖关系也不可能拆准。

### 方法 3：task 拆解必须服务正式开发

这里的 task 不是脑图节点，也不是泛泛的工作包，而是要能直接作为正式开发阶段的执行单元。

每个 task 至少必须回答：

- 这一项到底要完成什么
- 它依赖什么前置结果
- 完成后会产出什么
- 它和其他 task 是并行还是串行关系

### 方法 4：风险前移

高风险问题不能留到实现时再暴露。

如果某个 task 具有以下特征，应在本阶段直接标记为风险 task：

- 影响多个关键边界
- 改动面较大
- 很容易引发依赖反向穿透
- 需要较强的 review 或预览后写入门禁

## 架构设计原则

### 原则 1：围绕当前目标物，而不是抽象平台

架构说明必须服务当前目标物，不得滑向新的平台架构、运行时架构或 orchestrator 设计。

### 原则 2：沿用并增强 `superpowers`

必须明确哪些执行骨架继续沿用 `superpowers`，哪些只做前置替换或增强。

### 原则 3：边界清晰胜过术语华丽

不要为了显得“架构完整”而堆砌模式名词。真正重要的是：

- 边界有没有说清
- 职责有没有重叠
- 依赖有没有矛盾

## Task 拆解原则

### 原则 1：task 粒度必须适中

过大的 task 会导致实现期跨度过大，review 无法有效隔离。

过碎的 task 会导致切分成本过高，依赖关系反而混乱。

### 原则 2：task 之间的依赖必须闭合

不得存在“这个 task 要等另一个 task 做完，但文档里没写出来”的隐式依赖。

### 原则 3：区分可并行与必须串行

不要把所有 task 都按线性顺序排列，也不要为了追求并行而忽略真实依赖。

### 原则 4：不能靠实现期猜测推进

如果某个 task 的成立依赖“到时候实现看看再说”，说明拆解不合格，必须回到本阶段继续澄清。

## 对 Owner 的可见性要求

在本阶段开始时，先用中文说明：

```text
当前进入阶段：架构拆解（Architecture and Tasking）

我已读取：<已读取的材料路径>
本阶段目标：先明确结构边界、模块职责和依赖方向，再产出正式开发可直接消费的 task 列表与依赖关系。
本阶段不会进入编码，也不会提前完成测试契约。

接下来我会先收敛架构边界，再收敛 task 拆解与依赖关系。
```

当本阶段聚焦点发生切换时，要让 Owner 看见当前聚焦内容，例如：

```text
本轮聚焦：正式开发 task 的依赖关系与并行边界
```

在阶段结束时，必须先汇报再进入下一阶段：

```text
架构拆解阶段完成。

已产出：
- <架构文档路径>
- <task 文档路径>

本阶段确认的结构边界：<摘要>
本阶段确认的模块职责：<摘要>
本阶段确认的 task 列表与依赖关系：<摘要>
风险 task：<列表；若没有则明确写“无”>
仍未决的问题：<列表；若没有则明确写“无”>

若仍存在会影响 task 拆解可执行性的关键缺口，则不得进入 Contract Solidification。
```

## 架构文档建议结构

建议使用以下结构：

```markdown
# 架构设计文档

## 1. 本轮架构目标

## 2. 本轮明确不采用的方向

## 3. 结构边界

## 4. 模块职责

## 5. 依赖方向

## 6. 与 superpowers 原骨架的衔接方式

## 7. 风险点与控制策略
```

## Task 文档建议结构

建议使用以下结构：

```markdown
# 任务拆解文档

## 1. task 列表

## 2. 每个 task 的目标

## 3. 每个 task 的输入依赖

## 4. 每个 task 的输出结果

## 5. 串行/并行关系

## 6. 风险 task 标记

## 7. 不允许进入实现期临时假设的说明
```

## 放行条件

只有同时满足以下条件，才允许进入 `Contract Solidification`：

1. 结构边界已经清晰，而不是停留在抽象描述。
2. 模块职责已经清晰，不存在明显重叠或空洞。
3. task 列表已经形成，且每个 task 都有明确目标。
4. task 依赖关系已经明确，不存在隐式依赖或依赖矛盾。
5. 已区分可并行与必须串行的 task。
6. 风险 task 已被标记，不再留到实现期临时暴露。
7. 不需要依赖“实现时再看”才能让 task 成立。
8. `20-architecture/architecture.md` 与 `20-architecture/tasks.md` 的 frontmatter 中 `status` 都已更新为 `approved`。

如果以上任一条件不满足，本阶段应判定为未通过，继续调整架构边界或 task 拆解。

## 状态断言

本阶段启动前，必须先断言：

- `10-requirements/business_rules_memo.md` 存在且 `status: approved`
- `15-tech-selection/tech-selection.md` 存在且 `status: approved`

若以上任一条件不满足，则不得进入本阶段。

## 失败信号

出现以下情况时，说明本阶段没有真正完成：

- 只有宏观架构，没有可执行 task 来源
- 只有 task 列表，没有结构边界和依赖解释
- task 过大或过碎
- task 之间依赖矛盾
- 文档里大量出现“实现时再定”“开发时补充判断”
- 无法明确哪些 task 可以并行、哪些必须串行

## 与前后阶段的边界

- `Tech Selection` 负责回答“采用什么技术路线与复用策略”。
- 本阶段负责回答“在这些技术约束下，结构怎么组织，任务怎么拆”。
- `Contract Solidification` 负责回答“后续实现与 review 必须验证什么”。

不要把前后两个阶段的职责混进来。
