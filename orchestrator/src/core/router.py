"""
路由器模块
实现 I/O 托管与产物路由的核心逻辑
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from src.models.artifacts import Artifact, ArtifactType, RoutedArtifact
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class ArtifactRouter:
    """
    产物路由器
    根据 frontmatter 元数据自动路由产物到目标目录
    """

    def __init__(self):
        """初始化路由器"""
        self._settings = get_settings()

        # 类型到目录的映射
        self._type_to_dir = {
            ArtifactType.REQUIREMENT_CONTRACT: self._settings.planning_dir,
            ArtifactType.EXECUTION_EVIDENCE: self._settings.build_dir,
            ArtifactType.REVIEW_REPORT: self._settings.review_dir,
            ArtifactType.GO_NO_GO_RECORD: self._settings.release_dir,
        }

    async def route(self, artifact: Artifact) -> RoutedArtifact:
        """
        路由产物到目标目录

        Args:
            artifact: 要路由的产物

        Returns:
            已路由的产物对象

        Raises:
            ValueError: 路由规则无效时
        """
        # 校验产物
        self._validate_artifact(artifact)

        # 计算目标路径
        routed = RoutedArtifact.from_artifact(artifact, self._settings.artifacts_path)

        # 确保目标目录存在
        routed.target_directory.mkdir(parents=True, exist_ok=True)

        # 处理文件名冲突
        final_path = self._resolve_conflict(routed.full_path)

        # 写入文件
        await self._write_artifact(artifact, final_path)

        # 更新路径
        routed.full_path = final_path

        logger.info(
            f"Routed artifact {artifact.metadata.type.value} "
            f"to {final_path.relative_to(self._settings.artifacts_path)}"
        )

        return routed

    def _validate_artifact(self, artifact: Artifact) -> None:
        """
        校验产物

        Args:
            artifact: 要校验的产物

        Raises:
            ValueError: 校验失败时
        """
        metadata = artifact.metadata

        # 检查必需字段
        required_fields = ["type", "task_id", "stage", "status", "created_at"]
        for field in required_fields:
            if not hasattr(metadata, field) or getattr(metadata, field) is None:
                raise ValueError(f"Missing required metadata field: {field}")

        # 检查路由映射
        if metadata.type not in self._type_to_dir:
            raise ValueError(f"No routing rule for artifact type: {metadata.type}")

        # 检查状态值
        valid_statuses = ["draft", "ready", "approved", "rejected"]
        if metadata.status not in valid_statuses:
            raise ValueError(f"Invalid status: {metadata.status}")

    def _resolve_conflict(self, target_path: Path) -> Path:
        """
        解析文件名冲突

        Args:
            target_path: 目标路径

        Returns:
            解析冲突后的路径
        """
        if not target_path.exists():
            return target_path

        # 文件已存在，追加序号
        stem = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent

        counter = 1
        while True:
            new_name = f"{stem}-{counter}{suffix}"
            new_path = parent / new_name

            if not new_path.exists():
                logger.warning(f"File conflict resolved: {target_path.name} -> {new_name}")
                return new_path

            counter += 1

            # 防止无限循环
            if counter > 1000:
                raise RuntimeError(f"Too many file conflicts for {target_path}")

    async def _write_artifact(self, artifact: Artifact, path: Path) -> None:
        """
        写入产物到文件

        Args:
            artifact: 产物对象
            path: 目标路径
        """
        # 构建 frontmatter 格式的内容
        content = self._format_with_frontmatter(artifact)

        # 写入文件
        path.write_text(content, encoding='utf-8')

    def _format_with_frontmatter(self, artifact: Artifact) -> str:
        """
        格式化为 frontmatter 格式

        Args:
            artifact: 产物对象

        Returns:
            格式化后的字符串
        """
        metadata = artifact.metadata

        # 构建 YAML frontmatter
        frontmatter_dict = {
            "type": metadata.type.value,
            "task_id": metadata.task_id,
            "stage": metadata.stage,
            "status": metadata.status,
            "created_at": metadata.created_at.isoformat(),
        }

        if metadata.updated_at:
            frontmatter_dict["updated_at"] = metadata.updated_at.isoformat()
        if metadata.author:
            frontmatter_dict["author"] = metadata.author
        if metadata.version:
            frontmatter_dict["version"] = metadata.version
        if metadata.tags:
            frontmatter_dict["tags"] = metadata.tags

        # 转换为 YAML
        frontmatter_yaml = yaml.dump(frontmatter_dict, default_flow_style=False, sort_keys=False)

        # 组合内容
        return f"---\n{frontmatter_yaml}---\n\n{artifact.content}"

    async def route_from_file(self, source_path: Path) -> RoutedArtifact:
        """
        从文件路由

        读取源文件，解析 frontmatter，然后路由

        Args:
            source_path: 源文件路径

        Returns:
            已路由的产物对象
        """
        # 读取文件
        content = source_path.read_text(encoding='utf-8')

        # 解析 frontmatter
        artifact = self._parse_frontmatter(content)

        # 路由
        return await self.route(artifact)

    def _parse_frontmatter(self, content: str) -> Artifact:
        """
        解析 frontmatter 格式的内容

        Args:
            content: 文件内容

        Returns:
            产物对象

        Raises:
            ValueError: 解析失败时
        """
        # 查找 frontmatter 分隔符
        if not content.startswith("---"):
            raise ValueError("Content does not start with frontmatter delimiter")

        # 找到第二个 ---
        end_index = content.find("\n---\n", 4)
        if end_index == -1:
            raise ValueError("Invalid frontmatter format")

        # 提取 YAML 和内容
        frontmatter_text = content[4:end_index]
        body_content = content[end_index + 5:]

        # 解析 YAML
        try:
            frontmatter_dict = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid frontmatter YAML: {e}")

        # 创建元数据对象
        type_str = frontmatter_dict.get("type")
        if not type_str:
            raise ValueError("Missing 'type' in frontmatter")

        try:
            artifact_type = ArtifactType(type_str)
        except ValueError:
            raise ValueError(f"Invalid artifact type: {type_str}")

        # 解析时间戳
        created_at_str = frontmatter_dict.get("created_at")
        if created_at_str:
            created_at = datetime.fromisoformat(created_at_str)
        else:
            created_at = datetime.now()

        updated_at = None
        if "updated_at" in frontmatter_dict:
            updated_at = datetime.fromisoformat(frontmatter_dict["updated_at"])

        # 创建元数据
        from src.models.artifacts import FrontmatterMetadata

        metadata = FrontmatterMetadata(
            type=artifact_type,
            task_id=frontmatter_dict.get("task_id", "unknown"),
            stage=frontmatter_dict.get("stage", "unknown"),
            status=frontmatter_dict.get("status", "draft"),
            created_at=created_at,
            updated_at=updated_at,
            author=frontmatter_dict.get("author"),
            version=frontmatter_dict.get("version", "1.0"),
            tags=frontmatter_dict.get("tags", []),
        )

        return Artifact(
            metadata=metadata,
            content=body_content,
            raw_content=content
        )


class RouteValidator:
    """
    路由校验器
    校验路由规则和产物完整性
    """

    def __init__(self):
        """初始化校验器"""
        self._settings = get_settings()

    def validate_routing_rules(self) -> dict[str, bool]:
        """
        验证所有路由规则

        Returns:
            各规则的验证结果
        """
        results = {}

        # 检查目录是否存在
        results["planning_dir_exists"] = self._settings.planning_path.exists()
        results["build_dir_exists"] = self._settings.build_path.exists()
        results["review_dir_exists"] = self._settings.review_path.exists()
        results["release_dir_exists"] = self._settings.release_path.exists()

        # 检查目录可写
        results["planning_dir_writable"] = self._check_writable(self._settings.planning_path)
        results["build_dir_writable"] = self._check_writable(self._settings.build_path)
        results["review_dir_writable"] = self._check_writable(self._settings.review_path)
        results["release_dir_writable"] = self._check_writable(self._settings.release_path)

        return results

    def _check_writable(self, path: Path) -> bool:
        """检查目录是否可写"""
        try:
            test_file = path / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except (OSError, PermissionError):
            return False

    async def validate_artifact_at_path(self, path: Path) -> tuple[bool, list[str]]:
        """
        验证路径处的产物是否有效

        Args:
            path: 产物文件路径

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        if not path.exists():
            errors.append(f"File does not exist: {path}")
            return False, errors

        try:
            content = path.read_text(encoding='utf-8')

            # 尝试解析
            router = ArtifactRouter()
            artifact = router._parse_frontmatter(content)

            # 验证元数据
            if not artifact.metadata.task_id:
                errors.append("Missing task_id")
            if not artifact.metadata.stage:
                errors.append("Missing stage")
            if artifact.metadata.status not in ["draft", "ready", "approved", "rejected"]:
                errors.append(f"Invalid status: {artifact.metadata.status}")

            # 验证内容不为空
            if not artifact.content.strip():
                errors.append("Content is empty")

        except Exception as e:
            errors.append(f"Validation error: {e}")

        return len(errors) == 0, errors


class RouteSummary:
    """
    路由摘要
    生成路由统计和报告
    """

    def __init__(self):
        """初始化路由摘要"""
        self._settings = get_settings()

    async def generate_summary(self) -> dict[str, any]:
        """
        生成路由摘要

        Returns:
            摘要数据
        """
        summary = {
            "total_artifacts": 0,
            "by_type": {},
            "by_status": {},
            "by_task": {},
            "latest_artifacts": [],
        }

        # 扫描所有目录
        for artifact_type, path in [
            (ArtifactType.REQUIREMENT_CONTRACT, self._settings.planning_path),
            (ArtifactType.EXECUTION_EVIDENCE, self._settings.build_path),
            (ArtifactType.REVIEW_REPORT, self._settings.review_path),
            (ArtifactType.GO_NO_GO_RECORD, self._settings.release_path),
        ]:
            if not path.exists():
                continue

            # 统计该类型的产物
            type_count = 0
            for file_path in path.glob("*.md"):
                try:
                    router = ArtifactRouter()
                    artifact = router._parse_frontmatter(file_path.read_text(encoding='utf-8'))

                    type_count += 1

                    # 按状态统计
                    status = artifact.metadata.status
                    summary["by_status"][status] = summary["by_status"].get(status, 0) + 1

                    # 按任务统计
                    task_id = artifact.metadata.task_id
                    summary["by_task"][task_id] = summary["by_task"].get(task_id, 0) + 1

                    # 记录最新产物
                    summary["latest_artifacts"].append({
                        "type": artifact_type.value,
                        "task_id": task_id,
                        "path": str(file_path),
                        "created_at": artifact.metadata.created_at.isoformat(),
                    })

                except Exception as e:
                    logger.warning(f"Error processing {file_path}: {e}")

            summary["by_type"][artifact_type.value] = type_count
            summary["total_artifacts"] += type_count

        # 按时间排序最新产物
        summary["latest_artifacts"].sort(
            key=lambda x: x["created_at"],
            reverse=True
        )
        summary["latest_artifacts"] = summary["latest_artifacts"][:20]

        return summary

    def format_summary_markdown(self, summary: dict[str, any]) -> str:
        """
        将摘要格式化为 Markdown

        Args:
            summary: 摘要数据

        Returns:
            Markdown 字符串
        """
        lines = [
            "# Artifact Routing Summary",
            "",
            f"**Total Artifacts**: {summary['total_artifacts']}",
            "",
            "## By Type",
            ""
        ]

        for artifact_type, count in summary["by_type"].items():
            lines.append(f"- **{artifact_type}**: {count}")

        lines.extend([
            "",
            "## By Status",
            ""
        ])

        for status, count in summary["by_status"].items():
            emoji = {"approved": "✅", "rejected": "❌", "ready": "🟡", "draft": "📝"}.get(status, "📄")
            lines.append(f"- {emoji} **{status}**: {count}")

        if summary["by_task"]:
            lines.extend([
                "",
                "## By Task (Top 10)",
                ""
            ])

            sorted_tasks = sorted(summary["by_task"].items(), key=lambda x: x[1], reverse=True)[:10]
            for task_id, count in sorted_tasks:
                lines.append(f"- **{task_id}**: {count} artifacts")

        if summary["latest_artifacts"]:
            lines.extend([
                "",
                "## Latest Artifacts",
                ""
            ])

            for artifact in summary["latest_artifacts"][:10]:
                lines.append(
                    f"- [{artifact['created_at']}] "
                    f"{artifact['type']} - {artifact['task_id']}"
                )

        return "\n".join(lines)
