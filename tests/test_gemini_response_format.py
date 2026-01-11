# -*- coding: utf-8 -*-
"""
测试不同 Gemini 模型的响应格式
用于诊断和解决 LLM 输出格式不一致问题
"""
import asyncio
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 加载环境变量
from dotenv import load_dotenv
env_path = "/Users/kirk/PROJECT/FinAIcrew/dynamic-gptr/.env"
load_dotenv(env_path)

from langchain_google_genai import ChatGoogleGenerativeAI


MODELS_TO_TEST = [
    "gemini-2.0-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
]

TEST_PROMPT = """请返回一个JSON格式的响应：
```json
[{"title": "测试标题", "summary": "测试摘要", "questions": ["问题1", "问题2"]}]
```
只返回JSON，不要其他内容。"""


async def test_model(model_name: str):
    """测试单个模型的响应格式"""
    print(f"\n{'='*60}")
    print(f"测试模型: {model_name}")
    print('='*60)
    
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("[错误] 未设置 GOOGLE_API_KEY 环境变量")
            return {"model": model_name, "success": False, "error": "GOOGLE_API_KEY not set"}
        
        llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.3, google_api_key=api_key)
        messages = [{"role": "user", "content": TEST_PROMPT}]
        
        # 调用模型
        output = await llm.ainvoke(messages)
        
        # 打印原始输出信息
        print(f"\n[输出类型] {type(output)}")
        print(f"[输出类名] {output.__class__.__name__}")
        
        # 检查 content 属性
        content = output.content
        print(f"\n[content 类型] {type(content)}")
        print(f"[content 类名] {content.__class__.__name__ if hasattr(content, '__class__') else 'N/A'}")
        
        # 如果是列表，打印每个元素的类型和内容
        if isinstance(content, list):
            print(f"[content 长度] {len(content)}")
            for i, item in enumerate(content):
                print(f"\n  [元素 {i}]")
                print(f"    类型: {type(item)}")
                if isinstance(item, dict):
                    print(f"    键: {list(item.keys())}")
                    for k, v in item.items():
                        v_str = str(v)[:100] + "..." if len(str(v)) > 100 else str(v)
                        print(f"    {k}: {v_str}")
                else:
                    item_str = str(item)[:200] + "..." if len(str(item)) > 200 else str(item)
                    print(f"    内容: {item_str}")
        else:
            # 直接是字符串
            content_str = str(content)[:500] + "..." if len(str(content)) > 500 else str(content)
            print(f"[content 内容]\n{content_str}")
        
        # 测试标准化处理
        normalized = normalize_llm_response(content)
        print(f"\n[标准化后类型] {type(normalized)}")
        print(f"[标准化后内容]\n{normalized[:500]}..." if len(normalized) > 500 else f"[标准化后内容]\n{normalized}")
        
        return {"model": model_name, "success": True, "content_type": type(content).__name__}
        
    except Exception as e:
        print(f"\n[错误] {type(e).__name__}: {e}")
        return {"model": model_name, "success": False, "error": str(e)}


def normalize_llm_response(content) -> str:
    """
    标准化 LLM 响应为字符串
    处理不同模型返回格式的差异
    """
    # 情况1: 已经是字符串
    if isinstance(content, str):
        return content
    
    # 情况2: 是列表（multipart content）
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict):
                # 提取 'text' 字段（Gemini 2.5/3.0 的常见格式）
                if 'text' in item:
                    text_parts.append(str(item['text']))
                # 提取 'content' 字段
                elif 'content' in item:
                    text_parts.append(str(item['content']))
                # 其他情况，尝试转为字符串
                else:
                    # 跳过 signature 等元数据
                    if 'type' in item and item.get('type') == 'text':
                        if 'text' in item:
                            text_parts.append(str(item['text']))
            else:
                # 其他类型，尝试转为字符串
                text_parts.append(str(item))
        
        return "".join(text_parts)
    
    # 情况3: 是字典
    if isinstance(content, dict):
        if 'text' in content:
            return str(content['text'])
        elif 'content' in content:
            return str(content['content'])
        else:
            return str(content)
    
    # 兜底：转为字符串
    return str(content)


async def main():
    print("=" * 60)
    print("Gemini 模型响应格式测试")
    print("=" * 60)
    
    results = []
    for model in MODELS_TO_TEST:
        result = await test_model(model)
        results.append(result)
        await asyncio.sleep(1)  # 避免速率限制
    
    # 打印汇总
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    for r in results:
        status = "✅" if r.get("success") else "❌"
        content_type = r.get("content_type", r.get("error", "N/A"))
        print(f"{status} {r['model']}: {content_type}")


if __name__ == "__main__":
    asyncio.run(main())

