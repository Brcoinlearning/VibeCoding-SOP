#!/usr/bin/env python3
"""
编排引擎演示脚本
展示完整的事件驱动工作流程
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import track

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import get_settings, reset_settings
from src.core.event_bus import EventBus, get_event_bus, reset_event_bus
from src.core.router import ArtifactRouter, RouteSummary
from src.core.packager import EvidencePackager, GoNoGoPackager
from src.models.events import BuildCompletedEvent, TestCompletedEvent, EventType
from src.models.review import ReviewReport, ReviewDecision, Finding, SeverityLevel
from src.utils.logger import setup_logging

console = Console()


class WorkflowDemo:
    """工作流程演示"""

    def __init__(self):
        """初始化演示"""
        self.console = console
        self.settings = get_settings()
        self.event_bus = get_event_bus()
        self.router = ArtifactRouter()

    async def run(self):
        """运行完整演示"""
        self._print_header()

        # 启动事件总线
        await self.event_bus.start()

        try:
            # 演示步骤
            await self._demo_step_1_build()
            await self._demo_step_2_test()
            await self._demo_step_3_package()
            await self._demo_step_4_review()
            await self._demo_step_5_route()
            await self._demo_step_6_go_nogo()
            await self._demo_step_7_summary()

        finally:
            await self.event_bus.stop()

        self._print_footer()

    def _print_header(self):
        """打印标题"""
        self.console.print("\n")
        self.console.print(Panel.fit(
            "[bold blue]SOP Orchestrator Demo[/bold blue]\n"
            "事件驱动交接协议 + I/O 托管与产物路由",
            border_style="blue"
        ))

    def _print_footer(self):
        """打印结尾"""
        self.console.print("\n")
        self.console.print(Panel.fit(
            "[green]✓ 演示完成！[/green]\n\n"
            "这就是让 SOP 真正运行起来的代码。\n"
            "[bold]Talk is cheap. Show me the code.[/bold]",
            border_style="green"
        ))

    async def _demo_step_1_build(self):
        """步骤 1：构建完成"""
        self.console.print("\n[bold cyan]步骤 1: 构建完成[/bold cyan]")

        # 模拟构建事件
        build_event = BuildCompletedEvent(
            task_id="DEMO-001",
            commit_hash="demo123abc456",
            branch="feature/demo",
            diff_summary="5 files changed, 42 insertions(+), 10 deletions(-)",
            changed_files=["src/demo.py", "tests/test_demo.py"]
        )

        # 发布事件
        await self.event_bus.publish(build_event)

        # 显示事件信息
        table = Table(show_header=False, box=None)
        table.add_row("事件类型", f"[yellow]{build_event.event_type}[/yellow]")
        table.add_row("任务 ID", build_event.task_id)
        table.add_row("提交哈希", f"[code]{build_event.commit_hash}[/code]")
        table.add_row("分支", build_event.branch)
        table.add_row("变更摘要", build_event.diff_summary)

        self.console.print(table)

        self.build_event = build_event

    async def _demo_step_2_test(self):
        """步骤 2：测试完成"""
        self.console.print("\n[bold cyan]步骤 2: 测试完成[/bold cyan]")

        # 模拟测试事件
        test_event = TestCompletedEvent(
            task_id="DEMO-001",
            passed=True,
            total_tests=100,
            failed_tests=0,
            test_summary="All 100 tests passed successfully",
            coverage_percent=87.5
        )

        # 发布事件
        await self.event_bus.publish(test_event)

        # 显示测试结果
        status = "[green]✓ PASSED[/green]" if test_event.passed else "[red]✗ FAILED[/red]"
        table = Table(show_header=False, box=None)
        table.add_row("事件类型", f"[yellow]{test_event.event_type}[/yellow]")
        table.add_row("测试状态", status)
        table.add_row("测试数量", f"{test_event.total_tests} 个")
        table.add_row("失败数量", f"{test_event.failed_tests} 个")
        table.add_row("覆盖率", f"[cyan]{test_event.coverage_percent}%[/cyan]")

        self.console.print(table)

        self.test_event = test_event

    async def _demo_step_3_package(self):
        """步骤 3：封装证据"""
        self.console.print("\n[bold cyan]步骤 3: 封装证据[/bold cyan]")

        # 创建证据包
        packager = EvidencePackager()

        sample_diff = """diff --git a/src/demo.py b/src/demo.py
index abc123..def456 789
--- a/src/demo.py
+++ b/src/demo.py
@@ -1,5 +1,10 @@
 def process(data):
+    # Validate input
+    if not data:
+        return None
     return data.upper()
+
+def cleanup():
+    pass
"""

        sample_log = """Build started at 12:00:00
Compiling src/demo.py...
Warning: Unused function 'cleanup'
Build completed in 0.5s
All tests passed"""

        artifact = await packager.create_reviewer_input(
            task_id="DEMO-001",
            build_event=self.build_event,
            test_event=self.test_event,
            diff_content=sample_diff,
            log_summary=sample_log
        )

        self.console.print(f"[green]✓[/green] 证据包已创建")
        self.console.print(f"  - 类型: [cyan]{artifact.metadata.type.value}[/cyan]")
        self.console.print(f"  - 阶段: [cyan]{artifact.metadata.stage}[/cyan]")
        self.console.print(f"  - 内容长度: [cyan]{len(artifact.content)} 字符[/cyan]")

        self.artifact = artifact

    async def _demo_step_4_review(self):
        """步骤 4：模拟审查"""
        self.console.print("\n[bold cyan]步骤 4: 模拟审查[/bold cyan]")

        # 创建模拟审查报告
        review_report = ReviewReport(
            task_id="DEMO-001",
            reviewer_id="demo-reviewer",
            review_date=datetime.now(),
            decision=ReviewDecision.APPROVED,
            overall_score=88,
            findings=[
                Finding(
                    id="F-001",
                    severity=SeverityLevel.LOW,
                    category="code-quality",
                    title="未使用的函数",
                    description="cleanup 函数定义后未被调用",
                    evidence="def cleanup(): pass",
                    location="src/demo.py:8",
                    suggested_fix="移除未使用的函数或添加文档说明其用途"
                )
            ],
            files_reviewed=["src/demo.py", "tests/test_demo.py"],
            lines_of_code=42,
            test_coverage=87.5,
            notes="代码质量良好，测试覆盖充分。"
        )

        # 显示审查结果
        decision_emoji = "✅" if review_report.decision == ReviewDecision.APPROVED else "❌"
        table = Table(show_header=False, box=None)
        table.add_row("审查者", review_report.reviewer_id)
        table.add_row("决策", f"{decision_emoji} {review_report.decision.value.upper()}")
        table.add_row("评分", f"[cyan]{review_report.overall_score}/100[/cyan]")
        table.add_row("发现问题", f"{len(review_report.findings)} 个")
        table.add_row("覆盖文件", f"{len(review_report.files_reviewed)} 个")

        self.console.print(table)

        self.review_report = review_report

    async def _demo_step_5_route(self):
        """步骤 5：路由产物"""
        self.console.print("\n[bold cyan]步骤 5: 路由产物[/bold cyan]")

        from src.core.packager import ReviewOutputPackager

        # 封装审查报告
        output_packager = ReviewOutputPackager()
        report_artifact = await output_packager.package_review_output(
            task_id="DEMO-001",
            reviewer_id=self.review_report.reviewer_id,
            review_content=self.review_report.model_dump_json()
        )

        # 路由产物
        routed = await self.router.route(report_artifact)

        self.console.print(f"[green]✓[/green] 审查报告已路由")
        self.console.print(f"  - 目标目录: [cyan]{routed.target_directory.name}[/cyan]")
        self.console.print(f"  - 文件名: [cyan]{routed.target_filename}[/cyan]")
        self.console.print(f"  - 完整路径: [cyan]{routed.full_path}[/cyan]")

        # 路由证据包
        evidence_routed = await self.router.route(self.artifact)
        self.console.print(f"[green]✓[/green] 证据包已路由")
        self.console.print(f"  - 目标目录: [cyan]{evidence_routed.target_directory.name}[/cyan]")

    async def _demo_step_6_go_nogo(self):
        """步骤 6：Go/No-Go 裁决"""
        self.console.print("\n[bold cyan]步骤 6: Go/No-Go 裁决[/bold cyan]")

        # 创建 Go/No-Go 记录
        packager = GoNoGoPackager()

        go_artifact = await packager.create_go_nogo_record(
            task_id="DEMO-001",
            decision_maker="Owner",
            decision="go",
            review_summary=self.review_report.to_markdown()[:500],
            reasoning="代码质量符合标准，测试覆盖充分，可以放行。",
            risks_accepted=["存在一个低优先级的代码质量问题"],
            conditions=["在下次迭代中清理未使用的函数"]
        )

        # 路由 Go/No-Go 记录
        routed = await self.router.route(go_artifact)

        self.console.print(f"[green]✓[/green] Go/No-Go 记录已创建")
        self.console.print(f"  - 决策: [bold green]GO ✓[/bold green]")
        self.console.print(f"  - 决策者: {go_artifact.metadata.author}")
        self.console.print(f"  - 目标目录: [cyan]{routed.target_directory.name}[/cyan]")

    async def _demo_step_7_summary(self):
        """步骤 7：生成摘要"""
        self.console.print("\n[bold cyan]步骤 7: 生成摘要[/bold cyan]")

        # 生成路由摘要
        summary = RouteSummary()
        data = await summary.generate_summary()

        # 显示统计
        table = Table(title="产物统计摘要")
        table.add_column("指标", style="cyan")
        table.add_column("数值", style="green")

        table.add_row("总产物数", str(data["total_artifacts"]))

        for artifact_type, count in data["by_type"].items():
            table.add_row(f"  - {artifact_type}", str(count))

        for status, count in data["by_status"].items():
            table.add_row(f"  - {status}", str(count))

        self.console.print(table)


async def main():
    """主函数"""
    # 设置日志
    setup_logging("demo")

    # 运行演示
    demo = WorkflowDemo()
    await demo.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]演示已中断[/yellow]")
    except Exception as e:
        console.print(f"\n[red]错误: {e}[/red]")
        import traceback
        traceback.print_exc()
