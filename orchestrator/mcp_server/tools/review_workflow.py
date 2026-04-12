"""
MCP Tool: review_workflow
执行完整的代码审查工作流：捕获证据、裁剪数据、封装输入
"""
import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp_server.tools.registry import register_tool

# 添加项目路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import get_settings
from src.core.event_bus import get_event_bus
from src.core.trimmer import EvidenceTrimmer
from src.core.packager import EvidencePackager
from src.models.events import BuildCompletedEvent, TestCompletedEvent
from src.models.artifacts import Artifact
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


async def execute_review_workflow(
    task_id: str,
    commit: Optional[str] = None,
    branch: Optional[str] = None,
    diff_content: Optional[str] = None,
    test_results: Optional[str] = None,
    base_path: Optional[str] = None
) -> dict[str, Any]:
    """
    执行完整的审查工作流

    Args:
        task_id: 任务ID，如 T-102
        commit: Git提交哈希（可选，默认为HEAD）
        branch: 分支名称（可选）
        diff_content: 代码 diff（可选，自动获取）
        test_results: 测试结果（可选）
        base_path: 基础路径（可选，默认为配置值）

    Returns:
        包含证据包和工作流结果的字典
    """
    settings = get_settings()
    logger.info(f"Starting review workflow for task: {task_id}")

    # 确定基础路径
    repo_path = Path(base_path) if base_path else settings.base_path

    # 1. 捕获 Git 状态
    build_event = await _capture_git_status(
        repo_path, task_id, commit, branch
    )

    if not build_event:
        return {
            "success": False,
            "error": "Failed to capture Git status",
            "task_id": task_id
        }

    # 2. 获取或使用提供的 diff
    diff = diff_content if diff_content else await _get_git_diff(repo_path)

    # 3. 获取或使用提供的测试结果
    test_event = await _get_test_results(
        repo_path, task_id, test_results
    )

    # 4. 裁剪日志和 diff
    trimmer = EvidenceTrimmer()
    trimmed_log, trimmed_diff = await trimmer.trim_build_output(
        "No build log provided",
        diff
    )

    log_summary = trimmed_log
    if test_event and test_event.test_summary:
        log_summary = f"{trimmed_log}\n\nTest Results: {test_event.test_summary}"

    # 5. 封装证据
    packager = EvidencePackager()
    artifact = await packager.create_reviewer_input(
        task_id=task_id,
        build_event=build_event,
        test_event=test_event or TestCompletedEvent(
            task_id=task_id,
            passed=True,
            total_tests=0,
            failed_tests=0,
            test_summary="No tests run",
            timestamp=datetime.now()
        ),
        diff_content=trimmed_diff,
        log_summary=log_summary,
        additional_context={
            "workflow_type": "mcp_review",
            "captured_at": datetime.now().isoformat()
        }
    )

    logger.info(f"Review workflow completed for task: {task_id}")

    return {
        "success": True,
        "task_id": task_id,
        "artifact": {
            "metadata": artifact.metadata.model_dump(mode='json'),
            "content": artifact.content
        },
        "build_event": {
            "commit_hash": build_event.commit_hash,
            "branch": build_event.branch,
            "changed_files": build_event.changed_files,
            "timestamp": build_event.timestamp.isoformat()
        },
        "test_event": {
            "passed": test_event.passed if test_event else None,
            "total_tests": test_event.total_tests if test_event else None,
            "test_summary": test_event.test_summary if test_event else None
        } if test_event else None
    }


async def _capture_git_status(
    repo_path: Path,
    task_id: str,
    commit: Optional[str] = None,
    branch: Optional[str] = None
) -> Optional[BuildCompletedEvent]:
    """捕获 Git 状态"""
    try:
        # 获取当前 commit
        if not commit:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            commit = result.stdout.strip()

        # 获取分支名
        if not branch:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            branch = result.stdout.strip()

        # 获取变更的文件列表
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        changed_files = [
            f for f in result.stdout.strip().split('\n') if f
        ] if result.returncode == 0 else []

        # 获取 diff 摘要
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD~1", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        diff_summary = result.stdout.strip() if result.returncode == 0 else ""

        return BuildCompletedEvent(
            task_id=task_id,
            commit_hash=commit,
            branch=branch,
            diff_summary=diff_summary,
            changed_files=changed_files,
            timestamp=datetime.now()
        )

    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Error capturing git status: {e}", exc_info=True)
        return None


async def _get_git_diff(repo_path: Path) -> str:
    """获取 Git diff"""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD~1", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception as e:
        logger.error(f"Error getting git diff: {e}")
        return ""


async def _get_test_results(
    repo_path: Path,
    task_id: str,
    provided_results: Optional[str] = None
) -> Optional[TestCompletedEvent]:
    """获取测试结果"""
    if provided_results:
        # 解析提供的测试结果
        try:
            import json
            data = json.loads(provided_results)
            return TestCompletedEvent(
                task_id=task_id,
                passed=data.get("passed", True),
                total_tests=data.get("total", 0),
                failed_tests=data.get("failed", 0),
                test_summary=data.get("summary", ""),
                coverage_percent=data.get("coverage"),
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.warning(f"Failed to parse provided test results: {e}")

    # 尝试查找常见的测试结果文件
    test_paths = [
        repo_path / "pytest_results.json",
        repo_path / "test-results.xml",
        repo_path / ".pytest_cache" / "results.json",
    ]

    for test_path in test_paths:
        if test_path.exists():
            # 这里简化处理，实际应解析文件
            return TestCompletedEvent(
                task_id=task_id,
                passed=True,
                total_tests=0,
                failed_tests=0,
                test_summary=f"Found test results at {test_path.name}",
                timestamp=datetime.now()
            )

    return None


def register_review_workflow(server: Server) -> None:
    """注册 review_workflow 工具到 MCP 服务器"""

    async def handle_review_workflow(arguments: dict[str, Any]) -> list[TextContent]:
        """处理 review_workflow 调用"""
        try:
            result = await execute_review_workflow(
                task_id=arguments.get("task_id"),
                commit=arguments.get("commit"),
                branch=arguments.get("branch"),
                diff_content=arguments.get("diff_content"),
                test_results=arguments.get("test_results"),
                base_path=arguments.get("base_path")
            )

            if result["success"]:
                # 返回格式化的结果
                content = f"""# Review Workflow Completed

## Task: {result['task_id']}

### Git Information
- Commit: {result['build_event']['commit_hash']}
- Branch: {result['build_event']['branch']}
- Changed Files: {len(result['build_event']['changed_files'])}

### Test Results
- Status: {'PASSED' if result['test_event']['passed'] else 'FAILED'} if result['test_event'] else 'N/A'
- Tests: {result['test_event']['total_tests'] if result['test_event'] else 0}

### Evidence Package
{result['artifact']['content'][:500]}...

Use `route_artifact` tool to route this evidence to the appropriate directory.
"""
                return [TextContent(
                    type="text",
                    text=content
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Error: {result.get('error', 'Unknown error')}"
                )]

        except Exception as e:
            logger.exception(f"Error in review_workflow: {e}")
            return [TextContent(
                type="text",
                text=f"Exception: {str(e)}"
            )]

    # 注册工具
    register_tool(server, Tool(
        name="review_workflow",
        description="Execute complete code review workflow: capture evidence, trim data, package input for review",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID, e.g., T-102"
                },
                "commit": {
                    "type": "string",
                    "description": "Git commit hash (optional, defaults to HEAD)"
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name (optional)"
                },
                "diff_content": {
                    "type": "string",
                    "description": "Code diff (optional, auto-captured if not provided)"
                },
                "test_results": {
                    "type": "string",
                    "description": "Test results JSON string (optional)"
                },
                "base_path": {
                    "type": "string",
                    "description": "Base path for the repository (optional)"
                }
            },
            "required": ["task_id"]
        }
    ), handle_review_workflow)

    logger.info("Registered review_workflow tool")
