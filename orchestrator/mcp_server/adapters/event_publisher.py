"""
MCP Event Publisher Adapter
将同步操作转换为异步事件发布，实现真正的事件驱动
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from mcp_server.tools.registry import register_tool
from mcp.server import Server
from mcp.types import Tool, TextContent

# 添加项目路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import get_settings
from src.core.event_bus import get_event_bus
from src.models.events import BuildCompletedEvent, TestCompletedEvent, ReviewCompletedEvent
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


class MCPEventPublisher:
    """
    MCP 事件发布适配器
    将 MCP Server 的同步操作转换为异步事件发布
    """

    def __init__(self):
        """初始化事件发布器"""
        self._event_bus = get_event_bus()
        self._settings = get_settings()
        self._pending_events: dict[str, asyncio.Event] = {}

        # 从配置读取默认超时值（解决硬编码超时问题）
        self._default_timeout = float(self._settings.event_publish_timeout)

    async def publish_build_event(
        self,
        task_id: str,
        commit_hash: str,
        branch: str,
        diff_summary: Optional[str] = None,
        changed_files: Optional[list[str]] = None,
        wait_for_processing: bool = True,
        timeout: Optional[float] = None
    ) -> dict[str, Any]:
        """
        发布构建完成事件

        Args:
            task_id: 任务 ID
            commit_hash: Git 提交哈希
            branch: 分支名称
            diff_summary: Diff 摘要
            changed_files: 变更文件列表
            wait_for_processing: 是否等待事件处理完成
            timeout: 等待超时时间（秒）

        Returns:
            发布结果
        """
        # 使用配置的默认超时值（如果没有提供）
        actual_timeout = timeout if timeout is not None else self._default_timeout

        event = BuildCompletedEvent(
            task_id=task_id,
            commit_hash=commit_hash,
            branch=branch,
            diff_summary=diff_summary,
            changed_files=changed_files or [],
            timestamp=datetime.now()
        )

        # 创建等待事件
        if wait_for_processing:
            wait_key = f"build_{task_id}_{commit_hash[:8]}"
            self._pending_events[wait_key] = asyncio.Event()

        try:
            # 发布事件到 EventBus
            await self._event_bus.publish(event)
            logger.info(f"Published build event for task {task_id}, commit {commit_hash[:8]}")

            # 等待处理完成
            if wait_for_processing:
                try:
                    await asyncio.wait_for(
                        self._pending_events[wait_key].wait(),
                        timeout=actual_timeout
                    )
                    logger.info(f"Build event processing completed for task {task_id}")
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Build event processing timeout for task {task_id} "
                        f"after {actual_timeout}s"
                    )
                finally:
                    self._pending_events.pop(wait_key, None)

            return {
                "success": True,
                "task_id": task_id,
                "event_type": "build.completed",
                "commit_hash": commit_hash,
                "timestamp": event.timestamp.isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to publish build event: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id
            }

    async def publish_test_event(
        self,
        task_id: str,
        passed: bool,
        total_tests: int,
        failed_tests: int,
        test_summary: str,
        coverage_percent: Optional[float] = None,
        wait_for_processing: bool = True,
        timeout: Optional[float] = None
    ) -> dict[str, Any]:
        """
        发布测试完成事件

        Args:
            task_id: 任务 ID
            passed: 测试是否通过
            total_tests: 总测试数
            failed_tests: 失败测试数
            test_summary: 测试摘要
            coverage_percent: 代码覆盖率
            wait_for_processing: 是否等待事件处理完成
            timeout: 等待超时时间（秒）

        Returns:
            发布结果
        """
        # 使用配置的默认超时值（如果没有提供）
        actual_timeout = timeout if timeout is not None else self._default_timeout

        event = TestCompletedEvent(
            task_id=task_id,
            passed=passed,
            total_tests=total_tests,
            failed_tests=failed_tests,
            test_summary=test_summary,
            coverage_percent=coverage_percent,
            timestamp=datetime.now()
        )

        # 创建等待事件
        if wait_for_processing:
            wait_key = f"test_{task_id}_{datetime.now().timestamp()}"
            self._pending_events[wait_key] = asyncio.Event()

        try:
            # 发布事件到 EventBus
            await self._event_bus.publish(event)
            logger.info(f"Published test event for task {task_id}")

            # 等待处理完成
            if wait_for_processing:
                try:
                    await asyncio.wait_for(
                        self._pending_events[wait_key].wait(),
                        timeout=actual_timeout
                    )
                    logger.info(f"Test event processing completed for task {task_id}")
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Test event processing timeout for task {task_id} "
                        f"after {actual_timeout}s"
                    )
                finally:
                    self._pending_events.pop(wait_key, None)

            return {
                "success": True,
                "task_id": task_id,
                "event_type": "test.completed",
                "passed": passed,
                "timestamp": event.timestamp.isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to publish test event: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id
            }

    async def publish_review_event(
        self,
        task_id: str,
        reviewer_id: str,
        decision: str,
        findings_count: int,
        critical_issues: int,
        review_report_path: str,
        wait_for_processing: bool = True,
        timeout: Optional[float] = None
    ) -> dict[str, Any]:
        """
        发布审查完成事件

        Args:
            task_id: 任务 ID
            reviewer_id: 审查者 ID
            decision: 审查决策
            findings_count: 发现数量
            critical_issues: 严重问题数量
            review_report_path: 审查报告路径
            wait_for_processing: 是否等待事件处理完成
            timeout: 等待超时时间（秒）

        Returns:
            发布结果
        """
        # 使用配置的默认超时值（如果没有提供）
        actual_timeout = timeout if timeout is not None else self._default_timeout

        event = ReviewCompletedEvent(
            task_id=task_id,
            reviewer_id=reviewer_id,
            decision=decision,
            findings_count=findings_count,
            critical_issues=critical_issues,
            review_report_path=review_report_path,
            timestamp=datetime.now()
        )

        # 创建等待事件
        if wait_for_processing:
            wait_key = f"review_{task_id}_{reviewer_id}_{datetime.now().timestamp()}"
            self._pending_events[wait_key] = asyncio.Event()

        try:
            # 发布事件到 EventBus
            await self._event_bus.publish(event)
            logger.info(f"Published review event for task {task_id} by {reviewer_id}")

            # 等待处理完成
            if wait_for_processing:
                try:
                    await asyncio.wait_for(
                        self._pending_events[wait_key].wait(),
                        timeout=actual_timeout
                    )
                    logger.info(f"Review event processing completed for task {task_id}")
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Review event processing timeout for task {task_id} "
                        f"after {actual_timeout}s"
                    )
                finally:
                    self._pending_events.pop(wait_key, None)

            return {
                "success": True,
                "task_id": task_id,
                "event_type": "review.completed",
                "decision": decision,
                "timestamp": event.timestamp.isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to publish review event: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id
            }

    def mark_event_processed(self, wait_key: str) -> None:
        """
        标记事件已处理

        Args:
            wait_key: 等待键
        """
        if wait_key in self._pending_events:
            self._pending_events[wait_key].set()
            logger.debug(f"Marked event as processed: {wait_key}")


# 全局实例
_event_publisher: Optional[MCPEventPublisher] = None


def get_event_publisher() -> MCPEventPublisher:
    """
    获取全局事件发布器实例

    Returns:
        MCPEventPublisher 实例
    """
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = MCPEventPublisher()
    return _event_publisher


def register_event_publisher_tools(server: Server) -> None:
    """注册事件发布工具到 MCP 服务器"""

    publisher = get_event_publisher()

    async def handle_publish_build_event(arguments: dict[str, Any]) -> list[TextContent]:
        """处理发布构建事件"""
        try:
            result = await publisher.publish_build_event(
                task_id=arguments["task_id"],
                commit_hash=arguments["commit_hash"],
                branch=arguments["branch"],
                diff_summary=arguments.get("diff_summary"),
                changed_files=arguments.get("changed_files"),
                wait_for_processing=arguments.get("wait_for_processing", True),
                timeout=arguments.get("timeout")  # 不再有硬编码默认值，使用配置的默认值
            )

            return [TextContent(
                type="text",
                text=f"""Build event published successfully:
- Task: {result['task_id']}
- Commit: {result.get('commit_hash', 'N/A')}
- Timestamp: {result.get('timestamp', 'N/A')}
"""
            )]
        except Exception as e:
            logger.exception(f"Error in publish_build_event: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def handle_publish_test_event(arguments: dict[str, Any]) -> list[TextContent]:
        """处理发布测试事件"""
        try:
            result = await publisher.publish_test_event(
                task_id=arguments["task_id"],
                passed=arguments["passed"],
                total_tests=arguments["total_tests"],
                failed_tests=arguments["failed_tests"],
                test_summary=arguments["test_summary"],
                coverage_percent=arguments.get("coverage_percent"),
                wait_for_processing=arguments.get("wait_for_processing", True),
                timeout=arguments.get("timeout")  # 不再有硬编码默认值，使用配置的默认值
            )

            return [TextContent(
                type="text",
                text=f"""Test event published successfully:
- Task: {result['task_id']}
- Passed: {result.get('passed', 'N/A')}
- Timestamp: {result.get('timestamp', 'N/A')}
"""
            )]
        except Exception as e:
            logger.exception(f"Error in publish_test_event: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    # 注册工具
    register_tool(server, Tool(
        name="publish_build_event",
        description="Publish a build.completed event to the event bus",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID, e.g., T-102"
                },
                "commit_hash": {
                    "type": "string",
                    "description": "Git commit hash"
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name"
                },
                "diff_summary": {
                    "type": "string",
                    "description": "Diff summary (optional)"
                },
                "changed_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of changed files (optional)"
                },
                "wait_for_processing": {
                    "type": "boolean",
                    "description": "Wait for event processing to complete (default: true)"
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (default: uses config value, 300s = 5 minutes)"
                }
            },
            "required": ["task_id", "commit_hash", "branch"]
        }
    ), handle_publish_build_event)

    register_tool(server, Tool(
        name="publish_test_event",
        description="Publish a test.completed event to the event bus",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID, e.g., T-102"
                },
                "passed": {
                    "type": "boolean",
                    "description": "Whether tests passed"
                },
                "total_tests": {
                    "type": "integer",
                    "description": "Total number of tests"
                },
                "failed_tests": {
                    "type": "integer",
                    "description": "Number of failed tests"
                },
                "test_summary": {
                    "type": "string",
                    "description": "Test summary"
                },
                "coverage_percent": {
                    "type": "number",
                    "description": "Code coverage percentage (optional)"
                },
                "wait_for_processing": {
                    "type": "boolean",
                    "description": "Wait for event processing to complete (default: true)"
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (default: uses config value, 300s = 5 minutes)"
                }
            },
            "required": ["task_id", "passed", "total_tests", "failed_tests", "test_summary"]
        }
    ), handle_publish_test_event)

    logger.info("Registered event publisher tools")
