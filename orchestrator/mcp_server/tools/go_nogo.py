"""
MCP Tool: create_go_nogo
创建 Go/No-Go 裁决记录（唯一的权威放行入口）
"""
import logging
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp_server.tools.registry import register_tool

# 添加项目路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import get_settings
from src.core.packager import GoNoGoPackager
from src.core.router import ArtifactRouter
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


async def execute_create_go_nogo(
    task_id: str,
    decision: str,
    reasoning: str,
    review_summary: str = "",
    decision_maker: str = "Owner",
    risks_accepted: list[str] | None = None,
    conditions: list[str] | None = None
) -> dict[str, Any]:
    """
    创建 Go/No-Go 裁决记录

    Args:
        task_id: 任务ID
        decision: 决策 (go/no-go)
        reasoning: 决策理由
        review_summary: 审查摘要（可选）
        decision_maker: 决策者（默认为"Owner"）
        risks_accepted: 接受的风险列表
        conditions: 放行条件列表

    Returns:
        包含创建结果的字典
    """
    try:
        settings = get_settings()

        # 验证决策值
        if decision not in ["go", "no-go"]:
            return {
                "success": False,
                "error": f"Invalid decision: {decision}. Must be 'go' or 'no-go'",
                "task_id": task_id
            }

        # 验证必填字段
        if not reasoning or not reasoning.strip():
            return {
                "success": False,
                "error": "Reasoning is required for Go/No-Go decision",
                "task_id": task_id
            }

        # 创建 Go/No-Go 记录
        packager = GoNoGoPackager()
        artifact = await packager.create_go_nogo_record(
            task_id=task_id,
            decision_maker=decision_maker,
            decision=decision,
            review_summary=review_summary or "No review summary provided",
            reasoning=reasoning,
            risks_accepted=risks_accepted or [],
            conditions=conditions or []
        )

        # 自动路由到 release 目录
        router = ArtifactRouter()
        routed = await router.route(artifact)

        logger.info(f"Created Go/No-Go record for task {task_id}: {decision}")

        return {
            "success": True,
            "task_id": task_id,
            "decision": decision,
            "target_path": str(routed.full_path),
            "relative_path": str(routed.full_path.relative_to(settings.artifacts_path)),
            "decision_maker": decision_maker,
            "timestamp": artifact.metadata.created_at.isoformat()
        }

    except Exception as e:
        logger.exception(f"Error creating Go/No-Go record: {e}")
        return {
            "success": False,
            "error": str(e),
            "task_id": task_id
        }


def register_create_go_nogo(server: Server) -> None:
    """注册 create_go_nogo 工具到 MCP 服务器"""

    async def handle_create_go_nogo(arguments: dict[str, Any]) -> list[TextContent]:
        """处理 create_go_nogo 调用"""
        try:
            result = await execute_create_go_nogo(
                task_id=arguments.get("task_id"),
                decision=arguments.get("decision"),
                reasoning=arguments.get("reasoning"),
                review_summary=arguments.get("review_summary", ""),
                decision_maker=arguments.get("decision_maker", "Owner"),
                risks_accepted=arguments.get("risks_accepted"),
                conditions=arguments.get("conditions")
            )

            if result["success"]:
                emoji = "✅ GO" if result["decision"] == "go" else "❌ NO-GO"
                response = f"""# Go/No-Go Decision Created

## Task: {result['task_id']}

### Decision: {emoji}

### Decision Details
- **Decision Maker**: {result['decision_maker']}
- **Timestamp**: {result['timestamp']}
- **Reasoning**: {arguments.get('reasoning', 'N/A')[:100]}...

### Record Location
- **Path**: `{result['target_path']}`
- **Relative**: `{result['relative_path']}`

This decision is final and binding. The record has been routed to the release directory.
"""

                # 添加风险和条件信息
                if arguments.get("risks_accepted"):
                    response += "\n\n### Risks Accepted\n"
                    for risk in arguments["risks_accepted"]:
                        response += f"- {risk}\n"

                if arguments.get("conditions"):
                    response += "\n### Conditions for Release\n"
                    for condition in arguments["conditions"]:
                        response += f"- [ ] {condition}\n"

                return [TextContent(
                    type="text",
                    text=response
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Error: {result.get('error', 'Unknown error')}"
                )]

        except Exception as e:
            logger.exception(f"Error in create_go_nogo: {e}")
            return [TextContent(
                type="text",
                text=f"Exception: {str(e)}"
            )]

    # 注册工具
    register_tool(server, Tool(
        name="create_go_nogo",
        description="Create Go/No-Go decision record - the authoritative release gateway. Routes decision to release directory.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID (e.g., T-102)"
                },
                "decision": {
                    "type": "string",
                    "enum": ["go", "no-go"],
                    "description": "Decision: go (approve) or no-go (reject)"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Detailed reasoning for the decision (required)"
                },
                "review_summary": {
                    "type": "string",
                    "description": "Summary of the review that led to this decision (optional)"
                },
                "decision_maker": {
                    "type": "string",
                    "description": "Name/ID of the decision maker (optional, default: 'Owner')"
                },
                "risks_accepted": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of risks accepted with this decision (optional)"
                },
                "conditions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of conditions for release (optional)"
                }
            },
            "required": ["task_id", "decision", "reasoning"]
        }
    ), handle_create_go_nogo)

    logger.info("Registered create_go_nogo tool")
