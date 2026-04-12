# 🚀 Agent-in-Tool 盲审架构 - 完整实现

> **真正的敏捷单机架构** - Builder 只负责写代码；审查的脑力活交给 Tool 内部独立唤醒的 API Agent；复杂的 I/O 和隔离机制由 Python 脚本在后台默默承受。

## 📁 完整目录结构

```
skill/agent-in-tool/
├── README.md                              # 项目总览
├── ARCHITECTURE.md                        # 架构蓝图
├── SUMMARY.md                             # 本文件
├── start.sh                               # 快速启动脚本 ⭐
├── cli.py                                 # 独立 CLI 主入口
├── pyproject.toml                         # 项目配置
├── requirements.txt                       # Python 依赖
├── .env.example                           # 环境变量示例
│
├── scripts/
│   └── blind_reviewer.py                  # Agent-in-Tool 核心实现 ⭐
│
├── read_task_contract/                    # Skill 1: 读取需求
│   └── SKILL.md
│
├── trigger_blind_review/                  # Skill 2: 盲审 (核心)
│   └── SKILL.md
│
└── submit_to_owner/                       # Skill 3: 人类裁决
    └── SKILL.md
```

## 🎯 四大核心 Skill

### Skill 1: `skill_forge_contract` 🧱
**功能**: 需求锻造与契约固化

**用途**: 接收原始需求并生成标准化需求与契约文件（10-requirements + 20-planning）

### Skill 2: `read_task_contract` 📋
**功能**: 读取任务需求文档

**用途**: Builder 开始工作前调用，获取要干什么

**实现**: 简单的 Python 文件读取，从 `20-planning/` 目录读取需求

### Skill 3: `trigger_blind_review` ⭐
**功能**: 触发盲审 - **核心杀手锏**

**用途**: Builder 认为代码写完了，调用此工具请求验收

**核心逻辑**:
1. **抓取证据**: Git diff + 测试日志 (Builder 看不到)
2. **派生子智能体**: 在 Tool 内部初始化独立的 Anthropic API Client
3. **独立审查**: 发送到全新的、无状态的 LLM 会话 (物理隔离)
4. **结果落盘**: 将完整报告写入 `40-review/` (使用文件锁)
5. **克制返回**: 只返回一句话给 Builder (信息降维)

### Skill 4: `submit_to_owner` ✅
**功能**: 提交人类裁决

**用途**: 审查通过后，请求人类最终放行

**实现**:
- 弹出原生确认框 (Go/No-Go)
- Go → 自动 commit 并路由到 `50-release/`
- No-Go → 返回给 Builder 继续修复

## 🔐 三大隔离机制

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

## 🚀 快速开始（独立运行，不依赖 MCP）

### 1. 安装依赖

```bash
cd skill/agent-in-tool
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 3. 使用 CLI

```bash
python3 cli.py forge-contract TASK-001 "原始需求文本" --workspace .
python3 cli.py read-task TASK-001 --workspace .
python3 cli.py tdd-enforce TASK-001 --workspace . --test-command "pytest -q"
python3 cli.py blind-review TASK-001 --workspace .
python3 cli.py submit-owner TASK-001 --workspace .
```

## 💡 使用示例

```python
# Builder 的工作流

# 1. 读取需求
result = read_task_contract("TASK-001")
print(f"任务: {result['title']}")

# 2. 编写代码...

# 3. 请求审查
result = trigger_blind_review("TASK-001")
if result["status"] == "REJECTED":
    print(f"❌ {result['message']}")
    # 读取报告并修复
    # ...
    # 重新请求审查
    result = trigger_blind_review("TASK-001")

# 4. 请求人类放行
result = submit_to_owner("TASK-001")
```

## 🎨 核心代码片段

### Agent-in-Tool 实现 (blind_reviewer.py)

```python
class BlindReviewer:
    async def review(self, task_id: str, workspace: str) -> Dict:
        # 1. 收集证据
        evidence = await self._collect_evidence(workspace)

        # 2. 派发独立 LLM Agent
        client = AsyncAnthropic(api_key=self.api_key)
        response = await client.messages.create(
            model="claude-3-7-sonnet-20250219",
            system=REVIEWER_SYSTEM_PROMPT,  # 对抗性 Prompt
            messages=[{"role": "user", "content": evidence}]
        )

        # 3. 保存报告
        await self._save_review_report(task_id, response, workspace)

        # 4. 信息降维返回
        return self._format_minimal_response(task_id, response)
```

### Reviewer 对抗性 System Prompt

```python
REVIEWER_SYSTEM_PROMPT = """
你是一个冷酷无情的顶级安全审查员。

## 审查重点
1. SQL注入漏洞
2. XSS跨站脚本
3. 并发竞态条件
4. 空指针解引用
5. 业务逻辑错误

## 审查原则
- 宁可错杀，不可放过
- 发现 critical 级别问题必须 REJECTED
- 没有测试覆盖的功能自动 REJECTED

## 输出格式
纯 JSON：
{
  "status": "PASS" | "REJECTED",
  "lethal_flaw": "致命缺陷描述",
  "severity": "critical" | "major" | "minor",
  "exploit_path": "复现路径",
  "remediation": "修复建议"
}
"""
```

## 🏆 架构优势

### 与传统方案对比

| 方面 | 伪 Skill / 双开 | Agent-in-Tool |
|------|----------------|---------------|
| **隔离程度** | 逻辑隔离 | 物理隔离 |
| **审查质量** | 死板规则 | 真正 AI 理解 |
| **用户体验** | 切换窗口 | 单终端心流 |
| **上下文控制** | 容易泄露 | 完全隔离 |
| **可扩展性** | 受限 | 无限 |

### 关键优势

1. **真正的盲审**: Builder 无法影响审查结果
2. **AI 驱动**: 审查由 LLM 完成，而非死板规则
3. **心流保持**: Builder 无需切换窗口
4. **结果可靠**: 物理隔离确保审查公正性
5. **易于扩展**: 修改 System Prompt 即可调整策略

## 📊 工作流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    Builder Agent Workflow                    │
└─────────────────────────────────────────────────────────────┘
                              |
                              v
                    read_task_contract("TASK-001")
                              |
                              v
                    [读取需求文档]
                              |
                              v
                    [编写代码...]
                              |
                              v
                    trigger_blind_review("TASK-001")
                              |
        +---------------------+---------------------+
        |                                           |
        v                                           v
[后台 Agent-in-Tool]                        [Builder 等待]
        |                                           |
        +-> collect_evidence()                      |
        |                                           |
        +-> spawn_independent_llm()                 |
        |   - 新的 API 会话                          |
        |   - 对抗性 Prompt                         |
        |   - 物理隔离                              |
        |                                           |
        +-> save_report(40-review/)                 |
        |                                           |
        v                                           v
[返回极简结果] <-----------------------------------+
        |
        v
    "❌ 审查未通过" OR "✅ 审查通过"
        |
        v
submit_to_owner("TASK-001")
        |
        v
[人类确认框]
    /       \
  Go      No-Go
   |         |
   v         v
[Commit] [返回修复]
   |
   v
[路由到 50-release/]
   |
   v
✅ 发布完成
```

## 🔧 扩展指南

### 添加新的审查规则

修改 `scripts/blind_reviewer.py` 中的 `REVIEWER_SYSTEM_PROMPT`

### 自定义审查模型

```python
reviewer = BlindReviewer(model="claude-3-opus-20240229")
```

### CI/CD 集成

```python
await submit_to_owner(
    task_id="TASK-001",
    non_interactive=True,
    approval="auto"
)
```

## 📝 总结

这套 **Agent-in-Tool 盲审架构** 是真正的敏捷单机开发解决方案：

1. ✅ **真正的物理隔离** - 独立 LLM API 调用
2. ✅ **真正的 AI 审查** - 对抗性 Prompt + 无状态会话
3. ✅ **真正的单终端心流** - 无需切换窗口
4. ✅ **真正的信息降维** - Builder 只看到结果
5. ✅ **真正的可扩展性** - 修改 Prompt 即可

按照这个架构，开发者可以享受：
- 单终端心流体验
- 真正的 AI 审查质量
- 完全的物理隔离保证
- 简洁的工具接口

**这才是真正的敏捷开发架构！**
