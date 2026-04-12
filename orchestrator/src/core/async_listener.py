"""
Async Background Listeners
实现异步后台监听器，恢复主动监听能力
"""
import asyncio
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Set

# Try to import watchdog, provide fallback if not available
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None
    FileCreatedEvent = None
    FileModifiedEvent = None
    logging.warning("watchdog package not available. File watching will be disabled. Install with: pip install watchdog>=4.0.0")

from src.config.settings import get_settings
from src.core.event_bus import get_event_bus
from src.models.events import BuildCompletedEvent, TestCompletedEvent
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


class GitPollingListener:
    """
    异步 Git 轮询监听器
    监听 Git 仓库的变更并发布构建完成事件
    """

    def __init__(
        self,
        repo_path: Path,
        poll_interval: float = 5.0,
        event_callback: Optional[Callable] = None
    ):
        """
        初始化 Git 轮询监听器

        Args:
            repo_path: Git 仓库路径
            poll_interval: 轮询间隔（秒）
            event_callback: 事件回调函数
        """
        self.repo_path = repo_path
        self.poll_interval = poll_interval
        self.event_callback = event_callback
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_commit: Optional[str] = None
        self._event_bus = get_event_bus()

    async def start(self) -> None:
        """启动监听器"""
        if self._running:
            logger.warning("GitPollingListener is already running")
            return

        self._running = True
        # 获取初始 commit
        self._last_commit = await self._get_current_commit()

        self._task = asyncio.create_task(self._poll_loop())
        logger.info(
            f"GitPollingListener started for {self.repo_path} "
            f"with interval {self.poll_interval}s"
        )

    async def stop(self) -> None:
        """停止监听器"""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("GitPollingListener stopped")

    async def _poll_loop(self) -> None:
        """轮询循环"""
        while self._running:
            try:
                # 检查是否有新的 commit
                current_commit = await self._get_current_commit()

                if current_commit and current_commit != self._last_commit:
                    logger.info(
                        f"New commit detected: {current_commit[:8]} "
                        f"(previous: {self._last_commit[:8] if self._last_commit else 'None'})"
                    )

                    # 获取变更信息
                    event = await self._create_build_event(current_commit)

                    if event:
                        # 发布事件
                        await self._event_bus.publish(event)

                        # 调用回调
                        if self.event_callback:
                            await self.event_callback(event)

                    self._last_commit = current_commit

                # 等待下一次轮询
                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Git polling loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def _get_current_commit(self) -> Optional[str]:
        """获取当前 commit"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get current commit: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting current commit: {e}", exc_info=True)
            return None

    async def _create_build_event(self, commit_hash: str) -> Optional[BuildCompletedEvent]:
        """创建构建完成事件"""
        try:
            # 获取分支名
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            branch = result.stdout.strip()

            # 获取变更文件
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{commit_hash}~1", commit_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            changed_files = [
                f for f in result.stdout.strip().split('\n') if f
            ] if result.returncode == 0 else []

            # 获取 diff 摘要
            result = subprocess.run(
                ["git", "diff", "--stat", f"{commit_hash}~1", commit_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            diff_summary = result.stdout.strip() if result.returncode == 0 else ""

            # 生成任务 ID（基于时间戳）
            task_id = f"T-{int(datetime.now().timestamp())}"

            return BuildCompletedEvent(
                task_id=task_id,
                commit_hash=commit_hash,
                branch=branch,
                diff_summary=diff_summary,
                changed_files=changed_files,
                timestamp=datetime.now()
            )

        except Exception as e:
            logger.error(f"Error creating build event: {e}", exc_info=True)
            return None


class FileWatchHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """
    文件监听处理器
    监听测试结果文件并发布测试完成事件

    注意：当 watchdog 不可用时，此类不会被使用（AsyncFileWatcher 会使用轮询模式）
    """

    def __init__(
        self,
        event_bus,
        test_patterns: Optional[Set[str]] = None,
        event_callback: Optional[Callable] = None
    ):
        """
        初始化文件监听处理器

        Args:
            event_bus: 事件总线
            test_patterns: 测试文件模式集合
            event_callback: 事件回调函数
        """
        if not WATCHDOG_AVAILABLE:
            raise RuntimeError("FileWatchHandler requires watchdog package. Install with: pip install watchdog>=4.0.0")

        self._event_bus = event_bus
        self._test_patterns = test_patterns or {
            "pytest_results.json",
            "test-results.xml",
            ".pytest_cache/results.json"
        }
        self._event_callback = event_callback

        # 文件处理防抖：避免同一文件在写入过程中被多次处理
        self._processing_files: dict[str, asyncio.Task] = {}
        self._file_modification_times: dict[str, float] = {}

    def on_created(self, event):
        """文件创建时触发"""
        if event.is_directory:
            return

        if self._is_test_result_file(event.src_path):
            logger.info(f"Test result file created: {event.src_path}")
            asyncio.create_task(self._process_test_file(event.src_path))

    def on_modified(self, event):
        """文件修改时触发"""
        if event.is_directory:
            return

        if self._is_test_result_file(event.src_path):
            logger.info(f"Test result file modified: {event.src_path}")
            # 使用防抖机制，避免在文件写入过程中重复触发
            asyncio.create_task(self._process_test_file_with_debounce(event.src_path))

    def _is_test_result_file(self, file_path: str) -> bool:
        """判断是否为测试结果文件"""
        file_name = Path(file_path).name
        return any(pattern in file_path for pattern in self._test_patterns)

    async def _process_test_file_with_debounce(self, file_path: str) -> None:
        """
        防抖处理测试结果文件，解决文件 I/O 竞态条件问题

        问题：当大型测试框架（如 pytest）写入结果文件时，文件会被多次修改。
        直接读取可能遇到 JSON 未完成的情况，导致解析失败。

        解决方案：
        1. 防抖：等待文件稳定（不再修改）一段时间后再处理
        2. 文件写入完成检测：检查文件是否还在被写入
        3. 重试机制：如果解析失败，等待后重试
        """
        try:
            file_path_str = str(file_path)
            debounce_delay = 2.0

            # 记录文件修改时间（使用当前文件的实际 mtime）
            try:
                file_mtime = Path(file_path).stat().st_mtime
            except FileNotFoundError:
                logger.debug(f"File {file_path} no longer exists, skipping")
                return

            self._file_modification_times[file_path_str] = file_mtime

            # 防抖延迟：等待文件稳定（2秒内没有新的修改）
            await asyncio.sleep(debounce_delay)

            # 再次检查文件是否仍在被修改（重新获取 mtime）
            try:
                current_mtime = Path(file_path).stat().st_mtime
            except FileNotFoundError:
                logger.debug(f"File {file_path} no longer exists after sleep, skipping")
                return

            # 如果文件被修改过（有其他调用更新了时间戳），跳过此次处理
            if file_path_str in self._file_modification_times:
                last_mod_time = self._file_modification_times[file_path_str]
                # 如果文件的当前 mtime 与记录的不同，说明有新的修改
                if current_mtime != last_mod_time:
                    logger.debug(f"File {file_path} was modified during debounce, skipping")
                    return

            # 检查文件是否可以安全读取
            if not await self._is_file_safe_to_read(file_path):
                logger.debug(f"File {file_path} not safe to read yet, skipping")
                return

            # 尝试处理文件，带重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    event = await self._create_test_event(file_path)
                    if event:
                        await self._event_bus.publish(event)

                        if self._event_callback:
                            await self._event_callback(event)

                        logger.info(f"Successfully processed test file: {file_path}")
                        break
                    else:
                        logger.warning(f"Failed to create event from {file_path} (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1.0)

                except json.JSONDecodeError as e:
                    logger.warning(
                        f"JSON decode error for {file_path} (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2.0)
                    else:
                        logger.error(f"Failed to parse {file_path} after {max_retries} attempts")
                        break

                except Exception as e:
                    logger.error(f"Error processing test file {file_path}: {e}", exc_info=True)
                    break

        except Exception as e:
            logger.error(f"Error in debounced file processing: {e}", exc_info=True)

    async def _is_file_safe_to_read(self, file_path: str) -> bool:
        """检查文件是否可以安全读取（不再被写入）"""
        try:
            path = Path(file_path)
            if not path.exists():
                return False

            # 检查文件大小是否稳定
            size1 = path.stat().st_size
            await asyncio.sleep(0.5)
            size2 = path.stat().st_size

            if size1 != size2:
                return False

            return True

        except Exception as e:
            logger.debug(f"Error checking if file is safe to read: {e}")
            return False

    async def _process_test_file(self, file_path: str) -> None:
        """处理测试结果文件"""
        try:
            event = await self._create_test_event(file_path)
            if event:
                await self._event_bus.publish(event)

                if self._event_callback:
                    await self._event_callback(event)

        except Exception as e:
            logger.error(f"Error processing test file {file_path}: {e}", exc_info=True)

    async def _create_test_event(self, file_path: str) -> Optional[TestCompletedEvent]:
        """创建测试完成事件"""
        try:
            import json

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 生成任务 ID
            task_id = f"T-{int(datetime.now().timestamp())}"

            # 解析测试数据（根据不同格式调整）
            if "summary" in data:
                summary = data["summary"]
                return TestCompletedEvent(
                    task_id=task_id,
                    passed=summary.get("passed", summary.get("total", 0) == summary.get("passed", 0)),
                    total_tests=summary.get("total", 0),
                    failed_tests=summary.get("failed", 0),
                    test_summary=data.get("message", ""),
                    coverage_percent=data.get("coverage"),
                    timestamp=datetime.now()
                )
            elif "tests" in data:
                # pytest 格式
                tests = data["tests"]
                total = len(tests)
                failed = sum(1 for t in tests if t.get("outcome") == "failed")

                return TestCompletedEvent(
                    task_id=task_id,
                    passed=failed == 0,
                    total_tests=total,
                    failed_tests=failed,
                    test_summary=f"Ran {total} tests, {failed} failed",
                    timestamp=datetime.now()
                )
            else:
                # 默认格式
                return TestCompletedEvent(
                    task_id=task_id,
                    passed=data.get("passed", True),
                    total_tests=data.get("total", 0),
                    failed_tests=data.get("failed", 0),
                    test_summary=data.get("summary", ""),
                    coverage_percent=data.get("coverage"),
                    timestamp=datetime.now()
                )

        except Exception as e:
            logger.error(f"Error creating test event from {file_path}: {e}", exc_info=True)
            return None


class AsyncFileWatcher:
    """
    异步文件监听器
    使用 watchdog 监听文件系统变更（如果可用）
    否则使用轮询降级方案
    """

    def __init__(
        self,
        watch_path: Path,
        event_callback: Optional[Callable] = None,
        test_patterns: Optional[Set[str]] = None
    ):
        """
        初始化异步文件监听器

        Args:
            watch_path: 监听路径
            event_callback: 事件回调函数
            test_patterns: 测试文件模式集合
        """
        self.watch_path = watch_path
        self.event_callback = event_callback
        self.test_patterns = test_patterns
        self._running = False
        self._observer: Optional[Observer] = None
        self._event_bus = get_event_bus()
        self._use_polling = not WATCHDOG_AVAILABLE
        self._poll_task: Optional[asyncio.Task] = None
        self._last_modification_times: dict[str, float] = {}

        if self._use_polling:
            logger.warning(
                f"watchdog not available, using polling fallback for {watch_path}. "
                "Install watchdog for better performance: pip install watchdog>=4.0.0"
            )

    async def start(self) -> None:
        """启动监听器"""
        if self._running:
            logger.warning("AsyncFileWatcher is already running")
            return

        self._running = True

        if self._use_polling:
            # 使用轮询降级方案
            self._poll_task = asyncio.create_task(self._poll_loop())
            logger.info(f"AsyncFileWatcher started (polling mode) for {self.watch_path}")
        else:
            # 使用 watchdog
            try:
                self._observer = Observer()
                handler = FileWatchHandler(
                    event_bus=self._event_bus,
                    test_patterns=self.test_patterns,
                    event_callback=self.event_callback
                )
                self._observer.schedule(handler, str(self.watch_path), recursive=True)
                self._observer.start()
                logger.info(f"AsyncFileWatcher started (watchdog mode) for {self.watch_path}")
            except Exception as e:
                logger.error(f"Failed to start watchdog observer: {e}, falling back to polling")
                self._use_polling = True
                self._poll_task = asyncio.create_task(self._poll_loop())
                logger.info(f"AsyncFileWatcher started (fallback polling mode) for {self.watch_path}")

    async def stop(self) -> None:
        """停止监听器"""
        if not self._running:
            return

        self._running = False

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        if self._observer:
            self._observer.stop()
            self._observer.join()

        logger.info("AsyncFileWatcher stopped")

    async def _poll_loop(self) -> None:
        """轮询循环（降级方案）"""
        poll_interval = 2.0  # 2秒轮询间隔

        while self._running:
            try:
                await self._check_files()
                await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}", exc_info=True)
                await asyncio.sleep(poll_interval)

    async def _check_files(self) -> None:
        """检查文件变更（轮询模式）"""
        try:
            # 递归检查目录中的文件
            for root, dirs, files in os.walk(self.watch_path):
                for file in files:
                    file_path = Path(root) / file
                    if self._is_test_result_file(str(file_path)):
                        await self._check_file_modification(file_path)
        except Exception as e:
            logger.error(f"Error checking files: {e}", exc_info=True)

    async def _check_file_modification(self, file_path: Path) -> None:
        """检查文件是否被修改"""
        try:
            stat = file_path.stat()
            mtime = stat.st_mtime
            file_str = str(file_path)

            if file_str not in self._last_modification_times:
                self._last_modification_times[file_str] = mtime
                return  # 新文件，不触发（首次扫描）

            if mtime > self._last_modification_times[file_str]:
                self._last_modification_times[file_str] = mtime
                logger.info(f"Detected file modification: {file_path}")
                await self._process_test_file(file_path)
        except FileNotFoundError:
            # 文件被删除，忽略
            pass
        except Exception as e:
            logger.error(f"Error checking file modification: {e}", exc_info=True)

    def _is_test_result_file(self, file_path: str) -> bool:
        """判断是否为测试结果文件"""
        file_name = Path(file_path).name
        if not self.test_patterns:
            return False
        return any(pattern in file_name for pattern in self.test_patterns)

    async def _process_test_file(self, file_path: Path) -> None:
        """处理测试结果文件（带防抖和重试机制，解决轮询模式竞态条件）"""
        try:
            if self._use_polling:
                # 轮询模式使用防抖处理，避免文件写入过程中的竞态条件
                await self._process_test_file_with_debounce(file_path)
            else:
                # watchdog 模式直接处理（已由 FileWatchHandler 处理防抖）
                event = await self._create_test_event(file_path)
                if event:
                    await self._event_bus.publish(event)

                    if self.event_callback:
                        await self.event_callback(event)
        except Exception as e:
            logger.error(f"Error processing test file {file_path}: {e}", exc_info=True)

    async def _process_test_file_with_debounce(self, file_path: Path) -> None:
        """
        防抖处理测试结果文件，解决轮询模式的文件 I/O 竞态条件问题

        问题：轮询模式下，检测到文件修改时直接读取可能遇到：
        1. 文件正在写入中，JSON 未完成
        2. 大型测试结果文件写入需要时间
        3. 解析失败导致事件丢失

        解决方案：
        1. 防抖延迟：等待文件稳定
        2. 文件写入完成检测：检查文件大小是否稳定
        3. 重试机制：解析失败时重试
        """
        try:
            file_path_str = str(file_path)
            debounce_delay = 2.0

            # 记录文件修改时间（使用当前文件的实际 mtime）
            try:
                file_mtime = file_path.stat().st_mtime
            except FileNotFoundError:
                logger.debug(f"File {file_path} no longer exists, skipping")
                return

            self._last_modification_times[file_path_str] = file_mtime

            # 防抖延迟：等待文件稳定（2秒内没有新的修改）
            await asyncio.sleep(debounce_delay)

            # 再次检查文件是否仍在被修改（重新获取 mtime）
            try:
                current_mtime = file_path.stat().st_mtime
            except FileNotFoundError:
                logger.debug(f"File {file_path} no longer exists after sleep, skipping")
                return

            # 如果文件被修改过（有其他调用更新了时间戳），跳过此次处理
            if file_path_str in self._last_modification_times:
                last_mod_time = self._last_modification_times[file_path_str]
                # 如果文件的当前 mtime 与记录的不同，说明有新的修改
                if current_mtime != last_mod_time:
                    logger.debug(f"File {file_path} was modified during debounce, skipping")
                    return

            # 检查文件是否可以安全读取
            if not await self._is_file_safe_to_read(file_path):
                logger.debug(f"File {file_path} not safe to read yet, skipping")
                return

            # 尝试处理文件，带重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    event = await self._create_test_event(file_path)
                    if event:
                        await self._event_bus.publish(event)

                        if self.event_callback:
                            await self.event_callback(event)

                        logger.info(f"Successfully processed test file: {file_path}")
                        break
                    else:
                        logger.warning(f"Failed to create event from {file_path} (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1.0)

                except Exception as e:
                    import json
                    if isinstance(e, json.JSONDecodeError):
                        logger.warning(
                            f"JSON decode error for {file_path} (attempt {attempt + 1}/{max_retries}): {e}"
                        )
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2.0)
                        else:
                            logger.error(f"Failed to parse {file_path} after {max_retries} attempts")
                            break
                    else:
                        logger.error(f"Error processing test file {file_path}: {e}", exc_info=True)
                        break

        except Exception as e:
            logger.error(f"Error in debounced file processing: {e}", exc_info=True)

    async def _is_file_safe_to_read(self, file_path: Path) -> bool:
        """检查文件是否可以安全读取（不再被写入）"""
        try:
            if not file_path.exists():
                return False

            # 检查文件大小是否稳定
            size1 = file_path.stat().st_size
            await asyncio.sleep(0.5)
            size2 = file_path.stat().st_size

            if size1 != size2:
                return False

            return True

        except Exception as e:
            logger.debug(f"Error checking if file is safe to read: {e}")
            return False

    async def _create_test_event(self, file_path: Path) -> Optional[TestCompletedEvent]:
        """创建测试完成事件（从 FileWatchHandler 复制的逻辑）"""
        try:
            import json

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 生成任务 ID
            task_id = f"T-{int(datetime.now().timestamp())}"

            # 解析测试数据（根据不同格式调整）
            if "summary" in data:
                summary = data["summary"]
                return TestCompletedEvent(
                    task_id=task_id,
                    passed=summary.get("passed", summary.get("total", 0) == summary.get("passed", 0)),
                    total_tests=summary.get("total", 0),
                    failed_tests=summary.get("failed", 0),
                    test_summary=data.get("message", ""),
                    coverage_percent=data.get("coverage"),
                    timestamp=datetime.now()
                )
            elif "tests" in data:
                # pytest 格式
                tests = data["tests"]
                total = len(tests)
                failed = sum(1 for t in tests if t.get("outcome") == "failed")

                return TestCompletedEvent(
                    task_id=task_id,
                    passed=failed == 0,
                    total_tests=total,
                    failed_tests=failed,
                    test_summary=f"Ran {total} tests, {failed} failed",
                    timestamp=datetime.now()
                )
            else:
                # 默认格式
                return TestCompletedEvent(
                    task_id=task_id,
                    passed=data.get("passed", True),
                    total_tests=data.get("total", 0),
                    failed_tests=data.get("failed", 0),
                    test_summary=data.get("summary", ""),
                    coverage_percent=data.get("coverage"),
                    timestamp=datetime.now()
                )

        except Exception as e:
            logger.error(f"Error creating test event from {file_path}: {e}", exc_info=True)
            return None


class BackgroundListenerManager:
    """
    后台监听器管理器
    管理所有后台监听器的生命周期
    """

    def __init__(self):
        """初始化后台监听器管理器"""
        self._git_listeners: list[GitPollingListener] = []
        self._file_watchers: list[AsyncFileWatcher] = []
        self._running = False

    async def start(self) -> None:
        """启动所有监听器"""
        if self._running:
            logger.warning("BackgroundListenerManager is already running")
            return

        self._running = True
        logger.info("BackgroundListenerManager started")

    async def stop(self) -> None:
        """停止所有监听器"""
        if not self._running:
            return

        self._running = False

        # 停止所有 Git 监听器
        for listener in self._git_listeners:
            await listener.stop()

        # 停止所有文件监听器
        for watcher in self._file_watchers:
            await watcher.stop()

        logger.info("BackgroundListenerManager stopped")

    def add_git_listener(
        self,
        repo_path: Path,
        poll_interval: float = 5.0,
        event_callback: Optional[Callable] = None
    ) -> GitPollingListener:
        """
        添加 Git 监听器

        Args:
            repo_path: Git 仓库路径
            poll_interval: 轮询间隔（秒）
            event_callback: 事件回调函数

        Returns:
            GitPollingListener 实例
        """
        listener = GitPollingListener(
            repo_path=repo_path,
            poll_interval=poll_interval,
            event_callback=event_callback
        )
        self._git_listeners.append(listener)

        if self._running:
            asyncio.create_task(listener.start())

        return listener

    def add_file_watcher(
        self,
        watch_path: Path,
        event_callback: Optional[Callable] = None,
        test_patterns: Optional[Set[str]] = None
    ) -> AsyncFileWatcher:
        """
        添加文件监听器

        Args:
            watch_path: 监听路径
            event_callback: 事件回调函数
            test_patterns: 测试文件模式集合

        Returns:
            AsyncFileWatcher 实例
        """
        watcher = AsyncFileWatcher(
            watch_path=watch_path,
            event_callback=event_callback,
            test_patterns=test_patterns
        )
        self._file_watchers.append(watcher)

        if self._running:
            asyncio.create_task(watcher.start())

        return watcher

    async def start_all_listeners(self) -> None:
        """启动所有已添加的监听器"""
        # 启动所有 Git 监听器
        for listener in self._git_listeners:
            await listener.start()

        # 启动所有文件监听器
        for watcher in self._file_watchers:
            await watcher.start()

        logger.info("All background listeners started")

    def get_listener_count(self) -> dict[str, int]:
        """获取监听器数量"""
        return {
            "git_listeners": len(self._git_listeners),
            "file_watchers": len(self._file_watchers)
        }


# 全局实例
_background_listener_manager: Optional[BackgroundListenerManager] = None


def get_background_listener_manager() -> BackgroundListenerManager:
    """
    获取全局后台监听器管理器实例

    Returns:
        BackgroundListenerManager 实例
    """
    global _background_listener_manager
    if _background_listener_manager is None:
        _background_listener_manager = BackgroundListenerManager()
    return _background_listener_manager


def reset_background_listener_manager() -> None:
    """重置后台监听器管理器（主要用于测试）"""
    global _background_listener_manager
    _background_listener_manager = None
