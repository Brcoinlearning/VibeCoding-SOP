#!/usr/bin/env python3
"""
Git Capture Module
捕获Git状态和代码差异
"""
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


def capture_git_status(
    repo_path: Path,
    commit: Optional[str] = None,
    branch: Optional[str] = None
) -> Dict:
    """
    捕获Git状态信息

    Args:
        repo_path: 仓库路径
        commit: Git提交哈希 (可选, 默认HEAD)
        branch: 分支名称 (可选)

    Returns:
        {
            "commit_hash": str,
            "branch": str,
            "changed_files": List[str],
            "diff_summary": str,
            "full_diff": str,
            "timestamp": str
        }

    Raises:
        subprocess.CalledProcessError: Git命令执行失败
    """
    result = {}

    # 获取当前commit
    if not commit:
        try:
            commit_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            commit = commit_result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to get current commit: {e}")

    result["commit_hash"] = commit

    # 获取分支名
    if not branch:
        try:
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            branch = branch_result.stdout.strip()
        except subprocess.CalledProcessError:
            branch = "unknown"

    result["branch"] = branch

    # 获取变更的文件列表
    try:
        files_result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        changed_files = [
            f for f in files_result.stdout.strip().split('\n') if f
        ] if files_result.returncode == 0 else []
        result["changed_files"] = changed_files
    except subprocess.CalledProcessError:
        result["changed_files"] = []

    # 获取diff摘要
    try:
        summary_result = subprocess.run(
            ["git", "diff", "--stat", "HEAD~1", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        result["diff_summary"] = summary_result.stdout.strip() if summary_result.returncode == 0 else ""
    except subprocess.CalledProcessError:
        result["diff_summary"] = ""

    # 获取完整diff
    try:
        diff_result = subprocess.run(
            ["git", "diff", "HEAD~1", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        result["full_diff"] = diff_result.stdout if diff_result.returncode == 0 else ""
    except subprocess.CalledProcessError:
        result["full_diff"] = ""

    result["timestamp"] = datetime.now().isoformat()

    return result


def get_file_diff(repo_path: Path, file_path: str, commit: str = "HEAD") -> str:
    """
    获取单个文件的diff

    Args:
        repo_path: 仓库路径
        file_path: 文件路径
        commit: 提交哈希

    Returns:
        文件的diff内容
    """
    try:
        result = subprocess.run(
            ["git", "diff", f"{commit}~1", commit, "--", file_path],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to get diff for {file_path}: {e}")


def get_commit_message(repo_path: Path, commit: str = "HEAD") -> str:
    """
    获取提交信息

    Args:
        repo_path: 仓库路径
        commit: 提交哈希

    Returns:
        提交信息
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B", commit],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to get commit message: {e}")


def get_author_info(repo_path: Path, commit: str = "HEAD") -> Dict:
    """
    获取作者信息

    Args:
        repo_path: 仓库路径
        commit: 提交哈希

    Returns:
        {
            "name": str,
            "email": str,
            "date": str
        }
    """
    try:
        # 获取作者名和邮箱
        name_result = subprocess.run(
            ["git", "log", "-1", "--pretty=%an", commit],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        email_result = subprocess.run(
            ["git", "log", "-1", "--pretty=%ae", commit],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        date_result = subprocess.run(
            ["git", "log", "-1", "--pretty=%ai", commit],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )

        return {
            "name": name_result.stdout.strip(),
            "email": email_result.stdout.strip(),
            "date": date_result.stdout.strip()
        }
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to get author info: {e}")


if __name__ == "__main__":
    # 测试代码
    import sys

    if len(sys.argv) > 1:
        repo_path = Path(sys.argv[1])
    else:
        repo_path = Path.cwd()

    try:
        git_info = capture_git_status(repo_path)
        print("Git Status Captured:")
        print(f"  Commit: {git_info['commit_hash']}")
        print(f"  Branch: {git_info['branch']}")
        print(f"  Changed Files: {len(git_info['changed_files'])}")
        print(f"  Diff Summary:\n{git_info['diff_summary']}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
