#!/usr/bin/env python3
"""
Automated Email Sender

Sends personalized bulk emails from a CSV file. Can run with or without PDF attachments.

Requirements:
    pip install pandas python-dotenv jinja2

Usage:
    python auto_email.py

Setup:
    - Configure settings and file paths below.
    - Create a .env file for credentials (SENDER_EMAIL, SENDER_PASSWORD, SENDER_NAME).
"""
import smtplib
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
import os
import csv
from datetime import datetime
from pathlib import Path
import logging
from jinja2 import Environment, FileSystemLoader

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

# --- SMTP Configuration ---
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
SENDER_NAME = os.getenv("SENDER_NAME", "Your Name")

# --- Email Content & Mode ---
SUBJECT = "Change the subject line"
CC_EMAIL_LIST = []

# Set to True to attach PDFs, False to send without.
SEND_WITH_ATTACHMENTS = True

# --- File Paths ---
EMAIL_CSV = "result.csv"
LOG_FILE = "email_log.csv"
HTML_TEMPLATE_FILE = "template.html"
PDF_FOLDER = "split_pages"

def create_log_file():
    """Creates the log CSV file with headers if it doesn't exist."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "recipient", "email", "cc", "attachment", "status", "error_message"])

def log_email(recipient, email, cc_list, attachment, status, error_message=""):
    """Logs the result of a sent email to the CSV file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, recipient, email, ", ".join(cc_list), attachment, status, error_message])

def get_sent_emails():
    """Reads the log file to get a set of successfully sent email addresses."""
    if not os.path.exists(LOG_FILE):
        return set()
    try:
        log_df = pd.read_csv(LOG_FILE)
        if "status" in log_df.columns:
            successful_emails = log_df[log_df["status"] == "Success"]["email"].tolist()
            return set(successful_emails)
        return set()
    except (pd.errors.EmptyDataError, FileNotFoundError):
        return set()
    except Exception as e:
        logging.error(f"Error reading log file: {e}")
        return set()

def get_html_content(recipient_name="", recipient_data=None):
    """Renders the HTML email body from a Jinja2 template."""
    if not os.path.exists(HTML_TEMPLATE_FILE):
        logging.error(f"HTML template file '{HTML_TEMPLATE_FILE}' not found.")
        return None
    try:
        template_dir = os.path.dirname(os.path.abspath(HTML_TEMPLATE_FILE)) or '.'
        template_name = os.path.basename(HTML_TEMPLATE_FILE)
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(template_name)
        
        template_vars = {
            'recipient': recipient_name,
            'sender_name': SENDER_NAME,
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'current_year': datetime.now().year
        }
        if recipient_data:
            template_vars.update(recipient_data)
        
        return template.render(template_vars)
    except Exception as e:
        logging.error(f"Error rendering Jinja2 template: {e}")
        return None

def find_pdf_for_recipient(recipient_name):
    """Finds a recipient's PDF by matching their name to a filename."""
    if not os.path.exists(PDF_FOLDER):
        return None
    try:
        for filename in os.listdir(PDF_FOLDER):
            if filename.lower().endswith('.pdf'):
                pdf_name = Path(filename).stem
                if recipient_name.lower() == pdf_name.lower():
                    return os.path.join(PDF_FOLDER, filename)
    except Exception as e:
        logging.error(f"Error searching for PDF in '{PDF_FOLDER}': {e}")
    return None

def attach_pdf(msg, pdf_path):
    """Attaches a PDF file to an email message."""
    if not os.path.exists(pdf_path):
        logging.warning(f"PDF not found: {pdf_path}")
        return False
    try:
        with open(pdf_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{Path(pdf_path).name}"')
        msg.attach(part)
        return True
    except Exception as e:
        logging.error(f"Error attaching PDF {pdf_path}: {e}")
        return False

def send_email(recipient, recipient_email, recipient_data=None):
    """Builds and sends a single email."""
    msg = MIMEMultipart('mixed' if SEND_WITH_ATTACHMENTS else 'alternative')
    msg['Subject'] = SUBJECT
    msg['From'] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg['To'] = f"{recipient} <{recipient_email}>"
    if CC_EMAIL_LIST:
        msg['Cc'] = ', '.join(CC_EMAIL_LIST)

    html_content = get_html_content(recipient, recipient_data)
    if not html_content:
        log_email(recipient, recipient_email, CC_EMAIL_LIST, "None", "Failed", "HTML content failed to render")
        return
    msg.attach(MIMEText(html_content, 'html'))

    attachment_info = "None"
    if SEND_WITH_ATTACHMENTS:
        recipient_pdf = find_pdf_for_recipient(recipient)
        if recipient_pdf and attach_pdf(msg, recipient_pdf):
            attachment_info = Path(recipient_pdf).name
        else:
            logging.warning(f"PDF not found or failed to attach for {recipient}")

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, [recipient_email] + CC_EMAIL_LIST, msg.as_string())
        
        logging.info(f"Email sent to {recipient} <{recipient_email}>")
        log_email(recipient, recipient_email, CC_EMAIL_LIST, attachment_info, "Success")
    except Exception as e:
        logging.error(f"Failed to send email to {recipient}: {e}")
        log_email(recipient, recipient_email, CC_EMAIL_LIST, attachment_info, "Failed", str(e))

def main():
    """Loads recipients, checks for duplicates, and sends emails."""
    mode = "attachments" if SEND_WITH_ATTACHMENTS else "no attachments"
    logging.info(f"Starting email script (mode: {mode}).")

    if not all([SENDER_EMAIL, SENDER_PASSWORD]):
        logging.error("Email credentials not set in .env file.")
        return
    
    create_log_file()
    
    if not os.path.exists(EMAIL_CSV):
        logging.error(f"Email CSV file not found: {EMAIL_CSV}")
        return
    
    try:
        email_df = pd.read_csv(EMAIL_CSV)
    except Exception as e:
        logging.error(f"Error reading CSV file: {e}")
        return
    
    already_sent = get_sent_emails()
    if already_sent:
        logging.info(f"{len(already_sent)} emails found in log. Skipping.")
    
    sent_count = 0
    skipped_count = 0
    
    for index, row in email_df.iterrows():
        recipient_email = str(row.get('email', '')).strip()
        recipient = str(row.get('recipient', recipient_email)).strip()

        if not recipient_email:
            continue

        if recipient_email in already_sent:
            skipped_count += 1
            continue
        
        send_email(recipient, recipient_email, row.to_dict())
        sent_count += 1
    
    logging.info("Email process completed.")
    logging.info(f"Sent: {sent_count}, Skipped: {skipped_count}")
    logging.info(f"See '{LOG_FILE}' for details.")

if __name__ == "__main__":
    main()