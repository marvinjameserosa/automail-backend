#!/usr/bin/env python3
"""
Quick test to send an email to carlmelvinerosa3@gmail.com
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def send_test_email():
    """Send a single test email using the uploaded template."""
    
    print("=" * 70)
    print("  Sending Test Email to carlmelvinerosa3@gmail.com")
    print("=" * 70)
    print()
    
    # First, make sure the template exists
    print("1. Checking for available templates...")
    templates_response = requests.get(f"{BASE_URL}/templates/")
    templates = templates_response.json()
    print(f"Available templates: {templates['templates']}")
    
    # Use the interview_invitation template if it exists, otherwise use default
    template_name = None
    if 'interview_invitation' in templates['templates']:
        template_name = 'interview_invitation'
        print(f"✅ Using template: {template_name}")
    elif 'cisco_interview_email' in templates['templates']:
        template_name = 'cisco_interview_email'
        print(f"✅ Using template: {template_name}")
    else:
        print("⚠️  No template found, will use default template.html")
    
    print()
    print("2. Sending test email...")
    
    # Prepare the email request
    payload = {
        "recipient": "Carl Melvin Erosa",
        "recipient_email": "carlmelvinerosa3@gmail.com",
        "subject": "Test Email - HTML Template System",
        "cc_list": [],
        "recipient_data": {
            "Position": "Full Stack Developer",
            "Department": "Engineering",
            "InterviewDate": "2025-11-15",
            "InterviewTime": "10:00 AM",
            "Location": "Virtual Meeting - Zoom"
        },
        "with_attachment": False
    }
    
    # Add template_name if available
    if template_name:
        payload["template_name"] = template_name
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        response = requests.post(
            f"{BASE_URL}/emails/send",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        print()
        
        if response.status_code == 200 and result.get('status') == 'success':
            print("=" * 70)
            print("✅ SUCCESS! Email sent successfully!")
            print("=" * 70)
            print()
            print("Check your inbox at carlmelvinerosa3@gmail.com")
            print("Check email_log.csv for details")
            return True
        elif response.status_code == 500 and "Email credentials not configured" in result.get('detail', ''):
            print("=" * 70)
            print("❌ ERROR: Email credentials not configured")
            print("=" * 70)
            print()
            print("Please update your .env file with your Gmail App Password:")
            print()
            print("1. Go to https://myaccount.google.com/security")
            print("2. Enable 2-Step Verification (if not already enabled)")
            print("3. Click on 'App Passwords'")
            print("4. Generate a new app password for 'Mail'")
            print("5. Copy the 16-character password")
            print("6. Update .env file:")
            print()
            print("   SENDER_EMAIL=carlmelvinerosa3@gmail.com")
            print("   SENDER_PASSWORD=xxxx xxxx xxxx xxxx  (your app password)")
            print("   SENDER_NAME=Carl Melvin Erosa")
            print()
            return False
        else:
            print("=" * 70)
            print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
            print("=" * 70)
            return False
            
    except requests.exceptions.ConnectionError:
        print("=" * 70)
        print("❌ ERROR: Could not connect to server")
        print("=" * 70)
        print()
        print("Make sure the FastAPI server is running:")
        print("  uvicorn app.main:app --reload --port 8000")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = send_test_email()
    exit(0 if success else 1)
