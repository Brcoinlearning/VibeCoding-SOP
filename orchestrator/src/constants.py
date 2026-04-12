"""
SOP Orchestrator 系统常量与模板
系统级指令硬编码 - 人类无需关注这些细节
"""
from enum import Enum
from typing import Dict

# =============================================================================
# 产物路由规则（系统内部实现细节）
# =============================================================================

class ArtifactType(str, Enum):
    """产物类型枚举"""
    REQUIREMENT_CONTRACT = "requirement_contract"
    EXECUTION_EVIDENCE = "execution_evidence"
    REVIEW_REPORT = "review_report"
    GO_NO_GO_RECORD = "go_no_go_record"


class ArtifactStatus(str, Enum):
    """产物状态枚举"""
    DRAFT = "draft"
    READY = "ready"
    APPROVED = "approved"
    REJECTED = "rejected"


# 路由映射规则：产物类型 -> 目标目录
ARTIFACT_ROUTING_RULES: Dict[str, str] = {
    ArtifactType.REQUIREMENT_CONTRACT: "20-planning",
    ArtifactType.EXECUTION_EVIDENCE: "30-build",
    ArtifactType.REVIEW_REPORT: "40-review",
    ArtifactType.GO_NO_GO_RECORD: "50-release",
}

# 文件命名规则模板
FILENAME_TEMPLATE = "{task_id}-{artifact_type}-{timestamp}.md"
TIMESTAMP_FORMAT = "%Y%m%d-%H%M"

# =============================================================================
# 审查系统提示词（系统内部实现细节）
# =============================================================================

REVIEWER_SYSTEM_PROMPT = """You are a senior code reviewer. Your task is to:
1. Analyze the provided code changes for bugs, security issues, and best practices
2. Assess risks and provide actionable feedback
3. Make a recommendation: GO (approve) or NO-GO (reject)
4. Return findings in structured JSON format

Focus on:
- Critical bugs and security vulnerabilities
- Performance issues
- Code maintainability
- Test coverage gaps
- Documentation completeness"""

REVIEW_INPUT_TEMPLATE = """# Code Review Request

## Task Information
- **Task ID**: {task_id}
- **Commit**: {commit_hash}
- **Branch**: {branch}
- **Timestamp**: {timestamp}

## Code Changes
{diff_content}

## Test Results
{test_summary}

## Additional Context
{additional_context}

Please provide your review in the following JSON format:
{{
  "decision": "approved" | "rejected" | "conditional",
  "overall_score": 0-100,
  "findings": [
    {{
      "severity": "critical" | "high" | "medium" | "low",
      "category": "string",
      "title": "string",
      "description": "string",
      "location": "string",
      "suggested_fix": "string"
    }}
  ],
  "conditions": "string",
  "notes": "string"
}}
"""

# =============================================================================
# Go/No-Go 裁决模板（系统内部实现细节）
# =============================================================================

GO_NO_GO_TEMPLATE = """# Go/No-Go Decision: {decision_emoji}

## Decision Details
- **Task**: {task_id}
- **Decision Maker**: {decision_maker}
- **Decision Time**: {timestamp}
- **Decision**: {decision_upper}

## Reasoning
{reasoning}

{risks_section}

{conditions_section}

## Review Summary
{review_summary}

## Authorization
Decision made by: {decision_maker}
This decision is final and binding for task {task_id}.
"""

# =============================================================================
# 审查报告模板（系统内部实现细节）
# =============================================================================

REVIEW_REPORT_TEMPLATE = """# Review Report: {decision_upper} {emoji}

## Review Information
- **Reviewer**: {reviewer_id}
- **Score**: {overall_score}/100
- **Date**: {date}

{findings_section}

{conditions_section}

{notes_section}
"""

# =============================================================================
# 系统配置常量
# =============================================================================

# 证据收集限制
MAX_DIFF_SIZE = 50000  # 字符数
MAX_LOG_LINES = 1000
EVIDENCE_FRESHNESS_THRESHOLD = 3600  # 秒，1小时

# 工作流阶段
WORKFLOW_STAGES = {
    "planning": "20-planning",
    "build": "30-build",
    "review": "40-review",
    "release": "50-release",
}

# 默认超时设置
DEFAULT_AI_TIMEOUT = 120  # 秒
DEFAULT_RETRY_DELAY = 5  # 秒
MAX_RETRIES = 3
