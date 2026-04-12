"""
监听器模块
负责监听各种事件源（文件系统、Git、测试结果等）
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from src.models.events import BuildCompletedEvent, TestCompletedEvent, EventType
from src.core.event_bus import EventBus
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class GitEventListener:
    """
    Git 事件监听器
    监听 Git 仓库的提交、分支变更等事件
    """

    def __init__(self, repo_path: Path, event_bus: EventBus):
        """
        初始化 Git 监听器

        Args:
            repo_path: Git 仓库路径
            event_bus: 事件总线
        """
        self.repo_path = repo_path
        self.event_bus = event_bus
        self._last_known_commit: Optional[str] = None

    async def check_for_new_commits(self, task_id: str) -> Optional[BuildCompletedEvent]:
        """
        检查是否有新的提交

        Args:
            task_id: 关联的任务 ID

        Returns:
            如果有新提交则返回事件，否则返回 None
        """
        import subprocess

        try:
            # 获取当前 commit
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            current_commit = result.stdout.strip()

            # 检查是否有变化
            if self._last_known_commit == current_commit:
                return None

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
                ["git", "diff", "--name-only", f"{self._last_known_commit or 'HEAD~1'}", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            changed_files = [
                f for f in result.stdout.strip().split('\n') if f
            ] if result.returncode == 0 else []

            # 获取 diff 摘要
            result = subprocess.run(
                ["git", "diff", "--stat", f"{self._last_known_commit or 'HEAD~1'}", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            diff_summary = result.stdout.strip() if result.returncode == 0 else ""

            # 创建事件
            event = BuildCompletedEvent(
                task_id=task_id,
                commit_hash=current_commit,
                branch=branch,
                diff_summary=diff_summary,
                changed_files=changed_files,
                timestamp=datetime.now()
            )

            self._last_known_commit = current_commit
            return event

        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error checking for commits: {e}", exc_info=True)
            return None


class TestResultListener:
    """
    测试结果监听器
    监听测试执行结果文件或测试框架输出
    """

    def __init__(self, event_bus: EventBus):
        """
        初始化测试监听器

        Args:
            event_bus: 事件总线
        """
        self.event_bus = event_bus
        self._last_test_run: Optional[datetime] = None

    async def watch_test_results(self, results_path: Path, task_id: str) -> Optional[TestCompletedEvent]:
        """
        监听测试结果文件

        Args:
            results_path: 测试结果文件路径
            task_id: 关联的任务 ID

        Returns:
            如果检测到新的测试结果则返回事件
        """
        if not results_path.exists():
            return None

        # 检查文件修改时间
        mtime = datetime.fromtimestamp(results_path.stat().st_mtime)

        if self._last_test_run and mtime <= self._last_test_run:
            return None

        # 解析测试结果
        try:
            if results_path.suffix == ".xml":
                return await self._parse_junit_xml(results_path, task_id)
            elif results_path.name == "pytest_results.json":
                return await self._parse_pytest_json(results_path, task_id)
            else:
                logger.warning(f"Unsupported test result format: {results_path}")
                return None

        except Exception as e:
            logger.error(f"Error parsing test results: {e}", exc_info=True)
            return None

    async def _parse_junit_xml(self, xml_path: Path, task_id: str) -> Optional[TestCompletedEvent]:
        """解析 JUnit XML 格式的测试结果"""
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(xml_path)
            root = tree.getroot()

            # 提取测试统计
            tests = int(root.get("tests", 0))
            failures = int(root.get("failures", 0))
            errors = int(root.get("errors", 0))
            passed = tests - failures - errors

            # 构建摘要
            summary = f"Tests: {tests}, Passed: {passed}, Failed: {failures}, Errors: {errors}"

            event = TestCompletedEvent(
                task_id=task_id,
                passed=failedures == 0 and errors == 0,
                total_tests=tests,
                failed_tests=failures + errors,
                test_summary=summary,
                timestamp=datetime.fromtimestamp(xml_path.stat().st_mtime)
            )

            self._last_test_run = datetime.now()
            return event

        except Exception as e:
            logger.error(f"Error parsing JUnit XML: {e}", exc_info=True)
            return None

    async def _parse_pytest_json(self, json_path: Path, task_id: str) -> Optional[TestCompletedEvent]:
        """解析 pytest JSON 格式的测试结果"""
        try:
            import json

            with open(json_path) as f:
                data = json.load(f)

            summary = data.get("summary", {})
            total = summary.get("total", 0)
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)

            # 尝试获取覆盖率
            coverage = None
            if "coverage" in data:
                coverage = data["coverage"].get("percent_covered")

            event = TestCompletedEvent(
                task_id=task_id,
                passed=failed == 0,
                total_tests=total,
                failed_tests=failed,
                test_summary=f"{passed}/{total} tests passed",
                coverage_percent=coverage,
                timestamp=datetime.fromtimestamp(json_path.stat().st_mtime)
            )

            self._last_test_run = datetime.now()
            return event

        except Exception as e:
            logger.error(f"Error parsing pytest JSON: {e}", exc_info=True)
            return None


class FileSystemWatcher(FileSystemEventHandler):
    """
    文件系统监听器
    使用 watchdog 监听文件变化
    """

    def __init__(self, event_bus: EventBus, task_id: str):
        """
        初始化文件系统监听器

        Args:
            event_bus: 事件总线
            task_id: 关联的任务 ID
        """
        super().__init__()
        self.event_bus = event_bus
        self.task_id = task_id
        self.observer = Observer()

    def start(self, path: Path) -> None:
        """
        启动监听

        Args:
            path: 要监听的路径
        """
        self.observer.schedule(self, str(path), recursive=True)
        self.observer.start()
        logger.info(f"FileSystemWatcher started for {path}")

    def stop(self) -> None:
        """停止监听"""
        self.observer.stop()
        self.observer.join()
        logger.info("FileSystemWatcher stopped")

    def on_created(self, event: FileSystemEvent) -> None:
        """文件创建事件"""
        if event.is_directory:
            return

        path = Path(event.src_path)

        # 检查是否是测试结果文件
        if any(name in path.name for name in ["results", "report", "output"]):
            logger.info(f"Detected test result file: {path}")
            # 触发测试完成事件
            asyncio.create_task(self._handle_test_result(path))

    def on_modified(self, event: FileSystemEvent) -> None:
        """文件修改事件"""
        if event.is_directory:
            return

        path = Path(event.src_path)

        # 检查特定文件的变化
        if path.suffix in [".py", ".js", ".ts"]:
            logger.debug(f"Source file modified: {path}")
            # 可以触发代码分析等

    async def _handle_test_result(self, path: Path) -> None:
        """处理测试结果文件"""
        listener = TestResultListener(self.event_bus)
        event = await listener.watch_test_results(path, self.task_id)

        if event:
            await self.event_bus.publish(event)
