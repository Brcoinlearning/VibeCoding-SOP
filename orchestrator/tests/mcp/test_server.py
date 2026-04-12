"""
MCP Server 测试
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from mcp.server import Server


@pytest.mark.asyncio
async def test_server_initialization():
    """测试服务器初始化"""
    from mcp.server import Server
    server = Server("test-server")
    assert server.name == "test-server"


@pytest.mark.asyncio
async def test_review_workflow_tool_registration():
    """测试 review_workflow 工具注册"""
    from mcp_server.tools.review_workflow import register_review_workflow
    from mcp.server import Server

    server = Server("test-server")
    register_review_workflow(server)

    # 验证工具已注册
    assert "review_workflow" in [tool.name for tool in server._tools.values()]


@pytest.mark.asyncio
async def test_route_artifact_tool_registration():
    """测试 route_artifact 工具注册"""
    from mcp_server.tools.router import register_route_artifact
    from mcp.server import Server

    server = Server("test-server")
    register_route_artifact(server)

    # 验证工具已注册
    assert "route_artifact" in [tool.name for tool in server._tools.values()]


@pytest.mark.asyncio
async def test_create_go_nogo_tool_registration():
    """测试 create_go_nogo 工具注册"""
    from mcp_server.tools.go_nogo import register_create_go_nogo
    from mcp.server import Server

    server = Server("test-server")
    register_create_go_nogo(server)

    # 验证工具已注册
    assert "create_go_nogo" in [tool.name for tool in server._tools.values()]


@pytest.mark.asyncio
async def test_get_summary_tool_registration():
    """测试 get_artifacts_summary 工具注册"""
    from mcp_server.tools.summary import register_get_summary
    from mcp.server import Server

    server = Server("test-server")
    register_get_summary(server)

    # 验证工具已注册
    assert "get_artifacts_summary" in [tool.name for tool in server._tools.values()]
