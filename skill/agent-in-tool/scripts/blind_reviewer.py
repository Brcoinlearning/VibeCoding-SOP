#!/usr/bin/env python3
"""
Agent-in-Tool Blind Reviewer
核心实现：在独立运行时内部调用独立的LLM API
"""
import asyncio
import json
import subprocess
from pathlib import Path
from filelock import FileLock
from typing import Dict, Optional
import os

# Reviewer对抗性System Prompt
REVIEWER_SYSTEM_PROMPT = """你是一个冷酷无情的顶级安全审查员。你的任务是找出代码中的致命缺陷。

## 审查重点

1. **SQL注入漏洞**
   - 检查所有数据库查询
   - 验证参数化查询使用情况
   - 查找字符串拼接的SQL语句

2. **XSS跨站脚本**
   - 检查用户输入渲染
   - 验证HTML转义
   - 查找innerHTML、dangerouslySetInnerHTML等

3. **并发竞态条件**
   - 检查共享状态访问
   - 验证锁机制
   - 查找race condition

4. **空指针解引用**
   - 检查变量使用前是否验证
   - 查找可能的None值访问

5. **业务逻辑错误**
   - 检查边界条件
   - 验证错误处理
   - 查找逻辑漏洞

## 输出格式

你必须返回纯JSON格式（不要有其他文字）：

```json
{
  "status": "PASS" | "REJECTED",
  "lethal_flaw": "致命缺陷描述（如果存在）",
  "severity": "critical" | "major" | "minor" | "info",
  "exploit_path": "复现路径（步骤1/2/3格式）",
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

开始审查！"""


class BlindReviewer:
    """
    Agent-in-Tool盲审器

    在独立运行时发起独立的LLM API调用，实现真正的物理隔离
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-7-sonnet-20250219"):
        """
        初始化盲审器

        Args:
            api_key: Anthropic API密钥 (默认从环境变量读取)
            model: 使用的模型
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.model = model

    async def review(
        self,
        task_id: str,
        workspace_path: str,
        timeout: int = 120
    ) -> Dict:
        """
        执行盲审

        Args:
            task_id: 任务ID
            workspace_path: 工作区路径
            timeout: API超时时间(秒)

        Returns:
            极简返回结果
        """
        try:
            # 1. 收集证据
            evidence = await self._collect_evidence(workspace_path)

            # 2. 派生子智能体
            review_result = await self._spawn_independent_agent(evidence, timeout)

            # 3. 结果落盘
            await self._save_review_report(task_id, review_result, workspace_path)

            # 4. 信息降维返回
            return self._format_minimal_response(task_id, review_result)

        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"审查失败: {str(e)}",
                "action": "RETRY"
            }

    async def _collect_evidence(self, workspace_path: str) -> Dict:
        """收集审查证据"""
        workspace = Path(workspace_path)

        # Git diff
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD"],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=True
            )
            diff = result.stdout
        except subprocess.CalledProcessError:
            diff = "无法获取Git diff"

        # 测试日志
        test_log_paths = [
            workspace / "pytest_results.json",
            workspace / "test-results.xml",
            workspace / ".pytest_cache" / "results.json"
        ]

        test_logs = "No test results found"
        for log_path in test_log_paths:
            if log_path.exists():
                test_logs = log_path.read_text(encoding='utf-8')
                break

        # 变更文件列表
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=True
            )
            changed_files = [f for f in result.stdout.strip().split('\n') if f]
        except subprocess.CalledProcessError:
            changed_files = []

        return {
            "diff": diff,
            "test_logs": test_logs,
            "changed_files": changed_files
        }

    async def _spawn_independent_agent(self, evidence: Dict, timeout: int) -> Dict:
        """
        派发独立的LLM Agent进行审查

        这是Agent-in-Tool的核心：创建全新的、无状态的LLM会话
        """
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.api_key)

        # 构造审查提示词
        review_prompt = self._format_review_prompt(evidence)

        try:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0,  # 确保一致的审查
                    system=REVIEWER_SYSTEM_PROMPT,
                    messages=[{
                        "role": "user",
                        "content": review_prompt
                    }]
                ),
                timeout=timeout
            )

            # 解析响应
            return self._parse_review_response(response)

        except asyncio.TimeoutError:
            raise Exception(f"API调用超时({timeout}秒)")
        except Exception as e:
            raise Exception(f"API调用失败: {str(e)}")

    def _format_review_prompt(self, evidence: Dict) -> str:
        """格式化审查提示词"""
        return f"""请审查以下代码变更：

## Git Diff
```
{evidence['diff'][:50000]}  # 限制diff长度
```

## 测试结果
```
{evidence['test_logs'][:10000]}  # 限制日志长度
```

## 变更文件
{', '.join(evidence['changed_files'][:20])}  # 最多显示20个文件

请返回JSON格式的审查结果。记住：只返回JSON，不要有其他文字。"""

    def _parse_review_response(self, response) -> Dict:
        """解析LLM响应为JSON"""
        content = response.content[0].text

        # 提取JSON (可能被markdown代码块包裹)
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            json_str = content[json_start:json_end].strip()
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.rfind("```")
            json_str = content[json_start:json_end].strip()
        else:
            json_str = content.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # 如果解析失败，返回默认格式
            return {
                "status": "ERROR",
                "lethal_flaw": f"无法解析审查结果: {str(e)}",
                "severity": "critical",
                "exploit_path": "N/A",
                "remediation": "请手动检查代码",
                "findings": []
            }

    async def _save_review_report(self, task_id: str, review: Dict, workspace: str):
        """保存审查报告 (带文件锁)"""
        review_dir = Path(workspace) / "40-review"
        review_dir.mkdir(parents=True, exist_ok=True)

        # 保存JSON报告
        report_file = review_dir / f"{task_id}.json"
        lock_file = review_dir / f"{task_id}.lock"

        with FileLock(lock_file, timeout=5):
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(review, f, indent=2, ensure_ascii=False)

        # 生成Markdown报告
        md_file = review_dir / f"{task_id}.md"
        with FileLock(lock_file, timeout=5):
            md_content = self._format_review_markdown(review, task_id)
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(md_content)

    def _format_review_markdown(self, review: Dict, task_id: str) -> str:
        """格式化Markdown报告"""
        md = f"""# Blind Review Report: {task_id}

## Status: {review['status']}

---

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
            md += """## ✅ Approved

No critical issues found. Code is ready for human review.

"""

        # 详细发现
        findings = review.get("findings", [])
        if findings:
            md += "\n## Detailed Findings\n\n"
            for i, finding in enumerate(findings, 1):
                md += f"### {i}. {finding['issue']}\n\n"
                md += f"""- **File**: `{finding.get('file', 'unknown')}`
- **Line**: {finding.get('line', 'unknown')}
- **Category**: {finding.get('category', 'unknown')}

```{finding.get('code', 'N/A')}```

"""
        else:
            md += "\n## Detailed Findings\n\nNo issues found.\n"

        return md

    def _format_minimal_response(self, task_id: str, review: Dict) -> Dict:
        """格式化极简返回给Builder"""
        if review["status"] == "REJECTED":
            return {
                "status": "REJECTED",
                "message": f"""❌ 审查未通过！

发现 {review.get('severity', 'unknown')} 级别问题：
{review['lethal_flaw']}

详细报告已写入：40-review/{task_id}.md

请阅读报告并修复问题后重新提交审查。""",
                "report_file": f"40-review/{task_id}.md",
                "action": "FIX_AND_RETRY"
            }
        else:
            findings_count = len(review.get("findings", []))
            return {
                "status": "PASS",
                "message": f"""✅ 审查通过！

发现 {findings_count} 个非阻断性问题（详见报告）。

请调用 submit_to_owner 请求人类最终放行。""",
                "report_file": f"40-review/{task_id}.md",
                "action": "SUBMIT_TO_OWNER"
            }


if __name__ == "__main__":
    # 测试代码
    import sys

    async def test():
        if len(sys.argv) > 1:
            task_id = sys.argv[1]
        else:
            task_id = "TEST-001"

        if len(sys.argv) > 2:
            workspace = sys.argv[2]
        else:
            workspace = "."

        reviewer = BlindReviewer()
        result = await reviewer.review(task_id, workspace)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(test())
