# Agent-in-Tool 架构蓝图

## 核心思想

> "真正的敏捷不是把大象塞进冰箱，而是关注点分离（Separation of Concerns）。"

- **Builder** 只负责写代码和触发工具
- **审查的脑力活** 交给 Tool 内部独立唤醒的 API Agent
- **复杂的 I/O 和隔离机制** 由 Python 脚本在后台默默承受

## 架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Builder Agent (Claude)                       │
│                         - 编写代码                                  │
│                         - 调用工具                                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ trigger_blind_review()
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Standalone Skills (Python)                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  1. collect_evidence() - Git diff, Test logs              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                    │                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  2. spawn_independent_agent() - 独立LLM调用 ⭐            │   │
│  │     - 新的API会话                                         │   │
│  │     - 对抗性System Prompt                                │   │
│  │     - 物理隔离                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                    │                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  3. save_review_report() - 写入40-review/                  │   │
│  │     - 使用文件锁防竞态                                     │   │
│  │     - 生成JSON + Markdown                                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                    │                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  4. format_minimal_response() - 信息降维                   │   │
│  │     - 只返回一句话给Builder                                │   │
│  │     - 防止上下文污染                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ "❌ 审查未通过"
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Builder Agent (Claude)                       │
│                     - 读取 40-review/ 报告                         │
│                     - 修复代码                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 三大隔离机制

### 1. 上下文隔离
- Builder 的上下文完全不会传递给 Reviewer
- 每次审查都是全新的 LLM 会话
- Reviewer 不知道 Builder 的"思考过程"

### 2. 权限隔离
- Builder 只能调用工具，无法直接访问报告文件
- 报告文件由独立 Python Runtime 直接写入文件系统
- 使用文件锁防止并发冲突

### 3. 信息降维
- 报告文件包含完整的审查详情
- Builder 只能看到极简的返回消息
- 防止 Builder 被大量信息"污染"

## 与传统方案对比

| 方面 | 伪 Skill / 双开 | Agent-in-Tool |
|------|----------------|---------------|
| 隔离程度 | 逻辑隔离 | 物理隔离 |
| 审查质量 | 死板规则 | 真正 AI 理解 |
| 用户体验 | 切换窗口 | 单终端心流 |
| 上下文控制 | 容易泄露 | 完全隔离 |
| 可扩展性 | 受限于 Python 脚本 | 无限 (LLM 能力) |

## 关键技术点

### Agent-in-Tool 实现
```python
# 在独立 Skill 内部调用独立的 LLM
client = anthropic.AsyncAnthropic()
response = await client.messages.create(
    model="claude-3-7-sonnet-20250219",
    system=REVIEWER_SYSTEM_PROMPT,  # 对抗性 Prompt
    messages=[{"role": "user", "content": diff_and_logs}]
)
```

### 文件锁防竞态
```python
from filelock import FileLock

with FileLock("40-review/task.lock", timeout=5):
    with open("40-review/task.json", 'w') as f:
        json.dump(report, f)
```

### 信息降维返回
```python
# 报告文件：完整的审查详情 (Builder 看不到)
# 返回消息：极简的一句话 (Builder 只能看到这个)
return "❌ 审查未通过！发现 SQL 注入。请查阅 40-review/report.md"
```

## 使用流程

### Builder 工作流
```
1. read_task_contract("TASK-001")
   ↓
2. [编写代码...]
   ↓
3. trigger_blind_review("TASK-001")
   ↓
   [后台: 独立 LLM 盲审]
   ↓
4. 读取 40-review/TASK-001.md
   ↓
5. [修复代码...]
   ↓
6. trigger_blind_review("TASK-001")
   ↓
   [后台: 再次盲审]
   ↓
7. submit_to_owner("TASK-001")
   ↓
   [人类确认框]
   ↓
8. ✅ 发布完成
```

## 扩展指南

### 添加新的审查规则

修改 `scripts/blind_reviewer.py` 中的 `REVIEWER_SYSTEM_PROMPT`：

```python
REVIEWER_SYSTEM_PROMPT = """
你是一个冷酷无情的顶级安全审查员。

## 新增审查规则
- 规则1: ...
- 规则2: ...

...
"""
```

### 自定义审查模型

```python
reviewer = BlindReviewer(
    model="claude-3-opus-20240229"  # 使用更强模型
)
```

### CI/CD 集成

```python
# 非交互模式
result = await submit_to_owner(
    task_id="TASK-001",
    non_interactive=True,
    approval="auto"  # 自动通过审查
)
```

## 性能优化

1. **并发控制**: 使用文件锁防止多个任务同时审查
2. **缓存机制**: 缓存 Git diff 避免重复计算
3. **超时处理**: API 调用设置超时防止无限等待
4. **降级策略**: API 失败时使用规则引擎兜底

## 安全考虑

1. **API 密钥管理**: 使用环境变量，不硬编码
2. **路径验证**: 防止路径遍历攻击
3. **权限控制**: 限制 release 目录写入权限
4. **审计日志**: 记录所有审查操作

## 未来扩展

- [ ] 支持多模型审查 (GPT-4, Claude, Gemini)
- [ ] 审查历史追踪和趋势分析
- [ ] 自动修复建议生成
- [ ] 集成静态分析工具
- [ ] 支持分布式审查集群
