# Superpowers 深度定制版 - 测试契约文档

## 文档定位

本文档只定义**当前目标流程**的验收契约，不验证未来平台化实现，不假设独立 runtime orchestrator 已存在。

## 上游输入

- `10-requirements/business_rules_memo.md`
- `15-tech-selection/tech-selection.md`
- `20-architecture/architecture.md`
- `20-architecture/tasks.md`

进入本阶段时，上述上游文档都应已达到 `status: approved`。

## 契约范围

本轮契约覆盖以下对象：

1. 四阶段准备链
2. 固定产物命名与 frontmatter 状态门禁
3. `using-git-worktrees` 前的放行条件
4. 正式开发阶段的透明度检查点
5. reviewer 隔离与显式调用
6. Architecture 阶段 task 分解质量

## Feature 1：四阶段准备链

```gherkin
Feature: 四阶段准备链替代前半主链
  作为 Owner
  我希望需求在进入正式开发前经过四阶段准备
  以便后续执行有稳定、可验证的输入

  Scenario: 完整完成四阶段准备链
    Given 用户提出一个新的开发需求
    When 系统依次执行以下阶段：
      | 阶段 |
      | Boundary Convergence |
      | Tech Selection |
      | Architecture |
      | Contract Solidification |
    Then 系统应生成以下产物：
      | 目录 | 产物类型 |
      | 10-requirements | 业务规则备忘录 |
      | 15-tech-selection | 技术选型文档 |
      | 20-architecture | 架构与任务拆解文档 |
      | 25-contract | 测试契约文档 |
    And 在四阶段全部完成前，不得进入 using-git-worktrees

  Scenario: 任一前置阶段不合格时不得放行下一阶段
    Given 当前阶段产物缺少必需章节或验收项
    When 系统检查该阶段放行条件
    Then 该阶段状态应为未通过
    And 系统应明确指出缺失项
    And 不得进入下一阶段
```

## Feature 2：固定产物命名与 frontmatter 状态门禁

```gherkin
Feature: 四阶段产物必须使用固定文件名与 frontmatter 状态门禁
  作为流程消费者
  我希望阶段输入输出路径稳定且可断言
  以便避免文档命名漂移和阶段误放行

  Scenario: 四阶段产物使用固定文件名
    Given 系统正在执行四阶段准备链
    When 每个阶段产出文档
    Then 文件名应固定为：
      | 路径 |
      | 10-requirements/business_rules_memo.md |
      | 15-tech-selection/tech-selection.md |
      | 20-architecture/architecture.md |
      | 20-architecture/tasks.md |
      | 25-contract/test_contract.md |

  Scenario: 下一阶段开始前必须检查上游 frontmatter 状态
    Given 下一阶段准备启动
    When 系统检查上游文档
    Then 必须读取并展示至少以下关键字段：
      | 字段 |
      | doc_id |
      | phase |
      | status |
    And 只有当上游文档状态为 approved 时才允许继续
```

## Feature 3：Architecture 阶段的 task 分解质量

```gherkin
Feature: Architecture 阶段必须输出可执行 task 分解
  作为开发阶段的消费者
  我希望 Architecture 阶段已经处理好依赖和粒度问题
  以便正式开发不依赖临时假设推进

  Scenario: Architecture 产物包含可执行 task 分解
    Given Tech Selection 阶段已完成
    When 系统完成 Architecture 阶段
    Then 产物必须包含：
      | 内容 |
      | 架构边界 |
      | 模块职责 |
      | task 列表 |
      | task 依赖关系 |
      | 并行/串行约束 |
      | 风险 task 标记 |

  Scenario: task 粒度不合理时不得放行
    Given 某些 task 过大、过碎或依赖矛盾
    When 系统检查 Architecture 阶段放行条件
    Then Architecture 阶段不得通过
    And 系统应指出粒度或依赖问题
```

## Feature 4：正式开发阶段从 using-git-worktrees 开始

```gherkin
Feature: using-git-worktrees 是正式开发入口
  作为开发者
  我希望四阶段结束后先进入 worktree 再实施
  以便正式开发与主线隔离

  Scenario: 四阶段完成后进入 using-git-worktrees
    Given 四阶段准备链已全部通过
    When 系统进入正式开发阶段
    Then 第一步应是 using-git-worktrees

  Scenario: 未完成四阶段时不得进入 worktree
    Given 至少一个前置阶段未通过
    When 系统尝试进入正式开发阶段
    Then 系统必须阻止进入 using-git-worktrees
```

## Feature 5：task 开始前的透明度检查点

```gherkin
Feature: 每个 task 开始前必须与 Owner 对齐
  作为 Owner
  我希望 agent 在实施前先说明依据和目标
  以便避免闷头跑偏

  Scenario: task 开始前必须声明前置文档和目标
    Given 某个开发 task 即将开始
    When implementer 尚未开始实际实施
    Then 系统必须向 Owner 明确说明：
      | 说明项 |
      | 读取了哪些前置文档 |
      | 本轮要完成什么 |
      | 预计改哪些文件或文件类型 |
      | 将调用哪个 implementer subagent |
    And 在 Owner 同意前，不得开始实际修改

  Scenario: 缺少开始前说明时 task 无效
    Given implementer 已开始实施
    And Owner 未看到开始前说明
    When 系统检查 task 合规性
    Then 该 task 应被视为流程不合格
```

## Feature 6：reviewer 调用必须显式可见

```gherkin
Feature: reviewer 调用必须对 Owner 可见
  作为 Owner
  我希望能确认 reviewer 真的被调用了
  以便避免 implementer 蒙混过关

  Scenario: task 完成后立即触发 reviewer
    Given implementer 已完成当前 task
    When 系统准备进入 review
    Then 系统必须明确通知 Owner：
      | 通知项 |
      | 即将调用 spec reviewer |
      | 即将调用 code quality reviewer |
      | 每个 reviewer 的目标 |

  Scenario: reviewer 必须是独立 fresh subagent
    Given 当前 task 已进入 review 阶段
    When 系统调用 reviewer
    Then reviewer 不能是 implementer 本人
    And reviewer 必须使用专门 reviewer prompt

  Scenario: reviewer 调用不可见时 review 无效
    Given Owner 未看到 reviewer 调用说明
    When 当前 task 被标记为已完成
    Then 该 task 的 review 结果应视为无效
```

## Feature 7：task 完成后的汇报与高风险写入门禁

```gherkin
Feature: task 完成后必须汇报，高风险改动必须预览后写入
  作为 Owner
  我希望在 task 结束和高风险改动前看到足够信息
  以便保持过程可控

  Scenario: task 完成后必须先汇报再进入下一 task
    Given 当前 task 已完成实施与 review
    When 系统准备进入下一 task
    Then 必须先向 Owner 展示改动摘要和结果

  Scenario: 高风险 task 必须预览后写入
    Given 某个 task 被判定为高风险或大范围改动
    When implementer 准备写入关键文件
    Then 系统必须先展示改动预览
    And 在 Owner 确认前不得正式写入
```

## Feature 8：正式开发阶段仍沿用原后半执行骨架

```gherkin
Feature: 正式开发透明度协议是统一公共规则
  作为 Owner
  我希望正式开发阶段使用统一的透明度模板
  以便不同 skill 不会各说各话

  Scenario: 正式开发链统一遵循 transparency protocol
    Given 系统已进入正式开发阶段
    When implementer 或 reviewer 相关说明被触发
    Then 应遵循 development-transparency-protocol 中定义的统一模板
    And 不应由各个执行 skill 各自定义一套相互冲突的话术
```

## 结构化契约块

除人类可读的 Markdown 契约外，文档中还应嵌入可机器消费的结构化契约块，至少包含：

```yaml
contract_meta:
  doc_id: "test_contract"
  version: 1

scenarios:
  - scenario_id: "contract-gate-001"
    scenario_type: "phase_gate"
    phase_gate: "using-git-worktrees"
    required_evidence:
      - "business_rules_memo.status=approved"
      - "tech_selection.status=approved"
      - "architecture.status=approved"
      - "tasks.status=approved"
      - "test_contract.status=approved"
    pass_condition: "all_required_documents_approved"
    fail_block: true
```

这样做的目的不是引入新的执行平台，而是让后续自动化校验具备稳定锚点。

## Feature 9：后半执行骨架保持与原项目一致

```gherkin
Feature: 后半执行骨架保持与原项目一致
  作为架构设计者
  我希望只增强透明度和 reviewer 隔离
  以便避免目标物跑偏成另一套系统

  Scenario: 正式开发阶段沿用原后半骨架
    Given 系统已进入 using-git-worktrees
    When 开始正式开发
    Then 应按逐 task 实施、逐 task review、分支收尾的思路推进
    And 不要求本轮存在独立 runtime orchestrator

  Scenario: 若文档要求独立平台能力则视为超出本轮范围
    Given 某项设计依赖新的 Python orchestrator 或独立运行时
    When 检查本轮契约范围
    Then 该设计应被判定为超出本轮范围
```

---

**生成时间**：2026-04-15
**状态**：revised-draft
**版本**：v2
