---
name: execute-structured-review
description: Use when conducting deep code review that requires structured output with severity assessment, lethal flaw detection, exploit paths, and evidence binding. Enforces system-level validation through Tool Schema to prevent hallucinated reviews. Rejects calls without test evidence references. Use when Reviewer Agent needs to produce audit-ready review reports.
---

# Execute Structured Review

## Overview

强制结构化审查工具 - 将MCP Server的对抗审查规则与注入器转换为Schema强约束的被动工具。

限制大模型输出废话，强制进行深度逻辑排查。通过Tool/Function Schema进行系统级强约束，而非依赖Prompt。

## When to Use

```
            收到审查证据
                 |
        +--------+--------+
        |                 |
    证据完整          需要深度审查
        |                 |
        v                 v
   调用此Skill → 强制结构化输出
                 |
        +--------+--------+
        |                 |
   审查通过            审查失败
        |                 |
        v                 v
   返回GO建议          返回NO-GO+缺陷
```

**触发条件:**
- 收到 `fetch_and_trim_evidence` 输出
- 需要进行代码审查
- 需要生成审计就绪的报告
- 要求缺陷可复现路径

**前置要求:** 必须先调用 `fetch_and_trim_evidence` 获取证据

## Core Pattern

### Before (Prompt约束)
```python
# MCP: 依赖Prompt指导，可能被绕过
prompt = """
请进行代码审查，注意:
1. 评估严重级别
2. 找出致命缺陷
3. 提供复现路径
4. 绑定证据
"""
# Agent可能忽略或产生幻觉
```

### After (Schema强约束)
```python
# Skill: Schema级别的强制约束
inputSchema = {
    "required": [
        "severity",          # 必须有严重级别
        "lethal_flaw",       # 必须有致命缺陷分析
        "exploit_path",      # 必须有复现路径
        "evidence"           # 必须绑定证据
    ]
}
# 工具层验证，缺失则拒绝执行
```

## Quick Reference

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `severity` | enum | 严重级别 | `critical`, `major`, `minor` |
| `lethal_flaw` | string | 致命缺陷描述 | "SQL注入未做参数化查询" |
| `exploit_path` | string | 复现路径 | "步骤1: 登录→步骤2: 注入→..." |
| `evidence` | object | 证据引用 | `{"test_case": "test_login.py:42", "line": 125}` |

## Schema Definition

```json
{
    "type": "object",
    "properties": {
        "task_id": {
            "type": "string",
            "description": "任务标识符"
        },
        "severity": {
            "type": "string",
            "enum": ["critical", "major", "minor", "info"],
            "description": "缺陷严重级别"
        },
        "lethal_flaw": {
            "type": "string",
            "description": "致命缺陷的详细描述，包括缺陷类型、影响范围和风险等级"
        },
        "exploit_path": {
            "type": "string",
            "description": "复现路径 - 逐步说明如何触发该缺陷"
        },
        "evidence": {
            "type": "object",
            "properties": {
                "test_case": {"type": "string"},
                "file_path": {"type": "string"},
                "line_number": {"type": "integer"},
                "code_snippet": {"type": "string"},
                "test_output": {"type": "string"}
            },
            "required": ["test_case"],
            "description": "证据引用 - 必须关联到具体测试用例"
        },
        "recommendation": {
            "type": "string",
            "enum": ["go", "no-go", "conditional"],
            "description": "审查建议"
        },
        "remediation": {
            "type": "string",
            "description": "修复建议"
        }
    },
    "required": ["task_id", "severity", "lethal_flaw", "exploit_path", "evidence", "recommendation"]
}
```

## Implementation

### Validation Logic

```python
def validate_review_input(review_data: dict) -> tuple[bool, str]:
    """
    验证审查输入的完整性

    Returns:
        (is_valid, error_message)
    """
    required_fields = ["severity", "lethal_flaw", "exploit_path", "evidence"]

    # 检查必需字段
    for field in required_fields:
        if field not in review_data or not review_data[field]:
            return False, f"Missing required field: {field}"

    # 验证severity值
    valid_severities = ["critical", "major", "minor", "info"]
    if review_data["severity"] not in valid_severities:
        return False, f"Invalid severity: {review_data['severity']}"

    # 验证证据引用
    evidence = review_data["evidence"]
    if "test_case" not in evidence:
        return False, "Evidence must reference a test case"

    # 验证exploit_path格式
    exploit_path = review_data["exploit_path"]
    if not any(marker in exploit_path for marker in ["步骤", "Step", "→", "->"]):
        return False, "Exploit path must be step-by-step format"

    return True, ""

def execute_structured_review(evidence: dict, review_data: dict) -> dict:
    """
    执行结构化审查

    Args:
        evidence: 来自fetch_and_trim_evidence的输出
        review_data: Agent填写的审查结果

    Returns:
        审查报告
    """
    # 验证输入
    is_valid, error = validate_review_input(review_data)
    if not is_valid:
        raise ValueError(f"Invalid review input: {error}")

    # 验证证据引用
    test_case = review_data["evidence"]["test_case"]
    if not verify_evidence_reference(evidence, test_case):
        raise ValueError(f"Evidence reference not found: {test_case}")

    # 生成结构化报告
    report = {
        "task_id": evidence["task_id"],
        "timestamp": datetime.now().isoformat(),
        "evidence_metadata": evidence["metadata"],
        "review": review_data,
        "status": "completed"
    }

    return report

def verify_evidence_reference(evidence: dict, test_case: str) -> bool:
    """
    验证证据引用是否有效

    检查test_case是否在原始证据中存在
    """
    # 在evidence中查找test_case引用
    # ...
    return True
```

## Review Criteria

### Severity Classification

| 级别 | 定义 | 示例 | 建议 |
|------|------|------|------|
| `critical` | 安全漏洞、数据泄露、崩溃 | SQL注入、空指针解引用 | NO-GO, 立即修复 |
| `major` | 功能缺陷、性能问题 | 缓存穿透、内存泄漏 | NO-GO, 修复后重审 |
| `minor` | 代码规范、可维护性 | 未处理异常、魔法数字 | Conditional, 建议修复 |
| `info` | 优化建议、最佳实践 | 未使用变量、重复代码 | GO, 可选优化 |

### Lethal Flaw Detection Pattern

```python
# 致命缺陷检测要点
LETHAL_FLAW_PATTERNS = {
    "security": [
        "SQL注入",
        "XSS跨站脚本",
        "CSRF攻击",
        "敏感信息泄露",
        "认证绕过"
    ],
    "correctness": [
        "空指针解引用",
        "数组越界",
        "类型转换错误",
        "并发竞态"
    ],
    "performance": [
        "N+1查询",
        "死循环",
        "内存泄漏",
        "缓存穿透"
    ]
}
```

### Exploit Path Template

```markdown
# 复现路径

## 前置条件
- 用户角色: 普通用户
- 系统状态: 已登录

## 复现步骤
步骤1: 访问 `/api/user/profile?id=1`
步骤2: 修改参数为 `id=1' OR '1'='1`
步骤3: 观察返回所有用户数据

## 预期结果
返回403 Forbidden

## 实际结果
返回所有用户数据 (SQL注入成功)
```

## Common Mistakes

| 错误 | 原因 | 修复 |
|------|------|------|
| 证据幻觉 | 未引用真实测试用例 | 必须在evidence中找到test_case |
| 严重级别误判 | 未遵循分类标准 | 严格按照criteria表 |
| 复现路径模糊 | 缺少具体步骤 | 使用步骤1/2/3格式 |
| 审查意见主观 | 缺少证据支撑 | 所有结论必须有evidence |

## Anti-Hallucination Measures

### 1. Evidence Binding Verification
```python
# 拒绝无证据的审查
if not has_evidence_reference(review_data):
    raise EvidenceRequiredError(
        "Review must reference test evidence. "
        "Cannot proceed without test case binding."
    )
```

### 2. Exploit Path Validation
```python
# 要求逐步格式
if not is_stepwise_format(exploit_path):
    raise InvalidFormatError(
        "Exploit path must be step-by-step format. "
        "Use: 步骤1: ... 步骤2: ..."
    )
```

### 3. Severity Consistency Check
```python
# 严重级别必须与缺陷类型匹配
if severity_mismatch(lethal_flaw, severity):
    raise SeverityMismatchError(
        f"Severity '{severity}' does not match flaw type. "
        f"Flaw: {lethal_flaw}"
    )
```

## Integration Flow

```
fetch_and_trim_evidence
       ↓
   [证据数据]
       ↓
execute_structured_review (本Skill)
   - 验证证据引用
   - Schema验证输入
   - 生成结构化报告
       ↓
   [审查报告]
       ↓
archive_review_artifact
```

## Output Format

```json
{
    "task_id": "T-001",
    "timestamp": "2025-04-12T10:30:00Z",
    "review": {
        "severity": "critical",
        "lethal_flaw": "用户登录接口存在SQL注入漏洞，攻击者可通过构造恶意输入绕过认证",
        "exploit_path": "步骤1: 访问 /api/login\n步骤2: 输入 username=admin'--\n步骤3: 成功以admin身份登录",
        "evidence": {
            "test_case": "test_login_sql_injection.py",
            "file_path": "auth/login.py",
            "line_number": 42,
            "code_snippet": "query = f\"SELECT * FROM users WHERE username='{username}'\"",
            "test_output": "AssertionError: Expected 401, got 200"
        },
        "recommendation": "no-go",
        "remediation": "使用参数化查询替换字符串拼接: cursor.execute(\"SELECT * FROM users WHERE username=%s\", (username,))"
    },
    "status": "completed"
}
```

## Files Structure

```
execute_structured_review/
├── SKILL.md                 # 本文件
└── scripts/
    ├── review_validator.py  # 输入验证
    ├── flaw_detector.py     # 缺陷检测
    └── report_generator.py  # 报告生成
```

## Real-World Impact

**Schema强约束的好处:**
- ✅ 防止Agent"逃课"伪造审查
- ✅ 确保每条结论都有证据支撑
- ✅ 统一输出格式便于归档
- ✅ 可自动化验证报告质量

**对比Prompt-only方式:**
- Prompt: Agent可能忽略，产生幻觉
- Schema: 工具层强制验证，缺失即拒绝
