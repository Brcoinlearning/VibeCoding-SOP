"""
校验器模块
提供各种数据校验功能
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from pydantic import ValidationError

from src.models.artifacts import Artifact, ArtifactType
from src.models.review import ReviewReport, ReviewDecision, SeverityLevel
from src.config.settings import get_settings


class EvidenceValidator:
    """
    证据校验器
    验证证据的新鲜度、完整性等
    """

    def __init__(self):
        """初始化证据校验器"""
        self._settings = get_settings()

    def validate_freshness(self, timestamp: datetime) -> tuple[bool, Optional[str]]:
        """
        验证证据新鲜度

        Args:
            timestamp: 证据时间戳

        Returns:
            (是否新鲜, 错误消息)
        """
        threshold = timedelta(seconds=self._settings.evidence_freshness_threshold)
        age = datetime.now() - timestamp

        if age > threshold:
            minutes = int(age.total_seconds() / 60)
            return False, f"Evidence is stale ({minutes} minutes old, threshold is {threshold.seconds // 60} minutes)"

        return True, None

    def validate_completeness(self, evidence: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        验证证据完整性

        Args:
            evidence: 证据数据

        Returns:
            (是否完整, 缺失字段列表)
        """
        required_fields = [
            "task_id",
            "build_info",
            "test_info",
            "diff_content",
            "log_summary"
        ]

        missing = []

        for field in required_fields:
            if field not in evidence or evidence[field] is None:
                missing.append(field)

        return len(missing) == 0, missing

    def validate_diff_size(self, diff_content: str) -> tuple[bool, Optional[str]]:
        """
        验证 diff 大小

        Args:
            diff_content: diff 内容

        Returns:
            (是否有效, 错误消息)
        """
        if len(diff_content) == 0:
            return False, "Diff content is empty"

        if len(diff_content) > self._settings.max_diff_size:
            return False, f"Diff content too large ({len(diff_content)} chars, max is {self._settings.max_diff_size})"

        return True, None


class ReviewValidator:
    """
    审查校验器
    验证审查报告的完整性和格式
    """

    def validate_report_structure(self, report_data: dict) -> tuple[bool, list[str]]:
        """
        验证审查报告结构

        Args:
            report_data: 报告数据

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        # 必需字段
        required_fields = [
            "task_id",
            "reviewer_id",
            "decision",
            "overall_score",
            "findings"
        ]

        for field in required_fields:
            if field not in report_data:
                errors.append(f"Missing required field: {field}")

        # 验证决策
        if "decision" in report_data:
            valid_decisions = ["approved", "rejected", "conditional"]
            if report_data["decision"] not in valid_decisions:
                errors.append(f"Invalid decision: {report_data['decision']}")

        # 验证分数
        if "overall_score" in report_data:
            score = report_data["overall_score"]
            if not isinstance(score, (int, float)) or not (0 <= score <= 100):
                errors.append(f"Invalid score: {score} (must be 0-100)")

        # 验证 findings
        if "findings" in report_data:
            findings = report_data["findings"]
            if not isinstance(findings, list):
                errors.append("findings must be a list")
            else:
                for i, finding in enumerate(findings):
                    finding_errors = self._validate_finding(finding, i)
                    errors.extend(finding_errors)

        return len(errors) == 0, errors

    def _validate_finding(self, finding: dict, index: int) -> list[str]:
        """
        验证单个发现

        Args:
            finding: 发现数据
            index: 索引

        Returns:
            错误列表
        """
        errors = []

        required_fields = ["severity", "category", "title", "description", "evidence"]
        for field in required_fields:
            if field not in finding:
                errors.append(f"Finding #{index}: Missing required field '{field}'")

        # 验证严重程度
        if "severity" in finding:
            valid_severities = ["critical", "high", "medium", "low", "info"]
            if finding["severity"] not in valid_severities:
                errors.append(f"Finding #{index}: Invalid severity '{finding['severity']}'")

        # 验证可复现性
        if "evidence" in finding and not finding["evidence"].strip():
            errors.append(f"Finding #{index}: Evidence cannot be empty")

        return errors

    def validate_decision_consistency(self, report: ReviewReport) -> tuple[bool, Optional[str]]:
        """
        验证决策一致性

        Args:
            report: 审查报告

        Returns:
            (是否一致, 错误消息)
        """
        # 如果有 critical 问题，不能是 approved
        if report.decision == ReviewDecision.APPROVED and report.critical_count > 0:
            return False, "Cannot approve with critical issues"

        # 如果是 conditional，必须说明条件
        if report.decision == ReviewDecision.CONDITIONAL and not report.conditions:
            return False, "Conditional approval requires conditions"

        # 如果 rejected，分数应该较低
        if report.decision == ReviewDecision.REJECTED and report.overall_score > 50:
            return False, f"Low score ({report.overall_score}) inconsistent with rejection"

        return True, None


class ArtifactValidator:
    """
    产物校验器
    验证产物的格式和元数据
    """

    def validate_file_format(self, file_path: Path) -> tuple[bool, list[str]]:
        """
        验证产物文件格式

        Args:
            file_path: 文件路径

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        if not file_path.exists():
            errors.append(f"File does not exist: {file_path}")
            return False, errors

        if file_path.suffix != ".md":
            errors.append(f"File must be .md format: {file_path}")

        try:
            content = file_path.read_text(encoding='utf-8')

            # 检查 frontmatter
            if not content.startswith("---"):
                errors.append("Missing frontmatter delimiter")
            else:
                # 检查第二个分隔符
                if "\n---\n" not in content[4:]:
                    errors.append("Invalid frontmatter format")

        except Exception as e:
            errors.append(f"Error reading file: {e}")

        return len(errors) == 0, errors

    def validate_filename(self, filename: str) -> tuple[bool, Optional[str]]:
        """
        验证文件名格式

        Args:
            filename: 文件名

        Returns:
            (是否有效, 错误消息)
        """
        # 期望格式: {task_id}-{type}-{timestamp}.md
        pattern = r'^[A-Z0-9-]+-[a-z_]+-\d{8}-\d{4}\.md$'

        if not re.match(pattern, filename):
            return False, f"Invalid filename format: {filename} (expected: TASK-ID-type-YYYYMMDD-HHMM.md)"

        return True, None


class RollbackValidator:
    """
    回退校验器
    判断是否需要触发回退
    """

    def __init__(self):
        """初始化回退校验器"""
        self._settings = get_settings()
        self._evidence_validator = EvidenceValidator()
        self._review_validator = ReviewValidator()

    async def should_rollback(
        self,
        evidence: dict[str, Any],
        review_report: Optional[dict] = None
    ) -> tuple[bool, str]:
        """
        判断是否应该回退

        Args:
            evidence: 证据数据
            review_report: 审查报告（可选）

        Returns:
            (是否回退, 原因)
        """
        settings = self._settings

        # 检查证据新鲜度
        if settings.rollback_on_stale_evidence:
            timestamp = evidence.get("timestamp", datetime.now())
            is_fresh, error = self._evidence_validator.validate_freshness(timestamp)
            if not is_fresh:
                return True, f"Stale evidence: {error}"

        # 检查证据完整性
        if settings.rollback_on_missing_input:
            is_complete, missing = self._evidence_validator.validate_completeness(evidence)
            if not is_complete:
                return True, f"Missing evidence: {', '.join(missing)}"

        # 检查审查报告格式
        if review_report and settings.rollback_on_unstructured_output:
            is_valid, errors = self._review_validator.validate_report_structure(review_report)
            if not is_valid:
                return True, f"Invalid review format: {', '.join(errors[:3])}"

        return False, ""


def validate_task_id(task_id: str) -> tuple[bool, Optional[str]]:
    """
    验证任务 ID 格式

    Args:
        task_id: 任务 ID

    Returns:
        (是否有效, 错误消息)
    """
    if not task_id:
        return False, "Task ID cannot be empty"

    # 期望格式: T-数字 或 TASK-数字
    pattern = r'^(T|TASK)-\d+$'

    if not re.match(pattern, task_id):
        return False, f"Invalid task ID format: {task_id} (expected: T-123 or TASK-123)"

    return True, None


def validate_commit_hash(commit_hash: str) -> tuple[bool, Optional[str]]:
    """
    验证 Git commit hash 格式

    Args:
        commit_hash: commit hash

    Returns:
        (是否有效, 错误消息)
    """
    if not commit_hash:
        return False, "Commit hash cannot be empty"

    # Git hash 通常是 40 字符的十六进制（完整）或 7+ 字符（短哈希）
    pattern = r'^[0-9a-f]{7,40}$'

    if not re.match(pattern, commit_hash):
        return False, f"Invalid commit hash format: {commit_hash}"

    return True, None
