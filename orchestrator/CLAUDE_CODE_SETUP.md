# Claude Code 集成配置指南

本文档说明如何将 SOP Orchestrator MCP Server 集成到 Claude Code 中。

## 前置要求

- Python 3.10+
- Claude Code 已安装并配置

## 安装步骤

### 1. 安装 MCP Server

```bash
cd orchestrator
pip install -e .
```

### 2. 配置 Claude Code

在 Claude Code 配置文件中添加 MCP Server 配置：

**macOS/Linux**: `~/.config/claude-code/config.json`
**Windows**: `%APPDATA%\claude-code\config.json`

```json
{
  "mcpServers": {
    "sop-orchestrator": {
      "command": "python",
      "args": ["-m", "mcp.server"],
      "env": {
        "ORCHESTRATOR_BASE_PATH": "/path/to/orchestrator",
        "ORCHESTRATOR_MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

### 3. 环境变量配置

复制并配置环境变量：

```bash
cp orchestrator/.env.example orchestrator/.env
# 编辑 .env 文件设置正确的路径
```

**重要**：将 `ORCHESTRATOR_BASE_PATH` 设置为 orchestrator 目录的绝对路径。

### 4. 验证安装

重启 Claude Code，然后运行：

```
Use the get_artifacts_summary tool to verify the connection.
```

## 使用示例

### 完整工作流示例

```
User: "Task 102 搞定了，走一下验收流程"

Claude: [调用 review_workflow 工具]

Claude: "我已经完成了代码审查工作流，发现以下问题：
- 1 个中等级别的并发风险
- 2 个代码规范问题

Go 还是 No-Go？"

User: "Go"

Claude: [调用 create_go_nogo 工具]

Claude: "已创建 Go/No-Go 记录，任务 T-102 已放行。"
```

### 可用工具

| 工具 | 用途 | 示例 |
|------|------|------|
| `review_workflow` | 执行完整审查工作流 | "审查 T-102" |
| `route_artifact` | 路由产物到正确目录 | "保存这份审查报告" |
| `create_go_nogo` | 创建 Go/No-Go 裁决 | "Go" / "No-Go" |
| `get_artifacts_summary` | 查询产物统计 | "显示所有产物" |

## 工作流程

### 标准验收流程

1. **触发审查**：告诉 AI 任务完成
2. **自动收集证据**：AI 调用 `review_workflow`
3. **AI 进行审查**：AI 分析证据并生成报告
4. **人类决策**：根据风险清单做出 Go/No-Go 决策
5. **记录决策**：AI 调用 `create_go_nogo` 保存决策

### 产物管理

所有产物自动路由到正确目录：

```
artifacts/
├── 20-planning/     # requirement_contract
├── 30-build/        # execution_evidence
├── 40-review/       # review_report
└── 50-release/      # go_no_go_record
```

## 故障排除

### MCP Server 无法启动

1. 检查 Python 路径是否正确
2. 验证 `ORCHESTRATOR_BASE_PATH` 环境变量
3. 查看日志：`orchestrator/logs/mcp_server.log`

### 工具调用失败

1. 确认 Git 仓库已初始化
2. 检查文件权限
3. 验证 artifacts 目录可写

### 配置文件位置

- **macOS**: `~/Library/Application Support/Claude Code/config.json`
- **Linux**: `~/.config/claude-code/config.json`
- **Windows**: `%APPDATA%\Claude Code\config.json`

## 高级配置

### 自定义传输层

默认使用 stdio，可扩展为 HTTP-SSE：

```bash
ORCHESTRATOR_MCP_TRANSPORT=http-sse
ORCHESTRATOR_MCP_PORT=8080
```

### 调试模式

启用详细日志：

```bash
ORCHESTRATOR_LOG_LEVEL=DEBUG
ORCHESTRATOR_DEBUG_MODE=true
```

## 下一步

- 查看 [README.md](README.md) 了解系统概览
- 查看 `archive/` 目录了解旧版 CLI 文档
- 运行 `pytest` 查看测试用例

## 支持

遇到问题？检查：
1. MCP Server 日志
2. Claude Code 配置
3. 环境变量设置
