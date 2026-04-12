"""
Unit tests for Context Queue System
测试上下文队列和多 Agent 隔离通信
"""
import asyncio
import pytest
from datetime import datetime
from pathlib import Path
import tempfile

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.context_queue import (
    ContextQueue,
    ContextQueueManager,
    AgentRole,
    ContextMessage,
    get_context_queue_manager,
    reset_context_queue_manager
)


@pytest.fixture
def temp_persist_dir():
    """创建临时持久化目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def context_queue(temp_persist_dir):
    """创建上下文队列 fixture"""
    return ContextQueue(
        role=AgentRole.REVIEWER,
        max_size=10,
        persist_path=temp_persist_dir
    )


@pytest.fixture
def queue_manager(temp_persist_dir):
    """创建队列管理器 fixture"""
    reset_context_queue_manager()
    return ContextQueueManager(
        max_queue_size=10,
        persist_dir=temp_persist_dir
    )


@pytest.mark.asyncio
async def test_context_queue_put_and_get(context_queue):
    """测试队列的放入和获取"""
    message = ContextMessage(
        from_role=AgentRole.BUILDER,
        to_role=AgentRole.REVIEWER,
        task_id="T-102",
        message_type="evidence",
        content={"test": "data"}
    )

    # 放入消息
    success = await context_queue.put(message)
    assert success is True

    # 获取消息
    retrieved = await context_queue.get(timeout=1.0)
    assert retrieved is not None
    assert retrieved.task_id == "T-102"
    assert retrieved.message_type == "evidence"


@pytest.mark.asyncio
async def test_context_queue_size_limit(context_queue):
    """测试队列大小限制"""
    # 填满队列
    for i in range(10):
        message = ContextMessage(
            from_role=AgentRole.BUILDER,
            to_role=AgentRole.REVIEWER,
            task_id=f"T-{i}",
            message_type="test",
            content={}
        )
        await context_queue.put(message)

    # 尝试放入第 11 个消息
    overflow_message = ContextMessage(
        from_role=AgentRole.BUILDER,
        to_role=AgentRole.REVIEWER,
        task_id="T-overflow",
        message_type="test",
        content={}
    )
    success = await context_queue.put(overflow_message)
    assert success is False  # 队列已满


@pytest.mark.asyncio
async def test_context_queue_get_timeout(context_queue):
    """测试获取超时"""
    # 队列为空，应该超时
    result = await context_queue.get(timeout=0.1)
    assert result is None


@pytest.mark.asyncio
async def test_context_queue_clear(context_queue):
    """测试清空队列"""
    # 放入一些消息
    for i in range(5):
        message = ContextMessage(
            from_role=AgentRole.BUILDER,
            to_role=AgentRole.REVIEWER,
            task_id=f"T-{i}",
            message_type="test",
            content={}
        )
        await context_queue.put(message)

    assert context_queue.size() == 5

    # 清空队列
    await context_queue.clear()
    assert context_queue.size() == 0


@pytest.mark.asyncio
async def test_context_queue_history(context_queue):
    """测试历史记录"""
    messages = []
    for i in range(5):
        message = ContextMessage(
            from_role=AgentRole.BUILDER,
            to_role=AgentRole.REVIEWER,
            task_id=f"T-{i}",
            message_type="test",
            content={"index": i}
        )
        await context_queue.put(message)
        messages.append(message)

    # 获取历史
    history = await context_queue.get_history(limit=3)
    assert len(history) == 3
    assert history[0].content["index"] == 2  # 应该是最后 3 条
    assert history[2].content["index"] == 4


@pytest.mark.asyncio
async def test_context_queue_manager_routing(queue_manager):
    """测试队列管理器的路由功能"""
    await queue_manager.start()

    # 测试路由到 Reviewer
    evidence = {"file": "test.py", "diff": "+ code"}
    success = await queue_manager.route_to_reviewer(
        task_id="T-102",
        evidence=evidence
    )
    assert success is True

    # Reviewer 获取任务
    task = await queue_manager.get_reviewer_input(timeout=1.0)
    assert task is not None
    assert task.task_id == "T-102"
    assert task.message_type == "evidence"
    assert task.content == evidence

    await queue_manager.stop()


@pytest.mark.asyncio
async def test_context_queue_manager_review_submission(queue_manager):
    """测试审查结果提交"""
    await queue_manager.start()

    # Reviewer 提交审查结果
    review_result = {
        "decision": "approved",
        "score": 95,
        "findings": []
    }
    success = await queue_manager.submit_review(
        task_id="T-102",
        review_result=review_result,
        reviewer_id="reviewer-1"
    )
    assert success is True

    # Owner 获取审查结果
    result = await queue_manager.get_owner_input(timeout=1.0)
    assert result is not None
    assert result.task_id == "T-102"
    assert result.message_type == "review_result"
    assert result.content == review_result
    assert result.metadata["reviewer_id"] == "reviewer-1"

    await queue_manager.stop()


@pytest.mark.asyncio
async def test_context_queue_manager_notification_routing(queue_manager):
    """测试通知路由"""
    await queue_manager.start()

    notification = {"type": "info", "message": "Build completed"}
    success = await queue_manager.route_notification(
        task_id="T-102",
        notification=notification,
        to_role=AgentRole.OWNER,
        from_role=AgentRole.BUILDER
    )
    assert success is True

    await queue_manager.stop()


@pytest.mark.asyncio
async def test_context_queue_isolation(queue_manager):
    """测试 Agent 隔离"""
    await queue_manager.start()

    # Builder 发送到 Reviewer
    await queue_manager.route_to_reviewer(
        task_id="T-102",
        evidence={"data": "for_reviewer"}
    )

    # Builder 发送到 Owner
    await queue_manager.route_to_owner(
        task_id="T-102",
        review_result={"data": "for_owner"}
    )

    # 验证队列隔离
    reviewer_size = queue_manager.get_queue_size(AgentRole.REVIEWER)
    owner_size = queue_manager.get_queue_size(AgentRole.OWNER)

    assert reviewer_size == 1
    assert owner_size == 1

    # Reviewer 不应该能访问 Owner 的队列
    reviewer_task = await queue_manager.get_reviewer_input(timeout=0.1)
    assert reviewer_task.message_type == "evidence"

    owner_task = await queue_manager.get_owner_input(timeout=0.1)
    assert owner_task.message_type == "review_result"

    await queue_manager.stop()


@pytest.mark.asyncio
async def test_context_queue_concurrent_access(queue_manager):
    """测试并发访问"""
    await queue_manager.start()

    # 并发发送多个消息
    tasks = []
    for i in range(10):
        task = queue_manager.route_to_reviewer(
            task_id=f"T-{i}",
            evidence={"index": i}
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    assert all(results)

    # 验证所有消息都进入了队列
    assert queue_manager.get_queue_size(AgentRole.REVIEWER) == 10

    await queue_manager.stop()


def test_global_queue_manager():
    """测试全局队列管理器实例"""
    reset_context_queue_manager()
    manager1 = get_context_queue_manager()
    manager2 = get_context_queue_manager()

    # 应该返回同一个实例
    assert manager1 is manager2


@pytest.mark.asyncio
async def test_context_queue_persistence(temp_persist_dir):
    """测试持久化功能"""
    persist_path = temp_persist_dir / "test_queue"
    queue = ContextQueue(
        role=AgentRole.BUILDER,
        max_size=10,
        persist_path=persist_path
    )

    # 放入消息
    message = ContextMessage(
        from_role=AgentRole.BUILDER,
        to_role=AgentRole.REVIEWER,
        task_id="T-102",
        message_type="test",
        content={"persistent": "data"}
    )
    await queue.put(message)

    # 验证文件创建
    expected_file = persist_path / "builder_messages.jsonl"
    assert expected_file.exists()

    # 验证文件内容
    with open(expected_file, 'r') as f:
        content = f.read()
        assert "T-102" in content
        assert "persistent" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
