---
name: trigger-blind-review
description: Use when Builder Agent completes code and requests blind review. This tool spawns an independent LLM API call inside standalone Python runtime, achieving true physical isolation. The Builder cannot see the review process or prompt, only receives a simplified result message. Reports are written to 40-review/ directory with file locking.
---

# Trigger Blind Review

## Overview

⭐ **核心技能 - Agent-in-Tool盲审机制**

Builder认为代码写完了，调用此工具请求验收。

## Agent-in-Tool 模式

```python
# 在独立运行时内部调用独立的LLM，实现真正的物理隔离
async def trigger_blind_review(task_id: str) -> str:
    # 1. 抓取证据 (Builder看不到这个过程)
    diff = get_git_diff()
    logs = get_test_logs()

    # 2. 唤醒完全独立的Reviewer Agent
    client = anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model="claude-3-7-sonnet-20250219",
        system="你是一个冷酷无情的顶级安全审查员...",
        messages=[{"role": "user", "content": f"Diff:\n{diff}\nLogs:\n{logs}"}]
    )

    # 3. 结果落盘 (使用文件锁防竞态)
    save_report_to_disk(task_id, response)

    # 4. 对Builder进行"信息降维"返回
    return format_minimal_response(response)
```

## 隔离机制

### 1. 上下文隔离
- Builder的上下文完全不会传递给Reviewer
- 每次审查都是全新的LLM会话
- Reviewer不知道Builder的"思考过程"

### 2. 权限隔离
- Builder只能调用工具，无法直接访问报告文件
- 报告文件由独立 Python Runtime 直接写入文件系统
- 使用文件锁防止并发冲突

### 3. 信息降维
- 报告文件包含完整的审查详情
- Builder只能看到极简的返回消息
- 防止Builder被大量信息"污染"

## Reviewer System Prompt

```python
REVIEWER_SYSTEM_PROMPT = """
你是一个冷酷无情的顶级安全审查员。你的任务是找出代码中的致命缺陷。

## 审查重点

1. **SQL注入漏洞**
   - 检查所有数据库查询
   - 验证参数化查询使用情况

2. **XSS跨站脚本**
   - 检查用户输入渲染
   - 验证HTML转义

3. **并发竞态条件**
   - 检查共享状态访问
   - 验证锁机制

4. **空指针解引用**
   - 检查变量使用前是否验证

5. **业务逻辑错误**
   - 检查边界条件
   - 验证错误处理

## 输出格式

你必须返回纯JSON格式：

```json
{
  "status": "PASS" | "REJECTED",
  "lethal_flaw": "致命缺陷描述（如果存在）",
  "severity": "critical" | "major" | "minor" | "info",
  "exploit_path": "复现路径（步骤1/2/3）",
  "remediation": "修复建议",
  "findings": [
    {
      "category": "security | correctness | performance",
      "issue": "问题描述",
      "file": "文件路径",
      "line": 行号,
      "code": "问题代码片段"
    }
  ]
}
```

## 审查原则

- 宁可错杀，不可放过
- 发现任何critical级别问题必须REJECTED
- 没有测试覆盖的功能自动REJECTED
- 代码风格问题不影响通过，但必须在findings中标注

开始审查！
"""
```

## Implementation

```python
import anthropic
import subprocess
import json
from pathlib import Path
from filelock import FileLock
from typing import Dict

async def trigger_blind_review(
    task_id: str,
    workspace_path: str = None,
    api_key: str = None
) -> Dict:
    """
    触发盲审

    Args:
        task_id: 任务ID
        workspace_path: 工作区路径
        api_key: Anthropic API密钥

    Returns:
        极简返回结果
    """
    if workspace_path is None:
        workspace_path = "."

    # 1. 抓取证据
    evidence = await collect_evidence(workspace_path)

    # 2. 派生子智能体
    client = anthropic.AsyncAnthropic(api_key=api_key)

    try:
        response = await client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=4096,
            temperature=0,  # 确保一致的审查
            system=REVIEWER_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"""请审查以下代码变更：

## Git Diff
```
{evidence['diff']}
```

## 测试结果
```
{evidence['test_logs']}
```

## 变更文件
{', '.join(evidence['changed_files'])}

请返回JSON格式的审查结果。"""
            }]
        )

        # 3. 解析JSON响应
        review_json = parse_review_response(response)

        # 4. 结果落盘 (使用文件锁)
        await save_review_report(task_id, review_json, workspace_path)

        # 5. 信息降维返回
        return format_minimal_response(review_json)

    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"审查失败: {str(e)}"
        }


async def collect_evidence(workspace_path: str) -> Dict:
    """收集审查证据"""
    # Git diff
    result = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD"],
        cwd=workspace_path,
        capture_output=True,
        text=True
    )
    diff = result.stdout

    # 测试日志
    test_log_path = Path(workspace_path) / "pytest_results.json"
    if test_log_path.exists():
        test_logs = test_log_path.read_text()
    else:
        test_logs = "No test results found"

    # 变更文件
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
        cwd=workspace_path,
        capture_output=True,
        text=True
    )
    changed_files = [f for f in result.stdout.strip().split('\n') if f]

    return {
        "diff": diff,
        "test_logs": test_logs,
        "changed_files": changed_files
    }


def parse_review_response(response) -> Dict:
    """解析LLM响应为JSON"""
    content = response.content[0].text

    # 提取JSON (可能被markdown代码块包裹)
    if "```json" in content:
        json_start = content.find("```json") + 7
        json_end = content.find("```", json_start)
        json_str = content[json_start:json_end].strip()
    else:
        json_str = content.strip()

    return json.loads(json_str)


async def save_review_report(task_id: str, review: Dict, workspace: str):
    """保存审查报告 (带文件锁)"""
    review_dir = Path(workspace) / "40-review"
    review_dir.mkdir(parents=True, exist_ok=True)

    report_file = review_dir / f"{task_id}.json"
    lock_file = review_dir / f"{task_id}.lock"

    # 使用文件锁防止并发写入
    with FileLock(lock_file, timeout=5):
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(review, f, indent=2, ensure_ascii=False)

    # 同时生成Markdown报告
    md_file = review_dir / f"{task_id}.md"
    with FileLock(lock_file, timeout=5):
        md_content = format_review_markdown(review)
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)


def format_minimal_response(review: Dict) -> Dict:
    """格式化极简返回给Builder"""
    if review["status"] == "REJECTED":
        return {
            "status": "REJECTED",
            "message": f"❌ 审查未通过！发现 {review['severity']} 级别问题：{review['lethal_flaw']}",
            "report_file": f"40-review/{task_id}.md",
            "action": "FIX_AND_RETRY"
        }
    else:
        return {
            "status": "PASS",
            "message": "✅ 审查通过！请调用 submit_to_owner 请求人类放行。",
            "action": "SUBMIT_TO_OWNER"
        }


def format_review_markdown(review: Dict) -> str:
    """格式化Markdown报告"""
    md = f"""# Blind Review Report

## Status: {review['status']}

"""
    if review["status"] == "REJECTED":
        md += f"""## ❌ Rejected

### Lethal Flaw
{review['lethal_flaw']}

### Severity
{review['severity'].upper()}

### Exploit Path
```
{review['exploit_path']}
```

### Remediation
{review['remediation']}

"""
    else:
        md += "## ✅ Approved\n\nNo critical issues found.\n"

    md += "\n## Detailed Findings\n\n"
    for i, finding in enumerate(review.get("findings", []), 1):
        md += f"### {i}. {finding['issue']}\n"
        md += f"- **File**: `{finding['file']}`\n"
        md += f"- **Line**: {finding['line']}\n"
        md += f"- **Category**: {finding['category']}\n"
        md += f"```{finding['code']}``\n\n"

    return md
```

## Standalone CLI 调用

```bash
python3 cli.py blind-review TASK-001 --workspace .
```

## Architecture Diagram

```
Builder Agent             Standalone Skill              Anthropic API
     |                           |                            |
     |  trigger_blind_review     |                            |
     |-------------------------->|                            |
     |                           |  1. Collect Evidence        |
     |                           |  2. Spawn Independent Agent |
     |                           |---------------------------->|
     |                           |  System Prompt + Diff       |
     |                           |                            |
     |                           |  3. Blind Review            |
     |                           |<----------------------------|
     |                           |  JSON Report                |
     |                           |                            |
     |                           |  4. Save to Disk            |
     |                           |  (40-review/)              |
     |                           |                            |
     |  "❌ 审查未通过"           |                            |
     |<--------------------------|                            |
     |                           |                            |
     v                           v                            v
  Read Report                Review Complete            Isolated Review
```

## Files Structure

```
trigger_blind_review/
├── SKILL.md                    # 本文件
└── scripts/
    ├── blind_reviewer.py       # Agent-in-Tool实现
    ├── evidence_collector.py   # 证据收集
    └── report_generator.py     # 报告生成
```

## Key Insights

1. **物理隔离**：每个审查都是全新的API调用
2. **真正的AI**：审查由LLM理解完成，而非死板规则
3. **信息降维**：Builder只看到结果，不看到过程
4. **可追溯**：完整报告保存在文件系统
