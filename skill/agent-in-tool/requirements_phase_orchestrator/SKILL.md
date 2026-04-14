---
name: requirements-phase-orchestrator
description: Use when starting requirements analysis phase to orchestrate multi-agent workflow with isolated sub-agents. Each sub-agent calls specific skills (reverse-interviewing, architecture-patterns, tdd) while orchestrator defines input/output specifications and validates artifacts.
---

# Requirements Phase Orchestrator (主控 Agent)

需求分析阶段主控 Agent，负责编排子 Agent 调用具体 skills，定义输入输出规范，并验收产物。

## 🎯 核心职责

### 主控 Agent 职责
1. **定义规范**：定义每个阶段的输入输出规范
2. **启动子 Agent**：使用 Task 工具创建专门的子 Agent
3. **验收结果**：检查产物是否符合规范
4. **数据流转**：将前一阶段的输出传递给后一阶段
5. **错误处理**：如果不符合规范，要求重新执行
6. **最终汇报**：汇总所有产物，向用户汇报

### 子 Agent 职责
1. **调用 skill**：使用 Skill 工具调用指定的 skill
2. **监控执行**：观察 skill 的执行过程
3. **结果传递**：将 skill 的输出返回给主控
4. **不做判断**：不自己判断产物质量，只负责传递

### Skill 职责
1. **具体任务**：执行具体的需求分析任务
2. **生成产物**：生成符合规范的输出产物
3. **用户交互**：与用户进行必要的交互

## 📋 阶段流程

### 阶段 1：边界收敛 (req-boundary)

#### 输入输出规范
- **输入**：raw_requirement (string) - 用户的原始需求描述
- **输出**：business_rules_memo (markdown) - 《业务规则备忘录》

#### 调用 skill
- **skill 名称**：reverse-interviewing
- **skill 作用**：通过提问消除需求模糊地带

#### 验收标准
产物必须包含：
- ✅ 核心概念定义
- ✅ 目标用户描述
- ✅ 核心价值说明
- ✅ 边界条件说明
- ✅ 非功能需求（性能、安全、可用性）
- ✅ 异常处理说明

#### 执行方式

**第一步：向用户说明即将开始的阶段**

```
📋 阶段 1/3：边界收敛

目标：将你的原始需求转化为清晰的业务规则

即将启动专门的子 Agent 来调用 reverse-interviewing skill。
该 skill 会通过提问的方式消除需求中的模糊地带。
```

**第二步：启动子 Agent**

使用 Task 工具创建子 Agent：

```
subagent_type: "general-purpose"
prompt: """
你是 skill 调用专家，负责调用 reverse-interviewing skill。

**你的任务**：
1. 向用户说明：即将开始边界收敛分析
2. 调用 reverse-interviewing skill
3. 确保 skill 生成《业务规则备忘录》
4. 将备忘录的完整内容返回给我

**用户需求**：{raw_requirement}

**注意事项**：
- 你自己不要做需求分析，让 skill 去做
- 你自己不要生成产物，让 skill 去生成
- 你只负责调用 skill 和传递结果

请开始执行。
"""
```

**第三步：等待子 Agent 完成**

等待子 Agent 返回结果，期间用户会看到：
- 子 Agent 与 reverse-interviewing skill 的交互
- skill 向用户提问的过程
- 用户回答问题的过程
- skill 生成产物的过程

**第四步：验收产物**

检查子 Agent 返回的《业务规则备忘录》是否符合验收标准：
- 如果符合 → 标记阶段完成，进入下一阶段
- 如果不符合 → 要求子 Agent 重新调用 skill

### 阶段 2：架构拆解 (req-architecture)

#### 输入输出规范
- **输入**：business_rules_memo (markdown) - 《业务规则备忘录》
- **输出**：architecture_design (markdown) - 架构设计文档

#### 调用 skill
- **skill 名称**：architecture-patterns
- **skill 作用**：选择合适的架构模式并进行设计

#### 验收标准
产物必须包含：
- ✅ 架构模式选择及理由
- ✅ 分层设计说明
- ✅ 领域模型定义
- ✅ 任务拆解列表
- ✅ 技术栈选择

#### 执行方式

**第一步：向用户说明即将开始的阶段**

```
📋 阶段 2/3：架构拆解

目标：基于业务规则进行架构设计和任务拆解

《业务规则备忘录》已生成，即将启动专门的子 Agent 来调用 architecture-patterns skill。
```

**第二步：启动子 Agent**

使用 Task 工具创建子 Agent：

```
subagent_type: "general-purpose"
prompt: """
你是 skill 调用专家，负责调用 architecture-patterns skill。

**你的任务**：
1. 向用户说明：即将开始架构设计
2. 调用 architecture-patterns skill
3. 确保 skill 生成架构设计文档
4. 将设计文档的完整内容返回给我

**业务规则备忘录**：
{business_rules_memo}

**注意事项**：
- 你自己不要设计架构，让 skill 去做
- 你自己不要生成文档，让 skill 去生成
- 你只负责调用 skill 和传递结果

请开始执行。
"""
```

**第三步：验收产物**

检查返回的架构设计文档是否符合验收标准。

### 阶段 3：契约固化 (req-contract)

#### 输入输出规范
- **输入**：architecture_design (markdown) - 架构设计文档
- **输出**：test_contract (markdown) - 测试契约文档

#### 调用 skill
- **skill 名称**：tdd
- **skill 作用**：生成测试契约和 Gherkin 用例

#### 验收标准
产物必须包含：
- ✅ Gherkin Feature 文件
- ✅ 关键场景覆盖
- ✅ 主流程、边界流、失败流
- ✅ 可直接用于开发

#### 执行方式

**第一步：向用户说明即将开始的阶段**

```
📋 阶段 3/3：契约固化

目标：基于架构设计生成测试契约

架构设计已完成，即将启动专门的子 Agent 来调用 tdd skill。
```

**第二步：启动子 Agent**

使用 Task 工具创建子 Agent：

```
subagent_type: "general-purpose"
prompt: """
你是 skill 调用专家，负责调用 tdd skill。

**你的任务**：
1. 向用户说明：即将开始测试契约生成
2. 调用 tdd skill
3. 确保 skill 生成测试契约文档
4. 将契约文档的完整内容返回给我

**架构设计文档**：
{architecture_design}

**注意事项**：
- 你自己不要生成测试用例，让 skill 去做
- 你自己不要编写契约，让 skill 去编写
- 你只负责调用 skill 和传递结果

请开始执行。
"""
```

**第三步：验收产物**

检查返回的测试契约文档是否符合验收标准。

## 🎉 完成汇报

### 所有阶段完成后

向用户汇报：

```
🎉 需求分析阶段全部完成！

**执行摘要**：
- ✅ 阶段 1/3：边界收敛 → 《业务规则备忘录》
- ✅ 阶段 2/3：架构拆解 → 《架构设计文档》
- ✅ 阶段 3/3：契约固化 → 《测试契约文档》

**生成的文件**：
1. 10-requirements/{task_id}-business_rules_memo.md
2. 20-planning/{task_id}-architecture_design.md
3. 20-planning/{task_id}-test_contract.md

**下一步**：
需求分析已完成，可以进入开发阶段。

开发阶段包括：
1. 需求锻造（生成可执行契约）
2. TDD 门禁（测试驱动开发）
3. 独立盲审（代码审查）
4. 发布裁决（Owner 决策）

是否继续进入开发阶段？
```

## 🔍 透明度原则

此技能遵循**完全透明**原则：

- ✅ 显示每个阶段的开始和结束
- ✅ 显示子 Agent 的启动过程
- ✅ 显示 skill 的调用过程
- ✅ 显示产物的验收过程
- ✅ 显示所有生成的文件
- ✅ 提供追溯和调试的路径

## ⚠️ 错误处理

### 如果子 Agent 执行失败

1. 向用户说明失败原因
2. 显示错误信息
3. 提供重试选项

### 如果产物不符合验收标准

1. 向用户说明不符合的验收标准
2. 要求子 Agent 重新调用 skill
3. 直到符合标准或用户确认跳过

## 📚 相关技能

此主控 Agent 会编排以下 skills：
- `reverse-interviewing` - 边界收敛
- `architecture-patterns` - 架构设计
- `tdd` - 测试契约

这些技能都有明确的输入输出规范，子 Agent 只负责调用它们。
