"""
封装器模块
负责按统一模板生成 Reviewer 输入
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.models.events import BuildCompletedEvent, TestCompletedEvent
from src.models.artifacts import Artifact, FrontmatterMetadata, ArtifactType
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class EvidencePackager:
    """
    证据封装器
    将各种证据按统一模板封装为 Reviewer 可用的输入
    """

    def __init__(self):
        """初始化封装器"""
        self._settings = get_settings()

    async def create_reviewer_input(
        self,
        task_id: str,
        build_event: BuildCompletedEvent,
        test_event: TestCompletedEvent,
        diff_content: str,
        log_summary: str,
        additional_context: dict[str, Any] | None = None
    ) -> Artifact:
        """
        创建 Reviewer 输入产物

        Args:
            task_id: 任务 ID
            build_event: 构建完成事件
            test_event: 测试完成事件
            diff_content: 代码 diff 内容
            log_summary: 日志摘要
            additional_context: 额外上下文信息

        Returns:
            封装好的产物对象
        """
        # 生成内容
        content = self._generate_reviewer_input_content(
            task_id=task_id,
            build_event=build_event,
            test_event=test_event,
            diff_content=diff_content,
            log_summary=log_summary,
            additional_context=additional_context or {}
        )

        # 创建元数据
        metadata = FrontmatterMetadata(
            type=ArtifactType.EXECUTION_EVIDENCE,
            task_id=task_id,
            stage="review_preparation",
            status="ready",
            created_at=datetime.now(),
        )

        return Artifact(
            metadata=metadata,
            content=content
        )

    def _generate_reviewer_input_content(
        self,
        task_id: str,
        build_event: BuildCompletedEvent,
        test_event: TestCompletedEvent,
        diff_content: str,
        log_summary: str,
        additional_context: dict[str, Any]
    ) -> str:
        """
        生成 Reviewer 输入内容

        Args:
            task_id: 任务 ID
            build_event: 构建完成事件
            test_event: 测试完成事件
            diff_content: 代码 diff
            log_summary: 日志摘要
            additional_context: 额外上下文

        Returns:
            格式化的输入内容
        """
        sections = []

        # 标题
        sections.append(f"# Reviewer Input for Task: {task_id}")
        sections.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 任务信息
        sections.append("## Task Information")
        sections.append(f"- **Task ID**: {task_id}")
        sections.append(f"- **Commit**: `{build_event.commit_hash}`")
        sections.append(f"- **Branch**: {build_event.branch}")
        sections.append(f"- **Changed Files**: {len(build_event.changed_files)}")
        sections.append("")

        # 构建摘要
        sections.append("## Build Summary")
        if build_event.diff_summary:
            sections.append(f"```\n{build_event.diff_summary}\n```")
        else:
            sections.append("No build summary available.")
        sections.append("")

        # 测试结果
        sections.append("## Test Results")

        status_emoji = "✅ PASSED" if test_event.passed else "❌ FAILED"
        sections.append(f"- **Status**: {status_emoji}")
        sections.append(f"- **Total Tests**: {test_event.total_tests}")
        sections.append(f"- **Failed**: {test_event.failed_tests}")

        if test_event.coverage_percent:
            coverage_color = "🟢" if test_event.coverage_percent >= 80 else "🟡" if test_event.coverage_percent >= 60 else "🔴"
            sections.append(f"- **Coverage**: {coverage_color} {test_event.coverage_percent:.1f}%")

        sections.append(f"\n### Test Summary\n{test_event.test_summary}\n")

        # 代码变更
        sections.append("## Code Changes")
        sections.append("```diff")
        sections.append(diff_content)
        sections.append("```\n")

        # 构建日志
        sections.append("## Build Log Summary")
        sections.append(f"```\n{log_summary}\n```\n")

        # 额外上下文
        if additional_context:
            sections.append("## Additional Context")
            for key, value in additional_context.items():
                sections.append(f"### {key}")
                if isinstance(value, str):
                    sections.append(value)
                elif isinstance(value, list):
                    sections.append("\n".join(f"- {v}" for v in value))
                elif isinstance(value, dict):
                    sections.append("\n".join(f"- {k}: {v}" for k, v in value.items()))
                sections.append("")

        # 审查指引
        sections.append("## Review Guidelines")
        sections.append("""
Please review the changes and provide:

1. **Overall Assessment**: A score from 0-100
2. **Decision**: `approved`, `rejected`, or `conditional`
3. **Findings**: List all issues found with:
   - Severity level (critical/high/medium/low)
   - Category (security/performance/maintainability/etc.)
   - Description with evidence
   - Location (file:line)
   - Suggested fix (if applicable)

4. **Conditions**: For conditional approval, specify what needs to be fixed

**Output Format**: Please provide your review in structured JSON format.
""")

        return "\n".join(sections)


class ReviewOutputPackager:
    """
    审查输出封装器
    将 Reviewer 的输出封装为标准格式
    """

    def __init__(self):
        """初始化审查输出封装器"""
        self._settings = get_settings()

    async def package_review_output(
        self,
        task_id: str,
        reviewer_id: str,
        review_content: str
    ) -> Artifact:
        """
        封装审查输出

        Args:
            task_id: 任务 ID
            reviewer_id: 审查者 ID
            review_content: 审查内容（JSON 或 Markdown）

        Returns:
            封装好的审查报告产物
        """
        # 尝试解析 JSON
        try:
            import json
            review_data = json.loads(review_content)

            # 如果是 JSON，创建结构化报告
            content = self._format_review_as_markdown(review_data)
        except json.JSONDecodeError:
            # 如果不是 JSON，直接使用原内容
            content = review_content

        # 创建元数据
        metadata = FrontmatterMetadata(
            type=ArtifactType.REVIEW_REPORT,
            task_id=task_id,
            stage="review",
            status="ready",
            created_at=datetime.now(),
            author=reviewer_id,
        )

        return Artifact(
            metadata=metadata,
            content=content
        )

    def _format_review_as_markdown(self, review_data: dict) -> str:
        """
        将 JSON 格式的审查转换为 Markdown

        Args:
            review_data: 审查数据字典

        Returns:
            Markdown 格式的审查报告
        """
        sections = []

        # 标题
        decision = review_data.get("decision", "unknown")
        emoji = {"approved": "✅", "rejected": "❌", "conditional": "⚠️"}.get(decision, "❓")
        sections.append(f"# Review Report: {decision.upper()} {emoji}\n")

        # 基本信息
        sections.append("## Review Information")
        sections.append(f"- **Reviewer**: {review_data.get('reviewer_id', 'N/A')}")
        sections.append(f"- **Score**: {review_data.get('overall_score', 'N/A')}/100")
        sections.append(f"- **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 发现
        findings = review_data.get("findings", [])
        if findings:
            sections.append(f"## Findings ({len(findings)})")

            severity_order = ["critical", "high", "medium", "low"]
            for severity in severity_order:
                severity_findings = [f for f in findings if f.get("severity") == severity]
                if severity_findings:
                    sections.append(f"\n### {severity.upper()}")
                    for finding in severity_findings:
                        sections.append(f"\n#### {finding.get('title', 'Untitled')}")
                        sections.append(f"- **Category**: {finding.get('category', 'N/A')}")
                        sections.append(f"- **Location**: {finding.get('location', 'N/A')}")
                        sections.append(f"\n{finding.get('description', '')}")

                        if finding.get('evidence'):
                            sections.append(f"\n**Evidence**:\n```\n{finding['evidence']}\n```")

                        if finding.get('suggested_fix'):
                            sections.append(f"\n**Suggested Fix**: {finding['suggested_fix']}")

            sections.append("")

        # 条件
        if review_data.get('conditions'):
            sections.append("## Conditions")
            sections.append(review_data['conditions'])
            sections.append("")

        # 备注
        if review_data.get('notes'):
            sections.append("## Notes")
            sections.append(review_data['notes'])
            sections.append("")

        return "\n".join(sections)


class GoNoGoPackager:
    """
    Go/No-Go 封装器
    将 Owner 的决策封装为正式记录
    """

    def __init__(self):
        """初始化 Go/No-Go 封装器"""
        self._settings = get_settings()

    async def create_go_nogo_record(
        self,
        task_id: str,
        decision_maker: str,
        decision: str,  # "go" | "no-go"
        review_summary: str,
        reasoning: str,
        risks_accepted: list[str] | None = None,
        conditions: list[str] | None = None
    ) -> Artifact:
        """
        创建 Go/No-Go 记录

        Args:
            task_id: 任务 ID
            decision_maker: 决策者
            decision: 决策（go/no-go）
            review_summary: 审查摘要
            reasoning: 决策理由
            risks_accepted: 接受的风险列表
            conditions: 放行条件

        Returns:
            Go/No-Go 记录产物
        """
        content = self._generate_go_nogo_content(
            task_id=task_id,
            decision_maker=decision_maker,
            decision=decision,
            review_summary=review_summary,
            reasoning=reasoning,
            risks_accepted=risks_accepted or [],
            conditions=conditions or []
        )

        metadata = FrontmatterMetadata(
            type=ArtifactType.GO_NO_GO_RECORD,
            task_id=task_id,
            stage="release",
            status="approved" if decision == "go" else "rejected",
            created_at=datetime.now(),
            author=decision_maker,
        )

        return Artifact(
            metadata=metadata,
            content=content
        )

    def _generate_go_nogo_content(
        self,
        task_id: str,
        decision_maker: str,
        decision: str,
        review_summary: str,
        reasoning: str,
        risks_accepted: list[str],
        conditions: list[str]
    ) -> str:
        """生成 Go/No-Go 记录内容"""
        decision_emoji = "✅ GO" if decision == "go" else "❌ NO-GO"

        sections = [
            f"# Go/No-Go Decision: {decision_emoji}",
            "",
            "## Decision Details",
            f"- **Task**: {task_id}",
            f"- **Decision Maker**: {decision_maker}",
            f"- **Decision Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Decision**: {decision.upper()}",
            "",
            "## Reasoning",
            reasoning,
            ""
        ]

        if risks_accepted:
            sections.append("## Risks Accepted")
            for risk in risks_accepted:
                sections.append(f"- {risk}")
            sections.append("")

        if conditions:
            sections.append("## Conditions for Release")
            for condition in conditions:
                sections.append(f"- [ ] {condition}")
            sections.append("")

        sections.append("## Review Summary")
        sections.append(review_summary)
        sections.append("")

        sections.append("## Authorization")
        sections.append(f"Decision made by: {decision_maker}")
        sections.append(f"This decision is final and binding for task {task_id}.")

        return "\n".join(sections)
