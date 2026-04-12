"""
MCP Tool: get_artifacts_summary
查询产物统计摘要，支持按类型、状态、任务筛选
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
from src.core.router import RouteSummary
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


async def execute_get_summary(
    artifact_type: str | None = None,
    status: str | None = None,
    task_id: str | None = None,
    limit: int = 20
) -> dict[str, Any]:
    """
    获取产物统计摘要

    Args:
        artifact_type: 产物类型筛选（可选）
        status: 状态筛选（可选）
        task_id: 任务ID筛选（可选）
        limit: 返回数量限制（默认20）

    Returns:
        包含摘要数据的字典
    """
    try:
        settings = get_settings()

        # 生成摘要
        summary_generator = RouteSummary()
        full_summary = await summary_generator.generate_summary()

        # 应用筛选条件
        filtered_summary = _apply_filters(
            full_summary,
            artifact_type=artifact_type,
            status=status,
            task_id=task_id
        )

        # 限制数量
        if limit and len(filtered_summary.get("latest_artifacts", [])) > limit:
            filtered_summary["latest_artifacts"] = filtered_summary["latest_artifacts"][:limit]

        logger.info(f"Generated artifacts summary with filters: type={artifact_type}, status={status}, task={task_id}")

        return {
            "success": True,
            "summary": filtered_summary,
            "filters_applied": {
                "artifact_type": artifact_type,
                "status": status,
                "task_id": task_id,
                "limit": limit
            }
        }

    except Exception as e:
        logger.exception(f"Error generating summary: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def _apply_filters(
    summary: dict[str, Any],
    artifact_type: str | None = None,
    status: str | None = None,
    task_id: str | None = None
) -> dict[str, Any]:
    """应用筛选条件"""
    filtered = {
        "total_artifacts": 0,
        "by_type": {},
        "by_status": {},
        "by_task": {},
        "latest_artifacts": []
    }

    # 筛选产物列表
    artifacts = summary.get("latest_artifacts", [])

    if artifact_type:
        artifacts = [a for a in artifacts if a["type"] == artifact_type]
    if status:
        artifacts = [a for a in artifacts if _get_artifact_status(a, summary) == status]
    if task_id:
        artifacts = [a for a in artifacts if a["task_id"] == task_id]

    filtered["latest_artifacts"] = artifacts
    filtered["total_artifacts"] = len(artifacts)

    # 重新计算统计
    for artifact in artifacts:
        # 按类型统计
        atype = artifact["type"]
        filtered["by_type"][atype] = filtered["by_type"].get(atype, 0) + 1

        # 按任务统计
        tid = artifact["task_id"]
        filtered["by_task"][tid] = filtered["by_task"].get(tid, 0) + 1

    # 从原始摘要中复制状态统计（如果有）
    if status:
        # 如果按状态筛选，只显示该状态
        filtered["by_status"][status] = len(artifacts)
    else:
        filtered["by_status"] = summary.get("by_status", {})

    return filtered


def _get_artifact_status(artifact: dict, summary: dict) -> str | None:
    """从摘要中获取产物状态（简化版本）"""
    # 这里简化处理，实际应从文件中读取
    # 由于摘要中没有状态信息，我们假设为未知
    return None


def register_get_summary(server: Server) -> None:
    """注册 get_artifacts_summary 工具到 MCP 服务器"""

    async def handle_get_summary(arguments: dict[str, Any]) -> list[TextContent]:
        """处理 get_artifacts_summary 调用"""
        try:
            result = await execute_get_summary(
                artifact_type=arguments.get("artifact_type"),
                status=arguments.get("status"),
                task_id=arguments.get("task_id"),
                limit=arguments.get("limit", 20)
            )

            if result["success"]:
                summary = result["summary"]
                filters = result["filters_applied"]

                # 格式化为 Markdown
                response = f"""# Artifacts Summary

**Total Artifacts**: {summary['total_artifacts']}

"""

                # 添加筛选信息
                active_filters = [f"{k}={v}" for k, v in filters.items() if v and k != "limit"]
                if active_filters:
                    response += f"**Filters Applied**: {', '.join(active_filters)}\n\n"

                # 按类型统计
                if summary["by_type"]:
                    response += "## By Type\n\n"
                    for atype, count in summary["by_type"].items():
                        response += f"- **{atype}**: {count}\n"
                    response += "\n"

                # 按状态统计
                if summary["by_status"]:
                    response += "## By Status\n\n"
                    emoji_map = {"approved": "✅", "rejected": "❌", "ready": "🟡", "draft": "📝"}
                    for status, count in summary["by_status"].items():
                        emoji = emoji_map.get(status, "📄")
                        response += f"- {emoji} **{status}**: {count}\n"
                    response += "\n"

                # 按任务统计（最多10个）
                if summary["by_task"]:
                    response += "## By Task (Top 10)\n\n"
                    sorted_tasks = sorted(summary["by_task"].items(), key=lambda x: x[1], reverse=True)[:10]
                    for task_id, count in sorted_tasks:
                        response += f"- **{task_id}**: {count} artifacts\n"
                    response += "\n"

                # 最新产物
                if summary["latest_artifacts"]:
                    response += f"## Latest Artifacts (showing {len(summary['latest_artifacts'])})\n\n"
                    for artifact in summary["latest_artifacts"][:10]:
                        response += f"- [{artifact['created_at']}] {artifact['type']} - {artifact['task_id']}\n"

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
            logger.exception(f"Error in get_artifacts_summary: {e}")
            return [TextContent(
                type="text",
                text=f"Exception: {str(e)}"
            )]

    # 注册工具
    register_tool(server, Tool(
        name="get_artifacts_summary",
        description="Query artifact statistics summary with filtering by type, status, and task",
        inputSchema={
            "type": "object",
            "properties": {
                "artifact_type": {
                    "type": "string",
                    "enum": ["requirement_contract", "execution_evidence", "review_report", "go_no_go_record"],
                    "description": "Filter by artifact type (optional)"
                },
                "status": {
                    "type": "string",
                    "enum": ["draft", "ready", "approved", "rejected"],
                    "description": "Filter by status (optional)"
                },
                "task_id": {
                    "type": "string",
                    "description": "Filter by task ID (optional)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Limit number of results (optional, default: 20)"
                }
            }
        }
    ), handle_get_summary)

    logger.info("Registered get_artifacts_summary tool")
