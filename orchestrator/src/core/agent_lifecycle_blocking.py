"""
Agent Sleep/Wake-Up Blocking Protocol
真正的睡眠/唤醒阻塞机制，替代提示式人工编排
"""
import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Dict
from pathlib import Path
import json

from pydantic import BaseModel, Field

from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Agent 状态枚举"""
    IDLE = "idle"                    # 空闲，等待任务
    WORKING = "working"              # 工作中
    WAITING = "waiting"              # 等待其他 Agent
    BLOCKED = "blocked"              # 被阻塞
    COMPLETED = "completed"          # 任务完成
    ERROR = "error"                  # 错误状态
    SLEEPING = "sleeping"            # 休眠中


class AgentLifecycleEvent(BaseModel):
    """Agent 生命周期事件"""
    event_id: str = Field(default_factory=lambda: f"evt_{datetime.now().timestamp()}")
    agent_role: str
    state: AgentState
    task_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentBlockingSleepProtocol:
    """
    Agent 阻塞睡眠协议

    实现真正的阻塞等待机制，而不是提示式编排
    Agent 在进入睡眠后会真正阻塞，直到被唤醒
    """

    def __init__(
        self,
        agent_role: str,
        state_file: Optional[Path] = None
    ):
        """
        初始化 Agent 阻塞睡眠协议

        Args:
            agent_role: Agent 角色（builder/reviewer/owner）
            state_file: 状态文件路径
        """
        self.agent_role = agent_role
        self._state = AgentState.IDLE
        self._current_task: Optional[str] = None
        self._state_file = state_file
        self._sleep_conditions: Dict[str, Any] = {}

        # 阻塞机制：使用 ConditionVariable
        self._condition = asyncio.Condition()
        self._wake_up_signal = False

        # 事件历史
        self._event_history: list[AgentLifecycleEvent] = []

        # 从状态文件恢复
        if state_file and state_file.exists():
            self._restore_state()

    async def enter_blocking_sleep(
        self,
        task_id: str,
        wake_up_condition: Optional[str] = None,
        timeout: Optional[float] = None,
        check_interval: float = 5.0
    ) -> Dict[str, Any]:
        """
        进入阻塞睡眠状态

        这是真正的阻塞等待，Agent 会在这里暂停执行，直到：
        1. 被手动唤醒
        2. 满足唤醒条件
        3. 超时

        Args:
            task_id: 任务 ID
            wake_up_condition: 唤醒条件描述
            timeout: 超时时间（秒），None 表示无限等待
            check_interval: 检查唤醒条件的间隔（秒）

        Returns:
            唤醒结果
        """
        self._state = AgentState.SLEEPING
        self._current_task = task_id
        self._wake_up_signal = False

        sleep_event = AgentLifecycleEvent(
            agent_role=self.agent_role,
            state=AgentState.SLEEPING,
            task_id=task_id,
            metadata={
                "wake_up_condition": wake_up_condition,
                "timeout": timeout,
                "blocking": True
            }
        )

        self._record_event(sleep_event)
        await self._persist_state()

        logger.info(
            f"Agent {self.agent_role} entering BLOCKING sleep for task {task_id}. "
            f"Will block until woken up."
        )

        try:
            # 真正的阻塞等待
            async with self._condition:
                start_time = datetime.now().timestamp()

                while True:
                    # 检查是否被唤醒
                    if self._wake_up_signal:
                        logger.info(f"Agent {self.agent_role} woken up for task {task_id}")
                        break

                    # 检查超时
                    if timeout is not None:
                        elapsed = datetime.now().timestamp() - start_time
                        if elapsed > timeout:
                            logger.warning(
                                f"Agent {self.agent_role} sleep timeout for task {task_id}"
                            )
                            self._state = AgentState.ERROR
                            await self._persist_state()
                            return {
                                "success": False,
                                "reason": "timeout",
                                "task_id": task_id,
                                "elapsed_time": elapsed
                            }

                    # 等待信号或超时
                    try:
                        await asyncio.wait_for(
                            self._condition.wait(),
                            timeout=check_interval
                        )
                    except asyncio.TimeoutError:
                        # 正常超时，继续循环检查条件
                        continue

        finally:
            # 清理睡眠状态
            if self._state == AgentState.SLEEPING:
                self._state = AgentState.IDLE
                self._current_task = None
                await self._persist_state()

        wake_event = AgentLifecycleEvent(
            agent_role=self.agent_role,
            state=AgentState.IDLE,
            task_id=task_id,
            metadata={"wake_up_reason": "blocking_sleep_completed"}
        )
        self._record_event(wake_event)
        await self._persist_state()

        return {
            "success": True,
            "reason": "woken_up",
            "task_id": task_id
        }

    async def wake_up(self, task_id: str, reason: str = "manual_wake_up") -> bool:
        """
        唤醒阻塞睡眠的 Agent

        Args:
            task_id: 任务 ID
            reason: 唤醒原因

        Returns:
            是否成功唤醒
        """
        async with self._condition:
            if self._state != AgentState.SLEEPING:
                logger.warning(
                    f"Cannot wake up agent {self.agent_role}: "
                    f"not sleeping (current state: {self._state})"
                )
                return False

            # 验证任务 ID 匹配
            if self._current_task != task_id:
                logger.warning(
                    f"Task ID mismatch: expecting {self._current_task}, got {task_id}"
                )
                return False

            self._wake_up_signal = True
            self._state = AgentState.IDLE
            self._current_task = None

            # 通知等待的 Agent
            self._condition.notify_all()

            wake_event = AgentLifecycleEvent(
                agent_role=self.agent_role,
                state=AgentState.IDLE,
                task_id=task_id,
                metadata={"wake_up_reason": reason}
            )
            self._record_event(wake_event)
            await self._persist_state()

            logger.info(
                f"Agent {self.agent_role} woken up for task {task_id}: {reason}"
            )

            return True

    async def wait_for_review_complete(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Builder Agent 专用：等待审查完成

        这是一个便捷方法，封装了常见的"等待审查"场景

        Args:
            task_id: 任务 ID
            timeout: 超时时间（秒）

        Returns:
            审查结果
        """
        logger.info(f"Agent {self.agent_role} waiting for review completion for task {task_id}")

        # 进入阻塞睡眠，等待审查完成
        result = await self.enter_blocking_sleep(
            task_id=task_id,
            wake_up_condition="review_completed",
            timeout=timeout
        )

        if result["success"]:
            # 获取审查结果
            from src.core.context_queue import get_context_queue_manager
            queue_manager = get_context_queue_manager()

            review_result = await queue_manager.get_owner_input(
                task_id=task_id,
                timeout=5.0
            )

            if review_result:
                return {
                    "success": True,
                    "review_result": review_result.content,
                    "task_id": task_id
                }
            else:
                return {
                    "success": False,
                    "reason": "no_review_result",
                    "task_id": task_id
                }

        return result

    async def wait_for_decision(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Builder/Reviewer Agent 专用：等待 Owner 决策

        Args:
            task_id: 任务 ID
            timeout: 超时时间（秒）

        Returns:
            决策结果
        """
        logger.info(f"Agent {self.agent_role} waiting for owner decision for task {task_id}")

        # 进入阻塞睡眠，等待决策
        result = await self.enter_blocking_sleep(
            task_id=task_id,
            wake_up_condition="owner_decision",
            timeout=timeout
        )

        if result["success"]:
            # 获取决策结果
            # 这里可以根据实际需求实现
            return {
                "success": True,
                "task_id": task_id,
                "decision": "proceed"
            }

        return result

    def _record_event(self, event: AgentLifecycleEvent) -> None:
        """记录生命周期事件"""
        self._event_history.append(event)
        if len(self._event_history) > 100:
            self._event_history.pop(0)

    async def _persist_state(self) -> None:
        """持久化 Agent 状态"""
        if not self._state_file:
            return

        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)

            state_data = {
                "agent_role": self.agent_role,
                "state": self._state.value,
                "current_task": self._current_task,
                "timestamp": datetime.now().isoformat(),
                "sleep_conditions": self._sleep_conditions
            }

            with open(self._state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to persist agent state: {e}", exc_info=True)

    def _restore_state(self) -> None:
        """从持久化文件恢复 Agent 状态"""
        try:
            with open(self._state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            self._state = AgentState(state_data.get("state", "idle"))
            self._current_task = state_data.get("current_task")
            self._sleep_conditions = state_data.get("sleep_conditions", {})

            logger.info(
                f"Restored agent {self.agent_role} state: {self._state.value}"
            )

        except Exception as e:
            logger.error(f"Failed to restore agent state: {e}", exc_info=True)
            self._state = AgentState.IDLE

    def get_state(self) -> AgentState:
        """获取当前状态"""
        return self._state

    def get_current_task(self) -> Optional[str]:
        """获取当前任务 ID"""
        return self._current_task

    def get_event_history(
        self,
        task_id: Optional[str] = None,
        limit: int = 50
    ) -> list[AgentLifecycleEvent]:
        """获取事件历史"""
        events = self._event_history
        if task_id:
            events = [e for e in events if e.task_id == task_id]
        return events[-limit:]

    def is_sleeping(self) -> bool:
        """是否正在睡眠"""
        return self._state == AgentState.SLEEPING


class AgentLifecycleManager:
    """
    Agent 生命周期管理器（阻塞版本）

    管理所有 Agent 的生命周期，提供真正的阻塞等待机制
    """

    def __init__(self, state_dir: Optional[Path] = None):
        """初始化生命周期管理器"""
        self._state_dir = state_dir
        self._agents: Dict[str, AgentBlockingSleepProtocol] = {}
        self._running = False

    async def start(self) -> None:
        """启动生命周期管理器"""
        if self._running:
            return

        self._running = True

        # 初始化所有 Agent 的阻塞睡眠协议
        for role in ["builder", "reviewer", "owner"]:
            state_file = self._state_dir / f"{role}_lifecycle.json" if self._state_dir else None
            self._agents[role] = AgentBlockingSleepProtocol(role, state_file)

        logger.info("Agent Lifecycle Manager (Blocking) started")

    async def stop(self) -> None:
        """停止生命周期管理器"""
        if not self._running:
            return

        self._running = False

        # 保存所有 Agent 状态
        for agent in self._agents.values():
            await agent._persist_state()

        logger.info("Agent Lifecycle Manager stopped")

    def get_agent(self, role: str) -> AgentBlockingSleepProtocol:
        """获取指定角色的 Agent 协议"""
        if role not in self._agents:
            raise ValueError(f"Unknown agent role: {role}")
        return self._agents[role]

    async def put_agent_to_sleep(
        self,
        role: str,
        task_id: str,
        wake_up_condition: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """让指定 Agent 进入阻塞睡眠"""
        agent = self.get_agent(role)
        return await agent.enter_blocking_sleep(
            task_id=task_id,
            wake_up_condition=wake_up_condition,
            timeout=timeout
        )

    async def wake_up_agent(
        self,
        role: str,
        task_id: str,
        reason: str = "manual_wake_up"
    ) -> bool:
        """唤醒阻塞睡眠的 Agent"""
        agent = self.get_agent(role)
        return await agent.wake_up(task_id, reason)

    def get_agent_states(self) -> Dict[str, str]:
        """获取所有 Agent 的状态"""
        return {
            role: agent.get_state().value
            for role, agent in self._agents.items()
        }


# 全局实例
_lifecycle_manager: Optional[AgentLifecycleManager] = None


def get_lifecycle_manager() -> AgentLifecycleManager:
    """获取全局生命周期管理器实例"""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        # 使用默认状态目录
        from src.config.settings import get_settings
        settings = get_settings()
        state_dir = settings.base_path / ".agent_lifecycle" if hasattr(settings, 'base_path') else None

        _lifecycle_manager = AgentLifecycleManager(state_dir)
    return _lifecycle_manager


def reset_lifecycle_manager() -> None:
    """重置生命周期管理器（主要用于测试）"""
    global _lifecycle_manager
    _lifecycle_manager = None
