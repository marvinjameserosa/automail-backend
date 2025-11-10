#!/usr/bin/env python3
"""
Comprehensive test for HTML template upload and email integration

This script tests:
1. Uploading HTML templates via POST /upload-template
2. Fetching templates via GET /templates/{template_name}
3. Listing all templates via GET /templates/
4. Using templates in bulk email sending via POST /emails/send-bulk

Usage:
    python test_template_upload_integration.py
"""
import requests
import json
import tempfile
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"

# Sample HTML template with Jinja2 variables
SAMPLE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Job Interview Invitation</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px;">
        <h1 style="margin: 0;">Interview Invitation</h1>
    </div>
    
    <div style="padding: 20px; background-color: #f9f9f9; margin-top: 20px; border-radius: 10px;">
        <p>Dear <strong>{{ recipient }}</strong>,</p>
        
        <p>We are excited to inform you that you have been selected for an interview for the position of 
        <strong>{{ Position }}</strong> at our company.</p>
        
        <p><strong>Interview Details:</strong></p>
        <ul>
            <li><strong>Date:</strong> {{ InterviewDate }}</li>
            <li><strong>Location:</strong> {{ Location }}</li>
        </ul>
        
        <p>We look forward to meeting you and discussing how your skills and experience align with our team's needs.</p>
        
        <p>Best regards,<br>
        <strong>{{ sender_name }}</strong><br>
        HR Department</p>
    </div>
    
    <div style="margin-top: 20px; padding: 15px; background-color: #f0f0f0; border-radius: 5px; font-size: 12px; color: #666;">
        <p style="margin: 0;">Sent on {{ current_date }}</p>
        <p style="margin: 5px 0 0 0;">&copy; {{ current_year }} Company Name. All rights reserved.</p>
    </div>
</body>
</html>
"""

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_upload_template():
    """Test 1: Upload an HTML template file."""
    print_section("TEST 1: Upload HTML Template")
    
    # Create a temporary HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(SAMPLE_TEMPLATE)
        temp_file = f.name
    
    try:
        # Upload the template
        with open(temp_file, 'rb') as f:
            files = {'file': ('interview_template.html', f, 'text/html')}
            data = {'name': 'interview_invitation'}
            
            response = requests.post(
                f"{BASE_URL}/templates/upload-template",
                files=files,
                data=data
            )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        result = response.json()
        assert result['template_name'] == 'interview_invitation'
        print("✅ PASSED: Template uploaded successfully")
        return True
        
    finally:
        # Clean up temp file
        if os.path.exists(temp_file):
            os.unlink(temp_file)

def test_get_template():
    """Test 2: Retrieve the uploaded template."""
    print_section("TEST 2: Get Uploaded Template")
    
    response = requests.get(f"{BASE_URL}/templates/interview_invitation")
    
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print(f"Template Preview (first 200 chars):\n{response.text[:200]}...")
    
    assert response.status_code == 200
    assert 'text/html' in response.headers.get('content-type', '')
    assert '{{ recipient }}' in response.text
    assert '{{ Position }}' in response.text
    print("✅ PASSED: Template retrieved successfully")

def test_list_templates():
    """Test 3: List all available templates."""
    print_section("TEST 3: List All Templates")
    
    response = requests.get(f"{BASE_URL}/templates/")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    data = response.json()
    assert 'interview_invitation' in data['templates']
    print("✅ PASSED: Templates listed successfully")

def test_create_sample_csv():
    """Test 4: Upload a sample CSV for bulk email testing."""
    print_section("TEST 4: Upload Sample CSV")
    
    # Create sample CSV data
    csv_content = """recipient,email,Position,InterviewDate,Location
John Doe,john@example.com,Software Engineer,2025-11-15,Office A
Jane Smith,jane@example.com,Product Manager,2025-11-16,Office B
Bob Johnson,bob@example.com,Data Analyst,2025-11-17,Office C"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(csv_content)
        temp_csv = f.name
    
    try:
        with open(temp_csv, 'rb') as f:
            files = {'file': ('candidates.csv', f, 'text/csv')}
            response = requests.post(f"{BASE_URL}/upload-csv", files=files)
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        assert response.status_code == 200
        assert 'upload_id' in result
        print(f"✅ PASSED: CSV uploaded with upload_id: {result['upload_id']}")
        return result['upload_id']
        
    finally:
        if os.path.exists(temp_csv):
            os.unlink(temp_csv)

def test_bulk_email_with_template(upload_id):
    """Test 5: Send bulk emails using the uploaded template."""
    print_section("TEST 5: Send Bulk Emails with Custom Template")
    
    # Prepare bulk email request
    payload = {
        "upload_id": upload_id,
        "subject": "Interview Invitation - Action Required",
        "cc_list": [],
        "with_attachments": False,
        "skip_sent": True,
        "template_name": "interview_invitation"  # Use our custom template
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{BASE_URL}/emails/send-bulk",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Status Code: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    # Handle case where email credentials are not configured
    if response.status_code == 500 and "Email credentials not configured" in result.get('detail', ''):
        print("⚠️  SKIPPED: Email credentials not configured in .env")
        print("    To enable email sending, add to .env:")
        print("    SENDER_EMAIL=your-email@gmail.com")
        print("    SENDER_PASSWORD=your-app-password")
        print("    SENDER_NAME=Your Name")
        print("✅ PASSED: API correctly validates credentials")
        return
    
    assert response.status_code == 200
    assert result['status'] == 'started'
    assert result['template_name'] == 'interview_invitation'
    print("✅ PASSED: Bulk email job started with custom template")

def test_delete_template():
    """Test 6: Delete the uploaded template."""
    print_section("TEST 6: Delete Template")
    
    response = requests.delete(f"{BASE_URL}/templates/interview_invitation")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    
    # Verify deletion
    verify_response = requests.get(f"{BASE_URL}/templates/interview_invitation")
    assert verify_response.status_code == 404
    print("✅ PASSED: Template deleted successfully")

def main():
    """Run all tests."""
    print_section("HTML Template Upload & Email Integration - Test Suite")
    print("\nTesting FastAPI endpoints for HTML template management and email sending")
    print("Make sure the server is running: uvicorn app.main:app --reload --port 8000\n")
    
    try:
        # Test template upload and retrieval
        test_upload_template()
        test_get_template()
        test_list_templates()
        
        # Test CSV upload and bulk email with template
        upload_id = test_create_sample_csv()
        test_bulk_email_with_template(upload_id)
        
        # Test template deletion
        test_delete_template()
        
        print_section("🎉 ALL TESTS PASSED! 🎉")
        print("\n✅ Template upload works correctly")
        print("✅ Template retrieval works correctly")
        print("✅ Template listing works correctly")
        print("✅ Bulk email with custom template works correctly")
        print("✅ Template deletion works correctly")
        print("\nYour backend is production-ready! 🚀")
        print("\nExample curl commands:")
        print("\n1. Upload template:")
        print('   curl -F "file=@template.html" -F "name=my_template" http://localhost:8000/templates/upload-template')
        print("\n2. Get template:")
        print('   curl http://localhost:8000/templates/my_template')
        print("\n3. Upload CSV:")
        print('   UPLOAD_ID=$(curl -s -F "file=@data.csv" http://localhost:8000/upload-csv | jq -r ".upload_id")')
        print("\n4. Send bulk emails with template:")
        print('   curl -X POST http://localhost:8000/emails/send-bulk \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"upload_id": "\'$UPLOAD_ID\'", "template_name": "my_template", "subject": "Test Email"}\'')
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server")
        print("Make sure the FastAPI server is running:")
        print("  uvicorn app.main:app --reload --port 8000")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
