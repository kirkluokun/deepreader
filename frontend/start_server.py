#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: start_server.py
@time: 2025-01-01 10:00
@desc: DeepReader 前端启动脚本 (Poetry + Pyenv 环境)
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_poetry():
    """检查Poetry是否安装"""
    if not shutil.which('poetry'):
        print("❌ 错误: 未找到 Poetry")
        print("请先安装 Poetry:")
        print("  Linux/macOS: curl -sSL https://install.python-poetry.org | python3 -")
        print("  Windows: (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -")
        return False
    return True

def check_pyproject():
    """检查是否在Poetry项目目录"""
    current_dir = Path.cwd()
    deepreader_dir = current_dir.parent
    
    pyproject_path = deepreader_dir / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"❌ 错误: 未找到 pyproject.toml")
        print(f"当前目录: {current_dir}")
        print(f"查找路径: {pyproject_path}")
        print("请确保在正确的DeepReader项目目录")
        return False, None
    return True, deepreader_dir

def install_dependencies(project_dir):
    """安装项目依赖"""
    print("📥 安装项目依赖...")
    try:
        result = subprocess.run(['poetry', 'install'], 
                              cwd=project_dir, 
                              check=True, 
                              capture_output=True, 
                              text=True)
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        print(f"输出: {e.stdout}")
        print(f"错误: {e.stderr}")
        return False

def show_python_version(project_dir):
    """显示当前Python版本"""
    try:
        result = subprocess.run(['poetry', 'run', 'python', '--version'], 
                              cwd=project_dir, 
                              capture_output=True, 
                              text=True)
        print(f"🐍 当前Python版本: {result.stdout.strip()}")
    except subprocess.CalledProcessError:
        print("⚠️  无法获取Python版本信息")

def start_server(project_dir, frontend_dir):
    """启动服务器"""
    print("🚀 启动DeepReader前端服务器...")
    print("📱 访问地址: http://localhost:8000")
    print("📋 API文档: http://localhost:8000/docs")
    print("")
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    try:
        # 在frontend目录下运行api_server.py，但使用Poetry环境
        subprocess.run(['poetry', 'run', 'python', 'api_server.py'], 
                      cwd=frontend_dir, 
                      env={**os.environ, 'PYTHONPATH': str(project_dir)})
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 服务器启动失败: {e}")
        return False
    return True

def main():
    print("🔍 DeepReader 前端启动脚本 (Poetry + Pyenv 环境)")
    print("=" * 50)
    
    # 检查当前目录
    current_dir = Path.cwd()
    if not (current_dir / "api_server.py").exists():
        print("❌ 错误: 请在 frontend 目录下运行此脚本")
        return 1
    
    # 检查Poetry
    if not check_poetry():
        return 1
    
    # 检查项目结构
    project_exists, project_dir = check_pyproject()
    if not project_exists:
        return 1
    
    # 显示Python版本
    show_python_version(project_dir)
    
    # 安装依赖
    if not install_dependencies(project_dir):
        return 1
    
    # 启动服务器
    if not start_server(project_dir, current_dir):
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())