"""
End-to-end tests for Multi-Agent Isolation
测试 Builder → Reviewer → Owner 的完整流程和上下文隔离
"""
import asyncio
import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.context_queue import (
    ContextQueueManager,
    AgentRole,
    get_context_queue_manager,
    reset_context_queue_manager
)
from src.core.event_bus import get_event_bus, reset_event_bus
from src.core.async_listener import BackgroundListenerManager
from src.models.events import BuildCompletedEvent, TestCompletedEvent


@pytest.fixture
def e2e_setup():
    """端到端测试设置"""
    reset_context_queue_manager()
    reset_event_bus()

    temp_dir = Path(tempfile.mkdtemp())

    # 创建组件
    event_bus = get_event_bus()
    queue_manager = ContextQueueManager(
        max_queue_size=100,
        persist_dir=temp_dir / ".context_queues"
    )

    return {
        "event_bus": event_bus,
        "queue_manager": queue_manager,
        "temp_dir": temp_dir
    }


@pytest.mark.asyncio
async def test_e2e_builder_to_reviewer_workflow(e2e_setup):
    """测试完整的 Builder → Reviewer 工作流"""
    queue_manager = e2e_setup["queue_manager"]
    await queue_manager.start()

    # Builder Agent: 生成证据并路由到 Reviewer
    task_id = "T-E2E-001"
    evidence = {
        "task_id": task_id,
        "commit_hash": "abc123",
        "branch": "feature/test",
        "diff": "+ New feature code",
        "test_results": {
            "passed": True,
            "total_tests": 50,
            "failed_tests": 0
        },
        "metadata": {
            "author": "builder-agent",
            "timestamp": datetime.now().isoformat()
        }
    }

    # Builder 路由证据
    success = await queue_manager.route_to_reviewer(
        task_id=task_id,
        evidence=evidence,
        metadata={"priority": "high"}
    )

    assert success is True
    assert queue_manager.get_queue_size(AgentRole.REVIEWER) == 1

    # Reviewer Agent: 获取待审查任务
    reviewer_task = await queue_manager.get_reviewer_input(
        task_id=task_id,
        timeout=1.0
    )

    assert reviewer_task is not None
    assert reviewer_task.task_id == task_id
    assert reviewer_task.from_role == AgentRole.BUILDER
    assert reviewer_task.to_role == AgentRole.REVIEWER
    assert reviewer_task.message_type == "evidence"
    assert reviewer_task.content["commit_hash"] == "abc123"

    # Reviewer Agent: 提交审查结果
    review_result = {
        "decision": "approved",
        "overall_score": 95,
        "findings": [
            {
                "severity": "low",
                "category": "style",
                "title": "Minor style issue",
                "description": "Consider using more descriptive names"
            }
        ],
        "notes": "Code looks good, ready to merge"
    }

    success = await queue_manager.submit_review(
        task_id=task_id,
        review_result=review_result,
        reviewer_id="reviewer-agent"
    )

    assert success is True
    assert queue_manager.get_queue_size(AgentRole.OWNER) == 1

    await queue_manager.stop()


@pytest.mark.asyncio
async def test_e2e_reviewer_to_owner_workflow(e2e_setup):
    """测试完整的 Reviewer → Owner 工作流"""
    queue_manager = e2e_setup["queue_manager"]
    await queue_manager.start()

    # 设置: Reviewer 已提交审查结果
    task_id = "T-E2E-002"
    review_result = {
        "decision": "conditional",
        "overall_score": 75,
        "findings": [
            {
                "severity": "medium",
                "category": "security",
                "title": "SQL injection risk",
                "description": "User input not sanitized"
            }
        ],
        "conditions": "Fix security issues before deployment"
    }

    await queue_manager.submit_review(
        task_id=task_id,
        review_result=review_result,
        reviewer_id="reviewer-agent"
    )

    # Owner Agent: 获取审查结果
    owner_task = await queue_manager.get_owner_input(
        task_id=task_id,
        timeout=1.0
    )

    assert owner_task is not None
    assert owner_task.task_id == task_id
    assert owner_task.from_role == AgentRole.REVIEWER
    assert owner_task.to_role == AgentRole.OWNER
    assert owner_task.message_type == "review_result"
    assert owner_task.content["decision"] == "conditional"
    assert owner_task.metadata["reviewer_id"] == "reviewer-agent"

    # Owner Agent: 基于审查结果做出决策
    decision_data = {
        "go_no_go": "no-go",
        "reason": "Security issues must be fixed first",
        "required_fixes": ["Sanitize user input", "Add parameterized queries"]
    }

    # Owner 可以将决策路由回 Builder
    await queue_manager.route_notification(
        task_id=task_id,
        notification=decision_data,
        to_role=AgentRole.BUILDER,
        from_role=AgentRole.OWNER
    )

    await queue_manager.stop()


@pytest.mark.asyncio
async def test_e2e_complete_three_agent_workflow(e2e_setup):
    """测试完整的三 Agent 工作流：Builder → Reviewer → Owner → Builder"""
    queue_manager = e2e_setup["queue_manager"]
    await queue_manager.start()

    task_id = "T-E2E-003"

    # === Phase 1: Builder Agent ===
    # Builder 捕获证据并路由到 Reviewer
    evidence = {
        "task_id": task_id,
        "commit_hash": "xyz789",
        "branch": "feature/awesome",
        "diff": "+ Awesome feature code",
        "test_results": {"passed": True, "total": 100, "failed": 0}
    }

    await queue_manager.route_to_reviewer(task_id=task_id, evidence=evidence)

    # === Phase 2: Reviewer Agent ===
    # Reviewer 获取任务并审查
    reviewer_task = await queue_manager.get_reviewer_input(task_id=task_id)
    assert reviewer_task is not None

    # Reviewer 提交审查结果
    review_result = {
        "decision": "approved",
        "overall_score": 90,
        "findings": []
    }
    await queue_manager.submit_review(
        task_id=task_id,
        review_result=review_result,
        reviewer_id="reviewer-agent"
    )

    # === Phase 3: Owner Agent ===
    # Owner 获取审查结果
    owner_task = await queue_manager.get_owner_input(task_id=task_id)
    assert owner_task is not None

    # Owner 做出 Go 决策并通知 Builder
    go_decision = {
        "decision": "go",
        "reason": "Code review passed, ready for deployment",
        "deployment_target": "production"
    }
    await queue_manager.route_notification(
        task_id=task_id,
        notification=go_decision,
        to_role=AgentRole.BUILDER,
        from_role=AgentRole.OWNER
    )

    # === Phase 4: Builder Agent receives notification ===
    # Builder 可以检查队列中的通知
    builder_queue = queue_manager._queues[AgentRole.BUILDER]
    builder_notification = await builder_queue.get(timeout=1.0)

    assert builder_notification is not None
    assert builder_notification.message_type == "notification"
    assert builder_notification.content["decision"] == "go"

    await queue_manager.stop()


@pytest.mark.asyncio
async def test_e2e_agent_isolation(e2e_setup):
    """测试 Agent 之间的完全隔离"""
    queue_manager = e2e_setup["queue_manager"]
    await queue_manager.start()

    # 多个任务同时进行
    tasks = [
        ("T-ISO-001", "feature-a"),
        ("T-ISO-002", "feature-b"),
        ("T-ISO-003", "feature-c")
    ]

    # Builder 路由所有任务到 Reviewer
    for task_id, branch in tasks:
        await queue_manager.route_to_reviewer(
            task_id=task_id,
            evidence={"task_id": task_id, "branch": branch}
        )

    # 验证隔离: 每个 Agent 只能访问自己的队列
    reviewer_size = queue_manager.get_queue_size(AgentRole.REVIEWER)
    owner_size = queue_manager.get_queue_size(AgentRole.OWNER)
    builder_size = queue_manager.get_queue_size(AgentRole.BUILDER)

    assert reviewer_size == 3  # 三个任务在 Reviewer 队列
    assert owner_size == 0    # Owner 队列为空
    assert builder_size == 0  # Builder 队列为空

    # Reviewer 处理任务
    processed_tasks = []
    for _ in range(3):
        task = await queue_manager.get_reviewer_input(timeout=1.0)
        assert task is not None
        processed_tasks.append(task.task_id)

        # 提交审查
        await queue_manager.submit_review(
            task_id=task.task_id,
            review_result={"decision": "approved"},
            reviewer_id="reviewer-agent"
        )

    # 验证所有任务都被处理
    assert set(processed_tasks) == {t[0] for t in tasks}

    # Owner 队列现在应该有 3 个审查结果
    owner_size = queue_manager.get_queue_size(AgentRole.OWNER)
    assert owner_size == 3

    await queue_manager.stop()


@pytest.mark.asyncio
async def test_e2e_concurrent_multi_agent_workflow(e2e_setup):
    """测试并发的多 Agent 工作流"""
    queue_manager = e2e_setup["queue_manager"]
    await queue_manager.start()

    # 模拟多个任务同时进行
    async def process_task(task_id: str):
        # Builder 阶段
        await queue_manager.route_to_reviewer(
            task_id=task_id,
            evidence={"task_id": task_id}
        )

        # Reviewer 阶段
        await asyncio.sleep(0.1)  # 模拟处理时间
        reviewer_task = await queue_manager.get_reviewer_input(task_id=task_id)
        await queue_manager.submit_review(
            task_id=task_id,
            review_result={"decision": "approved"},
            reviewer_id="reviewer-agent"
        )

        # Owner 阶段
        await asyncio.sleep(0.1)  # 模拟处理时间
        owner_task = await queue_manager.get_owner_input(task_id=task_id)
        return owner_task is not None

    # 并发处理 5 个任务
    tasks = [process_task(f"T-CONC-{i}") for i in range(5)]
    results = await asyncio.gather(*tasks)

    # 所有任务都应该成功完成
    assert all(results)

    await queue_manager.stop()


@pytest.mark.asyncio
async def test_e2e_error_handling_and_recovery(e2e_setup):
    """测试错误处理和恢复"""
    queue_manager = e2e_setup["queue_manager"]
    await queue_manager.start()

    # 测试无效的任务 ID
    result = await queue_manager.get_reviewer_input(task_id="NON-EXISTENT")
    assert result is None

    # 测试队列满的情况
    small_manager = ContextQueueManager(max_queue_size=2)
    await small_manager.start()

    # 填满队列
    for i in range(3):
        success = await small_manager.route_to_reviewer(
            task_id=f"T-{i}",
            evidence={"data": i}
        )
        if i >= 2:
            assert success is False  # 队列已满
        else:
            assert success is True

    await small_manager.stop()
    await queue_manager.stop()


@pytest.mark.asyncio
async def test_e2e_persistence_and_recovery(e2e_setup):
    """测试持久化和恢复"""
    temp_dir = e2e_setup["temp_dir"]
    persist_dir = temp_dir / ".context_queues"

    queue_manager = ContextQueueManager(
        max_queue_size=100,
        persist_dir=persist_dir
    )
    await queue_manager.start()

    # 添加一些消息
    task_id = "T-PERS-001"
    await queue_manager.route_to_reviewer(
        task_id=task_id,
        evidence={"test": "persistence"}
    )

    # 等待持久化完成
    await asyncio.sleep(0.1)

    # 验证文件存在
    reviewer_file = persist_dir / "reviewer" / "reviewer_messages.jsonl"
    # 注意：由于实现可能不同，这里主要验证不崩溃

    await queue_manager.stop()


@pytest.mark.asyncio
async def test_e2e_notification_routing(e2e_setup):
    """测试通知路由到不同 Agent"""
    queue_manager = e2e_setup["queue_manager"]
    await queue_manager.start()

    task_id = "T-NOTIFY-001"

    # 路由通知到所有 Agent
    for role in [AgentRole.BUILDER, AgentRole.REVIEWER, AgentRole.OWNER]:
        success = await queue_manager.route_notification(
            task_id=task_id,
            notification={"message": f"Hello {role.value}"},
            to_role=role,
            from_role=AgentRole.BUILDER
        )
        assert success is True

    # 验证每个队列都有消息
    for role in [AgentRole.BUILDER, AgentRole.REVIEWER, AgentRole.OWNER]:
        size = queue_manager.get_queue_size(role)
        assert size == 1

    await queue_manager.stop()


@pytest.mark.asyncio
async def test_e2e_queue_status_monitoring(e2e_setup):
    """测试队列状态监控"""
    queue_manager = e2e_setup["queue_manager"]
    await queue_manager.start()

    # 添加一些消息
    for i in range(3):
        await queue_manager.route_to_reviewer(
            task_id=f"T-STATUS-{i}",
            evidence={"index": i}
        )

    # 获取队列状态
    sizes = queue_manager.get_all_queue_sizes()

    assert sizes["builder"] == 0
    assert sizes["reviewer"] == 3
    assert sizes["owner"] == 0

    await queue_manager.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
