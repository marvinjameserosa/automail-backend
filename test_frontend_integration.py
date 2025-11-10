#!/usr/bin/env python3
"""
Test fetching templates from frontend API
"""
import requests
import json

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

print("=" * 70)
print("  Testing Frontend Template Integration")
print("=" * 70)
print()

# Test 1: Check if backend can fetch from frontend
print("1. Testing backend's ability to fetch from frontend...")
print(f"   Frontend API URL: {FRONTEND_URL}/api/templates/test")
print()

# Test 2: Send email with fetch_from_frontend=True
payload = {
    "recipient": "Carl Melvin Erosa",
    "recipient_email": "carlmelvinerosa3@gmail.com",
    "subject": "Test - Frontend Template",
    "template_name": "cisco_interview_email",
    "fetch_from_frontend": True,  # Fetch from frontend
    "with_attachment": False,
    "recipient_data": {
        "Position": "Full Stack Developer",
        "Department": "Engineering"
    }
}

print("2. Sending test email with fetch_from_frontend=True")
print(f"   Payload: {json.dumps(payload, indent=2)}")
print()

try:
    response = requests.post(
        f"{BACKEND_URL}/emails/send",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"   Status Code: {response.status_code}")
    result = response.json()
    print(f"   Response: {json.dumps(result, indent=2)}")
    print()
    
    if response.status_code == 200:
        if result.get('status') == 'success':
            print("✅ SUCCESS! Email sent using frontend template")
        elif result.get('status') == 'failed':
            error = result.get('error', '')
            if 'Failed to fetch from frontend' in error or 'Connection' in error:
                print("⚠️  Note: Couldn't connect to frontend API")
                print("   The backend will fall back to local templates")
                print()
                print("   To enable frontend integration:")
                print("   1. Make sure your frontend is running on http://localhost:3000")
                print("   2. Implement: GET /api/templates/{template_name}")
                print("   3. Return JSON with 'html_content' field")
            else:
                print(f"❌ FAILED: {error}")
    
except requests.exceptions.ConnectionError:
    print("❌ ERROR: Could not connect to backend")
    print("   Make sure FastAPI is running: uvicorn app.main:app --reload")

print()
print("=" * 70)
print("  Documentation")
print("=" * 70)
print()
print("To use frontend templates, your frontend must provide:")
print()
print("Endpoint: GET /api/templates/{template_name}")
print("Response:")
print(json.dumps({
    "html_content": "<html>...template...</html>",
    "name": "template_name"
}, indent=2))
print()
print("Then from your frontend, call:")
print()
print("fetch('http://localhost:8000/emails/send-bulk', {")
print("  method: 'POST',")
print("  body: JSON.stringify({")
print("    upload_id: 'your-upload-id',")
print("    template_name: 'your-template-name',")
print("    fetch_from_frontend: true,  // ← KEY: Fetch from frontend")
print("    subject: 'Email Subject'")
print("  })")
print("})")
print()
print("See FRONTEND_INTEGRATION.md for complete guide!")
