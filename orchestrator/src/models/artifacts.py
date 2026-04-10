"""
产物定义模块
定义系统中的各类产物模型和元数据结构
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, validator
from src.models.events import BuildCompletedEvent, TestCompletedEvent


class ArtifactType(str, Enum):
    """产物类型枚举"""
    REQUIREMENT_CONTRACT = "requirement_contract"
    EXECUTION_EVIDENCE = "execution_evidence"
    REVIEW_REPORT = "review_report"
    GO_NO_GO_RECORD = "go_no_go_record"


class FrontmatterMetadata(BaseModel):
    """
    Frontmatter 元数据模型
    所有产物必须包含这些元数据
    """
    type: ArtifactType
    task_id: str
    stage: str
    status: str  # draft | ready | approved | rejected
    created_at: datetime
    updated_at: Optional[datetime] = None
    author: Optional[str] = None
    version: str = "1.0"
    tags: list[str] = Field(default_factory=list)

    @validator('status')
    def validate_status(cls, v):
        """验证状态值是否合法"""
        valid_statuses = ['draft', 'ready', 'approved', 'rejected']
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {v}")
        return v


class Artifact(BaseModel):
    """
    产物模型
    包含元数据和内容本体
    """
    metadata: FrontmatterMetadata
    content: str
    raw_content: Optional[str] = None  # 包含 frontmatter 的原始内容

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RoutedArtifact(BaseModel):
    """
    已路由的产物模型
    包含目标路径信息
    """
    artifact: Artifact
    target_directory: Path
    target_filename: str
    full_path: Path

    @classmethod
    def from_artifact(cls, artifact: Artifact, base_path: Path) -> "RoutedArtifact":
        """
        从产物创建已路由的产物

        Args:
            artifact: 原始产物
            base_path: 基础路径

        Returns:
            已路由的产物对象
        """
        # 根据类型确定目标目录
        type_to_dir = {
            ArtifactType.REQUIREMENT_CONTRACT: "20-planning",
            ArtifactType.EXECUTION_EVIDENCE: "30-build",
            ArtifactType.REVIEW_REPORT: "40-review",
            ArtifactType.GO_NO_GO_RECORD: "50-release",
        }

        target_dir_name = type_to_dir.get(artifact.metadata.type)
        if target_dir_name is None:
            raise ValueError(f"Unknown artifact type: {artifact.metadata.type}")

        target_directory = base_path / target_dir_name

        # 生成确定性文件名
        timestamp = artifact.metadata.created_at.strftime("%Y%m%d-%H%M")
        target_filename = f"{artifact.metadata.task_id}-{artifact.metadata.type.value}-{timestamp}.md"
        full_path = target_directory / target_filename

        return cls(
            artifact=artifact,
            target_directory=target_directory,
            target_filename=target_filename,
            full_path=full_path
        )


class EvidencePackage(BaseModel):
    """
    证据包模型
    用于传递给 Reviewer 的所有证据集合
    """
    task_id: str
    build_info: BuildCompletedEvent  # 循环导入，实际需要从 events 导入
    test_info: TestCompletedEvent
    diff_content: str
    log_summary: str
    coverage_info: Optional[str] = None
    additional_artifacts: dict[str, str] = Field(default_factory=dict)

    def to_reviewer_input(self) -> str:
        """
        转换为 Reviewer 输入格式

        Returns:
            结构化的输入字符串
        """
        return f"""# Reviewer Input

## Task Information
- Task ID: {self.task_id}
- Build Commit: {self.build_info.commit_hash}
- Branch: {self.build_info.branch}

## Build Summary
{self.build_info.diff_summary or "No summary available"}

## Test Results
- Status: {"✓ PASSED" if self.test_info.passed else "✗ FAILED"}
- Total Tests: {self.test_info.total_tests}
- Failed: {self.test_info.failed_tests}
- Coverage: {self.test_info.coverage_percent or 'N/A'}%

## Code Diff
```
{self.diff_content}
```

## Test Summary
{self.test_info.test_summary}

## Log Summary
{self.log_summary}
"""
