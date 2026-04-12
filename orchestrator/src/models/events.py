"""
事件定义模块
定义系统中所有事件类型和事件结构
"""

from enum import Enum
from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """事件类型枚举"""
    BUILD_COMPLETED = "build.completed"
    TEST_COMPLETED = "test.completed"
    REVIEW_COMPLETED = "review.completed"
    SESSION_START = "session.start"
    SESSION_END = "session.end"
    ERROR = "error"


class BaseEvent(BaseModel):
    """基础事件模型"""
    event_type: EventType
    task_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BuildCompletedEvent(BaseEvent):
    """构建完成事件"""
    event_type: EventType = EventType.BUILD_COMPLETED
    commit_hash: str
    branch: str
    diff_summary: Optional[str] = None
    changed_files: list[str] = Field(default_factory=list)


class TestCompletedEvent(BaseEvent):
    """测试完成事件"""
    event_type: EventType = EventType.TEST_COMPLETED
    passed: bool
    total_tests: int
    failed_tests: int
    test_summary: str
    coverage_percent: Optional[float] = None


class ReviewCompletedEvent(BaseEvent):
    """审查完成事件"""
    event_type: EventType = EventType.REVIEW_COMPLETED
    reviewer_id: str
    decision: str  # "approved" | "rejected" | "conditional"
    findings_count: int
    critical_issues: int
    review_report_path: str


class ErrorEvent(BaseEvent):
    """错误事件"""
    event_type: EventType = EventType.ERROR
    error_message: str
    error_type: str
    stack_trace: Optional[str] = None
    recovery_action: Optional[str] = None


# 事件工厂函数
def create_event(event_type: EventType, **kwargs) -> BaseEvent:
    """
    根据事件类型创建对应的事件对象

    Args:
        event_type: 事件类型
        **kwargs: 事件参数

    Returns:
        对应的事件对象

    Raises:
        ValueError: 事件类型不支持时
    """
    event_classes = {
        EventType.BUILD_COMPLETED: BuildCompletedEvent,
        EventType.TEST_COMPLETED: TestCompletedEvent,
        EventType.REVIEW_COMPLETED: ReviewCompletedEvent,
        EventType.ERROR: ErrorEvent,
    }

    event_class = event_classes.get(event_type)
    if event_class is None:
        raise ValueError(f"Unsupported event type: {event_type}")

    return event_class(event_type=event_type, **kwargs)
