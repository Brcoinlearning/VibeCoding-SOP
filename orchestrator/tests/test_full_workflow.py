"""
端到端测试
验证完整的编排工作流程
"""

import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

import pytest

from src.config.settings import get_settings, reset_settings
from src.core.event_bus import EventBus, reset_event_bus
from src.core.router import ArtifactRouter
from src.core.packager import EvidencePackager, ReviewOutputPackager, GoNoGoPackager
from src.core.injector import ReviewerInjector
from src.models.events import BuildCompletedEvent, TestCompletedEvent, EventType
from src.models.artifacts import Artifact, ArtifactType, FrontmatterMetadata
from src.models.review import ReviewReport, ReviewDecision, Finding, SeverityLevel


@pytest.fixture
def temp_dir(tmp_path):
    """临时目录 fixture"""
    reset_settings()
    settings = get_settings(base_path=tmp_path)
    settings.ensure_directories()
    return tmp_path


@pytest.fixture
def event_bus():
    """事件总线 fixture"""
    reset_event_bus()
    bus = get_event_bus()
    return bus


@pytest.fixture
def sample_build_event():
    """示例构建事件"""
    return BuildCompletedEvent(
        task_id="T-001",
        commit_hash="abc123def456",
        branch="main",
        diff_summary="3 files changed, 15 insertions(+), 5 deletions(-)",
        changed_files=["src/main.py", "tests/test_main.py"]
    )


@pytest.fixture
def sample_test_event():
    """示例测试事件"""
    return TestCompletedEvent(
        task_id="T-001",
        passed=True,
        total_tests=42,
        failed_tests=0,
        test_summary="All tests passed",
        coverage_percent=85.5
    )


@pytest.mark.asyncio
async def test_full_review_workflow(temp_dir, sample_build_event, sample_test_event):
    """
    测试完整的审查工作流程：
    1. 创建证据
    2. 裁剪数据
    3. 封装输入
    4. 模拟审查
    5. 路由产物
    """
    settings = get_settings()

    # 1. 创建证据包
    packager = EvidencePackager()
    diff_content = """diff --git a/src/main.py b/src/main.py
index 123..456 789
--- a/src/main.py
+++ b/src/main.py
@@ -1,5 +1,10 @@
 def hello():
+    print("Hello")
     return "world"
+
+def goodbye():
+    return "farewell"
"""

    log_summary = """Build completed successfully
Warning: Unused import in module 'utils'
Total build time: 2.3s"""

    artifact = await packager.create_reviewer_input(
        task_id="T-001",
        build_event=sample_build_event,
        test_event=sample_test_event,
        diff_content=diff_content,
        log_summary=log_summary
    )

    assert artifact.metadata.type == ArtifactType.EXECUTION_EVIDENCE
    assert artifact.metadata.task_id == "T-001"
    assert "Reviewer Input for Task: T-001" in artifact.content

    # 2. 模拟审查
    mock_review_data = {
        "task_id": "T-001",
        "reviewer_id": "test-reviewer",
        "review_date": datetime.now().isoformat(),
        "decision": "approved",
        "overall_score": 85,
        "findings": [
            {
                "id": "F-001",
                "severity": "low",
                "category": "code-quality",
                "title": "Unused import",
                "description": "Module 'utils' imports are unused",
                "evidence": "import utils",
                "location": "src/main.py:1",
                "suggested_fix": "Remove unused import"
            }
        ],
        "files_reviewed": ["src/main.py"],
        "notes": "Overall good code quality"
    }

    review_report = ReviewReport(**mock_review_data)
    assert review_report.can_proceed()

    # 3. 封装审查报告
    output_packager = ReviewOutputPackager()
    report_artifact = await output_packager.package_review_output(
        task_id="T-001",
        reviewer_id="test-reviewer",
        review_content=json.dumps(mock_review_data)
    )

    assert report_artifact.metadata.type == ArtifactType.REVIEW_REPORT

    # 4. 路由产物
    router = ArtifactRouter()

    # 路由证据
    routed_evidence = await router.route(artifact)
    assert routed_evidence.full_path.exists()
    assert "30-build" in str(routed_evidence.full_path)

    # 路由报告
    routed_report = await router.route(report_artifact)
    assert routed_report.full_path.exists()
    assert "40-review" in str(routed_report.full_path)

    # 5. 验证文件内容
    content = routed_report.full_path.read_text(encoding='utf-8')
    assert "---" in content
    assert "type: review_report" in content
    assert "task_id: T-001" in content


@pytest.mark.asyncio
async def test_go_nogo_workflow(temp_dir):
    """
    测试 Go/No-Go 工作流程
    """
    packager = GoNoGoPackager()
    router = ArtifactRouter()

    # 创建 Go 记录
    go_artifact = await packager.create_go_nogo_record(
        task_id="T-001",
        decision_maker="Owner",
        decision="go",
        review_summary="Review passed with minor findings",
        reasoning="Code quality is acceptable. Minor findings will be addressed in next sprint.",
        risks_accepted=["Unused import warning"],
        conditions=["Address unused import in next PR"]
    )

    # 路由产物
    routed = await router.route(go_artifact)

    assert routed.full_path.exists()
    assert "50-release" in str(routed.full_path)
    assert go_artifact.metadata.status == "approved"

    # 验证内容
    content = routed.full_path.read_text(encoding='utf-8')
    assert "✅ GO" in content
    assert "Owner" in content


@pytest.mark.asyncio
async def test_event_driven_workflow(temp_dir, event_bus):
    """
    测试事件驱动工作流程
    """
    received_events = []

    async def handler(event):
        received_events.append(event)

    # 订阅事件
    event_bus.subscribe(EventType.BUILD_COMPLETED, handler)
    event_bus.subscribe(EventType.TEST_COMPLETED, handler)

    await event_bus.start()

    try:
        # 发布事件
        build_event = BuildCompletedEvent(
            task_id="T-001",
            commit_hash="abc123",
            branch="main"
        )
        test_event = TestCompletedEvent(
            task_id="T-001",
            passed=True,
            total_tests=10,
            failed_tests=0,
            test_summary="OK"
        )

        await event_bus.publish(build_event)
        await event_bus.publish(test_event)

        # 等待处理
        await asyncio.sleep(0.5)

        # 验证事件被接收
        assert len(received_events) == 2
        assert all(isinstance(e, (BuildCompletedEvent, TestCompletedEvent)) for e in received_events)

    finally:
        await event_bus.stop()


@pytest.mark.asyncio
async def test_rollback_scenario(temp_dir, sample_build_event, sample_test_event):
    """
    测试回退场景
    """
    from src.utils.validators import RollbackValidator
    from datetime import timedelta

    validator = RollbackValidator()

    # 测试陈旧证据
    old_timestamp = datetime.now() - timedelta(hours=2)
    stale_evidence = {
        "timestamp": old_timestamp,
        "build_info": sample_build_event.dict(),
        "test_info": sample_test_event.dict(),
        "diff_content": "some diff",
        "log_summary": "some log"
    }

    should_rollback, reason = await validator.should_rollback(stale_evidence)
    assert should_rollback
    assert "stale" in reason.lower()

    # 测试缺失输入
    incomplete_evidence = {
        "timestamp": datetime.now(),
        "build_info": sample_build_event.dict(),
        # 缺少其他必需字段
    }

    should_rollback, reason = await validator.should_rollback(incomplete_evidence)
    assert should_rollback
    assert "missing" in reason.lower()


@pytest.mark.asyncio
async def test_filesystem_injection(temp_dir):
    """
    测试文件系统注入方式
    """
    injector = ReviewerInjector()
    settings = get_settings()

    # 创建测试产物
    artifact = Artifact(
        metadata=FrontmatterMetadata(
            type=ArtifactType.EXECUTION_EVIDENCE,
            task_id="T-001",
            stage="review_preparation",
            status="ready",
            created_at=datetime.now()
        ),
        content="Test review input"
    )

    # 创建模拟响应
    request_dir = settings.workspace_path / "review_requests" / "T-001"
    request_dir.mkdir(parents=True, exist_ok=True)

    response_file = request_dir / "response.json"

    # 在后台创建响应文件
    async def create_delayed_response():
        await asyncio.sleep(0.5)
        response_data = {
            "task_id": "T-001",
            "reviewer_id": "file-system-reviewer",
            "review_date": datetime.now().isoformat(),
            "decision": "approved",
            "overall_score": 90,
            "findings": [],
            "files_reviewed": []
        }
        response_file.write_text(json.dumps(response_data))

    # 并发执行注入和响应创建
    injection_task = asyncio.create_task(injector.inject_to_reviewer(artifact))
    response_task = asyncio.create_task(create_delayed_response())

    results = await asyncio.gather(injection_task, response_task)
    review_report = results[0]

    assert review_report is not None
    assert review_report.decision == ReviewDecision.APPROVED
    assert review_report.overall_score == 90


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
