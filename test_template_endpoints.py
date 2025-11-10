#!/usr/bin/env python3
"""
Test script for HTML template endpoints
Tests all CRUD operations and the auto_email integration
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_list_templates():
    """Test: List all templates"""
    print("\n1. Testing GET /templates/ (List all templates)")
    print("-" * 60)
    response = requests.get(f"{BASE_URL}/templates/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    assert "cisco_interview_email" in data["templates"]
    print("✅ PASSED")

def test_get_template():
    """Test: Get a specific template"""
    print("\n2. Testing GET /templates/cisco_interview_email")
    print("-" * 60)
    response = requests.get(f"{BASE_URL}/templates/cisco_interview_email")
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print(f"Response Preview (first 200 chars):\n{response.text[:200]}...")
    assert response.status_code == 200
    assert "text/html" in response.headers.get('content-type', '')
    assert "{{ recipient }}" in response.text
    assert "{{ sender_name }}" in response.text
    print("✅ PASSED")

def test_get_nonexistent_template():
    """Test: Get a template that doesn't exist"""
    print("\n3. Testing GET /templates/nonexistent (should fail)")
    print("-" * 60)
    response = requests.get(f"{BASE_URL}/templates/nonexistent")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 404
    print("✅ PASSED")

def test_create_template():
    """Test: Create a new template"""
    print("\n4. Testing POST /templates/ (Create new template)")
    print("-" * 60)
    new_template = {
        "name": "test_template",
        "html_content": "<html><body><h1>Hello {{ recipient }}</h1></body></html>"
    }
    response = requests.post(f"{BASE_URL}/templates/", json=new_template)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 201
    
    # Verify it was created
    verify_response = requests.get(f"{BASE_URL}/templates/test_template")
    assert verify_response.status_code == 200
    assert "Hello {{ recipient }}" in verify_response.text
    print("✅ PASSED")

def test_update_template():
    """Test: Update an existing template"""
    print("\n5. Testing POST /templates/ (Update existing template)")
    print("-" * 60)
    updated_template = {
        "name": "test_template",
        "html_content": "<html><body><h1>Updated: Hello {{ recipient }}</h1></body></html>"
    }
    response = requests.post(f"{BASE_URL}/templates/", json=updated_template)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 201
    
    # Verify it was updated
    verify_response = requests.get(f"{BASE_URL}/templates/test_template")
    assert verify_response.status_code == 200
    assert "Updated: Hello {{ recipient }}" in verify_response.text
    print("✅ PASSED")

def test_delete_template():
    """Test: Delete a template"""
    print("\n6. Testing DELETE /templates/test_template")
    print("-" * 60)
    response = requests.delete(f"{BASE_URL}/templates/test_template")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    
    # Verify it was deleted
    verify_response = requests.get(f"{BASE_URL}/templates/test_template")
    assert verify_response.status_code == 404
    print("✅ PASSED")

def test_auto_email_integration():
    """Test: Simulate what auto_email.py does"""
    print("\n7. Testing auto_email.py integration (get_remote_template)")
    print("-" * 60)
    
    # Simulate the get_remote_template() function
    template_name = "cisco_interview_email"
    url = f"{BASE_URL}/templates/{template_name}"
    
    print(f"Fetching template from: {url}")
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        html_content = response.text
        print(f"✅ Successfully fetched template")
        print(f"Template length: {len(html_content)} characters")
        print(f"Contains Jinja2 variables: {all(var in html_content for var in ['{{ recipient }}', '{{ sender_name }}'])}")
        
        # Test rendering with Jinja2
        from jinja2 import Environment, BaseLoader
        env = Environment(loader=BaseLoader())
        template = env.from_string(html_content)
        rendered = template.render(
            recipient="John Doe",
            sender_name="Jane Smith",
            current_date="2025-11-10",
            current_year=2025
        )
        print(f"✅ Template rendered successfully")
        print(f"Rendered preview (first 200 chars):\n{rendered[:200]}...")
        assert "John Doe" in rendered
        assert "Jane Smith" in rendered
        print("✅ PASSED")
    else:
        print(f"❌ FAILED: Could not fetch template")
        raise AssertionError(f"Expected status 200, got {response.status_code}")

def main():
    print("=" * 60)
    print("HTML Template API - Comprehensive Test Suite")
    print("=" * 60)
    
    try:
        # Test basic CRUD operations
        test_list_templates()
        test_get_template()
        test_get_nonexistent_template()
        test_create_template()
        test_update_template()
        test_delete_template()
        
        # Test integration with auto_email.py
        test_auto_email_integration()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("=" * 60)
        print("\nYour template API is working correctly!")
        print("The auto_email.py script should be able to fetch templates successfully.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server")
        print("Make sure the FastAPI server is running on http://localhost:8000")
        print("Run: uvicorn app.main:app --reload")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
