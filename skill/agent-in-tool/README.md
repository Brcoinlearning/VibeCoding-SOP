# Agent-in-Tool 盲审架构

> "真正的敏捷不是把大象塞进冰箱，而是关注点分离（Separation of Concerns）。"
> — Builder只负责写代码；审查的脑力活交给Tool内部独立唤醒的API Agent；复杂的I/O和隔离机制由Python脚本在后台默默承受。

## 🎯 核心设计理念

### Agent-in-Tool 模式

**传统模式的问题：**
- ❌ Builder和Reviewer共享上下文 → 容易"串通"
- ❌ 审查逻辑写死在Python脚本 → 无法真正"理解"代码
- ❌ 需要人类来回切换窗口 → 打断心流

**Agent-in-Tool的解决方案：**
- ✅ **物理隔离**：Tool内部发起完全独立的LLM API调用
- ✅ **真正的AI审查**：审查由无状态的新LLM会话完成
- ✅ **单终端心流**：Builder只需调用工具，无需切换窗口

## 📁 架构设计

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Builder Agent   │ ───> │ Standalone Skills │ ───> │ Anthropic API   │
│  (CLI 调用方)    │      │  (Python Engine)  │      │ (独立Reviewer)  │
└─────────────────┘      └──────────────────┘      └─────────────────┘
         │                         │                          │
         │ 1. 请求审查             │ 2. 收集证据               │ 3. 盲审
         │                         │    + 独立API调用          │
         │                         │                          │
         │                         │ 4. 报告落盘               │ 5. 返回JSON
         │                         │    (40-review/)          │
         │                         │                          │
         │ 6. 极简返回              │                          │
         │ <─────────────────────  │                          │
         │                         │                          │
         v                         v                          v
    继续工作                   审查完成                   隔离完成
```

## 🛠️ 四大核心Skill（覆盖两个SOP全链路）

### Skill 1: `skill_forge_contract`
**用途**：需求锻造（Requirements 阶段）

**能力**：
- 接收原始需求，生成 `10-requirements/{task_id}.md`
- 生成 `20-planning/{task_id}.md`
- 落盘 `requirement_contract` frontmatter 产物

### Skill 2: `read_task_contract`
**用途**：Builder开始工作前调用，获取要干什么

**实现**：
- 读取 `20-planning/` 目录下的需求Markdown
- 返回结构化的需求信息

### Skill 3: `trigger_blind_review` ⭐
**用途**：Builder认为代码写完了，调用此工具请求验收

**核心逻辑**：
```python
1. 抓取证据 (Builder看不到这个过程)
   - git diff
   - 测试日志
   - 代码变更

2. 派生子智能体 (Agent-in-Tool)
   - 初始化独立的 Anthropic API Client
   - 构造对抗性 Reviewer System Prompt
   - 发送到全新的、无状态的LLM会话

3. 独立审查 (绝对隔离)
   - LLM完全不知道Builder的存在
   - 基于对抗性Prompt进行深度审查
   - 输出结构化JSON报告

4. 结果落盘 (使用文件锁防竞态)
   - 将完整报告写入 40-review/ 目录
   - 包含详细的漏洞分析和修复建议

5. 克制返回 (信息降维)
   - 只返回一句话给Builder
   - 防止Builder被海量上下文冲刷
```

### Skill 4: `submit_to_owner`
**用途**：当审查终于通过时，请求人类放行

**实现**：
- 弹出原生确认框 (Go/No-Go)
- 人类输入Go → 自动commit并路由到 50-release/
- 人类输入No-Go → 返回给Builder继续修复

## 🚀 快速开始（独立运行，不依赖 MCP）

### 安装依赖

```bash
pip install anthropic filelock
```

### 配置环境变量

```bash
export ANTHROPIC_API_KEY="your-api-key"
export WORKSPACE_PATH="/path/to/your/project"
```

### 使用流程（CLI）

```bash
# 1) 需求锻造
python3 cli.py forge-contract TASK-001 "实现用户登录并输出审计日志" --workspace .

# 2) 读取契约
python3 cli.py read-task TASK-001 --workspace .

# 3) TDD 门禁
python3 cli.py tdd-enforce TASK-001 --workspace . --test-command "pytest -q"

# 4) 触发盲审
python3 cli.py blind-review TASK-001 --workspace .

# 5) 人类放行（交互式）
python3 cli.py submit-owner TASK-001 --workspace .

# 或非交互（CI）
python3 cli.py submit-owner TASK-001 --workspace . --non-interactive --approval go
```

## 🔐 隔离机制详解

### 1. 上下文隔离
- Builder的上下文完全不会传递给Reviewer
- 每次审查都是全新的LLM会话
- Reviewer不知道Builder的"思考过程"

### 2. 权限隔离
- Builder只能调用工具，无法直接访问报告文件
- 报告文件由独立 Python Runtime 直接写入文件系统
- 使用文件锁防止并发冲突

### 3. 信息降维
- 报告文件包含完整的审查详情
- 但Builder只能看到极简的返回消息
- 防止Builder被大量信息"污染"

## 📊 与传统架构对比

| 方面 | 传统模式 | Agent-in-Tool模式 |
|------|---------|-------------------|
| 隔离程度 | 逻辑隔离 | 物理隔离 |
| 审查质量 | 死板规则 | 真正AI理解 |
| 用户体验 | 切换窗口 | 单终端心流 |
| 上下文控制 | 容易泄露 | 完全隔离 |
| 扩展性 | 受限于Python脚本 | 无限(LLM能力) |

## 🎨 架构优势

1. **真正的盲审**：Builder无法影响审查结果
2. **AI驱动**：审查由LLM完成，而非死板规则
3. **心流保持**：Builder无需切换窗口
4. **结果可靠**：物理隔离确保审查公正性
5. **易于扩展**：修改System Prompt即可调整审查策略

## 📝 开发指南

### 添加新的审查规则

修改 `trigger_blind_review` 中的 System Prompt：

```python
REVIEWER_SYSTEM_PROMPT = """
你是一个冷酷无情的顶级安全审查员。

审查重点：
1. SQL注入漏洞
2. XSS跨站脚本
3. 并发竞态条件
4. 空指针解引用
5. 业务逻辑错误

输出格式：结构化JSON
{
  "status": "PASS" | "REJECTED",
  "lethal_flaw": "致命缺陷描述",
  "severity": "critical" | "major" | "minor",
  "exploit_path": "复现路径",
  "remediation": "修复建议"
}
"""
```

### 自定义文件锁策略

```python
from filelock import FileLock

def save_report_with_lock(task_id, report):
    report_path = f"40-review/{task_id}.json"
    lock_path = f"40-review/{task_id}.lock"

    with FileLock(lock_path, timeout=5):
        with open(report_path, 'w') as f:
            json.dump(report, f)
```

## 🏆 最佳实践

1. **System Prompt设计**：要足够"对抗性"，让Reviewer保持批判态度
2. **信息降维**：返回给Builder的消息要极简，但报告文件要详尽
3. **文件锁**：防止并发写入导致报告损坏
4. **超时处理**：API调用要有超时机制，避免无限等待
5. **错误处理**：API失败时的降级策略

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可

MIT License
