"""
注入器模块
负责将封装好的输入注入到隔离上下文中的 Reviewer
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional

from src.models.artifacts import Artifact
from src.models.review import ReviewReport
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class ReviewerInjector:
    """
    Reviewer 注入器
    将证据注入到 AI Reviewer 进行审查
    """

    def __init__(self):
        """初始化注入器"""
        self._settings = get_settings()

    async def inject_to_reviewer(
        self,
        artifact: Artifact,
        reviewer_context: Optional[dict[str, Any]] = None
    ) -> Optional[ReviewReport]:
        """
        将证据注入到 Reviewer

        Args:
            artifact: 要审查的证据产物
            reviewer_context: Reviewer 上下文配置

        Returns:
            审查报告，如果失败则返回 None
        """
        backend = self._settings.ai_backend

        if backend == "filesystem":
            return await self._inject_via_filesystem(artifact, reviewer_context)
        elif backend == "claude-api":
            return await self._inject_via_claude_api(artifact, reviewer_context)
        else:
            logger.error(f"Unsupported AI backend: {backend}")
            return None

    async def _inject_via_filesystem(
        self,
        artifact: Artifact,
        reviewer_context: Optional[dict[str, Any]]
    ) -> Optional[ReviewReport]:
        """
        通过文件系统注入

        创建一个审查请求文件，等待外部 AI 处理后读取结果

        Args:
            artifact: 证据产物
            reviewer_context: 审查上下文

        Returns:
            审查报告
        """
        # 创建审查请求目录
        request_dir = self._settings.workspace_path / "review_requests" / artifact.metadata.task_id
        request_dir.mkdir(parents=True, exist_ok=True)

        # 写入输入文件
        input_file = request_dir / "input.md"
        with open(input_file, 'w', encoding='utf-8') as f:
            f.write(artifact.content)

        # 写入元数据
        meta_file = request_dir / "meta.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump({
                "task_id": artifact.metadata.task_id,
                "stage": artifact.metadata.stage,
                "status": artifact.metadata.status,
                "created_at": artifact.metadata.created_at.isoformat(),
                "context": reviewer_context or {}
            }, f, indent=2)

        logger.info(f"Review request written to {request_dir}")

        # 等待响应文件
        response_file = request_dir / "response.json"
        max_wait = self._settings.ai_timeout
        check_interval = 2

        waited = 0
        while waited < max_wait:
            if response_file.exists():
                try:
                    with open(response_file, 'r', encoding='utf-8') as f:
                        response_data = json.load(f)

                    # 验证响应格式
                    if self._validate_review_response(response_data):
                        report = ReviewReport(**response_data)
                        logger.info(f"Review received for task {artifact.metadata.task_id}")
                        return report
                    else:
                        logger.error("Invalid review response format")

                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"Error reading review response: {e}")

            await asyncio.sleep(check_interval)
            waited += check_interval

        logger.warning(f"Timeout waiting for review response ({max_wait}s)")
        return None

    async def _inject_via_claude_api(
        self,
        artifact: Artifact,
        reviewer_context: Optional[dict[str, Any]]
    ) -> Optional[ReviewReport]:
        """
        通过 Claude API 注入

        直接调用 Claude API 进行审查

        Args:
            artifact: 证据产物
            reviewer_context: 审查上下文

        Returns:
            审查报告
        """
        # 需要 anthropic 包
        try:
            from anthropic import Anthropic
        except ImportError:
            logger.error("anthropic package not installed. Install with: pip install anthropic")
            return None

        if not self._settings.claude_api_key:
            logger.error("Claude API key not configured")
            return None

        client = Anthropic(api_key=self._settings.claude_api_key)

        # 构建提示词
        prompt = f"""You are a code reviewer. Please review the following changes and provide a structured review report.

{artifact.content}

Please respond with a JSON object following this exact structure:
{{
    "task_id": "{artifact.metadata.task_id}",
    "reviewer_id": "claude-api",
    "review_date": "ISO_DATE",
    "decision": "approved|rejected|conditional",
    "overall_score": 0-100,
    "findings": [
        {{
            "id": "unique_id",
            "severity": "critical|high|medium|low|info",
            "category": "security|performance|maintainability|etc",
            "title": "Short title",
            "description": "Detailed description",
            "evidence": "Code snippet or reference",
            "location": "file:line or N/A",
            "suggested_fix": "Optional suggestion"
        }}
    ],
    "files_reviewed": ["list of files"],
    "notes": "Additional notes"
}}

Respond ONLY with valid JSON, no markdown formatting.
"""

        try:
            message = await asyncio.to_thread(
                client.messages.create,
                model=self._settings.claude_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            # 提取 JSON 响应
            content = message.content[0].text

            # 清理可能的 markdown 包装
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            response_data = json.loads(content)

            if self._validate_review_response(response_data):
                return ReviewReport(**response_data)
            else:
                logger.error("Invalid review response from Claude API")

        except Exception as e:
            logger.error(f"Error calling Claude API: {e}", exc_info=True)

        return None

    def _validate_review_response(self, response: dict) -> bool:
        """
        验证审查响应格式

        Args:
            response: 响应数据

        Returns:
            是否有效
        """
        required_fields = ["task_id", "reviewer_id", "decision", "overall_score", "findings"]

        for field in required_fields:
            if field not in response:
                logger.error(f"Missing required field: {field}")
                return False

        # 验证决策值
        if response["decision"] not in ["approved", "rejected", "conditional"]:
            logger.error(f"Invalid decision value: {response['decision']}")
            return False

        # 验证分数范围
        if not isinstance(response["overall_score"], (int, float)) or not (0 <= response["overall_score"] <= 100):
            logger.error(f"Invalid score: {response['overall_score']}")
            return False

        # 验证 findings 是列表
        if not isinstance(response["findings"], list):
            logger.error("findings must be a list")
            return False

        return True


class NotificationInjector:
    """
    通知注入器
    将结果通知发送给 Owner
    """

    def __init__(self):
        """初始化通知注入器"""
        self._settings = get_settings()

    async def notify_owner(
        self,
        task_id: str,
        message: str,
        level: str = "info"  # info | warning | error
    ) -> bool:
        """
        通知 Owner

        Args:
            task_id: 任务 ID
            message: 通知消息
            level: 通知级别

        Returns:
            是否发送成功
        """
        if not self._settings.notification_enabled:
            return False

        method = self._settings.notification_method

        if method == "console":
            return await self._notify_console(task_id, message, level)
        elif method == "webhook":
            return await self._notify_webhook(task_id, message, level)
        else:
            logger.warning(f"Unsupported notification method: {method}")
            return False

    async def _notify_console(self, task_id: str, message: str, level: str) -> bool:
        """
        控制台通知

        Args:
            task_id: 任务 ID
            message: 消息
            level: 级别

        Returns:
            是否成功
        """
        emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }

        print(f"\n{emoji.get(level, '📢')} [{level.upper()}] Task {task_id}: {message}\n")
        return True

    async def _notify_webhook(self, task_id: str, message: str, level: str) -> bool:
        """
        Webhook 通知

        Args:
            task_id: 任务 ID
            message: 消息
            level: 级别

        Returns:
            是否成功
        """
        import aiohttp

        webhook_url = self._settings.model_dump().get("notification_webhook_url")
        if not webhook_url:
            logger.warning("Webhook URL not configured")
            return False

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "task_id": task_id,
                    "level": level,
                    "message": message,
                    "timestamp": asyncio.get_event_loop().time()
                }

                async with session.post(webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        logger.info(f"Notification sent via webhook for task {task_id}")
                        return True
                    else:
                        logger.error(f"Webhook returned status {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}", exc_info=True)
            return False


class SessionInjector:
    """
    会话注入器
    用于 Claude Code 的会话注入
    """

    def __init__(self):
        """初始化会话注入器"""
        self._settings = get_settings()

    async def inject_session_start(self, session_id: str) -> None:
        """
        注入会话开始事件

        Args:
            session_id: 会话 ID
        """
        session_file = self._settings.workspace_path / f".session_{session_id}"
        session_file.write_text(
            f"Session started: {asyncio.get_event_loop().time()}\n",
            encoding='utf-8'
        )
        logger.info(f"Session {session_id} started")

    async def inject_session_end(self, session_id: str, summary: str) -> None:
        """
        注入会话结束事件

        Args:
            session_id: 会话 ID
            summary: 会话摘要
        """
        session_file = self._settings.workspace_path / f".session_{session_id}"
        with open(session_file, 'a', encoding='utf-8') as f:
            f.write(f"Session ended: {asyncio.get_event_loop().time()}\n")
            f.write(f"Summary:\n{summary}\n")

        logger.info(f"Session {session_id} ended")
