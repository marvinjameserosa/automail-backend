from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Tuple
import smtplib
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
import os
import csv
import io
import json
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, BaseLoader
import requests

from app.routers.csv import dataframe_store, redis_client, USE_REDIS
from app.routers.html_template import get_template_content

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

# Frontend API URL - Configure this to point to your frontend API
FRONTEND_API_URL = os.getenv("FRONTEND_API_URL", "http://localhost:3000/api")

# Request models
class SingleEmailRequest(BaseModel):
    recipient: str
    recipient_email: str
    subject: Optional[str] = "Change the subject line"
    cc_list: Optional[List[str]] = []
    recipient_data: Optional[Dict] = {}
    with_attachment: bool = True
    template_name: Optional[str] = None  # Template name to fetch from frontend
    fetch_from_frontend: bool = False    # Flag to fetch from frontend instead of local storage
    html_content: Optional[str] = None   # Optional: HTML content provided directly by the frontend

class BulkEmailRequest(BaseModel):
    upload_id: str  # Identifier of the uploaded dataset
    subject: Optional[str] = "Change the subject line"
    cc_list: Optional[List[str]] = []
    with_attachments: bool = True
    skip_sent: bool = True  # Skip already sent emails
    template_name: Optional[str] = None  # Template name
    fetch_from_frontend: bool = False    # Flag to fetch template from frontend API


async def _fetch_dataframe(upload_id: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """Retrieve a stored DataFrame by upload_id from Redis or the in-memory store."""
    df: Optional[pd.DataFrame] = None
    filename: Optional[str] = None

    if USE_REDIS and redis_client is not None:
        try:
            csv_bytes = await redis_client.get(f"upload:{upload_id}:csv")
            if csv_bytes:
                csv_text = csv_bytes.decode() if isinstance(csv_bytes, (bytes, bytearray)) else str(csv_bytes)
                df = pd.read_csv(io.StringIO(csv_text))

                meta_raw = await redis_client.get(f"upload:{upload_id}:meta")
                if meta_raw:
                    meta_text = meta_raw.decode() if isinstance(meta_raw, (bytes, bytearray)) else str(meta_raw)
                    try:
                        meta = json.loads(meta_text)
                        filename = meta.get("filename")
                    except Exception:
                        filename = None
        except Exception:
            df = None

    if df is None:
        stored = dataframe_store.get(upload_id)
        if not stored:
            raise HTTPException(status_code=404, detail=f"upload_id not found: {upload_id}")
        df = stored["df"]
        filename = filename or stored.get("filename")

    return df, filename


def _dataframe_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert a pandas DataFrame to a list of JSON-safe dictionaries."""
    try:
        safe_df = df.where(pd.notnull(df), None)

        def _to_py(x: Any) -> Any:
            try:
                if hasattr(x, "item"):
                    return x.item()
            except Exception:
                pass
            return x

        return safe_df.astype(object).where(pd.notnull(safe_df), None).applymap(_to_py).to_dict(orient="records")
    except Exception:
        return df.to_dict(orient="records")


async def _load_records(upload_id: str) -> List[Dict[str, Any]]:
    """Load serialized row records for the given upload id."""
    df, _ = await _fetch_dataframe(upload_id)
    return _dataframe_to_records(df)

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

def get_html_content(recipient_name="", recipient_data=None, template_name=None, fetch_from_frontend=False, html_override: Optional[str] = None):
    """
    Renders the HTML email body from a Jinja2 template.

    Priority:
      1) If html_override is provided, use it (render with Jinja)
      2) If fetch_from_frontend=True and template_name provided: fetch from frontend API
      3) Else try local backend template store
      4) Else fallback to HTML_TEMPLATE_FILE
    """
    html_template = None

    # Highest priority: use HTML directly provided by the requester
    if html_override:
        html_template = html_override
        print(f"🔍 Using html_override provided in request (length={len(html_override)} chars)")
    else:
        # Option 1: Fetch template from frontend API
        if fetch_from_frontend and template_name:
            try:
                # Fetch template from frontend API using query parameter
                frontend_url = f"{FRONTEND_API_URL}/templates?name={template_name}"
                print(f"🔍 Fetching template from frontend: {frontend_url}")

                response = requests.get(frontend_url, timeout=10)
                print(f"📡 Frontend response status: {response.status_code}")

                if response.status_code == 200:
                    # Try to get HTML content from response
                    # Support both direct HTML response or JSON with html_content field
                    content_type = response.headers.get('content-type', '')
                    print(f"📋 Content-Type: {content_type}")

                    if 'application/json' in content_type:
                        data = response.json()
                        print(f"🔑 Response keys: {list(data.keys())}")
                        html_template = data.get('html_content') or data.get('content') or data.get('template')

                        if html_template:
                            print(f"✅ Successfully fetched template from frontend ({len(html_template)} chars)")
                        else:
                            print(f"❌ No html_content in response! Data: {data}")
                    else:
                        html_template = response.text
                        print(f"✅ Successfully fetched template as text ({len(html_template)} chars)")
                else:
                    print(f"⚠️ Frontend returned status {response.status_code}, falling back to local")
                    print(f"   Response: {response.text[:200]}")
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Failed to fetch from frontend: {e}, falling back to local")

        # Option 2: Fetch from local backend template store
        if not html_template and template_name:
            try:
                html_template = get_template_content(template_name)
            except HTTPException as e:
                # Template not found in local store
                pass

        # Option 3: Use default template file
        if not html_template:
            if not os.path.exists(HTML_TEMPLATE_FILE):
                return None
            try:
                with open(HTML_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                    html_template = f.read()
            except Exception as e:
                return None

    if not html_template:
        print(f"❌ No template found after all attempts")
        return None

    print(f"✅ Template loaded successfully, length: {len(html_template)} chars")

    try:
        # Use BaseLoader to render template from string
        env = Environment(loader=BaseLoader())
        template = env.from_string(html_template)

        template_vars = {
            'recipient': recipient_name,
            'sender_name': SENDER_NAME,
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'current_year': datetime.now().year
        }
        if recipient_data:
            template_vars.update(recipient_data)

        rendered = template.render(template_vars)
        print(f"✅ Template rendered successfully, length: {len(rendered)} chars")
        return rendered
    except Exception as e:
        print(f"❌ Template rendering error: {e}")
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

def send_single_email(recipient, recipient_email, subject, cc_list, recipient_data, with_attachment, template_name=None, fetch_from_frontend=False, html_override: Optional[str] = None):
    """Builds and sends a single email."""
    if not all([SENDER_EMAIL, SENDER_PASSWORD]):
        raise HTTPException(status_code=500, detail="Email credentials not configured")

    msg = MIMEMultipart('mixed' if with_attachment else 'alternative')
    msg['Subject'] = subject
    msg['From'] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg['To'] = f"{recipient} <{recipient_email}>"
    if cc_list:
        msg['Cc'] = ', '.join(cc_list)

    # Get HTML content, preferring html_override when present
    html_body = get_html_content(recipient, recipient_data, template_name, fetch_from_frontend, html_override=html_override)
    if not html_body:
        error_msg = f"HTML template '{template_name}' not found" if template_name else "HTML content failed to render"
        log_email(recipient, recipient_email, cc_list or [], "None", "Failed", error_msg)
        return {"status": "failed", "error": error_msg}
    msg.attach(MIMEText(html_body, 'html'))

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
            server.sendmail(SENDER_EMAIL, [recipient_email] + (cc_list or []), msg.as_string())

        log_email(recipient, recipient_email, cc_list or [], attachment_info, "Success")
        return {"status": "success", "message": f"Email sent to {recipient}"}
    except Exception as e:
        log_email(recipient, recipient_email, cc_list or [], attachment_info, "Failed", str(e))
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
    - **template_name**: Name of HTML template to use (optional)
    - **fetch_from_frontend**: If True, fetches template from frontend API (default: False)
    - **html_content**: If provided, this HTML will be used (highest priority)
    """
    create_log_file()
    result = send_single_email(
        request.recipient,
        request.recipient_email,
        request.subject,
        request.cc_list or [],
        request.recipient_data or {},
        request.with_attachment,
        request.template_name,
        request.fetch_from_frontend,
        request.html_content
    )
    return result

@router.post("/send-bulk")
async def send_bulk_emails(request: BulkEmailRequest, background_tasks: BackgroundTasks):
    """
    Send bulk emails using a previously uploaded dataset.

    - **upload_id**: Identifier returned by the CSV/JSON upload endpoints
    - **subject**: Email subject (optional)
    - **cc_list**: List of CC email addresses (optional)
    - **with_attachments**: Whether to attach PDFs (default: True)
    - **skip_sent**: Skip emails that were already sent successfully (default: True)
    - **template_name**: Name of HTML template to use (optional)
    - **fetch_from_frontend**: If True, fetches template from frontend API (default: False)

    Returns immediately with a job status. Emails are sent in the background.
    """
    if not all([SENDER_EMAIL, SENDER_PASSWORD]):
        raise HTTPException(status_code=500, detail="Email credentials not configured")

    create_log_file()

    try:
        records = await _load_records(request.upload_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {exc}")

    if not records:
        raise HTTPException(status_code=400, detail=f"No rows found for upload_id: {request.upload_id}")

    # Run in background
    background_tasks.add_task(
        process_bulk_emails,
        records,
        request.subject,
        request.cc_list,
        request.with_attachments,
        request.skip_sent,
        request.template_name,
        request.fetch_from_frontend
    )

    template_source = "frontend" if request.fetch_from_frontend else "backend"

    return {
        "status": "started",
        "message": "Bulk email job started. Check /logs/ for progress.",
        "upload_id": request.upload_id,
        "row_count": len(records),
        "template_name": request.template_name or "default",
        "template_source": template_source
    }

def process_bulk_emails(
    records: List[Dict[str, Any]],
    subject: str,
    cc_list: Optional[List[str]],
    with_attachments: bool,
    skip_sent: bool,
    template_name: Optional[str] = None,
    fetch_from_frontend: bool = False
):
    """Process bulk emails (runs in background)."""
    try:
        already_sent = get_sent_emails() if skip_sent else set()
        sent_count = 0
        skipped_count = 0

        for row in records:
            recipient_email = str(row.get('email', '') or '').strip()
            recipient = str(row.get('recipient', recipient_email) or '').strip()

            if not recipient_email:
                continue

            if skip_sent and recipient_email in already_sent:
                skipped_count += 1
                continue

            # For bulk, there is no html_override by default (per-row override could be added if needed)
            result = send_single_email(
                recipient,
                recipient_email,
                subject,
                cc_list or [],
                row,
                with_attachments,
                template_name,
                fetch_from_frontend,
                None
            )
            if result.get("status") == "success":
                sent_count += 1
                if skip_sent:
                    already_sent.add(recipient_email)

        return {
            "sent": sent_count,
            "skipped": skipped_count
        }
    except Exception as e:
        return {"error": str(e)}