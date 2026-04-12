"""
配置管理
使用 Pydantic Settings 进行配置管理，支持环境变量和配置文件
"""

from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置
    支持通过环境变量、.env 文件或直接传参覆盖
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ORCHESTRATOR_",
        case_sensitive=False,
    )

    # 基础路径配置
    base_path: Path = Path.cwd()
    workspace_path: Path = Field(default_factory=lambda: Path.cwd() / "workspace")
    artifacts_path: Path = Field(default_factory=lambda: Path.cwd() / "artifacts")
    logs_path: Path = Field(default_factory=lambda: Path.cwd() / "logs")

    # 路由目录配置
    planning_dir: str = "20-planning"
    build_dir: str = "30-build"
    review_dir: str = "40-review"
    release_dir: str = "50-release"

    # 日志配置
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_max_bytes: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5

    # 事件处理配置
    enable_event_logging: bool = True
    event_queue_size: int = 1000
    event_processing_timeout: int = 300  # 秒

    # 证据收集配置
    max_diff_size: int = 50000  # 字符数
    max_log_lines: int = 1000
    evidence_freshness_threshold: int = 3600  # 秒，1小时

    # AI 集成配置
    ai_backend: str = "filesystem"  # filesystem | claude-api | custom
    claude_api_key: Optional[str] = None
    claude_model: str = "claude-3-opus-20240229"
    ai_timeout: int = 120

    # Claude Code 集成
    claude_code_hook_enabled: bool = True
    claude_code_session_id: Optional[str] = None

    # 重试配置
    max_retries: int = 3
    retry_delay: int = 5  # 秒

    # 回退配置
    auto_rollback_enabled: bool = True
    rollback_on_stale_evidence: bool = True
    rollback_on_missing_input: bool = True
    rollback_on_unstructured_output: bool = True

    # 通知配置
    notification_enabled: bool = True
    notification_method: str = "console"  # console | webhook | email

    # 开发模式
    debug_mode: bool = False
    mock_mode: bool = False  # 用于测试，不实际执行

    @property
    def planning_path(self) -> Path:
        return self.artifacts_path / self.planning_dir

    @property
    def build_path(self) -> Path:
        return self.artifacts_path / self.build_dir

    @property
    def review_path(self) -> Path:
        return self.artifacts_path / self.review_dir

    @property
    def release_path(self) -> Path:
        return self.artifacts_path / self.release_dir

    def ensure_directories(self) -> None:
        """确保所有必要的目录存在"""
        for path in [
            self.workspace_path,
            self.artifacts_path,
            self.logs_path,
            self.planning_path,
            self.build_path,
            self.review_path,
            self.release_path,
        ]:
            path.mkdir(parents=True, exist_ok=True)


# 全局配置实例
_settings: Optional[Settings] = None


def get_settings(**kwargs) -> Settings:
    """
    获取配置实例（单例模式）

    Args:
        **kwargs: 覆盖默认配置的参数

    Returns:
        Settings 实例
    """
    global _settings

    if _settings is None or kwargs:
        _settings = Settings(**kwargs)
        _settings.ensure_directories()

    return _settings


def reset_settings() -> None:
    """重置配置（主要用于测试）"""
    global _settings
    _settings = None
