# Code Review Skills Library

从事件驱动MCP Server重构为轻量级Skill库

## 概述

本项目将复杂的MCP Server架构（事件总线、后台监听器、Agent生命周期管理）转换为三个独立的、被动的Skill工具。这种架构反转将控制权从系统调度转移到大模型的思维链(CoT)。

### 架构变化

**原始架构 (MCP Server):**
```
EventBus → BackgroundListener → Trimmer → Packager → ContextQueue → Agent
(主动系统)                                    (被动Agent)
```

**新架构 (Skill库):**
```
Human Request → Agent CoT → Skill Tool → Direct File/Git Operations
(主动触发)       (主动思考)     (被动工具)
```

## 技能列表

### 1. fetch_and_trim_evidence
**功能**: 上下文采集与裁剪

**替代组件**: Listener, Trimmer, Packager

**说明**: 当测试失败或需要审查时，Agent调用此工具执行Git Diff获取、测试报告读取和日志裁剪。

**输出**: 规范化的reviewer_input模板

**核心脚本**:
- `git_capture.py` - Git状态和diff获取
- `test_parser.py` - 测试结果解析
- `log_trimmer.py` - 日志和diff裁剪
- `evidence_packager.py` - 证据封装

### 2. execute_structured_review
**功能**: 强制结构化审查

**替代组件**: 对抗审查规则、注入器

**说明**: 通过Tool Schema进行系统级强约束，要求Agent输出包含severity、lethal_flaw、exploit_path、evidence的结构化审查结果。

**核心脚本**:
- `review_validator.py` - 输入验证
- `flaw_detector.py` - 缺陷检测
- `report_generator.py` - 报告生成

### 3. archive_review_artifact
**功能**: 产物路由与状态归档

**替代组件**: Router、Owner裁决逻辑

**说明**: 将审查结论写入文件系统，自动处理Frontmatter元数据、文件命名和目录路由。

**核心脚本**:
- `archiver.py` - 归档核心逻辑

## 目录结构

```
skill/
├── README.md                           # 本文件
├── fetch_and_trim_evidence/
│   ├── SKILL.md                        # 技能文档
│   └── scripts/
│       ├── git_capture.py              # Git状态捕获
│       ├── test_parser.py              # 测试结果解析
│       ├── log_trimmer.py              # 日志裁剪
│       └── evidence_packager.py        # 证据封装
├── execute_structured_review/
│   ├── SKILL.md                        # 技能文档
│   └── scripts/
│       ├── review_validator.py         # 输入验证
│       ├── flaw_detector.py            # 缺陷检测
│       └── report_generator.py         # 报告生成
└── archive_review_artifact/
    ├── SKILL.md                        # 技能文档
    └── scripts/
        └── archiver.py                 # 归档逻辑
```

## 使用流程

### 完整审查工作流

```
1. 人类触发
   ↓
2. fetch_and_trim_evidence (Agent调用)
   - 收集Git信息
   - 解析测试结果
   - 裁剪日志
   - 封装证据
   ↓
3. execute_structured_review (Agent调用)
   - 验证输入
   - 检测缺陷
   - 生成报告
   ↓
4. 人类审查报告
   ↓
5. archive_review_artifact (Agent调用)
   - 归档报告
   - 保存元数据
```

### 代码示例

```python
from skill.fetch_and_trim_evidence.scripts.git_capture import capture_git_status
from skill.fetch_and_trim_evidence.scripts.test_parser import parse_test_reports
from skill.fetch_and_trim_evidence.scripts.log_trimmer import trim_logs_and_diffs
from skill.fetch_and_trim_evidence.scripts.evidence_packager import package_reviewer_input

# 步骤1: 收集证据
repo_path = Path("/path/to/repo")
git_info = capture_git_status(repo_path)
test_results = parse_test_reports(repo_path)

# 步骤2: 裁剪数据
trimmed_log, trimmed_diff = trim_logs_and_diffs("", git_info["full_diff"])

# 步骤3: 封装证据
evidence = package_reviewer_input(
    task_id="T-001",
    git_info=git_info,
    test_results=test_results,
    trimmed_diff=trimmed_diff,
    trimmed_log=trimmed_log
)
```

```python
from skill.execute_structured_review.scripts.review_validator import validate_review_input
from skill.execute_structured_review.scripts.report_generator import execute_structured_review

# 步骤4: 执行结构化审查
review_data = {
    "severity": "critical",
    "lethal_flaw": "SQL注入漏洞",
    "exploit_path": "步骤1: ...",
    "evidence": {"test_case": "test_sql_injection"},
    "recommendation": "no-go"
}

report = execute_structured_review(evidence, review_data, "reviewer-1")
```

```python
from skill.archive_review_artifact.scripts.archiver import archive_review_artifact

# 步骤5: 归档审查结果
result = archive_review_artifact(report, "no-go")
print(f"Archived to: {result['filepath']}")
```

## 优势与权衡

### 优势
- ✅ 简单直接，易于调试
- ✅ 无需后台进程
- ✅ 代码量减少60%+
- ✅ 直接文件访问，便于审计
- ✅ 易于备份和迁移

### 权衡
- ⚠️ 失去全自动触发能力
- ⚠️ 需要人工触发工作流
- ⚠️ Agent可能"逃课"（需要系统提示词约束）

## 与原MCP Server的对比

| 方面 | MCP Server | Skill库 |
|------|-----------|---------|
| 架构 | 异步事件驱动 | 同步函数调用 |
| 触发方式 | 自动监听 | 人工触发 |
| 状态管理 | 队列、锁 | 简单参数 |
| 调试方式 | 追踪事件流 | 查看调用栈 |
| 部署 | 后台守护进程 | 按需函数 |
| 适用场景 | 生产环境、多用户 | 本地开发、单用户 |

## 迁移指南

### 从MCP迁移到Skill

1. **移除EventBus依赖**
   - 将事件发布改为函数调用
   - 将事件订阅改为直接函数执行

2. **简化异步代码**
   - 移除asyncio事件循环
   - 将await改为直接调用

3. **替换ContextQueue**
   - 将队列路由改为函数返回值
   - 将消息传递改为参数传递

4. **移除Agent生命周期管理**
   - 将睡眠/唤醒改为人工协调
   - 将状态机改为简单变量

## 开发建议

### 添加新技能

1. 在相应目录创建`SKILL.md`
2. 在`scripts/`目录添加实现脚本
3. 保持简单、被动的设计原则
4. 使用Schema约束而非Prompt

### 测试技能

```bash
# 测试证据收集
cd skill/fetch_and_trim_evidence/scripts
python git_capture.py /path/to/repo
python test_parser.py /path/to/repo

# 测试审查验证
cd skill/execute_structured_review/scripts
python review_validator.py

# 测试归档
cd skill/archive_review_artifact/scripts
python archiver.py
```

## 贡献

欢迎提交问题和改进建议！

## 许可

与主项目相同
