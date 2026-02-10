"""
Mock API service for simulating GitHub repository processing.
This will be replaced with actual API calls in Phase 2.
"""
import time
import random
from utils.validators import extract_owner_repo_from_url


def process_github_repository(github_url: str, github_token: str) -> dict:
    """
    Mock processing of a GitHub repository.
    Simulates the AI pipeline processing.
    
    Args:
        github_url: GitHub repository URL (https://github.com/owner/repo)
        github_token: GitHub personal access token
    
    Returns:
        dict: Processing result with status, data, and metrics
    """
    try:
        # Extract owner and repo from URL
        owner, repo = extract_owner_repo_from_url(github_url)
        
        if not owner or not repo:
            return {
                "status": "error",
                "error": "Invalid GitHub URL format",
                "error_details": "Could not extract owner and repository name from URL."
            }
        
        # Simulate processing time
        time.sleep(2)
        
        # Generate mock data
        num_prs = random.randint(5, 20)
        num_articles = random.randint(3, 10)
        
        mock_articles = []
        categories = ["Bug Fix", "Feature", "Performance", "Documentation", "Refactoring"]
        
        for i in range(num_articles):
            mock_articles.append({
                "title": f"Knowledge Article {i+1}: {random.choice(['API Integration', 'Database Schema', 'UI Component', 'Authentication Flow', 'Data Processing'])}",
                "category": random.choice(categories),
                "content": f"This is a mock knowledge base article extracted from pull request analysis.\n\n**Context:** Analyzing {owner}/{repo}\n\n**Key Points:**\n- Implementation details\n- Best practices\n- Common issues and solutions",
                "source_prs": [f"PR#{random.randint(1, 100)}" for _ in range(random.randint(1, 3))]
            })
        
        # Return successful result
        return {
            "status": "completed",
            "repository": f"{owner}/{repo}",
            "prs_analyzed": num_prs,
            "kb_articles": mock_articles,
            "execution_time": random.uniform(8.5, 15.2),
            "timestamp": time.time()
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_details": "An unexpected error occurred during processing. Please check your inputs and try again."
        }
