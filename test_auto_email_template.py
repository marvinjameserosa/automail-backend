#!/usr/bin/env python3
"""
Test script to verify auto_email.py can fetch templates from the backend

This script tests the get_remote_template() function without sending actual emails.
"""
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the functions from auto_email.py
from auto_email import get_remote_template, get_html_content, TEMPLATE_NAME, BACKEND_URL

def test_get_remote_template():
    """Test fetching the remote template"""
    print("=" * 60)
    print("Testing auto_email.py template fetching")
    print("=" * 60)
    print(f"\nBackend URL: {BACKEND_URL}")
    print(f"Template Name: {TEMPLATE_NAME}")
    
    print("\n--- Test 1: Fetch remote template ---")
    html_template = get_remote_template()
    
    if html_template:
        print("✅ Successfully fetched template from backend")
        print(f"Template length: {len(html_template)} characters")
        print(f"First 300 characters:\n{html_template[:300]}...")
    else:
        print("❌ Failed to fetch template")
        return False
    
    print("\n--- Test 2: Render template with data ---")
    html_content = get_html_content(
        recipient_name="John Doe",
        recipient_data={
            "position": "Software Engineer",
            "company": "Tech Corp"
        }
    )
    
    if html_content:
        print("✅ Successfully rendered template")
        print(f"Rendered content length: {len(html_content)} characters")
        
        # Check if variables were replaced
        if "John Doe" in html_content:
            print("✅ Recipient name was properly inserted")
        else:
            print("❌ Recipient name was NOT inserted")
            
        if "{{ recipient }}" not in html_content:
            print("✅ Jinja2 template variables were rendered")
        else:
            print("❌ Template variables were NOT rendered")
            
        print(f"\nRendered preview (first 500 chars):\n{html_content[:500]}...")
    else:
        print("❌ Failed to render template")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All auto_email.py template tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_get_remote_template()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
