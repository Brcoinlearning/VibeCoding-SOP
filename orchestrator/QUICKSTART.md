# 快速开始指南

## 📦 安装

### 1. 初始化环境

```bash
cd orchestrator
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
```

### 2. 激活虚拟环境

```bash
source venv/bin/activate
```

### 3. 验证安装

```bash
python -m src.main validate
```

## 🚀 基本使用

### 场景 1：审查一次代码变更

```bash
# 完整的审查流程（自动从 Git 获取信息）
python -m src.main review T-001

# 指定 commit 和文件
python -m src.main review T-001 \
  --commit abc123def \
  --diff-file ./changes.diff \
  --log-file ./build.log
```

**流程说明**：
1. 监听器捕获 build.completed 事件
2. 裁剪器执行日志摘要和 diff 限幅
3. 封装器生成 reviewer_input
4. 注入器发送到 Reviewer
5. 路由器保存审查报告

### 场景 2：监听模式（自动处理）

```bash
# 监听当前目录的文件变化
python -m src.main watch

# 监听指定目录
python -m src.main watch /path/to/project --task-id T-002
```

### 场景 3：Go/No-Go 裁决

```bash
# 批准发布
python -m src.main go-nogo T-001 go \
  --reviewer "张三" \
  --reasoning "代码质量符合标准，审查通过" \
  --risk "测试覆盖度略低于目标" \
  --condition "下周补充单元测试"

# 拒绝发布
python -m src.main go-nogo T-001 no-go \
  --reviewer "张三" \
  --reasoning "存在严重安全漏洞，必须修复"
```

## 🔧 与 Claude Code 集成

在你的项目根目录创建 `CLAUDE.md`：

```markdown
# Claude Code Hooks

## SessionStart
检测到会话开始，初始化 Orchestrator：

```bash
cd orchestrator && python -m src.main session-start --session-id $SESSION_ID
```

## SessionEnd
保存会话摘要：

```bash
cd orchestrator && python -m src.main session-end --session-id $SESSION_ID --summary "$SESSION_SUMMARY"
```

## PostCommit
提交后自动触发审查：

```bash
cd orchestrator && python -m src.main review T-$CURRENT_TASK_ID --commit $COMMIT_HASH
```
```

## 📊 查看产物

```bash
# 生成路由摘要
python -m src.main summary

# 保存摘要到文件
python -m src.main summary --output ./SUMMARY.md

# 手动路由产物
python -m src.main route ./my-review-report.md
```

## 🧪 运行测试

```bash
# 运行所有测试
pytest

# 运行端到端测试
pytest tests/test_full_workflow.py -v

# 查看覆盖率
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

## 📁 目录结构

```
orchestrator/
├── artifacts/              # 产物存储
│   ├── 20-planning/       # 需求契约
│   ├── 30-build/          # 执行证据
│   ├── 40-review/         # 审查报告
│   └── 50-release/        # Go/No-Go 记录
├── workspace/             # 工作空间
│   └── review_requests/   # 审查请求
├── logs/                  # 日志文件
└── src/                   # 源代码
```

## 🔍 故障排查

### 问题：审查请求没有响应

**原因**：使用 filesystem 后端时，需要手动创建响应文件

**解决**：
1. 检查 `workspace/review_requests/T-XXX/input.md`
2. 处理完成后，在同目录创建 `response.json`：
```json
{
  "task_id": "T-001",
  "reviewer_id": "your-name",
  "review_date": "2026-04-10T12:00:00",
  "decision": "approved",
  "overall_score": 85,
  "findings": [],
  "files_reviewed": []
}
```

### 问题：文件权限错误

**解决**：
```bash
chmod -R +x scripts/*.sh
chmod +w artifacts workspace logs
```

### 问题：依赖安装失败

**解决**：
```bash
pip install --upgrade pip
pip install -e . --no-cache-dir
```

## 📖 更多信息

- [完整文档](README.md)
- [架构设计](docs/ARCHITECTURE.md)
- [API 参考](docs/API.md)
