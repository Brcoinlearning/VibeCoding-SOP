"""
监听器适配器
将 GitEventListener 适配为 MCP 工具可用的同步版本
移除 watchdog 依赖，保留 Git 命令执行逻辑
"""
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

# 添加项目路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.events import BuildCompletedEvent, TestCompletedEvent
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


class GitListenerAdapter:
    """
    Git 监听器适配器
    提供同步接口供 MCP 工具调用
    """

    def __init__(self, repo_path: Path):
        """
        初始化适配器

        Args:
            repo_path: Git 仓库路径
        """
        self.repo_path = repo_path

    def get_git_status(self, task_id: str, commit: Optional[str] = None) -> Optional[BuildCompletedEvent]:
        """
        获取 Git 状态（同步版本）

        Args:
            task_id: 关联的任务 ID
            commit: 指定的提交哈希（可选）

        Returns:
            构建完成事件对象
        """
        try:
            # 获取当前 commit
            if not commit:
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                commit = result.stdout.strip()

            # 获取分支名
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            branch = result.stdout.strip()

            # 获取变更的文件列表
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            changed_files = [
                f for f in result.stdout.strip().split('\n') if f
            ] if result.returncode == 0 else []

            # 获取 diff 摘要
            result = subprocess.run(
                ["git", "diff", "--stat", "HEAD~1", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            diff_summary = result.stdout.strip() if result.returncode == 0 else ""

            return BuildCompletedEvent(
                task_id=task_id,
                commit_hash=commit,
                branch=branch,
                diff_summary=diff_summary,
                changed_files=changed_files,
                timestamp=datetime.now()
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting git status: {e}", exc_info=True)
            return None

    def get_git_diff(self, base: str = "HEAD~1", head: str = "HEAD") -> str:
        """
        获取 Git diff（同步版本）

        Args:
            base: 基础提交
            head: 目标提交

        Returns:
            diff 内容
        """
        try:
            result = subprocess.run(
                ["git", "diff", base, head],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception as e:
            logger.error(f"Error getting git diff: {e}")
            return ""


class TestListenerAdapter:
    """
    测试监听器适配器
    提供同步接口供 MCP 工具调用
    """

    def __init__(self):
        """初始化适配器"""
        pass

    def parse_test_results(self, results_content: str, task_id: str) -> Optional[TestCompletedEvent]:
        """
        解析测试结果（同步版本）

        Args:
            results_content: 测试结果内容（JSON 格式）
            task_id: 任务 ID

        Returns:
            测试完成事件对象
        """
        try:
            import json

            data = json.loads(results_content)

            summary = data.get("summary", {})
            total = summary.get("total", 0)
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)

            # 尝试获取覆盖率
            coverage = None
            if "coverage" in data:
                coverage = data["coverage"].get("percent_covered")

            return TestCompletedEvent(
                task_id=task_id,
                passed=failed == 0,
                total_tests=total,
                failed_tests=failed,
                test_summary=f"{passed}/{total} tests passed",
                coverage_percent=coverage,
                timestamp=datetime.now()
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse test results JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing test results: {e}", exc_info=True)
            return None

    def find_test_results(self, repo_path: Path) -> Optional[Path]:
        """
        查找测试结果文件（同步版本）

        Args:
            repo_path: 仓库路径

        Returns:
            测试结果文件路径或 None
        """
        test_paths = [
            repo_path / "pytest_results.json",
            repo_path / "test-results.xml",
            repo_path / ".pytest_cache" / "results.json",
        ]

        for test_path in test_paths:
            if test_path.exists():
                return test_path

        return None
