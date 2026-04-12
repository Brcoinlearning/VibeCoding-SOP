"""
MCP 适配器测试
"""
import pytest
from pathlib import Path
from datetime import datetime

from mcp_server.adapters.listener_adapter import GitListenerAdapter, TestListenerAdapter
from mcp_server.adapters.injector_adapter import ReviewerInjectorAdapter, NotificationInjectorAdapter
from mcp_server.adapters.router_adapter import RouterAdapter
from src.models.artifacts import Artifact, ArtifactType, FrontmatterMetadata


def test_git_listener_adapter_init():
    """测试 Git 监听器适配器初始化"""
    adapter = GitListenerAdapter(Path("/tmp/test"))
    assert adapter.repo_path == Path("/tmp/test")


def test_reviewer_injector_adapter_prepare():
    """测试审查器注入器准备"""
    adapter = ReviewerInjectorAdapter()

    metadata = FrontmatterMetadata(
        type=ArtifactType.REVIEW_REPORT,
        task_id="T-101",
        stage="review",
        status="ready",
        created_at=datetime.now()
    )
    artifact = Artifact(metadata=metadata, content="# Test Review")

    result = adapter.prepare_for_review(artifact)

    assert result["task_id"] == "T-101"
    assert result["content"] == "# Test Review"
    assert "metadata" in result


def test_reviewer_injector_adapter_format_prompt():
    """测试审查器提示词格式化"""
    adapter = ReviewerInjectorAdapter()

    metadata = FrontmatterMetadata(
        type=ArtifactType.EXECUTION_EVIDENCE,
        task_id="T-101",
        stage="build",
        status="ready",
        created_at=datetime.now()
    )
    artifact = Artifact(metadata=metadata, content="Test content")

    prompt = adapter.format_reviewer_prompt(artifact)

    assert "T-101" in prompt
    assert "Test content" in prompt
    assert "Code Review Request" in prompt


def test_notification_injector_adapter():
    """测试通知注入器"""
    adapter = NotificationInjectorAdapter()

    notification = adapter.prepare_notification(
        task_id="T-101",
        event_type="build.completed",
        message="Build completed successfully"
    )

    assert notification["task_id"] == "T-101"
    assert notification["event_type"] == "build.completed"
    assert notification["message"] == "Build completed successfully"

    formatted = adapter.format_notification(notification)
    assert "build.completed" in formatted
    assert "T-101" in formatted


def test_router_adapter_get_valid_types():
    """测试路由器获取有效类型"""
    adapter = RouterAdapter()
    types = adapter.get_valid_artifact_types()

    assert "requirement_contract" in types
    assert "execution_evidence" in types
    assert "review_report" in types
    assert "go_no_go_record" in types


def test_router_adapter_get_valid_statuses():
    """测试路由器获取有效状态"""
    adapter = RouterAdapter()
    statuses = adapter.get_valid_statuses()

    assert "draft" in statuses
    assert "ready" in statuses
    assert "approved" in statuses
    assert "rejected" in statuses


def test_router_adapter_validate_type():
    """测试路由器类型验证"""
    adapter = RouterAdapter()

    assert adapter.validate_artifact_type("review_report") is True
    assert adapter.validate_artifact_type("invalid_type") is False
