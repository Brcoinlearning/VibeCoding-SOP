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
from src.core.context_queue import get_context_queue_manager
from src.core.async_listener import get_background_listener_manager
from src.utils.logger import setup_logging

# 初始化
logger = setup_logging("mcp_server")
settings = get_settings()
event_bus: EventBus = get_event_bus()
context_queue_manager = get_context_queue_manager()
background_listener_manager = get_background_listener_manager()

# 创建 MCP 服务器
server = Server("sop-orchestrator")


async def main():
    """主入口"""
    logger.info("Starting SOP Orchestrator MCP Server with Hybrid Event-Driven Architecture...")

    # 启动事件总线
    await event_bus.start()

    # 启动上下文队列管理器
    await context_queue_manager.start()

    # 启动后台监听器管理器
    await background_listener_manager.start()

    # 设置后台监听器（从配置读取）
    if hasattr(settings, 'base_path'):
        # 添加 Git 轮询监听器
        background_listener_manager.add_git_listener(
            repo_path=settings.base_path,
            poll_interval=5.0
        )

        # 添加文件监听器
        background_listener_manager.add_file_watcher(
            watch_path=settings.base_path,
            test_patterns={
                "pytest_results.json",
                "test-results.xml",
                ".pytest_cache/results.json"
            }
        )

        # 启动所有监听器
        await background_listener_manager.start_all_listeners()

    # 导入并注册工具（延迟导入避免循环依赖）
    from mcp_server.tools import (
        register_review_workflow,
        register_route_artifact,
        register_create_go_nogo,
        register_get_summary
    )
    from mcp_server.adapters.event_publisher import register_event_publisher_tools
    from mcp_server.tools.context_tools import register_context_tools

    # 注册所有工具
    register_review_workflow(server)
    register_route_artifact(server)
    register_create_go_nogo(server)
    register_get_summary(server)
    register_event_publisher_tools(server)
    register_context_tools(server)

    logger.info("MCP Server tools registered successfully")
    logger.info(f"Event-driven components started: EventBus, ContextQueue, BackgroundListeners")

    # 启动 stdio 服务器
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    finally:
        # 清理资源
        logger.info("Shutting down event-driven components...")
        await background_listener_manager.stop()
        await context_queue_manager.stop()
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
