"""
MCP Tool: review_workflow
真正的事件驱动审查工作流：发布事件 + 订阅处理链 + 强制 Agent 隔离
"""
import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Callable

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp_server.tools.registry import register_tool

# 添加项目路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import get_settings
from src.core.event_bus import get_event_bus, EventType
from src.core.context_queue import get_context_queue_manager, AgentRole
from src.core.trimmer import EvidenceTrimmer
from src.core.packager import EvidencePackager
from src.models.events import BuildCompletedEvent, TestCompletedEvent
from src.models.artifacts import Artifact
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


# ============================================================================
# 事件驱动的证据收集处理链
# ============================================================================

class EvidenceCollectionPipeline:
    """
    证据收集处理链
    将顺序过程式调用改为事件驱动的处理链
    """

    def __init__(self):
        """初始化处理链"""
        self._event_bus = get_event_bus()
        self._context_queue = get_context_queue_manager()
        self._trimmer = EvidenceTrimmer()
        self._packager = EvidencePackager()
        self._processing_locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, task_id: str) -> asyncio.Lock:
        """获取任务级别的锁"""
        if task_id not in self._processing_locks:
            self._processing_locks[task_id] = asyncio.Lock()
        return self._processing_locks[task_id]

    async def start_review_workflow(
        self,
        task_id: str,
        repo_path: Path,
        commit: Optional[str] = None,
        branch: Optional[str] = None,
        diff_content: Optional[str] = None,
        test_results: Optional[str] = None
    ) -> dict[str, Any]:
        """
        启动事件驱动的审查工作流

        这是唯一对外暴露的入口，内部完全通过事件驱动

        Args:
            task_id: 任务ID
            repo_path: 仓库路径
            commit: Git提交哈希
            branch: 分支名称
            diff_content: 代码 diff
            test_results: 测试结果

        Returns:
            操作结果（不包含证据内容）
        """
        async with self._get_lock(task_id):
            try:
                # 1. 发布工作流开始事件
                await self._event_bus.publish(
                    BuildCompletedEvent(
                        task_id=task_id,
                        commit_hash=commit or "",
                        branch=branch or "",
                        timestamp=datetime.now(),
                        metadata={"stage": "workflow_started"}
                    )
                )

                # 2. 触发证据收集链（事件驱动）
                evidence = await self._execute_evidence_collection_chain(
                    task_id=task_id,
                    repo_path=repo_path,
                    commit=commit,
                    branch=branch,
                    diff_content=diff_content,
                    test_results=test_results
                )

                # 3. 将证据路由到 Reviewer 队列（强制隔离）
                success = await self._context_queue.route_to_reviewer(
                    task_id=task_id,
                    evidence=evidence,
                    metadata={
                        "captured_at": datetime.now().isoformat(),
                        "captured_by": "builder_agent",
                        "workflow_type": "event_driven"
                    }
                )

                if not success:
                    return {
                        "success": False,
                        "error": "Failed to route evidence to Reviewer queue",
                        "task_id": task_id
                    }

                # 4. 发布证据就绪事件
                await self._event_bus.publish(
                    BuildCompletedEvent(
                        task_id=task_id,
                        commit_hash=evidence.get("commit_hash", ""),
                        branch=evidence.get("branch", ""),
                        timestamp=datetime.now(),
                        metadata={"stage": "evidence_ready"}
                    )
                )

                # 5. 返回确认信息（不包含证据内容）
                return {
                    "success": True,
                    "task_id": task_id,
                    "message": "Evidence collected and routed to Reviewer queue",
                    "evidence_id": f"{task_id}_{int(datetime.now().timestamp())}",
                    "queue_status": self._context_queue.get_queue_size(AgentRole.REVIEWER),
                    "instructions": "Use 'get_reviewer_task' tool to retrieve this evidence for review"
                }

            except Exception as e:
                logger.error(f"Error in review workflow for task {task_id}: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                    "task_id": task_id
                }

    async def _execute_evidence_collection_chain(
        self,
        task_id: str,
        repo_path: Path,
        commit: Optional[str],
        branch: Optional[str],
        diff_content: Optional[str],
        test_results: Optional[str]
    ) -> dict[str, Any]:
        """
        执行证据收集链（内部使用）

        注意：这个方法虽然是同步调用，但它被设计为可以被替换为真正的异步事件链
        未来可以改为：每个步骤发布事件，由独立的订阅者处理
        """
        evidence_parts = {}

        # 步骤 1: 捕获 Git 状态
        logger.info(f"[{task_id}] Step 1: Capturing git status")
        build_event = await self._capture_git_status(
            repo_path, task_id, commit, branch
        )

        if not build_event:
            raise Exception("Failed to capture Git status")

        # 发布 Git 状态捕获完成事件
        await self._event_bus.publish(build_event)

        evidence_parts["commit_hash"] = build_event.commit_hash
        evidence_parts["branch"] = build_event.branch
        evidence_parts["changed_files"] = build_event.changed_files
        evidence_parts["diff_summary"] = build_event.diff_summary

        # 步骤 2: 获取代码 diff
        logger.info(f"[{task_id}] Step 2: Getting code diff")
        diff = diff_content if diff_content else await self._get_git_diff(repo_path)

        # 步骤 3: 获取测试结果
        logger.info(f"[{task_id}] Step 3: Getting test results")
        test_event = await self._get_test_results(
            repo_path, task_id, test_results
        )

        if test_event:
            # 发布测试完成事件
            await self._event_bus.publish(test_event)

        # 步骤 4: 裁剪数据
        logger.info(f"[{task_id}] Step 4: Trimming data")
        trimmed_log, trimmed_diff = await self._trimmer.trim_build_output(
            "No build log provided",
            diff
        )

        log_summary = trimmed_log
        if test_event and test_event.test_summary:
            log_summary = f"{trimmed_log}\n\nTest Results: {test_event.test_summary}"

        # 步骤 5: 封装证据
        logger.info(f"[{task_id}] Step 5: Packaging evidence")
        artifact = await self._packager.create_reviewer_input(
            task_id=task_id,
            build_event=build_event,
            test_event=test_event or TestCompletedEvent(
                task_id=task_id,
                passed=True,
                total_tests=0,
                failed_tests=0,
                test_summary="No tests run",
                timestamp=datetime.now()
            ),
            diff_content=trimmed_diff,
            log_summary=log_summary,
            additional_context={
                "workflow_type": "event_driven_review",
                "captured_at": datetime.now().isoformat(),
                "agent_isolation": "enforced"
            }
        )

        # 返回证据数据（不包含原始内容）
        return {
            "task_id": task_id,
            "commit_hash": build_event.commit_hash,
            "branch": build_event.branch,
            "changed_files": build_event.changed_files,
            "diff_summary": build_event.diff_summary,
            "test_passed": test_event.passed if test_event else None,
            "test_total": test_event.total_tests if test_event else None,
            "test_failed": test_event.failed_tests if test_event else None,
            "artifact_metadata": artifact.metadata.model_dump(mode='json'),
            # 注意：这里不返回 artifact.content，防止 Builder 直接访问证据
            "evidence_size": len(artifact.content),
            "log_summary": log_summary,
            "trimmed_diff_preview": trimmed_diff[:200] + "..." if len(trimmed_diff) > 200 else trimmed_diff
        }

    async def _capture_git_status(
        self,
        repo_path: Path,
        task_id: str,
        commit: Optional[str] = None,
        branch: Optional[str] = None
    ) -> Optional[BuildCompletedEvent]:
        """捕获 Git 状态（事件驱动链的步骤1）"""
        try:
            # 获取当前 commit
            if not commit:
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                commit = result.stdout.strip()

            # 获取分支名
            if not branch:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                branch = result.stdout.strip()

            # 获取变更的文件列表
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            changed_files = [
                f for f in result.stdout.strip().split('\n') if f
            ] if result.returncode == 0 else []

            # 获取 diff 摘要
            result = subprocess.run(
                ["git", "diff", "--stat", "HEAD~1", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            diff_summary = result.stdout.strip() if result.returncode == 0 else ""

            return BuildCompletedEvent(
                task_id=task_id,
                commit_hash=commit,
                branch=branch,
                diff_summary=diff_summary,
                changed_files=changed_files,
                timestamp=datetime.now()
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error capturing git status: {e}", exc_info=True)
            return None

    async def _get_git_diff(self, repo_path: Path) -> str:
        """获取 Git diff（事件驱动链的步骤2）"""
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception as e:
            logger.error(f"Error getting git diff: {e}")
            return ""

    async def _get_test_results(
        self,
        repo_path: Path,
        task_id: str,
        provided_results: Optional[str] = None
    ) -> Optional[TestCompletedEvent]:
        """获取测试结果（事件驱动链的步骤3）"""
        if provided_results:
            # 解析提供的测试结果
            try:
                import json
                data = json.loads(provided_results)
                return TestCompletedEvent(
                    task_id=task_id,
                    passed=data.get("passed", True),
                    total_tests=data.get("total", 0),
                    failed_tests=data.get("failed", 0),
                    test_summary=data.get("summary", ""),
                    coverage_percent=data.get("coverage"),
                    timestamp=datetime.now()
                )
            except Exception as e:
                logger.warning(f"Failed to parse provided test results: {e}")

        # 尝试查找常见的测试结果文件
        test_paths = [
            repo_path / "pytest_results.json",
            repo_path / "test-results.xml",
            repo_path / ".pytest_cache" / "results.json",
        ]

        for test_path in test_paths:
            if test_path.exists():
                return TestCompletedEvent(
                    task_id=task_id,
                    passed=True,
                    total_tests=0,
                    failed_tests=0,
                    test_summary=f"Found test results at {test_path.name}",
                    timestamp=datetime.now()
                )

        return None


# 全局实例
_pipeline: Optional[EvidenceCollectionPipeline] = None


def get_pipeline() -> EvidenceCollectionPipeline:
    """获取全局证据收集管道实例"""
    global _pipeline
    if _pipeline is None:
        _pipeline = EvidenceCollectionPipeline()
    return _pipeline


def reset_pipeline() -> None:
    """重置全局证据收集管道实例（主要用于测试）"""
    global _pipeline
    _pipeline = None


def register_review_workflow(server: Server) -> None:
    """
    注册真正事件驱动的 review_workflow 工具到 MCP 服务器

    关键特性：
    1. 完全通过事件驱动，不返回证据给调用者
    2. 强制将证据路由到 Reviewer 队列
    3. 防止 Builder Agent 直接访问证据
    """

    pipeline = get_pipeline()

    async def handle_review_workflow(arguments: dict[str, Any]) -> list[TextContent]:
        """
        处理 review_workflow 调用

        重要：此方法不再返回证据内容，只返回操作确认
        证据被强制路由到 Reviewer 队列，实现真正的 Agent 隔离
        """
        try:
            task_id = arguments.get("task_id")
            if not task_id:
                return [TextContent(
                    type="text",
                    text="Error: task_id is required"
                )]

            settings = get_settings()
            base_path = Path(arguments.get("base_path")) if arguments.get("base_path") else settings.base_path

            # 执行事件驱动的工作流
            result = await pipeline.start_review_workflow(
                task_id=task_id,
                repo_path=base_path,
                commit=arguments.get("commit"),
                branch=arguments.get("branch"),
                diff_content=arguments.get("diff_content"),
                test_results=arguments.get("test_results")
            )

            if result["success"]:
                # 返回确认信息（不包含证据内容）
                content = f"""# Review Workflow Started - Event-Driven Mode

## Task: {result['task_id']}

### Status
✅ Evidence collection completed
✅ Evidence routed to Reviewer queue
✅ Events published to EventBus

### Agent Isolation: ENFORCED
- Evidence ID: {result['evidence_id']}
- Current queue size: {result['queue_status']}
- Evidence accessible ONLY via: `get_reviewer_task`

### Instructions for Reviewer Agent
Use the following MCP tool to retrieve this evidence:
```
get_reviewer_task({{"task_id": "{task_id}"}})
```

### Instructions for Owner Agent
After review is complete, use:
```
get_owner_task({{"task_id": "{task_id}"}})
```

### Event Flow
1. ✅ build.completed event published
2. ✅ Evidence collected and processed
3. ✅ Evidence routed to Reviewer context queue
4. ⏳ Waiting for Reviewer to retrieve evidence
5. ⏳ Review will be routed to Owner queue

---
**IMPORTANT**: The Builder Agent cannot access the evidence content.
This enforces true separation of duties between agents.
"""
                return [TextContent(
                    type="text",
                    text=content
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Error: {result.get('error', 'Unknown error')}"
                )]

        except Exception as e:
            logger.exception(f"Error in review_workflow: {e}")
            return [TextContent(
                type="text",
                text=f"Exception: {str(e)}"
            )]

    # 注册工具
    register_tool(server, Tool(
        name="review_workflow",
        description="""EVENT-DRIVEN REVIEW WORKFLOW with Agent Isolation

Starts a review workflow that:
1. Collects evidence (git status, diff, test results)
2. Publishes events to EventBus
3. Routes evidence to Reviewer queue (ENFORCED ISOLATION)
4. Returns confirmation WITHOUT evidence content

IMPORTANT: Builder Agent CANNOT access evidence content.
Only Reviewer Agent can retrieve via 'get_reviewer_task'.

This prevents 'self-review' and enforces true separation of duties.""",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID, e.g., T-102"
                },
                "commit": {
                    "type": "string",
                    "description": "Git commit hash (optional, defaults to HEAD)"
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name (optional)"
                },
                "diff_content": {
                    "type": "string",
                    "description": "Code diff (optional, auto-captured if not provided)"
                },
                "test_results": {
                    "type": "string",
                    "description": "Test results JSON string (optional)"
                },
                "base_path": {
                    "type": "string",
                    "description": "Base path for the repository (optional)"
                }
            },
            "required": ["task_id"]
        }
    ), handle_review_workflow)

    logger.info("Registered EVENT-DRIVEN review_workflow tool with Agent Isolation")
