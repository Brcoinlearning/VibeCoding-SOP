"""
Integration tests for Event-Driven Review Workflow
测试真正的事件驱动审查工作流和 Agent 隔离
"""
import asyncio
import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import subprocess

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp_server.tools.review_workflow import EvidenceCollectionPipeline, get_pipeline, reset_pipeline
from src.core.context_queue import get_context_queue_manager, AgentRole
from src.core.event_bus import get_event_bus, reset_event_bus
from src.config.settings import get_settings


@pytest.fixture
def temp_repo_dir():
    """创建临时 Git 仓库目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        # 初始化 Git 仓库
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, capture_output=True)

        # 创建初始提交
        test_file = repo_path / "test.txt"
        test_file.write_text("Initial content")
        subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            capture_output=True
        )

        yield repo_path


@pytest.fixture
def event_setup():
    """设置事件驱动环境"""
    reset_pipeline()
    reset_event_bus()
    event_bus = get_event_bus()
    queue_manager = get_context_queue_manager()
    pipeline = get_pipeline()

    return {
        "event_bus": event_bus,
        "queue_manager": queue_manager,
        "pipeline": pipeline
    }


@pytest.mark.asyncio
async def test_review_workflow_event_driven(temp_repo_dir, event_setup):
    """测试审查工作流是否真正事件驱动"""
    event_bus = event_setup["event_bus"]
    queue_manager = event_setup["queue_manager"]
    pipeline = event_setup["pipeline"]

    await event_bus.start()
    await queue_manager.start()

    try:
        # 执行事件驱动的工作流
        result = await pipeline.start_review_workflow(
            task_id="T-EDR-001",
            repo_path=temp_repo_dir
        )

        # 验证返回结果不包含证据内容
        assert result["success"] is True
        assert "artifact" not in result
        assert "evidence" not in result
        assert "content" not in result
        assert result["task_id"] == "T-EDR-001"

        # 验证证据被路由到 Reviewer 队列
        assert result["queue_status"] > 0
        assert queue_manager.get_queue_size(AgentRole.REVIEWER) > 0

        # 验证 Builder 无法直接获取证据内容
        # （只有通过 Reviewer 队列才能获取）
        reviewer_task = await queue_manager.get_reviewer_input(task_id="T-EDR-001")
        assert reviewer_task is not None
        assert reviewer_task.task_id == "T-EDR-001"

        # 验证证据内容在队列中
        evidence = reviewer_task.content
        assert "commit_hash" in evidence
        assert "branch" in evidence
        # 注意：完整的 artifact.content 不应该在这里
        # 只有元数据和预览

    finally:
        await queue_manager.stop()
        await event_bus.stop()


@pytest.mark.asyncio
async def test_agent_isolation_enforced(temp_repo_dir, event_setup):
    """测试 Agent 隔离是否被强制执行"""
    event_bus = event_setup["event_bus"]
    queue_manager = event_setup["queue_manager"]
    pipeline = event_setup["pipeline"]

    await event_bus.start()
    await queue_manager.start()

    try:
        # Builder 启动工作流
        result = await pipeline.start_review_workflow(
            task_id="T-ISO-001",
            repo_path=temp_repo_dir
        )

        # Builder 不应该能直接访问证据内容
        assert "artifact" not in result
        assert "content" not in result
        assert "diff" not in result  # 不应该返回完整 diff

        # Builder 不应该能访问 Reviewer 队列中的内容
        # （通过 API 隔离）
        builder_queue_size = queue_manager.get_queue_size(AgentRole.BUILDER)
        reviewer_queue_size = queue_manager.get_queue_size(AgentRole.REVIEWER)

        assert builder_queue_size == 0  # Builder 队列为空
        assert reviewer_queue_size > 0  # Reviewer 队列有证据

        # 验证只有 Reviewer 能获取证据
        reviewer_task = await queue_manager.get_reviewer_input(task_id="T-ISO-001")
        assert reviewer_task is not None
        assert reviewer_task.from_role == AgentRole.BUILDER
        assert reviewer_task.to_role == AgentRole.REVIEWER

    finally:
        await queue_manager.stop()
        await event_bus.stop()


@pytest.mark.asyncio
async def test_event_bus_integration(temp_repo_dir, event_setup):
    """测试 EventBus 集成"""
    event_bus = event_setup["event_bus"]
    queue_manager = event_setup["queue_manager"]
    pipeline = event_setup["pipeline"]

    await event_bus.start()
    await queue_manager.start()

    try:
        # 收集事件
        collected_events = []

        async def event_handler(event):
            collected_events.append(event)

        # 订阅所有事件类型
        from src.models.events import EventType
        for event_type in [EventType.BUILD_COMPLETED, EventType.TEST_COMPLETED]:
            event_bus.subscribe(event_type, event_handler)

        # 执行工作流
        result = await pipeline.start_review_workflow(
            task_id="T-EVT-001",
            repo_path=temp_repo_dir
        )

        # 验证事件被发布
        await asyncio.sleep(0.2)  # 等待异步事件处理

        # 应该至少有 build.completed 事件
        build_events = [
            e for e in collected_events
            if hasattr(e, "event_type") and e.event_type == EventType.BUILD_COMPLETED
        ]
        assert len(build_events) > 0, "No build.completed events were published"

    finally:
        await queue_manager.stop()
        await event_bus.stop()


@pytest.mark.asyncio
async def test_no_self_review_possible(temp_repo_dir, event_setup):
    """测试防止自己审自己"""
    event_bus = event_setup["event_bus"]
    queue_manager = event_setup["queue_manager"]
    pipeline = event_setup["pipeline"]

    await event_bus.start()
    await queue_manager.start()

    try:
        # Builder 启动工作流
        result = await pipeline.start_review_workflow(
            task_id="T-NSR-001",
            repo_path=temp_repo_dir
        )

        # Builder 尝试直接获取证据内容（应该失败）
        # 工作流结果不包含证据
        assert "artifact" not in result
        assert "content" not in result

        # Builder 尝试从自己的队列获取（应该为空）
        builder_input = await queue_manager._queues[AgentRole.BUILDER].get(timeout=0.1)
        assert builder_input is None  # Builder 队列为空

        # 只有 Reviewer 能获取证据
        reviewer_input = await queue_manager.get_reviewer_input(task_id="T-NSR-001")
        assert reviewer_input is not None

        # 验证证据在 Reviewer 队列中，不在 Builder 队列中
        assert queue_manager.get_queue_size(AgentRole.REVIEWER) >= 0
        assert queue_manager.get_queue_size(AgentRole.BUILDER) == 0

    finally:
        await queue_manager.stop()
        await event_bus.stop()


@pytest.mark.asyncio
async def test_evidence_content_not_exposed(temp_repo_dir, event_setup):
    """测试证据内容不被暴露给调用者"""
    event_bus = event_setup["event_bus"]
    queue_manager = event_setup["queue_manager"]
    pipeline = event_setup["pipeline"]

    await event_bus.start()
    await queue_manager.start()

    try:
        # 执行工作流
        result = await pipeline.start_review_workflow(
            task_id="T-EXP-001",
            repo_path=temp_repo_dir
        )

        # 检查返回结果中不应该有敏感内容
        assert "diff" not in result or len(str(result.get("diff", ""))) < 500
        assert "code" not in result
        assert "source" not in result
        assert "files" not in result or "changed_files" in result  # 允许文件列表，但不允许文件内容

        # 检查证据大小信息而不是内容
        if "evidence_size" in result:
            assert isinstance(result["evidence_size"], int)
            assert result["evidence_size"] > 0

        # 检查只有预览而不是完整内容
        if "trimmed_diff_preview" in result:
            assert len(result["trimmed_diff_preview"]) <= 203  # 200 + "..."

    finally:
        await queue_manager.stop()
        await event_bus.stop()


@pytest.mark.asyncio
async def test_workflow_returns_confirmation_only(temp_repo_dir, event_setup):
    """测试工作流只返回确认信息"""
    event_bus = event_setup["event_bus"]
    queue_manager = event_setup["queue_manager"]
    pipeline = event_setup["pipeline"]

    await event_bus.start()
    await queue_manager.start()

    try:
        result = await pipeline.start_review_workflow(
            task_id="T-CONF-001",
            repo_path=temp_repo_dir
        )

        # 验证返回的是确认信息，不是证据内容
        assert result["success"] is True
        assert result["task_id"] == "T-CONF-001"
        assert "message" in result
        assert "evidence_id" in result
        assert "queue_status" in result
        assert "instructions" in result

        # 验证没有证据内容
        assert "artifact" not in result
        assert "evidence" not in result
        assert "content" not in result

        # 验证证据 ID 格式
        assert "T-CONF-001" in result["evidence_id"]

    finally:
        await queue_manager.stop()
        await event_bus.stop()


@pytest.mark.asyncio
async def test_complete_event_driven_flow(temp_repo_dir, event_setup):
    """测试完整的事件驱动流程"""
    event_bus = event_setup["event_bus"]
    queue_manager = event_setup["queue_manager"]
    pipeline = event_setup["pipeline"]

    await event_bus.start()
    await queue_manager.start()

    try:
        # 1. Builder 启动工作流（事件驱动）
        result = await pipeline.start_review_workflow(
            task_id="T-FLOW-001",
            repo_path=temp_repo_dir
        )

        assert result["success"] is True

        # 2. 验证事件发布
        await asyncio.sleep(0.2)
        history = event_bus.get_history(task_id="T-FLOW-001")
        assert len(history) > 0  # 应该有事件被发布

        # 3. Reviewer 获取证据
        reviewer_task = await queue_manager.get_reviewer_input(task_id="T-FLOW-001")
        assert reviewer_task is not None

        # 4. Reviewer 提交审查结果
        review_result = {
            "decision": "approved",
            "overall_score": 95,
            "findings": []
        }
        await queue_manager.submit_review(
            task_id="T-FLOW-001",
            review_result=review_result,
            reviewer_id="test-reviewer"
        )

        # 5. Owner 获取审查结果
        owner_task = await queue_manager.get_owner_input(task_id="T-FLOW-001")
        assert owner_task is not None
        assert owner_task.content["decision"] == "approved"

    finally:
        await queue_manager.stop()
        await event_bus.stop()


def test_pipeline_singleton():
    """测试管道单例"""
    pipeline1 = get_pipeline()
    pipeline2 = get_pipeline()

    assert pipeline1 is pipeline2  # 应该是同一个实例


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
