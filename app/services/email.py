from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
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
from jinja2 import Environment, FileSystemLoader

load_dotenv()

router = APIRouter()

# Configuration
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
SENDER_NAME = os.getenv("SENDER_NAME", "Your Name")
LOG_FILE = "email_log.csv"
HTML_TEMPLATE_FILE = "template.html"
PDF_FOLDER = "split_pages"

# Request models
class SingleEmailRequest(BaseModel):
    recipient: str
    recipient_email: str
    subject: Optional[str] = "Change the subject line"
    cc_list: Optional[List[str]] = []
    recipient_data: Optional[Dict] = {}
    with_attachment: bool = True

class BulkEmailRequest(BaseModel):
    csv_file: str = "result.csv"  # Path to CSV file
    subject: Optional[str] = "Change the subject line"
    cc_list: Optional[List[str]] = []
    with_attachments: bool = True
    skip_sent: bool = True  # Skip already sent emails

# Helper functions (same as auto_email.py)
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
        return set()

def get_html_content(recipient_name="", recipient_data=None):
    """Renders the HTML email body from a Jinja2 template."""
    if not os.path.exists(HTML_TEMPLATE_FILE):
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
        pass
    return None

def attach_pdf(msg, pdf_path):
    """Attaches a PDF file to an email message."""
    if not os.path.exists(pdf_path):
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
        return False

def send_single_email(recipient, recipient_email, subject, cc_list, recipient_data, with_attachment):
    """Builds and sends a single email."""
    if not all([SENDER_EMAIL, SENDER_PASSWORD]):
        raise HTTPException(status_code=500, detail="Email credentials not configured")
    
    msg = MIMEMultipart('mixed' if with_attachment else 'alternative')
    msg['Subject'] = subject
    msg['From'] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg['To'] = f"{recipient} <{recipient_email}>"
    if cc_list:
        msg['Cc'] = ', '.join(cc_list)

    html_content = get_html_content(recipient, recipient_data)
    if not html_content:
        log_email(recipient, recipient_email, cc_list, "None", "Failed", "HTML content failed to render")
        return {"status": "failed", "error": "HTML content failed to render"}
    msg.attach(MIMEText(html_content, 'html'))

    attachment_info = "None"
    if with_attachment:
        recipient_pdf = find_pdf_for_recipient(recipient)
        if recipient_pdf and attach_pdf(msg, recipient_pdf):
            attachment_info = Path(recipient_pdf).name
        else:
            attachment_info = "Not found"

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, [recipient_email] + cc_list, msg.as_string())
        
        log_email(recipient, recipient_email, cc_list, attachment_info, "Success")
        return {"status": "success", "message": f"Email sent to {recipient}"}
    except Exception as e:
        log_email(recipient, recipient_email, cc_list, attachment_info, "Failed", str(e))
        return {"status": "failed", "error": str(e)}

# API Endpoints
@router.post("/send")
def send_email(request: SingleEmailRequest):
    """
    Send a single email.
    
    - **recipient**: Name of the recipient
    - **recipient_email**: Email address of the recipient
    - **subject**: Email subject (optional)
    - **cc_list**: List of CC email addresses (optional)
    - **recipient_data**: Additional data for template variables (optional)
    - **with_attachment**: Whether to attach PDF (default: True)
    """
    create_log_file()
    result = send_single_email(
        request.recipient,
        request.recipient_email,
        request.subject,
        request.cc_list,
        request.recipient_data,
        request.with_attachment
    )
    return result

@router.post("/send-bulk")
def send_bulk_emails(request: BulkEmailRequest, background_tasks: BackgroundTasks):
    """
    Send bulk emails from a CSV file.
    
    - **csv_file**: Path to CSV file (default: "result.csv")
    - **subject**: Email subject (optional)
    - **cc_list**: List of CC email addresses (optional)
    - **with_attachments**: Whether to attach PDFs (default: True)
    - **skip_sent**: Skip emails that were already sent successfully (default: True)
    
    Returns immediately with a job status. Emails are sent in the background.
    """
    if not all([SENDER_EMAIL, SENDER_PASSWORD]):
        raise HTTPException(status_code=500, detail="Email credentials not configured")
    
    if not os.path.exists(request.csv_file):
        raise HTTPException(status_code=404, detail=f"CSV file not found: {request.csv_file}")
    
    create_log_file()
    
    # Run in background
    background_tasks.add_task(
        process_bulk_emails,
        request.csv_file,
        request.subject,
        request.cc_list,
        request.with_attachments,
        request.skip_sent
    )
    
    return {
        "status": "started",
        "message": "Bulk email job started. Check /logs/ for progress."
    }

def process_bulk_emails(csv_file, subject, cc_list, with_attachments, skip_sent):
    """Process bulk emails (runs in background)."""
    try:
        email_df = pd.read_csv(csv_file)
        already_sent = get_sent_emails() if skip_sent else set()
        
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
            
            send_single_email(
                recipient,
                recipient_email,
                subject,
                cc_list,
                row.to_dict(),
                with_attachments
            )
            sent_count += 1
        
        return {
            "sent": sent_count,
            "skipped": skipped_count
        }
    except Exception as e:
        return {"error": str(e)}