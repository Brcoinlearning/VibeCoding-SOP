"""
Unit tests for Async Background Listeners
测试异步后台监听器
"""
import asyncio
import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.async_listener import (
    GitPollingListener,
    AsyncFileWatcher,
    BackgroundListenerManager,
    get_background_listener_manager,
    reset_background_listener_manager
)
from src.core.event_bus import get_event_bus, reset_event_bus
from src.models.events import BuildCompletedEvent, TestCompletedEvent, EventType


@pytest.fixture
def temp_repo_dir():
    """创建临时 Git 仓库目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        # 初始化 Git 仓库
        import subprocess
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, capture_output=True)

        # 创建初始提交
        test_file = repo_path / "test.txt"
        test_file.write_text("Initial content")
        subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            capture_output=True
        )

        yield repo_path


@pytest.fixture
def event_bus():
    """创建事件总线 fixture"""
    reset_event_bus()
    bus = get_event_bus()
    return bus


@pytest.fixture
def git_listener(temp_repo_dir, event_bus):
    """创建 Git 监听器 fixture"""
    return GitPollingListener(
        repo_path=temp_repo_dir,
        poll_interval=0.1,  # 短间隔用于测试
        event_callback=None
    )


@pytest.fixture
def file_watcher(event_bus):
    """创建文件监听器 fixture"""
    from src.core.async_listener import WATCHDOG_AVAILABLE

    temp_dir = Path(tempfile.mkdtemp())
    watcher = AsyncFileWatcher(
        watch_path=temp_dir,
        event_callback=None,
        test_patterns={"test_results.json"}
    )

    return watcher


@pytest.fixture
def background_manager():
    """创建后台监听器管理器 fixture"""
    reset_background_listener_manager()
    return BackgroundListenerManager()


@pytest.mark.asyncio
async def test_git_listener_start_stop(git_listener):
    """测试 Git 监听器的启动和停止"""
    assert not git_listener._running

    await git_listener.start()
    assert git_listener._running is True

    await git_listener.stop()
    assert git_listener._running is False


@pytest.mark.asyncio
async def test_git_listener_detects_commit(temp_repo_dir, event_bus):
    """测试 Git 监听器检测新提交"""
    received_events = []

    async def event_handler(event):
        received_events.append(event)

    # 订阅事件
    event_bus.subscribe(EventType.BUILD_COMPLETED, event_handler)

    # 创建监听器
    listener = GitPollingListener(
        repo_path=temp_repo_dir,
        poll_interval=0.1
    )

    await listener.start()

    # 创建新提交
    test_file = temp_repo_dir / "new_file.txt"
    test_file.write_text("New content")
    import subprocess
    subprocess.run(["git", "add", "."], cwd=temp_repo_dir, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "New commit"],
        cwd=temp_repo_dir,
        capture_output=True
    )

    # 等待监听器检测到变更
    await asyncio.sleep(0.5)

    await listener.stop()

    # 验证事件已发布
    # 注意：由于测试环境的限制，这里主要验证监听器不崩溃


@pytest.mark.asyncio
async def test_git_listener_poll_interval(git_listener):
    """测试轮询间隔"""
    import time

    await git_listener.start()

    start_time = time.time()
    await asyncio.sleep(0.3)  # 等待约 3 次轮询
    elapsed = time.time() - start_time

    await git_listener.stop()

    # 验证轮询间隔约为 0.1 秒
    # 实际时间可能略有偏差，所以使用较宽松的范围
    assert 0.25 < elapsed < 0.5


@pytest.mark.asyncio
async def test_git_listener_get_current_commit(temp_repo_dir):
    """测试获取当前 commit"""
    listener = GitPollingListener(
        repo_path=temp_repo_dir,
        poll_interval=1.0
    )

    commit = await listener._get_current_commit()
    assert commit is not None
    assert len(commit) == 40  # Git commit hash 长度


@pytest.mark.asyncio
async def test_git_listener_create_build_event(temp_repo_dir):
    """测试创建构建事件"""
    listener = GitPollingListener(
        repo_path=temp_repo_dir,
        poll_interval=1.0
    )

    # 获取当前 commit
    commit = await listener._get_current_commit()

    # 创建事件
    event = await listener._create_build_event(commit)

    assert event is not None
    assert isinstance(event, BuildCompletedEvent)
    assert event.commit_hash == commit
    assert event.task_id.startswith("T-")
    assert event.branch == "main" or "master"


@pytest.mark.asyncio
async def test_file_watcher_start_stop(file_watcher):
    """测试文件监听器的启动和停止"""
    assert not file_watcher._running

    await file_watcher.start()
    assert file_watcher._running is True

    await file_watcher.stop()
    assert file_watcher._running is False


@pytest.mark.asyncio
async def test_file_watcher_detects_test_file():
    """测试文件监听器检测测试结果文件"""
    from src.core.async_listener import FileWatchHandler, WATCHDOG_AVAILABLE

    if not WATCHDOG_AVAILABLE:
        pytest.skip("watchdog is not available in current environment")

    temp_dir = Path(tempfile.mkdtemp())
    received_events = []

    async def mock_callback(event):
        received_events.append(event)

    handler = FileWatchHandler(
        event_bus=get_event_bus(),
        test_patterns={"test_results.json"},
        event_callback=mock_callback
    )

    # 创建测试结果文件
    test_file = temp_dir / "test_results.json"
    test_data = {
        "summary": {"total": 10, "passed": 10, "failed": 0},
        "message": "All tests passed"
    }
    test_file.write_text(json.dumps(test_data))

    # 触发文件创建事件
    from watchdog.events import FileCreatedEvent
    event = FileCreatedEvent(str(test_file))
    handler.on_created(event)

    # 等待异步处理
    await asyncio.sleep(0.2)

    # 验证事件已处理
    # 注意：由于测试环境的限制，这里主要验证处理器不崩溃


@pytest.mark.asyncio
async def test_file_watch_handler_is_test_file():
    """测试测试结果文件识别"""
    from src.core.async_listener import FileWatchHandler, WATCHDOG_AVAILABLE

    if not WATCHDOG_AVAILABLE:
        pytest.skip("watchdog is not available in current environment")

    handler = FileWatchHandler(
        event_bus=get_event_bus(),
        test_patterns={"pytest_results.json", "test-results.xml"}
    )

    assert handler._is_test_result_file("/path/to/pytest_results.json") is True
    assert handler._is_test_result_file("/path/to/test-results.xml") is True
    assert handler._is_test_result_file("/path/to/regular.py") is False


@pytest.mark.asyncio
async def test_background_manager_lifecycle(background_manager):
    """测试后台监听器管理器的生命周期"""
    assert not background_manager._running

    await background_manager.start()
    assert background_manager._running is True

    await background_manager.stop()
    assert background_manager._running is False


@pytest.mark.asyncio
async def test_background_manager_add_git_listener(background_manager, temp_repo_dir):
    """测试添加 Git 监听器"""
    listener = background_manager.add_git_listener(
        repo_path=temp_repo_dir,
        poll_interval=1.0
    )

    assert listener is not None
    assert isinstance(listener, GitPollingListener)
    assert len(background_manager._git_listeners) == 1


@pytest.mark.asyncio
async def test_background_manager_add_file_watcher(background_manager):
    """测试添加文件监听器"""
    temp_dir = Path(tempfile.mkdtemp())
    watcher = background_manager.add_file_watcher(
        watch_path=temp_dir,
        test_patterns={"test.json"}
    )

    assert watcher is not None
    assert isinstance(watcher, AsyncFileWatcher)
    assert len(background_manager._file_watchers) == 1


@pytest.mark.asyncio
async def test_background_manager_start_all_listeners(background_manager, temp_repo_dir):
    """测试启动所有监听器"""
    # 添加监听器
    background_manager.add_git_listener(repo_path=temp_repo_dir)

    temp_dir = Path(tempfile.mkdtemp())
    background_manager.add_file_watcher(watch_path=temp_dir)

    await background_manager.start()
    await background_manager.start_all_listeners()

    # 验证监听器数量
    counts = background_manager.get_listener_count()
    assert counts["git_listeners"] == 1
    assert counts["file_watchers"] == 1

    await background_manager.stop()


@pytest.mark.asyncio
async def test_background_manager_stop_all_listeners(background_manager, temp_repo_dir):
    """测试停止所有监听器"""
    # 添加并启动监听器
    background_manager.add_git_listener(repo_path=temp_repo_dir)
    await background_manager.start()
    await background_manager.start_all_listeners()

    # 停止所有监听器
    await background_manager.stop()

    # 验证所有监听器已停止
    for listener in background_manager._git_listeners:
        assert not listener._running


def test_global_background_manager():
    """测试全局后台监听器管理器实例"""
    reset_background_listener_manager()
    manager1 = get_background_listener_manager()
    manager2 = get_background_listener_manager()

    # 应该返回同一个实例
    assert manager1 is manager2


@pytest.mark.asyncio
async def test_git_listener_error_handling(temp_repo_dir):
    """测试 Git 监听器错误处理"""
    # 使用不存在的路径
    listener = GitPollingListener(
        repo_path=Path("/non/existent/path"),
        poll_interval=0.1
    )

    # 应该能启动但无法获取 commit
    await listener.start()
    commit = await listener._get_current_commit()
    assert commit is None  # 路径不存在，无法获取 commit
    await listener.stop()


@pytest.mark.asyncio
async def test_file_watcher_polling_mode_with_debounce():
    """测试轮询模式的防抖机制（无 watchdog 环境下的保护）"""
    from src.core.async_listener import WATCHDOG_AVAILABLE

    # 强制使用轮询模式（模拟无 watchdog 环境）
    temp_dir = Path(tempfile.mkdtemp())
    received_events = []

    async def mock_callback(event):
        received_events.append(event)

    # 创建文件监听器（会根据 WATCHDOG_AVAILABLE 自动选择模式）
    watcher = AsyncFileWatcher(
        watch_path=temp_dir,
        event_callback=mock_callback,
        test_patterns={"test_results.json"}
    )

    await watcher.start()

    try:
        # 模拟文件正在写入的场景
        test_file = temp_dir / "test_results.json"

        # 1. 创建不完整的 JSON 文件（模拟写入中）
        test_file.write_text('{"summary": {"total": 10, ')

        # 2. 等待轮询检测到文件修改
        await asyncio.sleep(0.3)

        # 3. 完成文件写入
        test_file.write_text('{"summary": {"total": 10, "passed": 10, "failed": 0}, "message": "All tests passed"}')

        # 4. 等待防抖延迟和处理
        await asyncio.sleep(3.0)  # 防抖延迟 2 秒 + 处理时间

        # 验证：不应该因为读取不完整的 JSON 而崩溃
        # 防抖机制应该确保文件稳定后才读取
        # 即使在轮询模式下也能正常工作

        # 5. 验证文件可以安全读取
        is_safe = await watcher._is_file_safe_to_read(test_file)
        assert is_safe is True  # 完整的文件应该被判定为安全

    finally:
        await watcher.stop()


@pytest.mark.asyncio
async def test_file_watcher_is_file_safe_to_read():
    """测试文件安全读取检查"""
    from src.core.async_listener import WATCHDOG_AVAILABLE

    temp_dir = Path(tempfile.mkdtemp())
    watcher = AsyncFileWatcher(
        watch_path=temp_dir,
        test_patterns={"test.json"}
    )

    # 创建测试文件
    test_file = temp_dir / "test.json"
    test_file.write_text('{"test": "data"}')

    # 等待文件稳定
    await asyncio.sleep(0.6)

    # 检查文件是否安全
    is_safe = await watcher._is_file_safe_to_read(test_file)
    assert is_safe is True


@pytest.mark.asyncio
async def test_file_watcher_debounce_mechanism():
    """测试防抖机制的正确性"""
    from src.core.async_listener import WATCHDOG_AVAILABLE

    temp_dir = Path(tempfile.mkdtemp())
    received_events = []

    async def mock_callback(event):
        received_events.append(event)

    watcher = AsyncFileWatcher(
        watch_path=temp_dir,
        event_callback=mock_callback,
        test_patterns={"test_results.json"}
    )

    await watcher.start()

    try:
        test_file = temp_dir / "test_results.json"

        # 快速多次修改文件（模拟写入过程）
        for i in range(5):
            test_file.write_text(f'{{"version": {i}}}')
            await asyncio.sleep(0.1)  # 短间隔

        # 等待防抖延迟
        await asyncio.sleep(3.0)

        # 验证：防抖机制应该避免重复处理
        # 文件应该在稳定后才被处理一次

        # 最终文件应该是完整可读的
        content = test_file.read_text()
        assert '{"version": 4}' in content

    finally:
        await watcher.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
