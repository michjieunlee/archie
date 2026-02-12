"""
Shared Utility Functions

Common helper functions used across multiple modules.
"""

from typing import Any, List


def flatten_list(items: Any) -> List[str]:
    """
    Flatten a potentially nested list to a single-level list of strings.
    
    Handles various formats:
    - Nested lists: [["a", "b"]] → ["a", "b"]
    - Flat lists: ["a", "b"] → ["a", "b"]
    - Single string: "a" → ["a"]
    - None/empty: None → []

    Args:
        items: Any value that could be a list, nested list, or string

    Returns:
        Flat list of strings
    """
    if not items:
        return []
    
    if isinstance(items, str):
        return [items]
    
    if not isinstance(items, list):
        return [str(items)]
    
    # Flatten nested lists
    result = []
    for item in items:
        if isinstance(item, list):
            for subitem in item:
                if isinstance(subitem, str):
                    result.append(subitem)
                else:
                    result.append(str(subitem))
        elif isinstance(item, str):
            result.append(item)
        else:
            result.append(str(item))
    
    return result
