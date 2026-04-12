#!/usr/bin/env python3
"""
Log Trimmer Module
裁剪日志和diff以控制上下文大小
"""
import re
from typing import Tuple, List


def trim_logs_and_diffs(
    build_log: str,
    diff_content: str,
    max_log_lines: int = 100,
    max_diff_chars: int = 50000
) -> Tuple[str, str]:
    """
    裁剪日志和diff以控制上下文大小

    保留策略:
    - 日志: 保留错误栈,移除重复信息
    - Diff: 保留变更统计,裁剪大文件

    Args:
        build_log: 构建日志
        diff_content: 代码diff
        max_log_lines: 日志最大行数
        max_diff_chars: diff最大字符数

    Returns:
        (trimmed_log, trimmed_diff)
    """
    trimmed_log = trim_build_log(build_log, max_log_lines)
    trimmed_diff = trim_code_diff(diff_content, max_diff_chars)

    return trimmed_log, trimmed_diff


def trim_build_log(build_log: str, max_lines: int = 100) -> str:
    """
    裁剪构建日志

    策略:
    1. 提取关键错误栈 (Traceback, ERROR, FATAL)
    2. 移除重复的进度信息
    3. 保留最后N行 (通常包含最终状态)
    4. 限制总字符数
    """
    if not build_log:
        return ""

    lines = build_log.split('\n')

    # 关键字列表
    error_keywords = [
        'Traceback',
        'ERROR',
        'FATAL',
        'CRITICAL',
        'Exception',
        'Failed',
        'Error:',
        'AssertionError',
        'ValueError',
        'KeyError',
        'TypeError',
        'AttributeError',
        'ImportError'
    ]

    warning_keywords = [
        'WARNING',
        'WARN',
        'DeprecationWarning',
        'UserWarning'
    ]

    # 提取错误行
    error_lines = []
    warning_lines = []
    other_lines = []

    for i, line in enumerate(lines):
        if any(keyword in line for keyword in error_keywords):
            error_lines.append((i, line))
        elif any(keyword in line for keyword in warning_keywords):
            warning_lines.append((i, line))
        else:
            other_lines.append((i, line))

    # 构建裁剪后的日志
    trimmed_lines = []

    # 1. 添加错误行 (带上下文)
    if error_lines:
        # 按行号排序
        error_lines.sort(key=lambda x: x[0])

        for line_no, line in error_lines:
            # 添加错误行
            trimmed_lines.append(line)

            # 添加上下文 (前后2行)
            for context_offset in [-2, -1, 1, 2]:
                context_idx = line_no + context_offset
                if 0 <= context_idx < len(lines):
                    context_line = lines[context_idx]
                    # 避免重复
                    if context_line not in [l for _, l in trimmed_lines]:
                        trimmed_lines.append(context_line)

    # 2. 添加警告行 (限制数量)
    if warning_lines:
        warning_lines.sort(key=lambda x: x[0])
        for _, line in warning_lines[:20]:  # 最多20行警告
            if line not in trimmed_lines:
                trimmed_lines.append(line)

    # 3. 添加最后N行 (通常包含最终状态)
    final_lines = other_lines[-max_lines:]
    for _, line in final_lines:
        if line not in trimmed_lines:
            trimmed_lines.append(line)

    # 4. 限制总行数
    if len(trimmed_lines) > max_lines:
        # 优先保留错误相关行
        error_related = [l for l in trimmed_lines if any(kw in l for kw in error_keywords)]
        other = [l for l in trimmed_lines if l not in error_related]

        trimmed_lines = error_related + other[-(max_lines - len(error_related)):]

    # 5. 移除重复的行
    seen = set()
    unique_lines = []
    for line in trimmed_lines:
        line_stripped = line.strip()
        if line_stripped and line_stripped not in seen:
            seen.add(line_stripped)
            unique_lines.append(line)

    # 6. 添加裁剪标记
    if len(lines) > len(unique_lines):
        unique_lines.insert(0, f"... [Log trimmed: showing {len(unique_lines)} of {len(lines)} lines] ...")

    return '\n'.join(unique_lines)


def trim_code_diff(diff_content: str, max_chars: int = 50000) -> str:
    """
    裁剪代码diff

    策略:
    1. 如果小于限制,保留全部
    2. 如果超过限制:
       - 保留文件头
       - 保留变更统计
       - 保留每个文件的前N行变更
    """
    if not diff_content:
        return ""

    # 如果小于限制,保留全部
    if len(diff_content) <= max_chars:
        return diff_content

    lines = diff_content.split('\n')

    # 提取文件头和统计信息
    header_lines = []
    diff_blocks = []
    current_block = []

    in_diff_block = False
    file_count = 0
    max_files = 20  # 最多保留20个文件

    for line in lines:
        # 文件头
        if line.startswith('diff --git') or line.startswith('---') or line.startswith('+++'):
            if current_block:
                diff_blocks.append(current_block)
                current_block = []

            if line.startswith('diff --git'):
                file_count += 1
                if file_count > max_files:
                    # 达到文件数量限制
                    break

            header_lines.append(line)
            in_diff_block = True

        # 变更统计 (@@ lines)
        elif line.startswith('@@'):
            if current_block:
                diff_blocks.append(current_block)
                current_block = []

            current_block.append(line)

        # 变更行
        elif in_diff_block and (line.startswith('+') or line.startswith('-') or line.startswith(' ')):
            if len(current_block) < 100:  # 每个文件最多100行变更
                current_block.append(line)

        # 其他行
        else:
            if in_diff_block and current_block:
                diff_blocks.append(current_block)
                current_block = []
            in_diff_block = False

    # 添加最后一个block
    if current_block:
        diff_blocks.append(current_block)

    # 组合结果
    result_lines = header_lines.copy()

    for block in diff_blocks[:max_files]:
        result_lines.extend(block)

    result = '\n'.join(result_lines)

    # 如果还是超过限制,进一步裁剪
    if len(result) > max_chars:
        # 只保留文件名和统计
        summary_lines = []
        for line in result_lines:
            if any(prefix in line for prefix in ['diff --git', '---', '+++', '@@']):
                summary_lines.append(line)

        result = '\n'.join(summary_lines)

        # 添加裁剪标记
        if len(result) > max_chars:
            result = f"... [Diff trimmed: showing file headers only] ...\n\n{result[:max_chars]}"

    return result


def extract_test_failures(test_output: str) -> List[str]:
    """
    从测试输出中提取失败的测试用例

    Args:
        test_output: 测试输出

    Returns:
        失败测试用例列表
    """
    failures = []

    # pytest格式
    pytest_pattern = r'FAILED\s+(.+?::\w+)'
    failures.extend(re.findall(pytest_pattern, test_output))

    # unittest格式
    unittest_pattern = r'FAIL:\s+(.+)'
    failures.extend(re.findall(unittest_pattern, test_output))

    return failures


def extract_error_summary(build_log: str) -> str:
    """
    提取错误摘要

    Args:
        build_log: 构建日志

    Returns:
        错误摘要
    """
    if not build_log:
        return "No errors"

    # 统计错误类型
    error_types = {
        'SyntaxError': 0,
        'ImportError': 0,
        'AssertionError': 0,
        'ValueError': 0,
        'KeyError': 0,
        'TypeError': 0,
        'AttributeError': 0,
        'RuntimeError': 0,
    }

    for error_type in error_types.keys():
        count = build_log.count(error_type)
        error_types[error_type] = count

    # 生成摘要
    total_errors = sum(error_types.values())
    if total_errors == 0:
        return "No errors detected"

    summary_parts = []
    for error_type, count in error_types.items():
        if count > 0:
            summary_parts.append(f"{error_type}: {count}")

    return f"Errors found: {', '.join(summary_parts)}"


if __name__ == "__main__":
    # 测试代码
    import sys

    if len(sys.argv) > 1:
        log_file = sys.argv[1]
        with open(log_file, 'r') as f:
            log_content = f.read()

        trimmed_log = trim_build_log(log_content)
        print("Trimmed Log:")
        print(trimmed_log)
        print("\n" + "="*50)
        print("Error Summary:")
        print(extract_error_summary(log_content))
    else:
        print("Usage: python log_trimmer.py <log_file>")
