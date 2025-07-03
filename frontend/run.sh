#!/bin/bash

# DeepReader 前端快速启动脚本 (Poetry + Pyenv 环境)

echo "🔍 DeepReader 前端启动脚本"
echo "=================================="

# 检查Poetry是否安装
if ! command -v poetry &> /dev/null; then
    echo "❌ 错误: 未找到 Poetry，请先安装 Poetry"
    echo "安装命令: curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# 检查是否在正确的目录
if [ ! -f "api_server.py" ]; then
    echo "❌ 错误: 请在 frontend 目录下运行此脚本"
    exit 1
fi

# 切换到项目根目录（DeepReader目录）
cd ..

# 检查pyproject.toml是否存在
if [ ! -f "pyproject.toml" ]; then
    echo "❌ 错误: 未找到 pyproject.toml，请确保在正确的项目目录"
    exit 1
fi

# 显示当前Python版本
echo "🐍 当前Python版本:"
poetry run python --version

# 安装依赖
echo "📥 安装项目依赖..."
poetry install

# 切换回frontend目录
cd frontend

# 启动服务器
echo "🚀 启动DeepReader前端服务器..."
echo "📱 访问地址: http://localhost:8000"
echo "📋 API文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "=================================="

poetry run python api_server.py