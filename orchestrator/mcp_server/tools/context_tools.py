"""
Context Queue Tools
支持多 Agent 隔离通信的 MCP 工具
"""
import logging
import json
from typing import Any, Optional
from datetime import datetime

from mcp.server import Server
from mcp.types import Tool, TextContent

from mcp_server.tools.registry import register_tool

# 添加项目路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.context_queue import (
    get_context_queue_manager,
    AgentRole,
    ContextMessage
)
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


def register_context_tools(server: Server) -> None:
    """注册上下文队列工具到 MCP 服务器"""

    manager = get_context_queue_manager()

    async def handle_get_reviewer_task(arguments: dict[str, Any]) -> list[TextContent]:
        """Reviewer Agent 获取待审查任务"""
        try:
            task_id = arguments.get("task_id")
            timeout = arguments.get("timeout")

            message = await manager.get_reviewer_input(
                task_id=task_id,
                timeout=timeout
            )

            if not message:
                return [TextContent(
                    type="text",
                    text="No review task available in the queue"
                )]

            # 格式化任务信息
            evidence = message.content
            response = f"""# Review Task Available

## Task Information
- **Task ID**: {message.task_id}
- **From**: {message.from_role.value}
- **Message Type**: {message.message_type}
- **Timestamp**: {message.timestamp.isoformat()}

## Evidence to Review

### Metadata
```json
{json.dumps(evidence.get('metadata', {}), indent=2)}
```

### Content
{evidence.get('content', 'No content provided')}

---

Use `submit_review` tool to submit your review results.
"""
            return [TextContent(type="text", text=response)]

        except Exception as e:
            logger.exception(f"Error in get_reviewer_task: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def handle_submit_review(arguments: dict[str, Any]) -> list[TextContent]:
        """Reviewer Agent 提交审查结果"""
        try:
            task_id = arguments["task_id"]
            review_result = arguments["review_result"]
            reviewer_id = arguments.get("reviewer_id", "unknown")

            success = await manager.submit_review(
                task_id=task_id,
                review_result=review_result,
                reviewer_id=reviewer_id
            )

            if success:
                return [TextContent(
                    type="text",
                    text=f"""Review submitted successfully:
- Task: {task_id}
- Reviewer: {reviewer_id}
- Decision: {review_result.get('decision', 'N/A')}
- Timestamp: {datetime.now().isoformat()}

The review result has been routed to the Owner context queue.
"""
                )]
            else:
                return [TextContent(
                    type="text",
                    text="Failed to submit review. The Owner queue might be full."
                )]

        except Exception as e:
            logger.exception(f"Error in submit_review: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def handle_get_owner_task(arguments: dict[str, Any]) -> list[TextContent]:
        """Owner Agent 获取待处理的审查结果"""
        try:
            task_id = arguments.get("task_id")
            timeout = arguments.get("timeout")

            message = await manager.get_owner_input(
                task_id=task_id,
                timeout=timeout
            )

            if not message:
                return [TextContent(
                    type="text",
                    text="No review result available in the queue"
                )]

            # 格式化审查结果
            review_result = message.content
            response = f"""# Review Result Available

## Task Information
- **Task ID**: {message.task_id}
- **From**: {message.from_role.value}
- **Reviewer**: {message.metadata.get('reviewer_id', 'Unknown')}
- **Timestamp**: {message.timestamp.isoformat()}

## Review Result

```json
{json.dumps(review_result, indent=2)}
```

---

Use this information to make your Go/No-Go decision.
"""
            return [TextContent(type="text", text=response)]

        except Exception as e:
            logger.exception(f"Error in get_owner_task: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def handle_get_queue_status(arguments: dict[str, Any]) -> list[TextContent]:
        """获取所有队列的状态"""
        try:
            sizes = manager.get_all_queue_sizes()

            response = "# Context Queue Status\n\n"
            response += "## Queue Sizes\n\n"
            response += "| Role | Size |\n"
            response += "|------|------|\n"

            for role, size in sizes.items():
                status_icon = "🟢" if size < 50 else "🟡" if size < 80 else "🔴"
                response += f"| {status_icon} {role.capitalize()} | {size} |\n"

            response += f"\n**Timestamp**: {datetime.now().isoformat()}"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            logger.exception(f"Error in get_queue_status: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def handle_route_evidence(arguments: dict[str, Any]) -> list[TextContent]:
        """将证据路由到 Reviewer 上下文"""
        try:
            task_id = arguments["task_id"]
            evidence = arguments["evidence"]
            metadata = arguments.get("metadata")

            success = await manager.route_to_reviewer(
                task_id=task_id,
                evidence=evidence,
                metadata=metadata
            )

            if success:
                return [TextContent(
                    type="text",
                    text=f"""Evidence routed successfully:
- Task: {task_id}
- To: Reviewer context queue
- Timestamp: {datetime.now().isoformat()}

The Reviewer Agent can now retrieve this evidence using `get_reviewer_task`.
"""
                )]
            else:
                return [TextContent(
                    type="text",
                    text="Failed to route evidence. The Reviewer queue might be full."
                )]

        except Exception as e:
            logger.exception(f"Error in route_evidence: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def handle_route_notification(arguments: dict[str, Any]) -> list[TextContent]:
        """路由通知消息"""
        try:
            task_id = arguments["task_id"]
            notification = arguments["notification"]
            to_role = arguments["to_role"]
            from_role = arguments.get("from_role")

            # 验证角色
            try:
                target_role = AgentRole(to_role)
                source_role = AgentRole(from_role) if from_role else None
            except ValueError:
                return [TextContent(
                    type="text",
                    text=f"Error: Invalid role. Must be one of: {', '.join([r.value for r in AgentRole])}"
                )]

            success = await manager.route_notification(
                task_id=task_id,
                notification=notification,
                to_role=target_role,
                from_role=source_role
            )

            if success:
                return [TextContent(
                    type="text",
                    text=f"""Notification routed successfully:
- Task: {task_id}
- From: {source_role.value if source_role else 'System'}
- To: {target_role.value}
- Timestamp: {datetime.now().isoformat()}
"""
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Failed to route notification. The {target_role.value} queue might be full."
                )]

        except Exception as e:
            logger.exception(f"Error in route_notification: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    # 注册所有工具
    register_tool(server, Tool(
        name="get_reviewer_task",
        description="Get the next review task from the queue (Reviewer Agent)",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Filter by task ID (optional)"
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (optional)"
                }
            }
        }
    ), handle_get_reviewer_task)

    register_tool(server, Tool(
        name="submit_review",
        description="Submit review results to the Owner context queue (Reviewer Agent)",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID"
                },
                "review_result": {
                    "type": "object",
                    "description": "Review result data"
                },
                "reviewer_id": {
                    "type": "string",
                    "description": "Reviewer ID (optional)"
                }
            },
            "required": ["task_id", "review_result"]
        }
    ), handle_submit_review)

    register_tool(server, Tool(
        name="get_owner_task",
        description="Get the next review result from the queue (Owner Agent)",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Filter by task ID (optional)"
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (optional)"
                }
            }
        }
    ), handle_get_owner_task)

    register_tool(server, Tool(
        name="get_queue_status",
        description="Get the status of all context queues",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ), handle_get_queue_status)

    register_tool(server, Tool(
        name="route_evidence",
        description="Route evidence to the Reviewer context queue",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID"
                },
                "evidence": {
                    "type": "object",
                    "description": "Evidence data to route"
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata (optional)"
                }
            },
            "required": ["task_id", "evidence"]
        }
    ), handle_route_evidence)

    register_tool(server, Tool(
        name="route_notification",
        description="Route a notification to a specific agent's context queue",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID"
                },
                "notification": {
                    "type": "object",
                    "description": "Notification data"
                },
                "to_role": {
                    "type": "string",
                    "enum": ["builder", "reviewer", "owner"],
                    "description": "Target agent role"
                },
                "from_role": {
                    "type": "string",
                    "enum": ["builder", "reviewer", "owner"],
                    "description": "Source agent role (optional)"
                }
            },
            "required": ["task_id", "notification", "to_role"]
        }
    ), handle_route_notification)

    logger.info("Registered context queue tools")
