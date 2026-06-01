#!/bin/bash
# 基金量化后端启动脚本
cd "$(dirname "$0")/backend"

HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-8000}

echo "🚀 基金量化API服务启动..."
echo "📡 地址: http://$HOST:$PORT"
echo "📖 Docs: http://$HOST:$PORT/docs"
echo ""

# 创建数据目录
mkdir -p data

python3 main.py
