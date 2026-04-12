#!/usr/bin/env python3
"""
SOP Orchestrator MCP Server
软件开发SOP编排引擎 - MCP Server版本

将 CLI 替换为 MCP Server，实现真正的 Agentic Workflow
"""
import asyncio
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings
from src.core.event_bus import EventBus, get_event_bus
from src.utils.logger import setup_logging

# 初始化
logger = setup_logging("mcp_server")
settings = get_settings()
event_bus: EventBus = get_event_bus()

# 创建 MCP 服务器
server = Server("sop-orchestrator")


async def main():
    """主入口"""
    logger.info("Starting SOP Orchestrator MCP Server...")

    await event_bus.start()

    # 导入并注册工具（延迟导入避免循环依赖）
    from mcp_server.tools import (
        register_review_workflow,
        register_route_artifact,
        register_create_go_nogo,
        register_get_summary
    )

    # 注册所有工具
    register_review_workflow(server)
    register_route_artifact(server)
    register_create_go_nogo(server)
    register_get_summary(server)

    logger.info("MCP Server tools registered successfully")

    # 启动 stdio 服务器
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

    await event_bus.stop()
    logger.info("MCP Server shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.exception(f"Server error: {e}")
        sys.exit(1)
