#!/bin/bash
# 运行编排引擎的便捷脚本

set -e

# 脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 激活虚拟环境
if [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
else
    echo "❌ Virtual environment not found. Run ./bootstrap.sh first."
    exit 1
fi

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 运行主程序
python -m src.main "$@"
