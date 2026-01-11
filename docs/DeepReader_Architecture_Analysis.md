# DeepReader Architecture Analysis

## 1. Overview

DeepReader is an advanced, multi-agent document analysis system designed to perform "active reading" and deep synthesis of long-form texts. Unlike simple summarizers, it mimics a human researcher's workflow: reading iteratively, asking questions, cross-referencing disparate parts of a text, and synthesizing a cohesive report based on a specific user query.

The system is built on **LangGraph** and orchestrates a complex workflow of specialized agents.

## 2. Core Architecture

The system operates as a state machine defined in `backend/read_graph.py`, with a central state object (`DeepReaderState`) passing data between nodes.

### High-Level Workflow
1.  **Ingestion & Indexing (`RAGPersistenceNode`)**: Prepares the "Global Memory".
2.  **Iterative Reading Loop (`IterativeReadingLoop`)**: The "Active Reading" phase. Agents read sequentially but think globally.
3.  **Global Synthesis & Writing (`ReportGenerationNode`)**: The "Workshop" phase. Agents debate themes and write a structured report.

## 3. Detailed Workflow Analysis

### Phase 1: Ingestion (The Foundation)
*   **Input**: Source document (converted to Markdown).
*   **Action**:
    *   The document is chunked into small segments.
    *   A hybrid vector store (`DeepReaderVectorStore`) is created using FAISS (for semantic search) and SQLite (for metadata/text storage).
    *   **Purpose**: This creates the "Long-Term Memory" that allows agents to look up information from *anywhere* in the book at any time.

### Phase 2: Iterative Reading Loop (The Active Reader)
This is the core innovation. The system does not just summarize chunk-by-chunk; it builds a cumulative understanding.

*   **Process**: The document is split into logical snippets (e.g., chapters).
*   **Agent Team**:
    1.  **Reading Agent**:
        *   **Role**: Reads the current snippet.
        *   **Output**: Summaries of sub-chapters and *Critical Questions* that arise from the text.
        *   **Prompt Strategy**: Instructed to link current content with "Previous Chapters Context".
    2.  **Reviewer Agent (RAG Powered)**:
        *   **Role**: Fact-checker and researcher.
        *   **Action**: Takes the *Critical Questions* from the Reading Agent and queries the **Global Vector Store**.
        *   **Why?**: This allows the agent to answer a question about Chapter 1 using information that might appear in Chapter 10, creating a holistic understanding.
    3.  **Key Info Agent**:
        *   **Role**: Data Analyst.
        *   **Action**: Extracts specific, citable data points (numbers, quotes) relevant to the user's core question.
    4.  **Summary Agent**:
        *   **Role**: Synthesizer.
        *   **Action**: Updates the "Background Memory" by combining the new chunk summary + the RAG-retrieved answers. This "rolling memory" is passed to the next iteration.

### Phase 3: Report Generation (The Writing Workshop)
Once reading is complete, the system enters a "Writing Workshop" mode managed by `ReportGenerationNode`.

*   **Step 1: Narrative Analysis**:
    *   **Agent**: Narrative Analyst.
    *   **Task**: Reviews all chapter summaries to map the book's logical flow (not just linear order).
*   **Step 2: Thematic Extraction**:
    *   **Agent**: Thematic Thinker.
    *   **Task**: Distills the "Key Idea," "Key Conclusion," and "Key Evidence," strictly aligned with the user's core question.
*   **Step 3: The Debate (Critique & Refine)**:
    *   **Agents**: Critical Thinker vs. Thematic Thinker.
    *   **Action**: The Critic challenges the extracted themes ("Does this really answer the user's prompt?"). The Thinker refines them. This loops for `debate_rounds` (configurable).
*   **Step 4: Outline Generation**:
    *   **Agent**: Chief Editor.
    *   **Task**: Creates a hierarchical outline for the final report, ensuring every section serves the user's question.
*   **Step 5: Iterative Writing**:
    *   **Agent**: Writer.
    *   **Mechanism**:
        *   For *each* section of the outline, the system performs a **Dynamic Context Selection**:
            *   **Summaries**: Selects the top 5 relevant chapter summaries.
            *   **Key Info**: Selects relevant data points.
            *   **RAG**: Performs a fresh vector search for the specific section topic.
        *   **Writing**: Generates the section text using this targeted context.

## 4. Data Flow & State Management

The `DeepReaderState` (in `backend/read_state.py`) is the bus carrying:
*   `user_core_question`: The guiding star for all agents.
*   `chapter_summaries`: Dictionary of all chapter summaries.
*   `key_information`: List of extracted data points.
*   `active_memory`: The rolling background summary.
*   `db_name`: Reference to the vector store.
*   `raw_reviewer_outputs`: Log of all Q&A pairs generated during reading.

## 5. Key Prompts & Personas

The system relies on strong persona-based prompting (found in `backend/prompts.py`):

| Agent Role | Persona | Key Instruction |
| :--- | :--- | :--- |
| **Reading Agent** | Research Role (configurable) | "Pose critical questions that probe deeper... suggest connections." |
| **Reviewer Agent** | Fact-checker | "Answer strictly based on provided context... state if info is unavailable." |
| **Narrative Analyst** | Narrative Analyst | "Discern the underlying logical structure... moving beyond linear presentation." |
| **Critical Thinker** | Devil's Advocate | "Challenge the thematic analysis... ensure it answers the user's core question." |
| **Writer** | Senior Analyst | "Go beyond surface summary... connect ideas... proactively cite data." |

## 6. Summary of Innovation

DeepReader distinguishes itself by:
1.  **Breaking Linearity**: Through the Reviewer Agent/RAG, it allows early chapters to be understood in the context of later ones.
2.  **Self-Correction**: The Debate mechanism prevents hallucination and ensures focus on the user's specific query.
3.  **Dynamic Context**: The Writer doesn't just dump context; it intelligently selects the *right* summaries and data for each specific section.
