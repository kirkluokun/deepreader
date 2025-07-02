# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: prompts.py
@time: 2024-07-29 15:00
@desc: Prompts for DeepReader Agents
"""
from langchain.prompts import PromptTemplate

RESTRUCTURE_MD_PROMPT = """
你是一个专业的文档结构分析师。你的任务是深入理解用户提供的Markdown文本，忽略其中所有现存的、不可靠的'#'标题标记，并根据文本的语义内容，重新构建一个层级清晰的目录结构。

请遵循以下规则：
1. **语义优先**: 不要被现有的'#'符号误导。你需要理解每个段落的真实意图，判断它是一个章节标题、一个小节标题，还是正文内容。
2. **层级识别**: 准确地识别出标题的层级关系（一级、二级、三级等）。
3. **内容过滤**: 忽略并排除任何与文档核心主题无关的内容，例如"目录"、"参考文献"、"法律声明"、"团队介绍"、"附录"等部分。
4. **精确输出**: 严格按照以下JSON格式输出结果，不要包含任何额外的解释或说明：

{
  "title": "文档主标题",
  "toc": [
    {
      "title": "第一章标题",
      "level": 1,
      "children": [
        {
          "title": "1.1节标题",
          "level": 2,
          "children": []
        },
        {
          "title": "1.2节标题",
          "level": 2,
          "children": []
        }
      ]
    },
    {
      "title": "第二章标题",
      "level": 1,
      "children": []
    }
  ]
}

以下是需要分析的Markdown文本：
---
{markdown_content}
---
"""

# --- ReadingAgent Prompt ---
READING_AGENT_PROMPT = PromptTemplate(
    input_variables=["chapter_content", "user_question", "background_memory"],
    template="""
You are a professional {research_role}. Your task is to read a snippets of a book or a report, based on the user's core research question (user_question) and the background memory, summarize and extract the main storyline, key viewpoints, and core data of this snippets. Then, propose a series of key questions related to this snippets. The response should be in Chinese.

**Context:**
- User's Core Research Question: "{user_question}"
- Background Memory from previous chapters: 
  ```
  {background_memory}
  ```

**Current Chapter Content to Analyze:**
```
{chapter_content}
```

**Your Tasks:**
Based on the chapter content, please perform the following two tasks and respond in a single, valid JSON object, language in Chinese.

1.  **`chapter_summary`**: Summarize the narrative, key arguments, and important data points of this chapter. The summary should be concise and relevant to the user's core research question. The background_memory is the essence and conclusion summary of previous chapters of this book, and the user's core question is user_question. Please summarize and abstract the main storyline, key viewpoints, and core data of this chapter based on chapter_content.
2.  **`questions`**: Focusing on the User's Core Research Question and the important issues you have identified from the background memory, formulate several insightful questions (less than 5) that probe deeper into the chapter's main themes or anticipate future developments in subsequent chapters. These questions will be used to search for related information within the entire document.

**JSON Output Format:**
```json
{{
  "chapter_summary": "A concise summary of the chapter's content...",
  "questions": [
    "An insightful question about the chapter...",
    "Another question to explore...",
    "A final question linking to potential future topics..."
  ]
}}
```
"""
)

# --- ReviewerAgent (RAG) Prompt ---
REVIEWER_AGENT_PROMPT = PromptTemplate(
    input_variables=["question", "context"],
    template="""
You are an expert fact-checker and researcher. Your goal is to answer a specific question based on a provided context, which is retrieved from the full document.Language in Chinese.

**Context from Document:**
```
{context}
```

**Question to Answer:**
{question}

**Instructions:**
- Answer the question based *only* on the provided context. Language in Chinese.
- If the context does not contain the answer, only allow answering that the information is not available in the provided text.
- Be concise and to the point.
"""
)

# --- SummaryAgent Prompt ---
SUMMARY_AGENT_PROMPT = PromptTemplate(
    input_variables=["chapter_summary", "reviewed_answers"],
    template="""
You are a master summarizer. Your task is to synthesize a snippets's summary and the answers to related questions into a highly condensed "background memory" paragraph. This memory will be provided as context for reading the next snippets.Language in Chinese.

**Original Chapter Summary:**
```
{chapter_summary}
```

**Insights from Intra-Document Review (Answers to questions):**
```
{reviewed_answers}
```

**Your Task:**
Combine the key information from the summary and the review insights into a single paragraph,langguae in Chinese. This paragraph should encapsulate the most critical takeaways from the current chapter, forming a cohesive background for the next stage of reading.
"""
)
