#!/bin/bash
# 编排引擎初始化脚本

set -e

echo "🚀 Initializing SOP Orchestrator..."

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# 检查是否满足最低版本要求
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "❌ Python 3.10 or higher is required"
    exit 1
fi

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# 升级 pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# 安装依赖
echo "📥 Installing dependencies..."
pip install -e .

# 安装开发依赖（可选）
if [ "$1" == "--dev" ]; then
    echo "📥 Installing development dependencies..."
    pip install -e ".[dev]"
fi

# 创建必要的目录
echo "📁 Creating directories..."
mkdir -p workspace/review_requests
mkdir -p artifacts/20-planning
mkdir -p artifacts/30-build
mkdir -p artifacts/40-review
mkdir -p artifacts/50-release
mkdir -p logs

# 创建示例配置文件
if [ ! -f ".env" ]; then
    echo "📝 Creating example .env file..."
    current_dir="$(pwd)"
    cat > .env << EOF
# Orchestrator Configuration

# 基础路径
ORCHESTRATOR_BASE_PATH=${current_dir}
ORCHESTRATOR_WORKSPACE_PATH=${current_dir}/workspace
ORCHESTRATOR_ARTIFACTS_PATH=${current_dir}/artifacts
ORCHESTRATOR_LOGS_PATH=${current_dir}/logs

# AI 后端配置
ORCHESTRATOR_AI_BACKEND=filesystem
# ORCHESTRATOR_AI_BACKEND=claude-api
# ORCHESTRATOR_CLAUDE_API_KEY=your-api-key-here

# 日志配置
ORCHESTRATOR_LOG_LEVEL=INFO

# 证据配置
ORCHESTRATOR_MAX_DIFF_SIZE=50000
ORCHESTRATOR_MAX_LOG_LINES=1000
ORCHESTRATOR_EVIDENCE_FRESHNESS_THRESHOLD=3600

# 调试模式
ORCHESTRATOR_DEBUG_MODE=false
ORCHESTRATOR_MOCK_MODE=false
EOF
fi

# 运行验证
echo "🔍 Validating installation..."
python3 -m src.main validate

echo ""
echo "✅ Initialization complete!"
echo ""
echo "To get started:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Run the orchestrator: python3 -m src.main --help"
echo "  3. Try a review: python3 -m src.main review T-001"
echo ""
