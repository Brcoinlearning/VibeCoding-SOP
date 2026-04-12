#!/usr/bin/env python3
"""
Flaw Detector Module
检测代码中的致命缺陷和安全漏洞
"""
import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
import os


def matches_file_pattern(file_path: str, file_ext: str, file_name: str, patterns: List[str]) -> bool:
    """
    检查文件是否匹配给定的模式列表

    Args:
        file_path: 完整文件路径
        file_ext: 文件扩展名 (如 .py, .js)
        file_name: 文件名 (如 login.py)
        patterns: 模式列表 (如 ['*.py', '*.js', '*'])

    Returns:
        是否匹配任一模式
    """
    for pattern in patterns:
        if pattern == '*':
            return True

        # 处理扩展名模式: *.py, *.js, *.jsx 等
        if pattern.startswith('*.'):
            pattern_ext = pattern[1:]  # 移除 *，保留 .py
            if file_ext == pattern_ext:
                return True

        # 处理完整文件路径匹配
        if pattern == file_path:
            return True

        # 处理文件名匹配 (不含扩展名)
        if pattern == file_name:
            return True

    return False


class FlawCategory(Enum):
    """缺陷类别"""
    SECURITY = "security"
    CORRECTNESS = "correctness"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"


class FlawSeverity(Enum):
    """缺陷严重度"""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


# 缺陷检测规则
FLAW_PATTERNS = {
    FlawCategory.SECURITY: {
        FlawSeverity.CRITICAL: [
            {
                "name": "SQL注入",
                "patterns": [
                    r'execute\s*\(\s*f[\'"][^"]*\{',
                    r'query\s*=\s*f[\'"][^"]*\{.*\}',
                    r'\.execute\s*\(\s*["\'][^"\']*%s',
                    r'SELECT.*FROM.*WHERE.*["\']\s*\+',
                ],
                "file_patterns": ['*.py', '*.js', '*.java', '*.go'],
                "description": "未使用参数化查询,存在SQL注入风险",
                "remediation": "使用参数化查询或ORM"
            },
            {
                "name": "XSS跨站脚本",
                "patterns": [
                    r'innerHTML\s*=\s*',
                    r'\.html\s*\(\s*request\.',
                    r'\.insertAdjacentHTML',
                    r'dangerouslySetInnerHTML',
                ],
                "file_patterns": ['*.js', '*.jsx', '*.tsx', '*.html'],
                "description": "直接渲染用户输入,存在XSS风险",
                "remediation": "对用户输入进行HTML转义"
            },
            {
                "name": "敏感信息泄露",
                "patterns": [
                    r'password\s*=\s*["\'][^"\']+["\']',
                    r'api_key\s*=\s*["\'][^"\']+["\']',
                    r'secret\s*=\s*["\'][^"\']+["\']',
                    r'token\s*=\s*["\'][^"\']+["\']',
                    r'AKIA[0-9A-Z]{16}',  # AWS Access Key
                    r'sk-[a-zA-Z0-9]{48}',  # OpenAI API Key
                ],
                "file_patterns": ['*'],
                "description": "硬编码敏感信息",
                "remediation": "使用环境变量或密钥管理服务"
            },
            {
                "name": "认证绕过",
                "patterns": [
                    r'@app\.route.*\n.*auth\s*=\s*False',
                    r'decorator.*auth.*=.*False',
                    r'login_required\s*=\s*False',
                ],
                "file_patterns": ['*.py', '*.js', '*.go'],
                "description": "认证被禁用或绕过",
                "remediation": "启用认证中间件"
            },
        ],
        FlawSeverity.MAJOR: [
            {
                "name": "CSRF攻击",
                "patterns": [
                    r'app\.post.*\n.*return.*json',
                    r'POST.*without.*csrf',
                    r'csrf.*disable',
                ],
                "file_patterns": ['*.py', '*.js'],
                "description": "POST请求缺少CSRF保护",
                "remediation": "添加CSRF token验证"
            },
        ]
    },
    FlawCategory.CORRECTNESS: {
        FlawSeverity.CRITICAL: [
            {
                "name": "空指针解引用",
                "patterns": [
                    r'\w+\.\w+\s*\(\s*\)\s*\.\w+',  # 链式调用可能空指针
                    r'if\s*\(\s*\w+\s*\)\s*{',
                ],
                "file_patterns": ['*.py', '*.js', '*.java', '*.go'],
                "description": "可能存在空指针解引用",
                "remediation": "添加空值检查"
            },
            {
                "name": "数组越界",
                "patterns": [
                    r'\[.*\d+\]',  # 索引访问
                    r'\.at\s*\(',   # at方法
                ],
                "file_patterns": ['*.py', '*.js', '*.java'],
                "description": "未检查索引边界",
                "remediation": "添加边界检查"
            },
        ],
        FlawSeverity.MAJOR: [
            {
                "name": "类型转换错误",
                "patterns": [
                    r'int\s*\(\s*request\.',
                    r'str\s*\(\s*\w+\s*\)\s*\.',
                    r'parseFloat\s*\(\s*',
                ],
                "file_patterns": ['*.py', '*.js', '*.java'],
                "description": "未验证类型直接转换",
                "remediation": "验证输入类型后再转换"
            },
        ]
    },
    FlawCategory.PERFORMANCE: {
        FlawSeverity.MAJOR: [
            {
                "name": "N+1查询",
                "patterns": [
                    r'for\s+\w+\s+in\s+.*:\s*.*\.get\s*\(',
                    r'foreach.*\.find',
                    r'query.*inside.*loop',
                ],
                "file_patterns": ['*.py', '*.js', '*.java'],
                "description": "循环中执行数据库查询",
                "remediation": "使用批量查询或预加载"
            },
            {
                "name": "内存泄漏",
                "patterns": [
                    r'setInterval\s*\(',
                    r'setTimeout\s*\([^,]+,\s*0\s*\)',  # 递归setTimeout
                    r'addEventListener\s*\([^,]+,\s*\w+\s*\)',  # 未移除监听器
                ],
                "file_patterns": ['*.js', '*.jsx', '*.tsx'],
                "description": "定时器或监听器未清理",
                "remediation": "在组件卸载时清理资源"
            },
            {
                "name": "死循环",
                "patterns": [
                    r'while\s*\(\s*True\s*\)',
                    r'for\s*\(\s*;\s*;\s*\)',
                    r'while\s*\(\s*1\s*\)',
                ],
                "file_patterns": ['*'],
                "description": "可能的无限循环",
                "remediation": "添加退出条件或超时"
            },
        ]
    },
    FlawCategory.MAINTAINABILITY: {
        FlawSeverity.MINOR: [
            {
                "name": "魔法数字",
                "patterns": [
                    r'\b\d{3,}\b',  # 3位及以上数字
                ],
                "file_patterns": ['*'],
                "description": "使用未命名的魔法数字",
                "remediation": "使用常量或枚举"
            },
            {
                "name": "重复代码",
                "patterns": [
                    # 需要多行分析,这里简化处理
                    r'def\s+\w+\s*\([^)]*\):\s*return\s+\w+',
                ],
                "file_patterns": ['*.py'],
                "description": "代码重复",
                "remediation": "提取公共函数"
            },
            {
                "name": "未处理异常",
                "patterns": [
                    r'except\s*:',
                    r'except\s*Exception',
                    r'catch\s*\(\s*\w+\s*\)\s*{\s*}',  # 空catch块
                ],
                "file_patterns": ['*.py', '*.js', '*.java'],
                "description": "异常未处理或处理不当",
                "remediation": "记录异常或添加处理逻辑"
            },
        ]
    }
}


def detect_flaws_in_code(
    code: str,
    file_path: str,
    categories: Optional[List[FlawCategory]] = None
) -> List[Dict]:
    """
    在代码中检测缺陷

    Args:
        code: 代码内容
        file_path: 文件路径
        categories: 要检测的缺陷类别 (默认全部)

    Returns:
        检测到的缺陷列表
    """
    flaws = []

    if categories is None:
        categories = list(FlawCategory)

    # 提取文件扩展名
    import os
    file_ext = os.path.splitext(file_path)[1].lower()  # 如 .py, .js
    file_name = os.path.basename(file_path).lower()

    for category in categories:
        if category not in FLAW_PATTERNS:
            continue

        for severity, patterns in FLAW_PATTERNS[category].items():
            for pattern_def in patterns:
                # 检查文件类型是否匹配
                if not matches_file_pattern(file_path, file_ext, file_name, pattern_def["file_patterns"]):
                    continue

                # 检查模式
                for pattern_regex in pattern_def["patterns"]:
                    matches = re.finditer(pattern_regex, code, re.MULTILINE | re.IGNORECASE)

                    for match in matches:
                        # 获取匹配的行号
                        line_num = code[:match.start()].count('\n') + 1
                        line_content = code.split('\n')[line_num - 1].strip()

                        flaws.append({
                            "name": pattern_def["name"],
                            "category": category.value,
                            "severity": severity.value,
                            "line": line_num,
                            "content": line_content,
                            "description": pattern_def["description"],
                            "remediation": pattern_def["remediation"],
                            "match": match.group(0)
                        })

    return flaws


def analyze_diff_for_flaws(diff_content: str) -> List[Dict]:
    """
    分析diff中的缺陷

    Args:
        diff_content: Git diff内容

    Returns:
        检测到的缺陷列表
    """
    flaws = []

    # 解析diff获取文件和变更内容
    current_file = None
    current_changes = []

    for line in diff_content.split('\n'):
        if line.startswith('+++ b/'):
            # 处理前一个文件
            if current_file and current_changes:
                code_block = '\n'.join(current_changes)
                file_flaws = detect_flaws_in_code(code_block, current_file)
                flaws.extend(file_flaws)

            # 开始新文件
            current_file = line[6:]  # 移除 '+++ b/'
            current_changes = []

        elif line.startswith('+') and not line.startswith('+++'):
            # 添加的行 (可能是新增的缺陷)
            current_changes.append(line[1:])  # 移除 '+'

    # 处理最后一个文件
    if current_file and current_changes:
        code_block = '\n'.join(current_changes)
        file_flaws = detect_flaws_in_code(code_block, current_file)
        flaws.extend(file_flaws)

    return flaws


def generate_flaw_report(
    flaws: List[Dict],
    task_id: str
) -> Dict:
    """
    生成缺陷报告

    Args:
        flaws: 检测到的缺陷列表
        task_id: 任务ID

    Returns:
        结构化的缺陷报告
    """
    # 按严重度分组
    by_severity = {
        FlawSeverity.CRITICAL.value: [],
        FlawSeverity.MAJOR.value: [],
        FlawSeverity.MINOR.value: [],
        FlawSeverity.INFO.value: []
    }

    for flaw in flaws:
        by_severity[flaw["severity"]].append(flaw)

    # 确定整体严重度
    if by_severity[FlawSeverity.CRITICAL.value]:
        overall_severity = FlawSeverity.CRITICAL.value
    elif by_severity[FlawSeverity.MAJOR.value]:
        overall_severity = FlawSeverity.MAJOR.value
    elif by_severity[FlawSeverity.MINOR.value]:
        overall_severity = FlawSeverity.MINOR.value
    else:
        overall_severity = FlawSeverity.INFO.value

    # 生成lethal_flaw描述
    critical_flaws = by_severity[FlawSeverity.CRITICAL.value]
    if critical_flaws:
        flaw_names = [f["name"] for f in critical_flaws]
        lethal_flaw = f"发现{len(critical_flaws)}个致命缺陷: {', '.join(flaw_names)}"
    elif by_severity[FlawSeverity.MAJOR.value]:
        major_flaws = by_severity[FlawSeverity.MAJOR.value]
        flaw_names = [f["name"] for f in major_flaws[:3]]  # 最多3个
        lethal_flaw = f"发现{len(major_flaws)}个主要缺陷: {', '.join(flaw_names)}"
    else:
        lethal_flaw = "未发现致命缺陷,但建议检查代码质量"

    # 生成exploit_path (针对最严重的缺陷)
    exploit_path = "N/A"
    if critical_flaws:
        top_flaw = critical_flaws[0]
        exploit_path = generate_exploit_path(top_flaw)

    return {
        "task_id": task_id,
        "overall_severity": overall_severity,
        "lethal_flaw": lethal_flaw,
        "exploit_path": exploit_path,
        "flaws_found": len(flaws),
        "flaws_by_severity": {k: len(v) for k, v in by_severity.items()},
        "flaws": flaws
    }


def generate_exploit_path(flaw: Dict) -> str:
    """
    为缺陷生成复现路径

    Args:
        flaw: 缺陷信息

    Returns:
        复现路径文本
    """
    if flaw["category"] == FlawCategory.SECURITY.value:
        if flaw["name"] == "SQL注入":
            return f"""步骤1: 定位漏洞代码 (文件: {flaw.get('file', 'unknown')}, 行: {flaw['line']})
步骤2: 构造恶意输入: admin' OR '1'='1
步骤3: 发送包含恶意payload的请求
步骤4: 观察响应,确认SQL注入成功"""
        elif flaw["name"] == "XSS跨站脚本":
            return f"""步骤1: 定位漏洞代码 (文件: {flaw.get('file', 'unknown')}, 行: {flaw['line']})
步骤2: 在输入框插入: <script>alert(document.cookie)</script>
步骤3: 提交表单
步骤4: 查看页面,确认XSS触发"""

    elif flaw["category"] == FlawCategory.CORRECTNESS.value:
        return f"""步骤1: 准备触发条件 (文件: {flaw.get('file', 'unknown')}, 行: {flaw['line']})
步骤2: 执行相关功能
步骤3: 观察系统行为
步骤4: 确认{flaw['name']}发生"""

    return "N/A (非安全缺陷,无复现路径)"


if __name__ == "__main__":
    # 测试代码
    test_code = '''
def login(username):
    query = f"SELECT * FROM users WHERE username='{username}'"
    return execute(query)
'''

    flaws = detect_flaws_in_code(test_code, "auth/login.py")
    for flaw in flaws:
        print(f"[{flaw['severity'].upper()}] {flaw['name']}: {flaw['description']}")
