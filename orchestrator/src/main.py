"""
命令行入口点
提供 CLI 接口来使用编排引擎
"""

import asyncio
import functools
import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from src.config.settings import get_settings
from src.core.event_bus import EventBus, get_event_bus
from src.core.listener import GitEventListener, TestResultListener
from src.core.trimmer import EvidenceTrimmer
from src.core.packager import EvidencePackager, ReviewOutputPackager, GoNoGoPackager
from src.core.injector import ReviewerInjector, NotificationInjector
from src.core.router import ArtifactRouter, RouteSummary
from src.models.events import BuildCompletedEvent, TestCompletedEvent, EventType
from src.models.artifacts import Artifact, ArtifactType
from src.models.review import ReviewReport
from src.utils.logger import setup_logging
from src.utils.validators import (
    validate_task_id,
    RollbackValidator,
)

# 初始化
console = Console()
logger = setup_logging("orchestrator")


def async_command(func):
    """Wrap async click commands so coroutines are executed."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper


@click.group()
@click.version_option(version="1.0.0")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--config", type=click.Path(), help="Path to config file")
def cli(debug: bool, config: Optional[str]):
    """
    软件开发 SOP 编排引擎

    让 SOP 真正运行起来的核心引擎
    """
    settings_kwargs = {}
    if debug:
        settings_kwargs["debug_mode"] = True
        settings_kwargs["log_level"] = "DEBUG"

    if config:
        import yaml
        with open(config) as f:
            config_data = yaml.safe_load(f)
            settings_kwargs.update(config_data)

    # 初始化设置
    settings = get_settings(**settings_kwargs)

    # 确保目录存在
    settings.ensure_directories()

    if debug:
        console.print("[yellow]Debug mode enabled[/yellow]")


@cli.command()
@click.argument("task_id")
@click.option("--commit", help="Git commit hash")
@click.option("--branch", default="main", help="Git branch")
@click.option("--diff-file", type=click.Path(), help="Path to diff file")
@click.option("--log-file", type=click.Path(), help="Path to build log file")
@click.option("--test-file", type=click.Path(), help="Path to test results file")
@click.option("--wait-for-review", is_flag=True, help="Wait for review to complete")
@async_command
async def review(task_id: str, commit: Optional[str], branch: str,
                diff_file: Optional[str], log_file: Optional[str],
                test_file: Optional[str], wait_for_review: bool):
    """
    触发完整的审查流程

    监听器 → 裁剪器 → 封装器 → 注入器 → 路由器
    """
    # 验证任务 ID
    is_valid, error = validate_task_id(task_id)
    if not is_valid:
        console.print(f"[red]Error:[/red] {error}")
        sys.exit(1)

    console.print(f"[blue]Starting review process for task:[/blue] {task_id}")

    # 初始化组件
    event_bus = get_event_bus()
    await event_bus.start()

    try:
        # 1. 获取构建信息
        if commit:
            build_event = BuildCompletedEvent(
                task_id=task_id,
                commit_hash=commit,
                branch=branch,
            )
        else:
            # 从 Git 获取
            git_listener = GitEventListener(Path.cwd(), event_bus)
            build_event = await git_listener.check_for_new_commits(task_id)
            if not build_event:
                console.print("[yellow]No new commits detected[/yellow]")
                sys.exit(0)

        console.print(f"[green]✓[/green] Build captured: {build_event.commit_hash[:8]}")

        # 2. 获取测试结果
        test_event = TestCompletedEvent(
            task_id=task_id,
            passed=True,
            total_tests=0,
            failed_tests=0,
            test_summary="No test results provided"
        )

        if test_file:
            test_listener = TestResultListener(event_bus)
            test_event = await test_listener.watch_test_results(Path(test_file), task_id)
            if test_event:
                console.print(f"[green]✓[/green] Tests captured: {test_event.total_tests} total, {test_event.failed_tests} failed")

        # 3. 裁剪数据
        trimmer = EvidenceTrimmer()

        if diff_file:
            diff_content = Path(diff_file).read_text(encoding='utf-8')
        else:
            # 从 Git 获取 diff
            import subprocess
            result = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD"],
                capture_output=True,
                text=True
            )
            diff_content = result.stdout

        if log_file:
            log_content = Path(log_file).read_text(encoding='utf-8')
        else:
            log_content = "No build log provided"

        trimmed_diff, trimmed_log = await trimmer.trim_build_output(log_content, diff_content)
        console.print("[green]✓[/green] Evidence trimmed")

        # 4. 封装为 Reviewer 输入
        packager = EvidencePackager()
        artifact = await packager.create_reviewer_input(
            task_id=task_id,
            build_event=build_event,
            test_event=test_event,
            diff_content=trimmed_diff,
            log_summary=trimmed_log
        )
        console.print("[green]✓[/green] Evidence packaged")

        # 5. 注入到 Reviewer
        injector = ReviewerInjector()
        review_report = await injector.inject_to_reviewer(artifact)

        if not review_report:
            console.print("[yellow]Review not completed (timeout or error)[/yellow]")
            console.print(f"[blue]Review request written to:[/blue] {get_settings().workspace_path / 'review_requests' / task_id}")
            sys.exit(0)

        console.print(f"[green]✓[/green] Review received: {review_report.decision.value} ({review_report.overall_score}/100)")

        # 6. 路由审查报告
        router = ArtifactRouter()
        from src.core.packager import ReviewOutputPackager

        output_packager = ReviewOutputPackager()
        report_artifact = await output_packager.package_review_output(
            task_id=task_id,
            reviewer_id=review_report.reviewer_id,
            review_content=review_report.to_json()
        )

        routed = await router.route(report_artifact)
        console.print(f"[green]✓[/green] Review routed to: {routed.full_path}")

        # 7. 检查是否可以继续
        if not review_report.can_proceed():
            console.print("[red]✗[/red] Review blocked: critical issues found")
            if review_report.critical_count > 0:
                console.print(f"[red]  Critical issues: {review_report.critical_count}[/red]")
            sys.exit(1)

        console.print("[green]✓[/green] Review process completed successfully")

    finally:
        await event_bus.stop()


@cli.command()
@click.argument("directory", type=click.Path(), default=".")
@click.option("--task-id", help="Task ID to associate events with")
@async_command
async def watch(directory: str, task_id: Optional[str]):
    """
    监听模式（自动处理事件）

    持续监听文件系统事件并自动触发处理流程
    """
    from src.core.listener import FileSystemWatcher

    watch_path = Path(directory).resolve()
    console.print(f"[blue]Watching directory:[/blue] {watch_path}")

    event_bus = get_event_bus()
    await event_bus.start()

    # 创建文件系统监听器
    if not task_id:
        task_id = "auto"

    fs_watcher = FileSystemWatcher(event_bus, task_id)
    fs_watcher.start(watch_path)

    try:
        console.print("[green]Watching for changes...[/green] Press Ctrl+C to stop")

        # 保持运行
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping watcher...[/yellow]")
    finally:
        fs_watcher.stop()
        await event_bus.stop()


@cli.command()
@click.argument("artifact", type=click.Path())
@async_command
async def route(artifact: str):
    """
    路由单个产物

    读取产物文件，解析 frontmatter，然后路由到正确的目录
    """
    artifact_path = Path(artifact)

    if not artifact_path.exists():
        console.print(f"[red]Error:[/red] File not found: {artifact_path}")
        sys.exit(1)

    console.print(f"[blue]Routing artifact:[/blue] {artifact_path}")

    router = ArtifactRouter()

    try:
        routed = await router.route_from_file(artifact_path)
        console.print(f"[green]✓[/green] Routed to: {routed.full_path}")
    except Exception as e:
        console.print(f"[red]Error routing artifact:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option("--output", type=click.Path(), help="Output file for summary")
@async_command
async def summary(output: Optional[str]):
    """
    生成路由摘要报告
    """
    console.print("[blue]Generating routing summary...[/blue]")

    route_summary = RouteSummary()
    data = await route_summary.generate_summary()
    markdown = route_summary.format_summary_markdown(data)

    if output:
        Path(output).write_text(markdown, encoding='utf-8')
        console.print(f"[green]✓[/green] Summary written to: {output}")
    else:
        console.print(markdown)


@cli.command()
@click.argument("task_id")
@click.argument("decision", type=click.Choice(["go", "no-go"]))
@click.option("--reviewer", help="Name of the reviewer who provided the report")
@click.option("--reasoning", required=True, help="Reasoning for the decision")
@click.option("--risk", multiple=True, help="Risks being accepted (can specify multiple)")
@click.option("--condition", multiple=True, help="Conditions for release (can specify multiple)")
@async_command
async def go_nogo(task_id: str, decision: str, reviewer: Optional[str],
                 reasoning: str, risk: tuple, condition: tuple):
    """
    创建 Go/No-Go 裁决记录

    这是唯一的权威放行入口
    """
    # 验证任务 ID
    is_valid, error = validate_task_id(task_id)
    if not is_valid:
        console.print(f"[red]Error:[/red] {error}")
        sys.exit(1)

    console.print(f"[blue]Creating Go/No-Go record for task:[/blue] {task_id}")

    # 获取最近的审查报告
    settings = get_settings()
    review_dir = settings.review_path

    # 查找最近的审查报告
    review_files = sorted(
        review_dir.glob(f"*-{task_id}-*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not review_files:
        console.print("[yellow]Warning:[/yellow] No review report found for this task")

        # 使用空摘要
        review_summary = "No review report available"
    else:
        # 读取最近的报告
        latest_report = review_files[0]
        review_summary = latest_report.read_text(encoding='utf-8')
        console.print(f"[green]✓[/green] Using review report: {latest_report.name}")

    # 创建 Go/No-Go 记录
    packager = GoNoGoPackager()
    artifact = await packager.create_go_nogo_record(
        task_id=task_id,
        decision_maker=reviewer or "Owner",
        decision=decision,
        review_summary=review_summary[:1000],  # 限制长度
        reasoning=reasoning,
        risks_accepted=list(risk),
        conditions=list(condition)
    )

    # 路由产物
    router = ArtifactRouter()
    routed = await router.route(artifact)

    console.print(f"[green]✓[/green] Go/No-Go record created: {routed.full_path}")
    console.print(f"[bold]Decision: {decision.upper()}[/bold]")


@cli.command()
@click.option("--session-id", required=True, help="Claude Code session ID")
@async_command
async def session_start(session_id: str):
    """
    触发会话开始事件（用于 Claude Code hook）
    """
    from src.core.injector import SessionInjector

    injector = SessionInjector()
    await injector.inject_session_start(session_id)

    console.print(f"[green]✓[/green] Session {session_id} started")


@cli.command()
@click.option("--session-id", required=True, help="Claude Code session ID")
@click.option("--summary", help="Session summary")
@async_command
async def session_end(session_id: str, summary: Optional[str]):
    """
    触发会话结束事件（用于 Claude Code hook）
    """
    from src.core.injector import SessionInjector

    injector = SessionInjector()
    await injector.inject_session_end(
        session_id=session_id,
        summary=summary or "No summary provided"
    )

    console.print(f"[green]✓[/green] Session {session_id} ended")


@cli.command()
@click.argument("event_type", type=click.Choice(["build.completed", "test.completed", "review.completed"]))
@click.option("--task-id", required=True, help="Task ID")
@click.option("--data", type=click.Path(), help="JSON file with event data")
@async_command
async def trigger(event_type: str, task_id: str, data: Optional[str]):
    """
    手动触发事件
    """
    event_type_enum = EventType(event_type)

    # 加载事件数据
    event_data = {"task_id": task_id}
    if data:
        with open(data) as f:
            event_data.update(json.load(f))

    # 创建事件
    from src.models.events import create_event
    event = create_event(event_type_enum, **event_data)

    # 发布事件
    event_bus = get_event_bus()
    event_bus.publish_sync(event)

    console.print(f"[green]✓[/green] Event triggered: {event_type} for task {task_id}")


@cli.command()
def validate():
    """
    验证编排引擎配置
    """
    console.print("[blue]Validating orchestrator configuration...[/blue]")

    settings = get_settings()

    # 检查目录
    table = Table(title="Directory Status")
    table.add_column("Directory", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Path", style="blue")

    directories = [
        ("Workspace", settings.workspace_path),
        ("Artifacts", settings.artifacts_path),
        ("Planning", settings.planning_path),
        ("Build", settings.build_path),
        ("Review", settings.review_path),
        ("Release", settings.release_path),
        ("Logs", settings.logs_path),
    ]

    all_valid = True
    for name, path in directories:
        exists = path.exists()
        writable = path.exists() and path.is_dir()

        if exists and writable:
            status = "✓ OK"
        else:
            status = "✗ ERROR"
            all_valid = False

        table.add_row(name, status, str(path))

    console.print(table)

    # 检查配置
    console.print("\n[bold]Configuration:[/bold]")
    console.print(f"  AI Backend: {settings.ai_backend}")
    console.print(f"  Log Level: {settings.log_level}")
    console.print(f"  Max Diff Size: {settings.max_diff_size} chars")
    console.print(f"  Evidence Freshness: {settings.evidence_freshness_threshold}s")

    if all_valid:
        console.print("\n[green]✓ All validations passed[/green]")
        sys.exit(0)
    else:
        console.print("\n[red]✗ Some validations failed[/red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
