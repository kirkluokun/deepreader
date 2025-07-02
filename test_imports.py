#!/usr/bin/env python3
"""
测试导入是否正常工作
"""
import sys
print("Python 路径:", sys.executable)
print("Python 版本:", sys.version)

try:
    from gpt_researcher.config import Config, config
    print("✅ gpt_researcher.config 导入成功")
    print("Config 类:", Config)
    print("config 对象:", config)
except ImportError as e:
    print("❌ gpt_researcher.config 导入失败:", e)

try:
    from gpt_researcher.utils.llm import create_chat_completion
    print("✅ gpt_researcher.utils.llm 导入成功")
    print("create_chat_completion 函数:", create_chat_completion)
except ImportError as e:
    print("❌ gpt_researcher.utils.llm 导入失败:", e)

print("\n所有导入测试完成！") 