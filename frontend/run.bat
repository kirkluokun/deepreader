@echo off
chcp 65001 >nul

echo 🔍 DeepReader 前端启动脚本 (Poetry + Pyenv 环境)
echo ==================================

REM 检查Poetry是否安装
poetry --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Poetry，请先安装 Poetry
    echo 安装命令: (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content ^| python -
    pause
    exit /b 1
)

REM 检查是否在正确的目录
if not exist "api_server.py" (
    echo ❌ 错误: 请在 frontend 目录下运行此脚本
    pause
    exit /b 1
)

REM 切换到项目根目录（DeepReader目录）
cd ..

REM 检查pyproject.toml是否存在
if not exist "pyproject.toml" (
    echo ❌ 错误: 未找到 pyproject.toml，请确保在正确的项目目录
    pause
    exit /b 1
)

REM 显示当前Python版本
echo 🐍 当前Python版本:
poetry run python --version

REM 安装依赖
echo 📥 安装项目依赖...
poetry install

REM 切换回frontend目录
cd frontend

REM 启动服务器
echo 🚀 启动DeepReader前端服务器...
echo 📱 访问地址: http://localhost:8000
echo 📋 API文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务器
echo ==================================

poetry run python api_server.py

pause