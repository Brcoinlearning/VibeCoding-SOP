"""
Unit tests for MCP Event Publisher
测试事件发布机制
"""
import asyncio
import pytest
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp_server.adapters.event_publisher import MCPEventPublisher, get_event_publisher
from src.core.event_bus import get_event_bus, reset_event_bus
from src.models.events import BuildCompletedEvent, TestCompletedEvent, EventType


@pytest.fixture
def event_bus():
    """创建事件总线 fixture"""
    reset_event_bus()
    bus = get_event_bus()
    return bus


@pytest.fixture
def event_publisher():
    """创建事件发布器 fixture"""
    return MCPEventPublisher()


@pytest.mark.asyncio
async def test_publish_build_event(event_publisher, event_bus):
    """测试发布构建事件"""
    # 订阅事件以验证
    received_events = []

    async def handler(event: BuildCompletedEvent):
        received_events.append(event)

    event_bus.subscribe(EventType.BUILD_COMPLETED, handler)

    # 发布事件
    result = await event_publisher.publish_build_event(
        task_id="T-102",
        commit_hash="abc123",
        branch="main",
        diff_summary="Test changes",
        changed_files=["test.py"],
        wait_for_processing=False
    )

    assert result["success"] is True
    assert result["task_id"] == "T-102"
    assert result["event_type"] == "build.completed"


@pytest.mark.asyncio
async def test_publish_test_event(event_publisher, event_bus):
    """测试发布测试事件"""
    result = await event_publisher.publish_test_event(
        task_id="T-102",
        passed=True,
        total_tests=100,
        failed_tests=0,
        test_summary="All tests passed",
        coverage_percent=85.5,
        wait_for_processing=False
    )

    assert result["success"] is True
    assert result["task_id"] == "T-102"
    assert result["event_type"] == "test.completed"
    assert result["passed"] is True


@pytest.mark.asyncio
async def test_publish_with_timeout(event_publisher):
    """测试事件发布超时机制"""
    result = await event_publisher.publish_build_event(
        task_id="T-103",
        commit_hash="def456",
        branch="feature",
        wait_for_processing=True,
        timeout=0.1  # 非常短的超时时间
    )

    # 即使超时也应该成功发布
    assert result["success"] is True


@pytest.mark.asyncio
async def test_event_publisher_error_handling(event_publisher):
    """测试错误处理"""
    # 测试无效参数
    result = await event_publisher.publish_build_event(
        task_id="",  # 无效的任务 ID
        commit_hash="",
        branch=""
    )

    # 应该处理错误而不崩溃
    assert "success" in result


@pytest.mark.asyncio
async def test_concurrent_event_publishing(event_publisher):
    """测试并发事件发布"""
    tasks = []
    for i in range(10):
        task = event_publisher.publish_build_event(
            task_id=f"T-{i}",
            commit_hash=f"commit{i}",
            branch="main",
            wait_for_processing=False
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    # 所有事件都应该成功发布
    assert all(r["success"] for r in results)


@pytest.mark.asyncio
async def test_event_processing_wait机制(event_publisher):
    """测试事件处理等待机制"""
    task_id = "T-wait-test"

    # 发布事件并等待处理
    publish_task = asyncio.create_task(
        event_publisher.publish_build_event(
            task_id=task_id,
            commit_hash="wait123",
            branch="main",
            wait_for_processing=True,
            timeout=5.0
        )
    )

    # 模拟处理完成
    await asyncio.sleep(0.5)
    wait_key = f"build_{task_id}_wait123"
    event_publisher.mark_event_processed(wait_key)

    # 等待发布完成
    result = await publish_task

    assert result["success"] is True


def test_global_event_publisher():
    """测试全局事件发布器实例"""
    publisher1 = get_event_publisher()
    publisher2 = get_event_publisher()

    # 应该返回同一个实例
    assert publisher1 is publisher2


@pytest.mark.asyncio
async def test_publish_review_event(event_publisher):
    """测试发布审查事件"""
    result = await event_publisher.publish_review_event(
        task_id="T-102",
        reviewer_id="reviewer-1",
        decision="approved",
        findings_count=5,
        critical_issues=0,
        review_report_path="/path/to/report.json",
        wait_for_processing=False
    )

    assert result["success"] is True
    assert result["task_id"] == "T-102"
    assert result["event_type"] == "review.completed"
    assert result["decision"] == "approved"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
