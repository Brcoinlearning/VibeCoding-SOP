#!/usr/bin/env python3
"""
Review Validator Module
验证审查输入的完整性和格式
"""
from typing import Dict, Tuple, List, Optional
from enum import Enum


class SeverityLevel(Enum):
    """严重级别枚举"""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class RecommendationType(Enum):
    """建议类型枚举"""
    GO = "go"
    NO_GO = "no-go"
    CONDITIONAL = "conditional"


def validate_review_input(review_data: Dict) -> Tuple[bool, str, List[str]]:
    """
    验证审查输入的完整性

    Args:
        review_data: 审查数据

    Returns:
        (is_valid, error_message, warnings)
    """
    errors = []
    warnings = []

    # 必需字段检查
    required_fields = [
        "severity",
        "lethal_flaw",
        "exploit_path",
        "evidence",
        "recommendation"
    ]

    for field in required_fields:
        if field not in review_data:
            errors.append(f"Missing required field: {field}")
        elif not review_data[field]:
            errors.append(f"Field cannot be empty: {field}")

    # 验证severity
    if "severity" in review_data:
        valid_severities = [s.value for s in SeverityLevel]
        if review_data["severity"] not in valid_severities:
            errors.append(
                f"Invalid severity: {review_data['severity']}. "
                f"Must be one of {valid_severities}"
            )

    # 验证recommendation
    if "recommendation" in review_data:
        valid_recommendations = [r.value for r in RecommendationType]
        if review_data["recommendation"] not in valid_recommendations:
            errors.append(
                f"Invalid recommendation: {review_data['recommendation']}. "
                f"Must be one of {valid_recommendations}"
            )

    # 验证evidence结构
    if "evidence" in review_data and isinstance(review_data["evidence"], dict):
        evidence = review_data["evidence"]
        if "test_case" not in evidence:
            errors.append("Evidence must contain 'test_case' reference")

        # 检查evidence中的关键字段
        if "test_case" in evidence and not evidence["test_case"]:
            warnings.append("Evidence 'test_case' is empty")

    # 验证exploit_path格式
    if "exploit_path" in review_data:
        exploit_path = review_data["exploit_path"]
        if exploit_path and exploit_path.lower() not in ["n/a", "none", ""]:
            if not is_stepwise_format(exploit_path):
                warnings.append(
                    "Exploit path should be in step-by-step format. "
                    "Use: 步骤1: ... 步骤2: ... or Step 1: ... Step 2: ..."
                )

    # 严重级别与lethal_flaw的一致性检查
    if "severity" in review_data and "lethal_flaw" in review_data:
        if review_data["severity"] == SeverityLevel.CRITICAL.value:
            if not review_data["lethal_flaw"] or len(review_data["lethal_flaw"]) < 20:
                warnings.append(
                    "CRITICAL severity requires detailed lethal_flaw description"
                )

    # 判断是否有效
    is_valid = len(errors) == 0
    error_message = "; ".join(errors) if errors else ""

    return is_valid, error_message, warnings


def is_stepwise_format(text: str) -> bool:
    """
    检查文本是否为逐步格式

    判断标准:
    - 包含 "步骤" 或 "Step"
    - 包含数字编号 (1., 2.)
    - 包含箭头符号 (→, ->)
    """
    if not text:
        return False

    step_indicators = [
        "步骤1", "步骤2", "步骤 1", "步骤 2",
        "Step 1", "Step 2", "step1", "step2",
        "→", "->", "\n1.", "\n2.",
        "\n- ", "\n* "
    ]

    return any(indicator in text for indicator in step_indicators)


def verify_evidence_reference(evidence: Dict, test_case: str) -> bool:
    """
    验证证据引用是否有效

    Args:
        evidence: 来自fetch_and_trim_evidence的证据
        test_case: 测试用例引用

    Returns:
        是否找到对应的证据
    """
    # 检查test_results中的failed_test_cases
    test_results = evidence.get("artifacts", {}).get("test_results", {})
    failed_cases = test_results.get("failed_test_cases", [])

    for case in failed_cases:
        # 检查name或nodeid是否匹配
        if test_case in [case.get("name", ""), case.get("nodeid", "")]:
            return True

    # 检查是否在test_summary中
    test_summary = test_results.get("test_summary", "")
    if test_case in test_summary:
        return True

    # 模糊匹配
    for case in failed_cases:
        case_name = case.get("name", "")
        if test_case.lower() in case_name.lower() or case_name.lower() in test_case.lower():
            return True

    return False


def check_severity_consistency(lethal_flaw: str, severity: str) -> Tuple[bool, str]:
    """
    检查严重级别与缺陷类型的一致性

    Args:
        lethal_flaw: 致命缺陷描述
        severity: 严重级别

    Returns:
        (is_consistent, message)
    """
    # 定义每种严重级别对应的关键词
    severity_keywords = {
        SeverityLevel.CRITICAL.value: [
            "security", "injection", "xss", "csrf", "sql",
            "漏洞", "注入", "泄露", "bypass", "crash",
            "critical", "severe", "emergency"
        ],
        SeverityLevel.MAJOR.value: [
            "performance", "slow", "timeout", "memory leak",
            "功能缺陷", "性能", "内存泄漏", "超时",
            "incorrect", "wrong", "bug"
        ],
        SeverityLevel.MINOR.value: [
            "style", "format", "naming", "unused",
            "代码规范", "格式", "命名", "未使用",
            "cosmetic", "minor"
        ],
        SeverityLevel.INFO.value: [
            "optimization", "suggest", "improve",
            "优化", "建议", "改进"
        ]
    }

    flaw_lower = lethal_flaw.lower()

    # 检查是否包含对应严重级别的关键词
    expected_keywords = severity_keywords.get(severity, [])

    if severity == SeverityLevel.CRITICAL.value:
        # CRITICAL必须有安全相关关键词
        if not any(kw in flaw_lower for kw in expected_keywords):
            return False, (
                f"CRITICAL severity requires security-related keywords. "
                f"Consider using: {', '.join(expected_keywords[:5])}"
            )

    # 检查是否有矛盾
    for other_severity, keywords in severity_keywords.items():
        if other_severity != severity:
            if severity == SeverityLevel.CRITICAL.value:
                # CRITICAL不应该有MINOR/INFO的关键词
                minor_keywords = severity_keywords.get(SeverityLevel.MINOR.value, [])
                minor_keywords.extend(severity_keywords.get(SeverityLevel.INFO.value, []))
                if any(kw in flaw_lower for kw in minor_keywords):
                    return False, (
                        f"CRITICAL severity conflicts with minor issues. "
                        f"Remove keywords like: {', '.join(minor_keywords[:3])}"
                    )

    return True, ""


class ValidationError(Exception):
    """验证错误异常"""
    pass


class EvidenceNotFoundError(Exception):
    """证据未找到异常"""
    pass


def validate_and_throw(review_data: Dict, evidence: Optional[Dict] = None) -> None:
    """
    验证并抛出异常 (用于工具层强制验证)

    Args:
        review_data: 审查数据
        evidence: 原始证据 (用于验证引用)

    Raises:
        ValidationError: 验证失败
        EvidenceNotFoundError: 证据引用无效
    """
    is_valid, error_message, warnings = validate_review_input(review_data)

    if not is_valid:
        raise ValidationError(error_message)

    # 如果提供了原始证据,验证引用
    if evidence and "evidence" in review_data:
        test_case = review_data["evidence"].get("test_case", "")
        if test_case:
            if not verify_evidence_reference(evidence, test_case):
                raise EvidenceNotFoundError(
                    f"Test case reference not found in evidence: {test_case}"
                )


if __name__ == "__main__":
    # 测试代码
    import sys

    # 测试用例1: 有效输入
    valid_review = {
        "severity": "critical",
        "lethal_flaw": "SQL注入漏洞: 用户登录接口未做参数化查询",
        "exploit_path": "步骤1: 访问 /api/login\n步骤2: 输入 username=admin'--\n步骤3: 成功绕过认证",
        "evidence": {
            "test_case": "test_login_sql_injection",
            "file_path": "auth/login.py",
            "line_number": 42
        },
        "recommendation": "no-go",
        "remediation": "使用参数化查询"
    }

    is_valid, error, warnings = validate_review_input(valid_review)
    print(f"Valid: {is_valid}, Error: {error}, Warnings: {warnings}")

    # 测试用例2: 无效输入
    invalid_review = {
        "severity": "invalid"
    }

    is_valid, error, warnings = validate_review_input(invalid_review)
    print(f"Valid: {is_valid}, Error: {error}")
