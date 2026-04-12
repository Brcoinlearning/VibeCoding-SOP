"""
审查模型定义
定义审查相关的数据结构和报告格式
"""

from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    """问题严重程度"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ReviewDecision(str, Enum):
    """审查决策"""
    APPROVED = "approved"
    REJECTED = "rejected"
    CONDITIONAL = "conditional"  # 有条件通过，需要修复后验证


class Finding(BaseModel):
    """
    审查发现
    每个问题都必须可复现并绑定证据
    """
    id: str
    severity: SeverityLevel
    category: str  # e.g., "security", "performance", "maintainability"
    title: str
    description: str
    evidence: str  # 必须绑定证据（代码片段、日志行号等）
    location: Optional[str] = None  # file:line
    suggested_fix: Optional[str] = None
    reproducible: bool = True  # 是否可复现


class ReviewReport(BaseModel):
    """
    结构化审查报告
    强制 JSON 输出格式
    """
    task_id: str
    reviewer_id: str
    review_date: datetime
    decision: ReviewDecision
    overall_score: float = Field(ge=0, le=100)  # 0-100 分
    findings: list[Finding] = Field(default_factory=list)

    # 统计信息
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    # 审查范围
    files_reviewed: list[str] = Field(default_factory=list)
    lines_of_code: int = 0
    test_coverage: Optional[float] = None

    # 备注
    notes: Optional[str] = None
    conditions: Optional[str] = None  # CONDITIONAL 决策时的条件说明

    def __init__(self, **data):
        super().__init__(**data)
        # 自动计算统计
        self.total_findings = len(self.findings)
        self.critical_count = sum(1 for f in self.findings if f.severity == SeverityLevel.CRITICAL)
        self.high_count = sum(1 for f in self.findings if f.severity == SeverityLevel.HIGH)
        self.medium_count = sum(1 for f in self.findings if f.severity == SeverityLevel.MEDIUM)
        self.low_count = sum(1 for f in self.findings if f.severity == SeverityLevel.LOW)

    def can_proceed(self) -> bool:
        """
        判断是否可以继续

        Returns:
            True 如果可以继续（approved 或 conditional 且无 critical 问题）
        """
        if self.decision == ReviewDecision.APPROVED:
            return True
        if self.decision == ReviewDecision.CONDITIONAL:
            return self.critical_count == 0
        return False

    def to_markdown(self) -> str:
        """
        转换为 Markdown 格式

        Returns:
            Markdown 字符串
        """
        decision_emoji = {
            ReviewDecision.APPROVED: "✅",
            ReviewDecision.REJECTED: "❌",
            ReviewDecision.CONDITIONAL: "⚠️",
        }

        md = f"""# Review Report

**Task ID**: {self.task_id}
**Reviewer**: {self.reviewer_id}
**Date**: {self.review_date.strftime('%Y-%m-%d %H:%M:%S')}
**Decision**: {decision_emoji.get(self.decision, '')} {self.decision.value.upper()}
**Score**: {self.overall_score}/100

## Summary

- Total Findings: {self.total_findings}
- Critical: {self.critical_count}
- High: {self.high_count}
- Medium: {self.medium_count}
- Low: {self.low_count}

"""

        if self.findings:
            md += "## Findings\n\n"
            for finding in self.findings:
                severity_emoji = {
                    SeverityLevel.CRITICAL: "🔴",
                    SeverityLevel.HIGH: "🟠",
                    SeverityLevel.MEDIUM: "🟡",
                    SeverityLevel.LOW: "🟢",
                    SeverityLevel.INFO: "🔵",
                }
                emoji = severity_emoji.get(finding.severity, "•")
                md += f"""### {emoji} [{finding.severity.value.upper()}] {finding.title}

**Category**: {finding.category}
**Location**: {finding.location or 'N/A'}

{finding.description}

**Evidence**:
```
{finding.evidence}
```

"""
                if finding.suggested_fix:
                    md += f"**Suggested Fix**: {finding.suggested_fix}\n\n"
        else:
            md += "## Findings\n\nNo findings reported. ✨\n\n"

        if self.conditions:
            md += f"""## Conditions

{self.conditions}

"""

        if self.notes:
            md += f"""## Notes

{self.notes}

"""

        return md


class GoNoGoRecord(BaseModel):
    """
    Go/No-Go 裁决记录
    唯一的权威放行入口
    """
    task_id: str
    decision_maker: str
    decision_time: datetime
    decision: str  # "go" | "no-go"
    review_report_summary: str
    risks_accepted: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    reasoning: str  # 裁决理由

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        decision_emoji = "✅ GO" if self.decision == "go" else "❌ NO-GO"

        return f"""# Go/No-Go Record

**Task ID**: {self.task_id}
**Decision Maker**: {self.decision_maker}
**Time**: {self.decision_time.strftime('%Y-%m-%d %H:%M:%S')}
**Decision**: {decision_emoji}

## Reasoning

{self.reasoning}

## Risks Accepted

{self._format_list(self.risks_accepted)}

## Conditions

{self._format_list(self.conditions)}

## Review Summary

{self.review_report_summary}
"""

    @staticmethod
    def _format_list(items: list[str]) -> str:
        if not items:
            return "None"
        return "\n".join(f"- {item}" for item in items)
