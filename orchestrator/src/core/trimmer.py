"""
裁剪器模块
负责执行日志摘要、diff 限幅等数据裁剪操作
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Optional

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class LogTrimmer:
    """
    日志裁剪器
    将长日志裁剪为关键信息摘要
    """

    def __init__(self):
        """初始化日志裁剪器"""
        self._settings = get_settings()

    async def trim_log(self, log_content: str, context_lines: int = 5) -> str:
        """
        裁剪日志内容

        Args:
            log_content: 原始日志内容
            context_lines: 保留错误上下文的行数

        Returns:
            裁剪后的日志摘要
        """
        lines = log_content.split('\n')

        # 如果日志行数在限制内，直接返回
        if len(lines) <= self._settings.max_log_lines:
            return log_content

        # 提取关键行（错误、警告、关键事件）
        key_lines = self._extract_key_lines(lines, context_lines)

        # 如果关键行仍然太多，进行进一步压缩
        if len(key_lines) > self._settings.max_log_lines:
            # 按优先级保留
            key_lines = self._prioritize_lines(key_lines)[:self._settings.max_log_lines]

        # 添加摘要信息
        summary = f"""Log Summary (trimmed from {len(lines)} lines)
Total key lines extracted: {len(key_lines)}
"""

        return summary + '\n'.join(key_lines)

    def _extract_key_lines(self, lines: list[str], context: int) -> list[str]:
        """
        提取关键行及其上下文

        Args:
            lines: 所有日志行
            context: 上下文行数

        Returns:
            关键行列表
        """
        key_patterns = [
            r'\b(ERROR|CRITICAL|FATAL)\b',  # 错误级别
            r'\bWARNING\b',  # 警告
            r'\bException\b',  # 异常
            r'\bfailed\b',  # 失败
            r'\bStack trace\b',  # 堆栈跟踪
            r'^\s{2,}\^',  # Python 错误指针
        ]

        key_indices = set()

        # 查找匹配关键模式的行
        for i, line in enumerate(lines):
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in key_patterns):
                # 添加上下文
                for j in range(max(0, i - context), min(len(lines), i + context + 1)):
                    key_indices.add(j)

        # 添加日志头尾
        header_lines = min(10, len(lines))
        for i in range(header_lines):
            key_indices.add(i)

        footer_lines = min(10, len(lines))
        for i in range(len(lines) - footer_lines, len(lines)):
            key_indices.add(i)

        # 返回排序后的行
        sorted_indices = sorted(key_indices)
        return [lines[i] for i in sorted_indices]

    def _prioritize_lines(self, lines: list[str]) -> list[str]:
        """
        按优先级排序行

        Args:
            lines: 日志行

        Returns:
            排序后的行
        """
        priorities = {
            'CRITICAL': 0,
            'ERROR': 1,
            'Exception': 2,
            'WARNING': 3,
            'failed': 4,
        }

        def get_priority(line: str) -> int:
            for pattern, priority in priorities.items():
                if pattern.lower() in line.lower():
                    return priority
            return 999

        return sorted(lines, key=get_priority)

    async def extract_test_failures(self, log_content: str) -> Optional[str]:
        """
        提取测试失败信息

        Args:
            log_content: 日志内容

        Returns:
            失败的测试摘要，如果没有失败则返回 None
        """
        # 常见测试框架的失败模式
        failure_patterns = [
            r'FAILED\s+(.+?::.+)',  # pytest
            r'✗\s+(FAILED|Error)\s+(.+)',  # 其他框架
            r'Test\s+.*\s+failed',  # 通用模式
        ]

        failures = []

        for line in log_content.split('\n'):
            for pattern in failure_patterns:
                match = re.search(pattern, line)
                if match:
                    failures.append(line.strip())
                    break

        if failures:
            return f"""Test Failures Summary:
{chr(10).join(f'- {f}' for f in failures)}
Total failures: {len(failures)}
"""

        return None


class DiffTrimmer:
    """
    Diff 裁剪器
    将大型 diff 限幅为关键变更
    """

    def __init__(self):
        """初始化 Diff 裁剪器"""
        self._settings = get_settings()

    async def trim_diff(self, diff_content: str) -> str:
        """
        裁剪 diff 内容

        Args:
            diff_content: 原始 diff 内容

        Returns:
            裁剪后的 diff
        """
        if len(diff_content) <= self._settings.max_diff_size:
            return diff_content

        # 解析 diff 为文件块
        files = self._parse_diff_files(diff_content)

        # 为每个文件生成摘要
        summaries = []
        total_size = 0

        for file_info in files:
            summary = self._summarize_file_diff(file_info)
            size = len(summary)

            if total_size + size > self._settings.max_diff_size:
                summaries.append(f"\n... (diff truncated, {len(files) - len(summaries)} more files)")
                break

            summaries.append(summary)
            total_size += size

        header = f"""Diff Summary (truncated from {len(diff_content)} chars)
Files changed: {len(files)}
"""

        return header + '\n'.join(summaries)

    def _parse_diff_files(self, diff_content: str) -> list[dict]:
        """
        解析 diff 为文件块

        Args:
            diff_content: diff 内容

        Returns:
            文件信息列表
        """
        files = []
        current_file = None

        for line in diff_content.split('\n'):
            # 检测新文件
            if line.startswith('diff --git'):
                if current_file:
                    files.append(current_file)

                parts = line.split()
                file_path = parts[2].lstrip('a/') if len(parts) > 2 else 'unknown'
                current_file = {
                    'path': file_path,
                    'header': line,
                    'lines': [],
                    'additions': 0,
                    'deletions': 0
                }
            elif current_file:
                current_file['lines'].append(line)

                # 统计增删行数
                if line.startswith('+') and not line.startswith('+++'):
                    current_file['additions'] += 1
                elif line.startswith('-') and not line.startswith('---'):
                    current_file['deletions'] += 1

        if current_file:
            files.append(current_file)

        return files

    def _summarize_file_diff(self, file_info: dict) -> str:
        """
        为单个文件生成 diff 摘要

        Args:
            file_info: 文件信息

        Returns:
            摘要字符串
        """
        path = file_info['path']
        additions = file_info['additions']
        deletions = file_info['deletions']
        lines = file_info['lines']

        # 只显示关键部分
        summary_lines = [
            f"\n📄 {path}",
            f"   +{additions} -{deletions} lines"
        ]

        # 添加函数/类级别的变更摘要（如果适用）
        for line in lines[:50]:  # 限制行数
            if line.startswith('@@'):
                summary_lines.append(f"   {line}")
            elif line.startswith('+') or line.startswith('-'):
                # 只显示有实质内容的行
                stripped = line[1:].strip()
                if stripped and not stripped.startswith('#'):
                    summary_lines.append(f"   {line}")
                    if len(summary_lines) > 20:  # 限制每个文件的摘要行数
                        summary_lines.append("   ...")
                        break

        return '\n'.join(summary_lines)

    async def extract_changed_functions(self, diff_content: str, language: str = "python") -> list[str]:
        """
        提取变更的函数/方法列表

        Args:
            diff_content: diff 内容
            language: 编程语言

        Returns:
            变更的函数/方法名称列表
        """
        if language == "python":
            return self._extract_python_functions(diff_content)
        elif language in ["javascript", "typescript"]:
            return self._extract_js_functions(diff_content)
        else:
            return []

    def _extract_python_functions(self, diff_content: str) -> list[str]:
        """提取 Python 函数变更"""
        functions = []

        # 匹配函数定义
        pattern = r'^[\+\-]\s*def\s+(\w+)\s*\('

        for line in diff_content.split('\n'):
            match = re.match(pattern, line)
            if match:
                func_name = match.group(1)
                if line.startswith('+'):
                    functions.append(f"+ {func_name}()")
                else:
                    functions.append(f"- {func_name}()")

        return functions

    def _extract_js_functions(self, diff_content: str) -> list[str]:
        """提取 JS/TS 函数变更"""
        functions = []

        # 匹配函数定义（多种模式）
        patterns = [
            r'^[\+\-]\s*(?:function\s+(\w+)|(\w+)\s*[=:]\s*(?:async\s+)?\(|const\s+(\w+)\s*=)',
            r'^[\+\-]\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*{',  # 箭头函数和方法
        ]

        for line in diff_content.split('\n'):
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    func_name = match.group(1) or match.group(2) or match.group(3)
                    if func_name:
                        if line.startswith('+'):
                            functions.append(f"+ {func_name}()")
                        else:
                            functions.append(f"- {func_name}()")
                        break

        return functions


class EvidenceTrimmer:
    """
    证据裁剪器
    统一的证据裁剪接口
    """

    def __init__(self):
        """初始化证据裁剪器"""
        self.log_trimmer = LogTrimmer()
        self.diff_trimmer = DiffTrimmer()

    async def trim_build_output(self, build_log: str, diff_content: str) -> tuple[str, str]:
        """
        裁剪构建输出

        Args:
            build_log: 构建日志
            diff_content: 代码 diff

        Returns:
            裁剪后的日志和 diff
        """
        trimmed_log, trimmed_diff = await asyncio.gather(
            self.log_trimmer.trim_log(build_log),
            self.diff_trimmer.trim_diff(diff_content)
        )

        return trimmed_log, trimmed_diff

    async def trim_test_output(self, test_log: str) -> tuple[str, Optional[str]]:
        """
        裁剪测试输出

        Args:
            test_log: 测试日志

        Returns:
            裁剪后的日志和失败摘要
        """
        trimmed_log = await self.log_trimmer.trim_log(test_log)
        failures = await self.log_trimmer.extract_test_failures(test_log)

        return trimmed_log, failures
