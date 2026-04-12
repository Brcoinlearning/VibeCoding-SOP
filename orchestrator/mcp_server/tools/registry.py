"""
MCP 工具注册器
兼容 mcp 低层 Server API（list_tools / call_tool）。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool


ToolHandler = Callable[[dict[str, Any]], Awaitable[list[TextContent]]]


def register_tool(server: Server, tool: Tool, handler: ToolHandler) -> None:
    """向 low-level Server 注册工具定义与处理函数。"""
    if not hasattr(server, "_sop_tools"):
        server._sop_tools = {}  # type: ignore[attr-defined]
    if not hasattr(server, "_sop_tool_handlers"):
        server._sop_tool_handlers = {}  # type: ignore[attr-defined]

    tools: dict[str, Tool] = server._sop_tools  # type: ignore[attr-defined]
    handlers: dict[str, ToolHandler] = server._sop_tool_handlers  # type: ignore[attr-defined]

    tools[tool.name] = tool
    handlers[tool.name] = handler

    # 兼容现有测试里对 server._tools 的读取
    server._tools = tools  # type: ignore[attr-defined]

    if not hasattr(server, "_sop_registry_installed"):

        @server.list_tools()
        async def _list_tools() -> list[Tool]:
            return list(server._sop_tools.values())  # type: ignore[attr-defined]

        @server.call_tool()
        async def _call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
            callback = server._sop_tool_handlers.get(name)  # type: ignore[attr-defined]
            if callback is None:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
            return await callback(arguments or {})

        server._sop_registry_installed = True  # type: ignore[attr-defined]
