#!/usr/bin/env python3
"""
Test script for HTML Template API endpoints

This script demonstrates how to test the template API endpoints.
Run this after starting the FastAPI server.

Usage:
    python test_template_api.py
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_list_templates():
    """Test listing all available templates"""
    print("\n=== Testing: List all templates ===")
    response = requests.get(f"{BASE_URL}/templates/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_get_template(template_name="cisco_interview_email"):
    """Test fetching a specific template"""
    print(f"\n=== Testing: Get template '{template_name}' ===")
    response = requests.get(f"{BASE_URL}/templates/{template_name}")
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print(f"Response (first 500 chars):\n{response.text[:500]}...")
    return response.status_code == 200

def test_create_template():
    """Test creating a new template"""
    print("\n=== Testing: Create new template ===")
    new_template = {
        "name": "test_template",
        "html_content": """
        <!DOCTYPE html>
        <html>
        <head><title>Test Template</title></head>
        <body>
            <h1>Hello {{ recipient }}!</h1>
            <p>This is a test template from {{ sender_name }}</p>
        </body>
        </html>
        """
    }
    response = requests.post(f"{BASE_URL}/templates/", json=new_template)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 201

def test_delete_template(template_name="test_template"):
    """Test deleting a template"""
    print(f"\n=== Testing: Delete template '{template_name}' ===")
    response = requests.delete(f"{BASE_URL}/templates/{template_name}")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_get_nonexistent_template():
    """Test fetching a template that doesn't exist"""
    print("\n=== Testing: Get non-existent template ===")
    response = requests.get(f"{BASE_URL}/templates/nonexistent_template")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 404

def main():
    """Run all tests"""
    print("=" * 60)
    print("HTML Template API Tests")
    print("=" * 60)
    print(f"Testing against: {BASE_URL}")
    
    try:
        # Test 1: List templates
        assert test_list_templates(), "Failed: List templates"
        
        # Test 2: Get existing template
        assert test_get_template(), "Failed: Get template"
        
        # Test 3: Create new template
        assert test_create_template(), "Failed: Create template"
        
        # Test 4: List templates again (should include new one)
        assert test_list_templates(), "Failed: List templates after creation"
        
        # Test 5: Get the newly created template
        assert test_get_template("test_template"), "Failed: Get new template"
        
        # Test 6: Delete the test template
        assert test_delete_template(), "Failed: Delete template"
        
        # Test 7: Try to get non-existent template
        assert test_get_nonexistent_template(), "Failed: Get non-existent template"
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the server.")
        print("Make sure the FastAPI server is running at http://localhost:8000")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
