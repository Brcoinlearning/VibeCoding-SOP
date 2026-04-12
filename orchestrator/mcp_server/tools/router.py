"""
MCP Tool: route_artifact
将产物路由到正确的目录，基于 frontmatter 元数据自动分类
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp_server.tools.registry import register_tool

# 添加项目路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import get_settings
from src.core.router import ArtifactRouter
from src.models.artifacts import Artifact, ArtifactType, FrontmatterMetadata
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


async def execute_route_artifact(
    artifact_type: str,
    task_id: str,
    content: str,
    stage: str = "default",
    status: str = "draft",
    author: str | None = None,
    tags: list[str] | None = None
) -> dict[str, Any]:
    """
    路由产物到目标目录

    Args:
        artifact_type: 产物类型
        task_id: 任务ID
        content: 产物内容
        stage: 阶段
        status: 状态 (draft, ready, approved, rejected)
        author: 作者
        tags: 标签列表

    Returns:
        包含路由结果的字典
    """
    try:
        settings = get_settings()

        # 验证产物类型
        try:
            artifact_type_enum = ArtifactType(artifact_type)
        except ValueError:
            valid_types = [t.value for t in ArtifactType]
            return {
                "success": False,
                "error": f"Invalid artifact_type: {artifact_type}. Must be one of: {valid_types}",
                "task_id": task_id
            }

        # 验证状态
        if status not in ["draft", "ready", "approved", "rejected"]:
            return {
                "success": False,
                "error": f"Invalid status: {status}. Must be one of: draft, ready, approved, rejected",
                "task_id": task_id
            }

        # 创建元数据
        metadata = FrontmatterMetadata(
            type=artifact_type_enum,
            task_id=task_id,
            stage=stage,
            status=status,
            created_at=datetime.now(),
            author=author,
            tags=tags or []
        )

        # 创建产物
        artifact = Artifact(metadata=metadata, content=content)

        # 路由产物
        router = ArtifactRouter()
        routed = await router.route(artifact)

        logger.info(f"Successfully routed artifact {task_id} to {routed.full_path}")

        return {
            "success": True,
            "task_id": task_id,
            "artifact_type": artifact_type,
            "target_path": str(routed.full_path),
            "relative_path": str(routed.full_path.relative_to(settings.artifacts_path)),
            "metadata": metadata.model_dump(mode='json')
        }

    except Exception as e:
        logger.exception(f"Error routing artifact: {e}")
        return {
            "success": False,
            "error": str(e),
            "task_id": task_id
        }


def register_route_artifact(server: Server) -> None:
    """注册 route_artifact 工具到 MCP 服务器"""

    async def handle_route_artifact(arguments: dict[str, Any]) -> list[TextContent]:
        """处理 route_artifact 调用"""
        try:
            result = await execute_route_artifact(
                artifact_type=arguments.get("artifact_type"),
                task_id=arguments.get("task_id"),
                content=arguments.get("content"),
                stage=arguments.get("stage", "default"),
                status=arguments.get("status", "draft"),
                author=arguments.get("author"),
                tags=arguments.get("tags")
            )

            if result["success"]:
                response = f"""# Artifact Routed Successfully

## Task: {result['task_id']}

### Target Location
- **Path**: `{result['target_path']}`
- **Relative**: `{result['relative_path']}`

### Metadata
- **Type**: {result['artifact_type']}
- **Stage**: {result['metadata']['stage']}
- **Status**: {result['metadata']['status']}
- **Created**: {result['metadata']['created_at']}

The artifact has been successfully routed to the appropriate directory based on its type.
"""
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
            logger.exception(f"Error in route_artifact: {e}")
            return [TextContent(
                type="text",
                text=f"Exception: {str(e)}"
            )]

    # 注册工具
    register_tool(server, Tool(
        name="route_artifact",
        description="Route artifacts to the correct directory based on frontmatter metadata. Automatically classifies and stores artifacts.",
        inputSchema={
            "type": "object",
            "properties": {
                "artifact_type": {
                    "type": "string",
                    "enum": ["requirement_contract", "execution_evidence", "review_report", "go_no_go_record"],
                    "description": "Type of artifact to route"
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID (e.g., T-102)"
                },
                "content": {
                    "type": "string",
                    "description": "Artifact content (markdown formatted)"
                },
                "stage": {
                    "type": "string",
                    "description": "Stage identifier (optional, default: 'default')"
                },
                "status": {
                    "type": "string",
                    "enum": ["draft", "ready", "approved", "rejected"],
                    "description": "Artifact status (optional, default: 'draft')"
                },
                "author": {
                    "type": "string",
                    "description": "Author name (optional)"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tags (optional)"
                }
            },
            "required": ["artifact_type", "task_id", "content"]
        }
    ), handle_route_artifact)

    logger.info("Registered route_artifact tool")
