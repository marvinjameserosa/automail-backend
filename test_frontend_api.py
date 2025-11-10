#!/usr/bin/env python3
"""
Test if frontend API endpoint is accessible from backend
"""
import requests

FRONTEND_URL = "http://localhost:3000"

print("=" * 70)
print("  Testing Frontend Template API Endpoint")
print("=" * 70)
print()

# Test 1: Check if frontend is running
print("1. Testing if frontend is accessible...")
try:
    response = requests.get(f"{FRONTEND_URL}", timeout=3)
    print(f"   ✅ Frontend is running (Status: {response.status_code})")
except requests.exceptions.RequestException as e:
    print(f"   ❌ Frontend is not accessible: {e}")
    print()
    print("   Please start your Next.js frontend:")
    print("   > npm run dev")
    print()
    exit(1)

print()

# Test 2: Check if template API endpoint exists
print("2. Testing template API endpoint...")
template_name = "cisco_interview_email"  # Change this to match your template name
api_url = f"{FRONTEND_URL}/api/templates?name={template_name}"

try:
    response = requests.get(api_url, timeout=3)
    print(f"   URL: {api_url}")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ SUCCESS! Template endpoint is working")
        print()
        print("   Response:")
        print(f"   - Name: {data.get('name', 'N/A')}")
        print(f"   - Subject: {data.get('subject', 'N/A')}")
        print(f"   - Has HTML Content: {'Yes' if data.get('html_content') else 'No'}")
        print(f"   - Content Length: {len(data.get('html_content', ''))} characters")
        print()
        print("=" * 70)
        print("  🎉 Frontend API is ready! You can now send emails.")
        print("=" * 70)
    elif response.status_code == 404:
        print(f"   ❌ FAILED: Template API endpoint not found")
        print()
        print("   You need to create: app/api/templates/[name]/route.ts")
        print("   See FRONTEND_API_ROUTE.md for instructions")
    else:
        print(f"   ⚠️  Unexpected response: {response.status_code}")
        print(f"   Response: {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"   ❌ FAILED: {e}")
    print()
    print("   Common issues:")
    print("   1. Frontend API route doesn't exist yet")
    print("   2. Create: app/api/templates/[name]/route.ts")
    print("   3. See FRONTEND_API_ROUTE.md for complete instructions")

print()
