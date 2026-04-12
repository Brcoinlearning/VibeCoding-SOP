#!/bin/bash
# Agent-in-Tool Standalone CLI 快速启动脚本

set -e

echo "=========================================="
echo "  Agent-in-Tool Standalone CLI"
echo "  真正的敏捷单机架构"
echo "=========================================="
echo ""

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
pip3 install anthropic filelock --quiet 2>/dev/null || {
    echo "安装依赖..."
    pip3 install anthropic filelock
}

# 检查API密钥
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  ANTHROPIC_API_KEY 环境变量未设置"
    echo "请设置: export ANTHROPIC_API_KEY='your-key-here'"
    echo ""
    read -p "是否现在输入API密钥? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "请输入API密钥: " api_key
        export ANTHROPIC_API_KEY="$api_key"
    else
        exit 1
    fi
fi

# 创建必要目录
echo "📁 创建工作目录..."
mkdir -p 20-planning
mkdir -p 40-review
mkdir -p 50-release
mkdir -p src

echo "✅ 环境准备完成！"
echo ""
echo "🚀 启动Standalone CLI..."
echo ""
echo "使用方法："
echo "1. 读取需求:"
echo "   python3 cli.py read-task TASK-001 --workspace ."
echo "1.5 需求锻造:"
echo "   python3 cli.py forge-contract TASK-001 \"你的需求\" --workspace ."
echo "2. TDD门禁:"
echo "   python3 cli.py tdd-enforce TASK-001 --workspace . --test-command \"pytest -q\""
echo "2. 触发盲审:"
echo "   python3 cli.py blind-review TASK-001 --workspace ."
echo "3. 提交放行:"
echo "   python3 cli.py submit-owner TASK-001 --workspace ."
echo ""
echo "这是独立运行模式，不依赖MCP Server。"
echo "=========================================="
echo ""

# 显示帮助
python3 cli.py --help
