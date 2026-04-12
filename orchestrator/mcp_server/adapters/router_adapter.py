"""
路由器适配器
将路由器适配为 MCP 工具可用的版本
添加批量路由支持，优化文件操作
"""
import logging
from pathlib import Path
from typing import Any, List

# 添加项目路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.router import ArtifactRouter
from src.models.artifacts import Artifact, ArtifactType, FrontmatterMetadata
from src.config.settings import get_settings
from src.utils.logger import setup_logging
from datetime import datetime

logger = logging.getLogger(__name__)


class RouterAdapter:
    """
    路由器适配器
    为 MCP 工具提供简化的路由接口
    """

    def __init__(self):
        """初始化适配器"""
        self._router = ArtifactRouter()
        self._settings = get_settings()

    async def route_single(self, artifact: Artifact) -> dict[str, Any]:
        """
        路由单个产物

        Args:
            artifact: 要路由的产物

        Returns:
            路由结果字典
        """
        try:
            routed = await self._router.route(artifact)
            return {
                "success": True,
                "path": str(routed.full_path),
                "relative_path": str(routed.full_path.relative_to(self._settings.artifacts_path)),
                "artifact_type": artifact.metadata.type.value,
                "task_id": artifact.metadata.task_id
            }
        except Exception as e:
            logger.error(f"Error routing artifact: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "artifact_type": artifact.metadata.type.value,
                "task_id": artifact.metadata.task_id
            }

    async def route_batch(self, artifacts: List[Artifact]) -> List[dict[str, Any]]:
        """
        批量路由产物

        Args:
            artifacts: 要路由的产物列表

        Returns:
            路由结果列表
        """
        results = []
        for artifact in artifacts:
            result = await self.route_single(artifact)
            results.append(result)
        return results

    async def route_from_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        从字典数据创建并路由产物

        Args:
            data: 包含产物数据的字典

        Returns:
            路由结果字典
        """
        try:
            # 验证必需字段
            required_fields = ["artifact_type", "task_id", "content"]
            for field in required_fields:
                if field not in data:
                    return {
                        "success": False,
                        "error": f"Missing required field: {field}"
                    }

            # 创建产物类型
            try:
                artifact_type = ArtifactType(data["artifact_type"])
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid artifact_type: {data['artifact_type']}"
                }

            # 创建元数据
            metadata = FrontmatterMetadata(
                type=artifact_type,
                task_id=data["task_id"],
                stage=data.get("stage", "default"),
                status=data.get("status", "draft"),
                created_at=datetime.now(),
                author=data.get("author"),
                tags=data.get("tags", [])
            )

            # 创建产物
            artifact = Artifact(
                metadata=metadata,
                content=data["content"]
            )

            # 路由
            return await self.route_single(artifact)

        except Exception as e:
            logger.error(f"Error creating artifact from dict: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def get_target_directory(self, artifact_type: str) -> Path:
        """
        获取指定类型的目标目录

        Args:
            artifact_type: 产物类型

        Returns:
            目标目录路径
        """
        type_mappings = {
            "requirement_contract": self._settings.planning_path,
            "execution_evidence": self._settings.build_path,
            "review_report": self._settings.review_path,
            "go_no_go_record": self._settings.release_path,
        }

        return type_mappings.get(artifact_type, self._settings.artifacts_path)

    def validate_artifact_type(self, artifact_type: str) -> bool:
        """
        验证产物类型是否有效

        Args:
            artifact_type: 产物类型字符串

        Returns:
            是否有效
        """
        try:
            ArtifactType(artifact_type)
            return True
        except ValueError:
            return False

    def get_valid_artifact_types(self) -> List[str]:
        """
        获取所有有效的产物类型

        Returns:
            产物类型列表
        """
        return [t.value for t in ArtifactType]

    def get_valid_statuses(self) -> List[str]:
        """
        获取所有有效的状态

        Returns:
            状态列表
        """
        return ["draft", "ready", "approved", "rejected"]
