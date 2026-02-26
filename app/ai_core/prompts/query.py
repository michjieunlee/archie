"""
Prompts for KB QnA (Question and Answer) functionality.

This module contains system prompts and helper functions for the KB query
generation feature, which answers user questions based on knowledge base content.
"""

from typing import List, Dict, Any


QNA_SYSTEM_PROMPT = """
You are a Knowledge Base Assistant. Answer questions ONLY using information from the provided documents.

CRITICAL RULES:
1. If the information IS in the documents: Answer with exact quotes and citations
2. If the information IS NOT in the documents: Say "I don't have information about this in the knowledge base" and STOP
3. NEVER provide suggestions, alternatives, or advice not found in the documents
4. NEVER say where the user "may want to look" or "should check" - this is not your job
5. Do not use your general knowledge - ONLY use the provided documents

YOUR ONLY TWO OUTPUTS:
- Found: "According to [Document Title], [exact answer from document]... Sources: [Document Title]"
- Not Found: "I don't have information about this in the knowledge base"

Do not add anything else.
"""


def create_qna_prompt(question: str, kb_documents: List[Dict[str, Any]], doc_scores: Dict[str, float] = None) -> str:
    """
    Create prompt for KB query based on user question and relevant documents.

    Args:
        question: User's question
        kb_documents: List of relevant KB documents with content
        doc_scores: Optional dictionary mapping document paths to relevance scores

    Returns:
        Formatted prompt for the LLM
    """
    prompt = f"""
Question: {question}

Available Documents:
"""

    for i, doc in enumerate(kb_documents):
        prompt += f"""
--- DOCUMENT {i+1}: {doc.get("title", f"Document {i+1}")} ---
Category: {doc.get("category", "unknown")}
Content:
{doc.get("content", "")}
---

"""

    prompt += """
Your Task:
1. Search through ALL documents above for information that answers the question
2. If found: Provide the answer with citation
3. If NOT found: Say "I don't have information about this in the knowledge base" and STOP
4. Do NOT provide any suggestions, advice, or information not in these documents

Answer:
"""

    return prompt