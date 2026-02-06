"""
Results section component for the Streamlit app.
Displays processing results in chat-style format.
"""
import streamlit as st


def render_results_section(processing_result):
    """
    Add processing results to the chat interface.
    
    Args:
        processing_result: Result from the processing pipeline
    """
    if not processing_result:
        return
    
    status = processing_result.get("status", "unknown")
    
    if status == "completed":
        # Extract results
        kb_articles = processing_result.get("kb_articles", [])
        prs_analyzed = processing_result.get("prs_analyzed", 0)
        execution_time = processing_result.get("execution_time", 0)
        
        # Create result message
        result_content = f"""### 📊 Processing Results

**Summary:**
- ✅ Successfully processed **{prs_analyzed}** pull requests
- 📝 Generated **{len(kb_articles)}** knowledge base articles
- ⏱️ Execution time: **{execution_time:.2f}s**
"""
        
        # Add KB articles if available
        if kb_articles:
            result_content += "\n\n**Generated Knowledge Base Articles:**\n\n"
            for i, article in enumerate(kb_articles, 1):
                title = article.get("title", "Untitled")
                category = article.get("category", "General")
                result_content += f"{i}. **{title}** (Category: {category})\n"
        
        # Add the result message to chat
        st.session_state.messages.append({
            "role": "assistant",
            "content": result_content
        })
        
        # Display download button for KB articles
        if kb_articles:
            with st.chat_message("assistant"):
                st.download_button(
                    label="📥 Download Knowledge Base Articles",
                    data=format_kb_articles_for_download(kb_articles),
                    file_name="kb_articles.md",
                    mime="text/markdown"
                )
    
    elif status == "error":
        # Error already handled in status section, but we can add more details
        error_details = processing_result.get("error_details", "")
        if error_details:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"### ❌ Error Details\n\n{error_details}\n\nPlease check your inputs and try again."
            })


def format_kb_articles_for_download(kb_articles):
    """
    Format KB articles as markdown for download.
    
    Args:
        kb_articles: List of KB article dictionaries
    
    Returns:
        str: Formatted markdown content
    """
    content = "# Knowledge Base Articles\n\n"
    content += f"Generated: {st.session_state.get('github_url', 'Unknown repository')}\n\n"
    content += "---\n\n"
    
    for i, article in enumerate(kb_articles, 1):
        content += f"## Article {i}: {article.get('title', 'Untitled')}\n\n"
        content += f"**Category:** {article.get('category', 'General')}\n\n"
        content += f"**Content:**\n\n{article.get('content', 'No content available')}\n\n"
        content += "---\n\n"
    
    return content