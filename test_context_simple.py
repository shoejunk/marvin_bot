#!/usr/bin/env python3
"""
test_context_simple.py - Simple test for context store functionality.
"""

import json
from context_store import update_home_assistant_query_result, get_context_for_llm, clear_context

def main():
    """Main function."""
    print("Testing context store functionality...")
    
    # Clear the context first
    clear_context()
    print("Context cleared.")
    
    # Create a sample result
    result = {
        "success": True,
        "message": "This is a test message"
    }
    
    # Store the result in context
    update_home_assistant_query_result("test_action", result)
    print("Result stored in context.")
    
    # Get the context for LLM
    context = get_context_for_llm()
    
    # Print the context
    print("\nContext for LLM:")
    print(context)
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()
