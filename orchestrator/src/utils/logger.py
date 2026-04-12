"""
日志工具
提供统一的日志配置和处理
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler

from src.config.settings import get_settings


def setup_logging(name: str = "orchestrator") -> logging.Logger:
    """
    设置日志配置

    Args:
        name: 日志器名称

    Returns:
        配置好的 Logger 实例
    """
    settings = get_settings()
    logger = logging.getLogger(name)

    # 避免重复配置
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # 清除默认处理器
    logger.propagate = False

    # Rich 控制台处理器（带彩色输出）
    console_handler = RichHandler(
        rich_tracebacks=True,
        tracebacks_show_locals=settings.debug_mode,
        show_time=True,
        show_path=True,
    )
    console_handler.setLevel(logging.INFO)

    # 控制台格式
    console_formatter = logging.Formatter(
        "%(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(console_handler)

    # 文件处理器（带轮转）
    log_file = settings.logs_path / f"{name}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)

    # 文件格式
    file_formatter = logging.Formatter(settings.log_format)
    file_handler.setFormatter(file_formatter)

    logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取 Logger 实例

    Args:
        name: 日志器名称

    Returns:
        Logger 实例
    """
    return logging.getLogger(name)
