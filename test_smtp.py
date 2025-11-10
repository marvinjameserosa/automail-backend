#!/usr/bin/env python3
"""
Test SMTP connection to verify credentials
"""
import smtplib
from dotenv import load_dotenv
import os

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

print("=" * 70)
print("  SMTP Connection Test")
print("=" * 70)
print()
print(f"Email: {SENDER_EMAIL}")
print(f"Password: {'*' * len(SENDER_PASSWORD) if SENDER_PASSWORD else 'NOT SET'}")
print()

if not SENDER_EMAIL or not SENDER_PASSWORD:
    print("❌ ERROR: Email credentials not set in .env file")
    exit(1)

print("Testing SMTP connection to smtp.gmail.com:587...")
print()

try:
    # Connect to Gmail SMTP server
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.set_debuglevel(1)  # Show debug output
    
    print("\n1. Starting TLS...")
    server.starttls()
    
    print("\n2. Attempting login...")
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    
    print("\n3. Login successful!")
    server.quit()
    
    print()
    print("=" * 70)
    print("✅ SUCCESS! SMTP connection works!")
    print("=" * 70)
    print()
    print("Your email credentials are correctly configured.")
    print("You can now send emails using the system.")
    
except smtplib.SMTPAuthenticationError as e:
    print()
    print("=" * 70)
    print("❌ Authentication Failed")
    print("=" * 70)
    print()
    print(f"Error: {e}")
    print()
    print("Possible solutions:")
    print()
    print("1. Make sure you're using an App Password, not your regular Gmail password")
    print("   - Go to: https://myaccount.google.com/apppasswords")
    print("   - Generate a new 16-character app password")
    print("   - Remove all spaces from the password")
    print()
    print("2. Make sure 2-Step Verification is enabled:")
    print("   - Go to: https://myaccount.google.com/security")
    print("   - Enable 2-Step Verification")
    print()
    print("3. Try generating a new App Password and update .env file")
    
except Exception as e:
    print()
    print("=" * 70)
    print("❌ Connection Error")
    print("=" * 70)
    print()
    print(f"Error: {e}")
