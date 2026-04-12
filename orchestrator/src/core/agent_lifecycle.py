"""
Agent Lifecycle Protocol
Agent 生命周期协议：定义 Agent 的休眠、唤醒和状态管理
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


class AgentSleepProtocol:
    """
    Agent 休眠协议

    定义 Agent 在提交任务后如何休眠，以及如何被唤醒继续工作
    """

    def __init__(
        self,
        agent_role: str,
        state_file: Optional[Path] = None
    ):
        """
        初始化 Agent 休眠协议

        Args:
            agent_role: Agent 角色（builder/reviewer/owner）
            state_file: 状态文件路径
        """
        self.agent_role = agent_role
        self._state = AgentState.IDLE
        self._current_task: Optional[str] = None
        self._state_file = state_file
        self._sleep_conditions: Dict[str, Any] = {}
        self._wake_up_triggers: Dict[str, Callable] = {}
        self._event_history: list[AgentLifecycleEvent] = []

        # 从状态文件恢复
        if state_file and state_file.exists():
            self._restore_state()

    async def go_to_sleep(
        self,
        task_id: str,
        wake_up_condition: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Agent 进入休眠状态

        Args:
            task_id: 任务 ID
            wake_up_condition: 唤醒条件（如 "review_completed", "owner_decision"）
            timeout: 超时时间（秒）

        Returns:
            休眠状态信息
        """
        self._state = AgentState.SLEEPING
        self._current_task = task_id

        sleep_event = AgentLifecycleEvent(
            agent_role=self.agent_role,
            state=AgentState.SLEEPING,
            task_id=task_id,
            metadata={
                "wake_up_condition": wake_up_condition,
                "timeout": timeout
            }
        )

        self._record_event(sleep_event)
        await self._persist_state()

        logger.info(
            f"Agent {self.agent_role} going to sleep for task {task_id}. "
            f"Wake-up condition: {wake_up_condition}"
        )

        return {
            "state": "sleeping",
            "task_id": task_id,
            "wake_up_condition": wake_up_condition,
            "timeout": timeout,
            "instructions": f"Agent {self.agent_role} is now sleeping. "
                          f"It will be woken up when {wake_up_condition} occurs."
        }

    async def wait_for_wake_up(
        self,
        task_id: str,
        check_interval: float = 5.0,
        timeout: Optional[float] = None
    ) -> bool:
        """
        等待被唤醒

        Args:
            task_id: 任务 ID
            check_interval: 检查间隔（秒）
            timeout: 超时时间（秒）

        Returns:
            是否被成功唤醒
        """
        start_time = datetime.now().timestamp()

        while self._state == AgentState.SLEEPING:
            # 检查超时
            if timeout:
                elapsed = datetime.now().timestamp() - start_time
                if elapsed > timeout:
                    logger.warning(
                        f"Agent {self.agent_role} sleep timeout for task {task_id}"
                    )
                    self._state = AgentState.ERROR
                    await self._persist_state()
                    return False

            # 检查唤醒条件
            if await self._check_wake_up_condition(task_id):
                self._state = AgentState.IDLE
                wake_event = AgentLifecycleEvent(
                    agent_role=self.agent_role,
                    state=AgentState.IDLE,
                    task_id=task_id,
                    metadata={"wake_up_reason": "condition_met"}
                )
                self._record_event(wake_event)
                await self._persist_state()

                logger.info(f"Agent {self.agent_role} woken up for task {task_id}")
                return True

            # 等待下次检查
            await asyncio.sleep(check_interval)

        return False

    async def wake_up(
        self,
        task_id: str,
        reason: str = "manual_wake_up"
    ) -> bool:
        """
        手动唤醒 Agent

        Args:
            task_id: 任务 ID
            reason: 唤醒原因

        Returns:
            是否成功唤醒
        """
        if self._state != AgentState.SLEEPING:
            logger.warning(
                f"Cannot wake up agent {self.agent_role}: "
                f"not sleeping (current state: {self._state})"
            )
            return False

        self._state = AgentState.IDLE
        self._current_task = None

        wake_event = AgentLifecycleEvent(
            agent_role=self.agent_role,
            state=AgentState.IDLE,
            task_id=task_id,
            metadata={"wake_up_reason": reason}
        )
        self._record_event(wake_event)
        await self._persist_state()

        logger.info(f"Agent {self.agent_role} manually woken up for task {task_id}: {reason}")
        return True

    async def set_wake_up_trigger(
        self,
        condition: str,
        trigger_func: Callable
    ) -> None:
        """
        设置唤醒触发器

        Args:
            condition: 触发条件
            trigger_func: 触发函数（返回 bool）
        """
        self._wake_up_triggers[condition] = trigger_func
        logger.debug(f"Set wake-up trigger for condition: {condition}")

    async def _check_wake_up_condition(self, task_id: str) -> bool:
        """检查唤醒条件是否满足"""
        for condition, trigger_func in self._wake_up_triggers.items():
            try:
                if await trigger_func(task_id):
                    logger.debug(f"Wake-up condition met: {condition}")
                    return True
            except Exception as e:
                logger.error(f"Error checking wake-up condition {condition}: {e}")

        return False

    def _record_event(self, event: AgentLifecycleEvent) -> None:
        """记录生命周期事件"""
        self._event_history.append(event)
        # 保留最近 100 条事件
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


class AgentLifecycleManager:
    """
    Agent 生命周期管理器

    管理所有 Agent 的生命周期，提供统一的休眠/唤醒接口
    """

    def __init__(self, state_dir: Optional[Path] = None):
        """
        初始化生命周期管理器

        Args:
            state_dir: 状态文件目录
        """
        self._state_dir = state_dir
        self._agents: Dict[str, AgentSleepProtocol] = {}
        self._running = False

    async def start(self) -> None:
        """启动生命周期管理器"""
        if self._running:
            return

        self._running = True

        # 初始化所有 Agent 的休眠协议
        for role in ["builder", "reviewer", "owner"]:
            state_file = self._state_dir / f"{role}_lifecycle.json" if self._state_dir else None
            self._agents[role] = AgentSleepProtocol(role, state_file)

        logger.info("Agent Lifecycle Manager started")

    async def stop(self) -> None:
        """停止生命周期管理器"""
        if not self._running:
            return

        self._running = False

        # 保存所有 Agent 状态
        for agent in self._agents.values():
            await agent._persist_state()

        logger.info("Agent Lifecycle Manager stopped")

    def get_agent(self, role: str) -> AgentSleepProtocol:
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
        """让指定 Agent 进入休眠"""
        agent = self.get_agent(role)
        return await agent.go_to_sleep(task_id, wake_up_condition, timeout)

    async def wake_up_agent(
        self,
        role: str,
        task_id: str,
        reason: str = "manual_wake_up"
    ) -> bool:
        """唤醒指定 Agent"""
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
