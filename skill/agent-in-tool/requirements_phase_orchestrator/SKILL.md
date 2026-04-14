---
name: requirements-phase-orchestrator
description: Use when starting requirements analysis phase to orchestrate multi-agent workflow with isolated sub-agents for boundary convergence, architecture decomposition, and contract solidification to avoid context accumulation and hallucinations.
---

# SOP Requirements Phase Orchestrator (多 Agent 版本)

需求分析阶段总控 Skill，使用**多 Agent 架构**避免上下文累积和幻觉。

## 🏗️ 多 Agent 架构

**传统单 Agent 问题**：
- 上下文窗口压力过大
- 前面阶段的信息可能被遗忘
- 容易产生幻觉
- 难以追溯问题

**多 Agent 解决方案**：
```
主控 Agent (Orchestrator)
    │
    ├──> 子 Agent 1 (边界收敛) ──> 独立 LLM 会话
    │         └─> 返回极简结果
    │
    ├──> 子 Agent 2 (架构拆解) ──> 独立 LLM 会话
    │         └─> 返回极简结果
    │
    └──> 子 Agent 3 (契约固化) ──> 独立 LLM 会话
              └─> 返回极简结果
```

**优势**：
- ✅ 上下文隔离 - 每个 Agent 只处理自己的任务
- ✅ 状态管理集中 - 主控 Agent 负责流程编排
- ✅ 降低幻觉风险 - 独立 LLM 会话避免上下文污染
- ✅ 可追溯性 - 每个阶段产物独立保存

## 触发条件

当以下情况时使用此技能：
- 用户提出新的 Feature 想法，需要开始需求分析
- 需要进行需求收敛、架构拆解、契约固化
- 需要生成需求到开发的交接产物

## 阶段流程

### 阶段 1：收敛边界 (req-boundary)
**子 Agent 任务**：
- 深度提问消除模糊地带
- 识别核心概念、目标用户、核心价值
- 分析输入/输出规格、处理逻辑
- 探索边界条件（数据、用户、系统、环境）
- 确认非功能需求（性能、安全、可用性）

**验收产物**：`10-requirements/{task_id}-business_rules_memo.md`

### 阶段 2：架构拆解 (req-architecture)
**子 Agent 任务**：
- 分析业务规则备忘录
- 选择架构模式（Clean Architecture, DDD 等）
- 进行领域建模和分层设计
- 拆解任务并创建执行计划

**验收产物**：`20-planning/{task_id}-architecture_design.md`

### 阶段 3：契约固化 (req-contract)
**子 Agent 任务**：
- 分析架构设计文档
- 识别关键验收场景
- 编写 Gherkin 测试用例
- 产出测试契约

**验收产物**：`20-planning/{task_id}-test_contract.md`

## 执行方式

**重要**：当此技能被触发时，你必须执行以下操作：

### 第一步：告知用户即将执行的操作
```
🔧 正在调用 requirements-phase-orchestrator 技能...
├─> 执行文件：scripts/requirements_subagent_dispatcher.py
├─> 执行命令：python3 cli.py req-dispatch TASK-001 "用户的需求描述"
└─> 预计时间：1-3 分钟（取决于需求复杂度）
```

### 第二步：执行多 Agent 调度命令
```bash
cd /Users/mr.hu/Desktop/开发项目/软件开发SOP/skill/agent-in-tool
python3 cli.py req-dispatch TASK-001 "用户的需求描述" --workspace .
```

### 第三步：实时反馈执行进度
在命令执行过程中，向用户报告进度：
```
✅ 阶段 1/3：边界收敛 (独立 LLM 会话) - 完成
✅ 阶段 2/3：架构拆解 (独立 LLM 会话) - 进行中...
```

### 第四步：汇报完整结果
向用户汇报：
- 执行的代码文件
- 生成的产物文件
- 各阶段的执行状态
- 需要用户确认或修改的地方

## 透明度原则

此技能遵循**完全透明**原则：
- ✅ 显示执行的具体代码文件
- ✅ 显示执行的完整命令
- ✅ 实时反馈执行进度
- ✅ 汇报所有生成的文件
- ✅ 说明每个阶段的作用
- ✅ 提供追溯和调试的路径

## CLI 命令

### 方式一：多 Agent 自动调度（推荐）

```bash
# 一键执行完整需求分析阶段（三个子 Agent 自动调度）
python3 cli.py req-dispatch TASK-001 "用户评论功能" --workspace .
```

**输出示例**：
```json
{
  "success": true,
  "task_id": "TASK-001",
  "stages_completed": ["req-boundary", "req-architecture", "req-contract"],
  "artifacts": [
    "10-requirements/TASK-001-business_rules_memo.md",
    "20-planning/TASK-001-architecture_design.md",
    "20-planning/TASK-001-test_contract.md"
  ]
}
```

### 方式二：手动分步执行

```bash
# 初始化需求分析状态
python3 cli.py req-init TASK-001 --workspace .

# 查看当前阶段状态
python3 cli.py req-status TASK-001 --workspace .

# 标记阶段完成（在验收产物合格后）
python3 cli.py req-mark TASK-001 req-boundary pass --workspace . --note="业务规则备忘录已生成"
python3 cli.py req-mark TASK-001 req-architecture pass --workspace . --note="架构设计已完成"
python3 cli.py req-mark TASK-001 req-contract pass --workspace . --note="测试契约已生成"

# 生成需求到开发的交接产物
python3 cli.py req-handoff TASK-001 --workspace .
```

### 方式三：使用外部技能（传统方式）

如果你想手动使用外部技能，可以按以下流程：

```bash
# 阶段1：手动调用外部技能
# （通过 Claude Code Skill 工具调用）
reverse-interviewing
interview-conducting
elicitation-methodology

# 阶段2：手动调用外部技能
architecture-patterns
decomposition-planning-roadmap

# 阶段3：手动调用外部技能
tdd
```

## 门禁规则

1. 任一阶段未通过验收前，不允许进入下一阶段
2. 产物不合格时，要求重新执行对应子 Agent
3. 只有所有阶段通过后，才能执行 `req-handoff` 生成交接文件

## 交接产物

`req-handoff` 生成的 `requirements_handoff.json` 包含：
- 业务规则备忘录
- 架构设计文档
- 测试契约文档
- Task 执行列表

此文件将被 `development_phase_orchestrator` 的 `dev-init` 命令作为承接条件。

## 技术实现

多 Agent 调度器使用以下技术实现上下文隔离：

1. **独立 LLM 会话**：每个子 Agent 使用独立的 Anthropic API 调用
2. **文件锁机制**：防止并发写入冲突
3. **信息降维**：只返回极简结果给主控 Agent
4. **产物持久化**：每个阶段的完整产物保存到文件系统

## 与盲审的一致性

这个多 Agent 架构与 `trigger-blind-review` 的设计理念一致：
- 盲审：Builder Agent → 独立 Reviewer Agent → 极简结果
- 需求分析：主控 Agent → 独立子 Agent → 极简结果

两者都实现了**物理隔离**和**上下文独立**，确保高质量的执行结果。
