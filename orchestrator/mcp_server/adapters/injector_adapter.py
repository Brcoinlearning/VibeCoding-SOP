"""
注入器适配器
将注入器适配为 MCP 工具可用的版本
移除文件系统等待机制，改为直接返回证据内容给 MCP 客户端
"""
import logging
from pathlib import Path
from typing import Any, Optional

# 添加项目路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.artifacts import Artifact
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


class ReviewerInjectorAdapter:
    """
    审查器注入器适配器
    为 MCP 工具提供简化的注入接口
    """

    def __init__(self):
        """初始化适配器"""
        pass

    def prepare_for_review(self, artifact: Artifact) -> dict[str, Any]:
        """
        准备审查输入（同步版本）

        不再写入文件系统等待，而是直接返回结构化数据供 MCP 客户端使用

        Args:
            artifact: 证据产物

        Returns:
            包含审查输入的字典
        """
        return {
            "task_id": artifact.metadata.task_id,
            "stage": artifact.metadata.stage,
            "status": artifact.metadata.status,
            "created_at": artifact.metadata.created_at.isoformat(),
            "content": artifact.content,
            "metadata": {
                "type": artifact.metadata.type.value,
                "author": artifact.metadata.author,
                "version": artifact.metadata.version,
                "tags": artifact.metadata.tags
            }
        }

    def format_reviewer_prompt(self, artifact: Artifact) -> str:
        """
        格式化为审查提示词

        Args:
            artifact: 证据产物

        Returns:
            格式化的提示词字符串
        """
        prompt = f"""# Code Review Request

## Task Information
- **Task ID**: {artifact.metadata.task_id}
- **Stage**: {artifact.metadata.stage}
- **Status**: {artifact.metadata.status}
- **Created**: {artifact.metadata.created_at.isoformat()}

## Review Instructions
Please review the following code changes and provide:
1. **Findings**: List any issues found (severity: critical, high, medium, low)
2. **Risk Assessment**: Identify potential risks
3. **Recommendations**: Suggest improvements
4. **Decision**: Recommend GO or NO-GO for release

## Evidence to Review

{artifact.content}

---
Please provide your review in JSON format:
{{
  "decision": "approved" | "rejected" | "conditional",
  "overall_score": 0-100,
  "findings": [
    {{
      "severity": "critical" | "high" | "medium" | "low",
      "category": "string",
      "title": "string",
      "description": "string",
      "location": "string",
      "evidence": "string",
      "suggested_fix": "string"
    }}
  ],
  "conditions": "string",
  "notes": "string"
}}
"""
        return prompt


class NotificationInjectorAdapter:
    """
    通知注入器适配器
    为 MCP 工具提供通知接口
    """

    def __init__(self):
        """初始化适配器"""
        pass

    def prepare_notification(
        self,
        task_id: str,
        event_type: str,
        message: str,
        metadata: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        准备通知消息

        Args:
            task_id: 任务 ID
            event_type: 事件类型
            message: 通知消息
            metadata: 额外元数据

        Returns:
            通知数据字典
        """
        return {
            "task_id": task_id,
            "event_type": event_type,
            "message": message,
            "metadata": metadata or {},
            "timestamp": None  # Will be set when sent
        }

    def format_notification(self, notification: dict[str, Any]) -> str:
        """
        格式化通知为可读文本

        Args:
            notification: 通知数据

        Returns:
            格式化的通知字符串
        """
        lines = [
            f"## {notification['event_type']}",
            "",
            f"**Task**: {notification['task_id']}",
            f"**Message**: {notification['message']}",
        ]

        if notification.get('metadata'):
            lines.append("**Metadata**:")
            for key, value in notification['metadata'].items():
                lines.append(f"- {key}: {value}")

        return "\n".join(lines)
