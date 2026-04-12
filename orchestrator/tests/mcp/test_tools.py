"""
MCP 工具测试
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from mcp_server.tools.review_workflow import execute_review_workflow
from mcp_server.tools.router import execute_route_artifact
from mcp_server.tools.go_nogo import execute_create_go_nogo
from mcp_server.tools.summary import execute_get_summary


@pytest.mark.asyncio
async def test_review_workflow_success():
    """测试成功的审查工作流"""
    with patch('mcp_server.tools.review_workflow._capture_git_status') as mock_git:
        from src.models.events import BuildCompletedEvent
        from datetime import datetime

        mock_git.return_value = BuildCompletedEvent(
            task_id="T-101",
            commit_hash="abc123",
            branch="main",
            diff_summary="2 files changed",
            changed_files=["file1.py"],
            timestamp=datetime.now()
        )

        result = await execute_review_workflow(
            task_id="T-101",
            base_path="/tmp/test"
        )

        assert result["success"] is True
        assert result["task_id"] == "T-101"
        assert "artifact" in result


@pytest.mark.asyncio
async def test_route_artifact_success():
    """测试成功的产物路由"""
    result = await execute_route_artifact(
        artifact_type="review_report",
        task_id="T-101",
        content="# Test Review\n\nThis is a test review.",
        stage="review",
        status="ready"
    )

    assert result["success"] is True
    assert result["task_id"] == "T-101"
    assert "target_path" in result


@pytest.mark.asyncio
async def test_route_artifact_invalid_type():
    """测试无效的产物类型"""
    result = await execute_route_artifact(
        artifact_type="invalid_type",
        task_id="T-101",
        content="# Test"
    )

    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_create_go_nogo_success():
    """测试成功的 Go/No-Go 创建"""
    result = await execute_create_go_nogo(
        task_id="T-101",
        decision="go",
        reasoning="All tests passed, no critical issues found."
    )

    assert result["success"] is True
    assert result["decision"] == "go"
    assert "target_path" in result


@pytest.mark.asyncio
async def test_create_go_nogo_invalid_decision():
    """测试无效的决策值"""
    result = await execute_create_go_nogo(
        task_id="T-101",
        decision="invalid",
        reasoning="Test"
    )

    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_create_go_nogo_missing_reasoning():
    """测试缺少决策理由"""
    result = await execute_create_go_nogo(
        task_id="T-101",
        decision="go",
        reasoning=""
    )

    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_get_summary():
    """测试获取摘要"""
    result = await execute_get_summary(
        limit=10
    )

    assert result["success"] is True
    assert "summary" in result
    assert "filters_applied" in result
