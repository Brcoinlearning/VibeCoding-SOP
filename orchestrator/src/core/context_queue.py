"""
Context Queue System
实现 Agent 间的异步通信队列，支持多 Agent 隔离
"""
import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union
from pathlib import Path
import json

from pydantic import BaseModel, Field

from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Agent 角色枚举"""
    BUILDER = "builder"
    REVIEWER = "reviewer"
    OWNER = "owner"


class ContextMessage(BaseModel):
    """上下文消息"""
    id: str = Field(default_factory=lambda: f"msg_{datetime.now().timestamp()}")
    from_role: AgentRole
    to_role: AgentRole
    task_id: str
    message_type: str  # "evidence", "review_request", "review_result", "notification"
    content: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ContextQueue:
    """
    上下文队列
    实现 Agent 间的异步通信
    """

    def __init__(
        self,
        role: AgentRole,
        max_size: int = 100,
        persist_path: Optional[Path] = None
    ):
        """
        初始化上下文队列

        Args:
            role: Agent 角色
            max_size: 队列最大大小
            persist_path: 持久化路径（可选）
        """
        self.role = role
        self._queue: asyncio.Queue[ContextMessage] = asyncio.Queue(maxsize=max_size)
        self._max_size = max_size
        self._persist_path = persist_path
        self._message_history: list[ContextMessage] = []
        self._lock = asyncio.Lock()

    async def put(self, message: ContextMessage) -> bool:
        """
        放入消息

        Args:
            message: 上下文消息

        Returns:
            是否成功放入
        """
        try:
            await self._queue.put(message)
            logger.info(
                f"Message put into {self.role.value} queue: "
                f"{message.message_type} for task {message.task_id}"
            )

            # 记录历史
            async with self._lock:
                self._message_history.append(message)
                # 保留最近 1000 条消息
                if len(self._message_history) > 1000:
                    self._message_history.pop(0)

            # 持久化
            if self._persist_path:
                await self._persist_message(message)

            return True
        except asyncio.QueueFull:
            logger.error(f"{self.role.value} queue is full, message dropped")
            return False

    async def get(self, timeout: Optional[float] = None) -> Optional[ContextMessage]:
        """
        获取消息

        Args:
            timeout: 超时时间（秒）

        Returns:
            上下文消息或 None
        """
        try:
            if timeout:
                message = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            else:
                message = await self._queue.get()

            logger.info(
                f"Message retrieved from {self.role.value} queue: "
                f"{message.message_type} for task {message.task_id}"
            )
            return message
        except asyncio.TimeoutError:
            logger.debug(f"No message in {self.role.value} queue within {timeout}s")
            return None

    async def peek(self) -> Optional[ContextMessage]:
        """
        查看队列头部的消息但不移除

        Returns:
            上下文消息或 None
        """
        if self._queue.empty():
            return None
        # Note: asyncio.Queue doesn't support peek, this is a workaround
        return None

    def size(self) -> int:
        """获取队列大小"""
        return self._queue.qsize()

    async def clear(self) -> None:
        """清空队列"""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        logger.info(f"{self.role.value} queue cleared")

    async def get_history(
        self,
        task_id: Optional[str] = None,
        message_type: Optional[str] = None,
        limit: int = 100
    ) -> list[ContextMessage]:
        """
        获取历史消息

        Args:
            task_id: 任务 ID 筛选
            message_type: 消息类型筛选
            limit: 返回数量限制

        Returns:
            消息列表
        """
        async with self._lock:
            messages = self._message_history

            if task_id:
                messages = [m for m in messages if m.task_id == task_id]
            if message_type:
                messages = [m for m in messages if m.message_type == message_type]

            return messages[-limit:]

    async def _persist_message(self, message: ContextMessage) -> None:
        """持久化消息到文件"""
        try:
            if not self._persist_path:
                return

            self._persist_path.mkdir(parents=True, exist_ok=True)
            file_path = self._persist_path / f"{self.role.value}_messages.jsonl"

            with open(file_path, "a", encoding="utf-8") as f:
                f.write(message.model_dump_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to persist message: {e}", exc_info=True)


class ContextQueueManager:
    """
    上下文队列管理器
    管理多个 Agent 的上下文队列
    """

    def __init__(
        self,
        max_queue_size: int = 100,
        persist_dir: Optional[Path] = None
    ):
        """
        初始化上下文队列管理器

        Args:
            max_queue_size: 每个队列的最大大小
            persist_dir: 持久化目录
        """
        self._max_queue_size = max_queue_size
        self._persist_dir = persist_dir
        self._queues: dict[AgentRole, ContextQueue] = {}
        self._running = False
        self._router_task: Optional[asyncio.Task] = None

        # 初始化队列
        self._initialize_queues()

    def _initialize_queues(self) -> None:
        """初始化所有队列"""
        for role in AgentRole:
            persist_path = self._persist_dir / role.value if self._persist_dir else None
            self._queues[role] = ContextQueue(
                role=role,
                max_size=self._max_queue_size,
                persist_path=persist_path
            )
            logger.info(f"Initialized {role.value} context queue")

    async def start(self) -> None:
        """启动上下文队列管理器"""
        if self._running:
            logger.warning("ContextQueueManager is already running")
            return

        self._running = True
        self._router_task = asyncio.create_task(self._route_messages())
        logger.info("ContextQueueManager started")

    async def stop(self) -> None:
        """停止上下文队列管理器"""
        if not self._running:
            return

        self._running = False

        if self._router_task:
            self._router_task.cancel()
            try:
                await self._router_task
            except asyncio.CancelledError:
                pass

        logger.info("ContextQueueManager stopped")

    async def route_to_reviewer(
        self,
        task_id: str,
        evidence: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None
    ) -> bool:
        """
        将证据路由到 Reviewer 上下文

        Args:
            task_id: 任务 ID
            evidence: 证据数据
            metadata: 额外元数据

        Returns:
            是否成功路由
        """
        message = ContextMessage(
            from_role=AgentRole.BUILDER,
            to_role=AgentRole.REVIEWER,
            task_id=task_id,
            message_type="evidence",
            content=evidence,
            metadata=metadata or {}
        )

        reviewer_queue = self._queues[AgentRole.REVIEWER]
        success = await reviewer_queue.put(message)

        if success:
            logger.info(f"Evidence routed to reviewer for task {task_id}")
        else:
            logger.error(f"Failed to route evidence to reviewer for task {task_id}")

        return success

    async def route_to_owner(
        self,
        task_id: str,
        review_result: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None
    ) -> bool:
        """
        将审查结果路由到 Owner 上下文

        Args:
            task_id: 任务 ID
            review_result: 审查结果数据
            metadata: 额外元数据

        Returns:
            是否成功路由
        """
        message = ContextMessage(
            from_role=AgentRole.REVIEWER,
            to_role=AgentRole.OWNER,
            task_id=task_id,
            message_type="review_result",
            content=review_result,
            metadata=metadata or {}
        )

        owner_queue = self._queues[AgentRole.OWNER]
        success = await owner_queue.put(message)

        if success:
            logger.info(f"Review result routed to owner for task {task_id}")
        else:
            logger.error(f"Failed to route review result to owner for task {task_id}")

        return success

    async def route_notification(
        self,
        task_id: str,
        notification: dict[str, Any],
        to_role: AgentRole,
        from_role: Optional[AgentRole] = None
    ) -> bool:
        """
        路由通知消息

        Args:
            task_id: 任务 ID
            notification: 通知数据
            to_role: 目标角色
            from_role: 源角色（可选）

        Returns:
            是否成功路由
        """
        message = ContextMessage(
            from_role=from_role or AgentRole.BUILDER,
            to_role=to_role,
            task_id=task_id,
            message_type="notification",
            content=notification,
            metadata={}
        )

        target_queue = self._queues[to_role]
        success = await target_queue.put(message)

        if success:
            logger.info(
                f"Notification routed to {to_role.value} for task {task_id}"
            )
        else:
            logger.error(
                f"Failed to route notification to {to_role.value} for task {task_id}"
            )

        return success

    async def get_reviewer_input(
        self,
        task_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Optional[ContextMessage]:
        """
        获取待审查的输入（Reviewer Agent 使用）

        Args:
            task_id: 任务 ID 筛选（可选）
            timeout: 超时时间（秒）

        Returns:
            上下文消息或 None
        """
        reviewer_queue = self._queues[AgentRole.REVIEWER]

        if task_id:
            # 从历史中查找匹配的消息
            history = await reviewer_queue.get_history(task_id=task_id)
            if history:
                return history[-1]
            return None

        return await reviewer_queue.get(timeout=timeout)

    async def get_owner_input(
        self,
        task_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Optional[ContextMessage]:
        """
        获取待处理的审查结果（Owner Agent 使用）

        Args:
            task_id: 任务 ID 筛选（可选）
            timeout: 超时时间（秒）

        Returns:
            上下文消息或 None
        """
        owner_queue = self._queues[AgentRole.OWNER]

        if task_id:
            # 从历史中查找匹配的消息
            history = await owner_queue.get_history(task_id=task_id)
            if history:
                return history[-1]
            return None

        return await owner_queue.get(timeout=timeout)

    async def submit_review(
        self,
        task_id: str,
        review_result: dict[str, Any],
        reviewer_id: str
    ) -> bool:
        """
        提交审查结果到 Owner 上下文

        Args:
            task_id: 任务 ID
            review_result: 审查结果
            reviewer_id: 审查者 ID

        Returns:
            是否成功提交
        """
        message = ContextMessage(
            from_role=AgentRole.REVIEWER,
            to_role=AgentRole.OWNER,
            task_id=task_id,
            message_type="review_result",
            content=review_result,
            metadata={"reviewer_id": reviewer_id}
        )

        owner_queue = self._queues[AgentRole.OWNER]
        success = await owner_queue.put(message)

        if success:
            logger.info(
                f"Review submitted by {reviewer_id} for task {task_id}"
            )
        else:
            logger.error(
                f"Failed to submit review for task {task_id}"
            )

        return success

    def get_queue_size(self, role: AgentRole) -> int:
        """获取指定角色的队列大小"""
        return self._queues[role].size()

    def get_all_queue_sizes(self) -> dict[str, int]:
        """获取所有队列的大小"""
        return {
            role.value: queue.size()
            for role, queue in self._queues.items()
        }

    async def _route_messages(self) -> None:
        """消息路由循环"""
        while self._running:
            try:
                await asyncio.sleep(0.1)  # 避免忙等待
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in message routing loop: {e}", exc_info=True)


# 全局实例
_context_queue_manager: Optional[ContextQueueManager] = None


def get_context_queue_manager() -> ContextQueueManager:
    """
    获取全局上下文队列管理器实例

    Returns:
        ContextQueueManager 实例
    """
    global _context_queue_manager
    if _context_queue_manager is None:
        # 使用默认持久化目录
        from src.config.settings import get_settings
        settings = get_settings()
        persist_dir = None
        if hasattr(settings, 'base_path'):
            persist_dir = settings.base_path / ".context_queues"

        _context_queue_manager = ContextQueueManager(
            max_queue_size=100,
            persist_dir=persist_dir
        )
    return _context_queue_manager


def reset_context_queue_manager() -> None:
    """重置上下文队列管理器（主要用于测试）"""
    global _context_queue_manager
    _context_queue_manager = None
