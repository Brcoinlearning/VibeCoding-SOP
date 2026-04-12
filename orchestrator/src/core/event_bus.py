"""
事件总线
实现发布-订阅模式，支持异步事件处理和链式处理
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Optional
from datetime import datetime

from src.models.events import BaseEvent, EventType
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class EventBus:
    """
    事件总线
    实现发布-订阅模式，支持多个监听器订阅同一事件
    """

    def __init__(self):
        """初始化事件总线"""
        self._subscribers: dict[EventType, list[Callable]] = defaultdict(list)
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        self._event_history: list[BaseEvent] = []
        self._settings = get_settings()

    def subscribe(self, event_type: EventType, handler: Callable[[BaseEvent], Any]) -> None:
        """
        订阅事件

        Args:
            event_type: 要订阅的事件类型
            handler: 事件处理函数
        """
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            logger.debug(f"Subscribed handler {handler.__name__} to {event_type}")

    def unsubscribe(self, event_type: EventType, handler: Callable[[BaseEvent], Any]) -> None:
        """
        取消订阅

        Args:
            event_type: 事件类型
            handler: 要取消的处理函数
        """
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            logger.debug(f"Unsubscribed handler {handler.__name__} from {event_type}")

    async def publish(self, event: BaseEvent) -> None:
        """
        发布事件（异步）

        Args:
            event: 要发布的事件
        """
        await self._event_queue.put(event)

        if self._settings.enable_event_logging:
            self._event_history.append(event)
            # 保留最近 1000 个事件
            if len(self._event_history) > 1000:
                self._event_history.pop(0)

        logger.info(f"Event published: {event.event_type} for task {event.task_id}")

    def publish_sync(self, event: BaseEvent) -> None:
        """
        发布事件（同步）

        Args:
            event: 要发布的事件
        """
        # 在新的事件循环中发布
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.publish(event))
            else:
                loop.run_until_complete(self.publish(event))
        except RuntimeError:
            # 没有事件循环，创建一个新的
            asyncio.run(self.publish(event))

    async def start(self) -> None:
        """启动事件处理器"""
        if self._running:
            logger.warning("Event bus is already running")
            return

        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")

    async def stop(self) -> None:
        """停止事件处理器"""
        if not self._running:
            return

        self._running = False

        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        logger.info("Event bus stopped")

    async def _process_events(self) -> None:
        """事件处理循环"""
        settings = get_settings()

        while self._running:
            try:
                # 等待事件，带超时
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )

                # 获取该事件类型的所有订阅者
                handlers = self._subscribers.get(event.event_type, [])

                if not handlers:
                    logger.debug(f"No handlers for event type: {event.event_type}")
                    continue

                # 并发执行所有处理器
                tasks = []
                for handler in handlers:
                    task = asyncio.create_task(self._execute_handler(handler, event))
                    tasks.append(task)

                # 等待所有处理器完成或超时
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=settings.event_processing_timeout
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        f"Event processing timeout for {event.event_type} "
                        f"(task: {event.task_id})"
                    )

            except asyncio.TimeoutError:
                # 正常超时，继续循环
                continue
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}", exc_info=True)

    async def _execute_handler(self, handler: Callable, event: BaseEvent) -> None:
        """
        执行单个处理器

        Args:
            handler: 处理函数
            event: 事件对象
        """
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            logger.error(
                f"Error executing handler {handler.__name__} "
                f"for event {event.event_type}: {e}",
                exc_info=True
            )

    def get_history(self, event_type: Optional[EventType] = None,
                    task_id: Optional[str] = None,
                    limit: int = 100) -> list[BaseEvent]:
        """
        获取事件历史

        Args:
            event_type: 筛选事件类型
            task_id: 筛选任务 ID
            limit: 返回数量限制

        Returns:
            事件列表
        """
        events = self._event_history

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if task_id:
            events = [e for e in events if e.task_id == task_id]

        return events[-limit:]

    def clear_history(self) -> None:
        """清空事件历史"""
        self._event_history.clear()


# 全局事件总线实例
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    获取全局事件总线实例

    Returns:
        EventBus 实例
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus() -> None:
    """重置事件总线（主要用于测试）"""
    global _event_bus
    _event_bus = None
