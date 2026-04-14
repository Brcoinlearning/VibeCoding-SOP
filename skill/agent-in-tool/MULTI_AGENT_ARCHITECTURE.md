# 多 Agent 架构改进方案

## 🎯 问题

**单 Agent 执行全流程的问题**：
- 上下文窗口压力过大
- 前面阶段的信息可能被遗忘
- 容易产生幻觉
- 难以追溯问题

## ✅ 解决方案

**多 Agent 架构**：
- 主控 Agent 负责流程编排和状态管理
- 子 Agent 负责执行具体任务
- 结果返回给主控，实现上下文隔离

## 🏗️ 架构对比

### 传统单 Agent 架构

```
requirements-phase-orchestrator (同一个 Agent)
├── 执行 reverse-interviewing (上下文累积)
├── 执行 interview-conducting (上下文累积)
├── 执行 elicitation-methodology (上下文累积)
├── 执行 architecture-patterns (上下文累积)
├── 执行 decomposition-planning-roadmap (上下文累积)
└── 执行 tdd (上下文累积)
```

### 新的多 Agent 架构

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

## 📁 实现文件

### 核心调度器
- `scripts/requirements_subagent_dispatcher.py` - 多 Agent 调度器实现

### CLI 集成
- `cli.py` - 添加 `req-dispatch` 命令

### Skill 描述
- `~/.claude/skills/requirements-phase-orchestrator/SKILL.md` - 更新为多 Agent 架构

## 🚀 使用方式

### 方式一：多 Agent 自动调度（推荐）

```bash
# 一键执行完整需求分析阶段
python3 cli.py req-dispatch TASK-001 "用户评论功能" --workspace .
```

### 方式二：手动分步执行

```bash
# 初始化状态
python3 cli.py req-init TASK-001 --workspace .

# 标记各阶段完成
python3 cli.py req-mark TASK-001 req-boundary pass --workspace .
python3 cli.py req-mark TASK-001 req-architecture pass --workspace .
python3 cli.py req-mark TASK-001 req-contract pass --workspace .

# 生成交接文件
python3 cli.py req-handoff TASK-001 --workspace .
```

## 🔍 技术实现

### 独立 LLM 会话

每个子 Agent 使用独立的 Anthropic API 调用：

```python
import anthropic

client = anthropic.AsyncAnthropic(api_key=api_key)
response = await client.messages.create(
    model="claude-3-7-sonnet-20250219",
    system=system_prompt,  # 针对该阶段的 System Prompt
    messages=[{"role": "user", "content": user_prompt}],
    max_tokens=4096
)
```

### 文件锁机制

防止并发写入冲突：

```python
from filelock import FileLock

with FileLock(str(output_file) + ".lock"):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
```

### 信息降维

只返回极简结果给主控 Agent：

```python
return {
    "success": True,
    "stage_id": "req-boundary",
    "artifact_file": str(output_file),
    "summary": "边界收敛完成，业务规则备忘录已生成"
}
```

## 🎯 与盲审的一致性

这个多 Agent 架构与 `trigger-blind-review` 的设计理念一致：

| 组件 | 盲审 | 需求分析 |
|------|------|----------|
| 主控 | Builder Agent | Orchestrator Agent |
| 子 Agent | Reviewer Agent | Boundary/Architecture/Contract Agents |
| 隔离 | 物理隔离 | 上下文隔离 |
| 结果 | 极简返回 | 极简返回 |

## 📊 优势对比

| 方面 | 单 Agent | 多 Agent |
|------|----------|----------|
| 上下文压力 | 高 | 低 |
| 幻觉风险 | 高 | 低 |
| 可追溯性 | 差 | 好 |
| 并发能力 | 无 | 有 |
| 错误隔离 | 无 | 有 |
| 实现复杂度 | 低 | 中 |

## 🔮 未来扩展

这个多 Agent 架构可以扩展到：

1. **开发阶段**：将 `forge-contract`、`tdd-enforce` 等也改为多 Agent
2. **并行执行**：某些独立的子 Agent 可以并行执行
3. **动态路由**：根据任务复杂度动态选择使用单 Agent 还是多 Agent
4. **Agent 池**：维护一个 Agent 池，可以复用和调度

## 📝 总结

多 Agent 架构通过**上下文隔离**、**状态管理集中**、**信息降维**等机制，有效解决了单 Agent 执行长流程时的问题，提高了系统的可靠性和可维护性。

与现有的 `blind_reviewer.py` 设计理念一致，形成了统一的多 Agent 架构风格。
