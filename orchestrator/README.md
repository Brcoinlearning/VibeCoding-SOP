# SOP Orchestrator MCP Server

软件开发SOP编排引擎 - AI驱动的代码审查与交付决策系统

## 🚀 启动 MCP Server

```bash
# 安装依赖
pip install -e .

# 启动 MCP Server（通过 Claude Code 自动启动）
# 无需手动启动，配置见 CLAUDE_CODE_SETUP.md
```

## 🤖 人类唯一的决策点

**Go/No-Go 裁决**：当AI完成代码审查后，会呈现风险清单和改进建议，你只需做出最终决策。

```
AI: "发现 1 个并发风险，Go 还是 No-Go？"
你: "Go"
```

## 📦 MCP 工具

| 工具 | 说明 | 人类输入 |
|------|------|----------|
| `review_workflow` | 执行完整审查工作流，捕获并封装证据 | Task ID |
| `route_artifact` | 自动路由产物到正确目录 | - |
| `create_go_nogo` | 创建 Go/No-Go 裁决记录 | **你的决策** |
| `get_artifacts_summary` | 查询产物统计摘要 | - |

## 📖 配置与集成

详见 [CLAUDE_CODE_SETUP.md](CLAUDE_CODE_SETUP.md)

## 📚 旧版文档

已归档至 `archive/` 目录，保留参考价值但不再维护。
