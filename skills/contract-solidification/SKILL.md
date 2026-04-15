---
name: contract-solidification
description: 用于四阶段准备链的第 4 阶段，在架构与任务拆解完成后固化开发前契约，明确后续实现、review 与透明度门禁必须验证什么，并决定是否允许进入 using-git-worktrees
---

# Contract Solidification

## 技能定位

这是当前项目四阶段准备链的第 4 阶段 skill，也是正式开发开始前的最后一道准备阶段。

它的目标不是提前开始编码，也不是把后续每个 task 的测试直接写出来，而是先把“什么算完成、什么必须覆盖、什么情况下不得放行”固化成统一契约，让后续 implementer、reviewer 和 Owner 都基于同一套外部标准推进。

## 本阶段的唯一目标

形成一份可交接的《测试契约文档》，并明确：

- 四阶段准备链是否已经满足进入正式开发的条件
- 后续正式开发必须覆盖哪些主流程、边界流、失败流
- 透明度门禁和 reviewer 隔离要如何验证
- 哪些情况必须阻止进入 `using-git-worktrees`
- 是否已经具备进入正式开发的条件

## 不做什么

本阶段禁止混入以下内容：

- 直接开始进入 worktree
- 直接开始实现 task
- 把每个 task 的具体测试代码提前写出来
- 把 TDD 的 RED-GREEN-REFACTOR 循环提前执行
- 用“后续实现时再补”替代契约空缺

如果讨论开始滑向具体测试代码、具体实现步骤，要把话题拉回“必须验证什么”。

## 输入

至少包含：

- `Boundary Convergence` 阶段产出的 `10-requirements/business_rules_memo.md`
- `Tech Selection` 阶段产出的 `15-tech-selection/tech-selection.md`
- `Architecture` 阶段产出的 `20-architecture/architecture.md`
- `Architecture` 阶段产出的 `20-architecture/tasks.md`

可选输入：

- 已知高风险 task
- 已知 review 要点
- 用户对验收标准的额外要求

读取规则：

- 启动时先检查前三阶段产物是否存在
- 先读取 frontmatter 和摘要，再按需读取正文关键章节
- 仅当四份上游文档的 `status` 都为 `approved` 时才允许进入本阶段
- 不要默认把所有上游正文全文放入上下文

## 输出

输出文件：

- `25-contract/test_contract.md`

该文档必须包含统一 frontmatter：

```yaml
---
doc_id: "test_contract"
phase: "contract-solidification"
artifact: "test_contract"
status: "draft|in_review|approved|superseded"
derived_from:
  - "business_rules_memo"
  - "tech_selection"
  - "architecture"
  - "tasks"
updated_at: "YYYY-MM-DD"
---
```

输出内容至少必须覆盖：

1. 四阶段准备链放行契约
2. `using-git-worktrees` 前置放行契约
3. 正式开发主流程契约
4. 边界流契约
5. 失败流契约
6. 透明度检查点契约
7. reviewer 隔离契约
8. 高风险改动预览后写入契约
9. 超出本轮范围的阻断契约

## 核心方法

### 方法 1：先提炼“必须验证什么”，再选择表达形式

本阶段的重点不是把文档写得像测试，而是先提炼：

- 后续必须验证哪些行为
- 哪些验证属于放行条件
- 哪些验证失败时必须阻断流程

在这些内容清楚后，再用可执行、可审查的契约形式写出。

### 方法 2：契约面向整个开发流，不只面向单个 task

本阶段必须覆盖两层：

#### 第一层：流程级契约

- 四阶段是否通过
- 是否允许进入 `using-git-worktrees`
- reviewer 是否独立
- 透明度门禁是否满足

#### 第二层：实现级契约

- 主流程必须覆盖什么
- 边界场景必须覆盖什么
- 失败场景必须覆盖什么
- 哪些 task 属于高风险改动

### 方法 3：契约必须能被后续实现和 review 消费

如果契约只停留在抽象表述，后续实现和 review 就仍然会各自理解。

因此契约必须做到：

- 说得清楚
- 能据此判断 pass / fail
- 能据此阻断不合格推进

### 方法 4：不要把 TDD 和契约混成一件事

本阶段可以借鉴 TDD 的“先定义要验证什么”的思想，但它不是后续的 task 内 TDD 执行。

区别是：

- 本阶段定义统一外部验收基线
- 后续 `test-driven-development` 负责在单个 task 内按这些基线执行 RED-GREEN-REFACTOR

## 契约设计原则

### 原则 1：先约束完成标准，再允许实现

如果完成标准没固化，就不允许进入正式开发。

### 原则 2：必须覆盖主流程、边界流、失败流

不能只写“正常情况下应该成功”，必须明确：

- 边界情况怎么判定
- 异常情况怎么阻断
- 哪些行为超出本轮范围

### 原则 3：把透明度和 reviewer 隔离写进契约

透明度和 reviewer 隔离不是“实现建议”，而是当前目标物的一部分，必须写成可验证契约。

### 原则 4：契约要阻止流程跑偏

如果某条契约失败后仍可继续推进，那它就不是有效契约。

## 与后续 TDD 的边界

本阶段与后续 `test-driven-development` 的边界必须明确：

### 本阶段负责

- 定义必须验证哪些行为与场景
- 定义正式开发前后的放行规则
- 定义 review 和透明度的约束基线

### 后续 TDD 负责

- 在单个 task 内写 failing test
- 观察 RED
- 写最小实现进入 GREEN
- 在 REFACTOR 中保持测试仍然通过

### 明确禁止

- 不要把本阶段写成“提前执行 TDD”
- 不要把后续 TDD 降级成“自己随便决定测什么”

## 对 Owner 的可见性要求

在本阶段开始时，先用中文说明：

```text
当前进入阶段：契约固化（Contract Solidification）

我已读取：<已读取的材料路径>
本阶段目标：把前面三个阶段的产物固化成统一测试契约，明确后续实现、review 和透明度门禁必须验证什么。
本阶段不会进入 worktree，也不会提前执行 TDD 编码。

接下来我会先收敛必须验证的行为和门禁，再把它们落成正式契约。
```

当本阶段聚焦点发生切换时，要让 Owner 看见当前聚焦内容，例如：

```text
本轮聚焦：reviewer 隔离与透明度门禁的契约表达
```

在阶段结束时，必须先汇报再进入正式开发：

```text
契约固化阶段完成。

已产出：<测试契约文档路径>
本阶段确认的放行条件：<摘要>
本阶段确认的主流程/边界流/失败流：<摘要>
本阶段确认的透明度与 reviewer 契约：<摘要>
仍未决的问题：<列表；若没有则明确写“无”>

若仍存在会影响正式开发放行的关键契约缺口，则不得进入 using-git-worktrees。
```

## 测试契约文档建议结构

建议使用以下结构：

```markdown
# 测试契约文档

## 1. 四阶段准备链放行契约

## 2. using-git-worktrees 前置放行契约

## 3. 正式开发主流程契约

## 4. 边界流契约

## 5. 失败流契约

## 6. 透明度检查点契约

## 7. reviewer 隔离契约

## 8. 高风险改动预览后写入契约

## 9. 超出本轮范围的阻断契约
```

在 Markdown 正文中，至少应嵌入可机器消费的结构化契约块。建议格式如下：

```yaml
contract_meta:
  doc_id: "test_contract"
  version: 1

scenarios:
  - scenario_id: "contract-gate-001"
    scenario_type: "phase_gate"
    phase_gate: "using-git-worktrees"
    title: "四阶段全部通过后才允许进入正式开发"
    required_evidence:
      - "business_rules_memo.status=approved"
      - "tech_selection.status=approved"
      - "architecture.status=approved"
      - "tasks.status=approved"
      - "test_contract.status=approved"
    pass_condition: "all_required_documents_approved"
    fail_block: true

  - scenario_id: "contract-review-001"
    scenario_type: "review_isolation"
    title: "implementer 不得审核自己的实现"
    required_evidence:
      - "spec_reviewer_is_fresh_subagent"
      - "code_quality_reviewer_is_fresh_subagent"
    pass_condition: "independent_review_confirmed"
    fail_block: true
```

## 放行条件

只有同时满足以下条件，才允许进入 `using-git-worktrees`：

1. 四阶段准备链的放行条件已经被固化为正式契约。
2. 主流程、边界流、失败流已经被覆盖。
3. 透明度检查点已经写成可验证契约。
4. reviewer 隔离已经写成可验证契约。
5. 高风险改动的预览后写入规则已经写清楚。
6. 不存在会影响正式开发放行的关键契约缺口。
7. 输出文档 frontmatter 中 `status` 已更新为 `approved`。

如果以上任一条件不满足，本阶段应判定为未通过，不得进入正式开发。

## 状态断言

本阶段启动前，必须先断言：

- `10-requirements/business_rules_memo.md` 存在且 `status: approved`
- `15-tech-selection/tech-selection.md` 存在且 `status: approved`
- `20-architecture/architecture.md` 存在且 `status: approved`
- `20-architecture/tasks.md` 存在且 `status: approved`

若以上任一条件不满足，则不得进入本阶段。

## 失败信号

出现以下情况时，说明本阶段没有真正完成：

- 契约只描述“应该做好”，没有 pass / fail 判断基础
- 只有主流程，没有边界流或失败流
- 没有把透明度门禁写成契约
- 没有把 reviewer 隔离写成契约
- 把具体测试代码或实现步骤提前写进来
- 仍然需要后续实现者自己决定“究竟该验证什么”

## 与前后阶段的边界

- `Architecture` 负责回答“结构怎么组织、任务怎么拆”。
- 本阶段负责回答“后续实现与 review 必须验证什么”。
- `using-git-worktrees` 负责在四阶段全部通过后正式进入开发环境。
- 后续 `test-driven-development` 负责在单个 task 内落实这些契约。

不要把这些职责混在一起。
