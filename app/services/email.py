from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
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
from jinja2 import Environment, FileSystemLoader, BaseLoader, select_autoescape
import httpx

from app.routers.csv import dataframe_store, redis_client, USE_REDIS

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
DEFAULT_EMAIL_SUBJECT = "Change the subject line"

DEFAULT_TEMPLATE_ENDPOINT = "http://localhost:3000/api/templates"
ENABLE_TEMPLATE_FETCH = os.getenv("ENABLE_FRONTEND_TEMPLATE_FETCH", "true").lower() in {"1", "true", "yes", "on"}

_frontend_endpoint_env = os.getenv("FRONTEND_TEMPLATES_ENDPOINT")
if _frontend_endpoint_env:
    FRONTEND_TEMPLATES_ENDPOINT = _frontend_endpoint_env.rstrip("/")
elif ENABLE_TEMPLATE_FETCH:
    _frontend_base_env = os.getenv("FRONTEND_BASE_URL")
    FRONTEND_TEMPLATES_ENDPOINT = f"{_frontend_base_env.rstrip('/')}/api/templates" if _frontend_base_env else DEFAULT_TEMPLATE_ENDPOINT
else:
    FRONTEND_TEMPLATES_ENDPOINT = None

FRONTEND_TEMPLATE_TIMEOUT = float(os.getenv("FRONTEND_TEMPLATE_TIMEOUT", "5.0"))

# Request models
class SingleEmailRequest(BaseModel):
    recipient: str
    recipient_email: str
    subject: Optional[str] = DEFAULT_EMAIL_SUBJECT
    cc_list: List[str] = Field(default_factory=list)
    recipient_data: Dict[str, Any] = Field(default_factory=dict)
    with_attachment: bool = True
    template_id: Optional[str] = None
    template_html: Optional[str] = None
    template_subject: Optional[str] = None

class BulkEmailRequest(BaseModel):
    upload_id: str  # Identifier of the uploaded dataset
    subject: Optional[str] = DEFAULT_EMAIL_SUBJECT
    cc_list: List[str] = Field(default_factory=list)
    with_attachments: bool = True
    skip_sent: bool = True  # Skip already sent emails
    template_id: Optional[str] = None
    template_html: Optional[str] = None
    template_subject: Optional[str] = None

TemplatePayload = Dict[str, Any]


def _fetch_template_from_frontend(template_id: str) -> Optional[TemplatePayload]:
    """Fetch a template payload from the frontend API."""
    if not FRONTEND_TEMPLATES_ENDPOINT:
        return None

    template_id = template_id.strip()
    if not template_id:
        return None

    url = f"{FRONTEND_TEMPLATES_ENDPOINT.rstrip('/')}/{template_id}"
    try:
        response = httpx.get(url, timeout=FRONTEND_TEMPLATE_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        template = data.get("template", data)

        if template and template.get("message"):
            return {
                "id": template.get("id") or template_id,
                "name": template.get("name"),
                "subject": template.get("subject"),
                "html": template.get("message"),
                "filename": template.get("filename"),
            }
    except httpx.HTTPStatusError as exc:
        # 404 should bubble up as not found; other status errors logged for visibility
        if exc.response.status_code == 404:
            return None
        print(f"[email] Frontend template endpoint returned {exc.response.status_code}: {exc.response.text}")
    except httpx.RequestError as exc:
        print(f"[email] Failed to reach frontend template endpoint: {exc}")
    except Exception as exc:
        print(f"[email] Unexpected error fetching template '{template_id}': {exc}")

    return None


def _resolve_template_payload(
    template_id: Optional[str],
    template_html: Optional[str],
    template_subject: Optional[str],
) -> Optional[TemplatePayload]:
    """Normalize template references into a consistent payload shape."""
    template_html = template_html.strip() if template_html and template_html.strip() else None
    template_subject = template_subject.strip() if template_subject and template_subject.strip() else None

    if template_html:
        return {
            "id": template_id.strip() if template_id else "inline-template",
            "name": None,
            "subject": template_subject,
            "html": template_html,
            "filename": None,
        }

    if template_id:
        payload = _fetch_template_from_frontend(template_id)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Template not found or unavailable: {template_id}")
        if template_subject:
            payload["subject"] = template_subject
        return payload

    return None


def _determine_subject(
    requested_subject: Optional[str],
    template_payload: Optional[TemplatePayload],
    template_subject_override: Optional[str],
) -> str:
    """Choose the final email subject following the configured precedence."""
    candidate = (requested_subject or "").strip() or DEFAULT_EMAIL_SUBJECT

    if template_payload and template_payload.get("subject"):
        if not requested_subject or requested_subject.strip() == DEFAULT_EMAIL_SUBJECT:
            candidate = template_payload["subject"]
            if candidate:
                return candidate

    if template_subject_override and (not requested_subject or requested_subject.strip() == DEFAULT_EMAIL_SUBJECT):
        return template_subject_override

    return candidate or DEFAULT_EMAIL_SUBJECT


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

def get_html_content(
    recipient_name: str = "",
    recipient_data: Optional[Dict[str, Any]] = None,
    template_html: Optional[str] = None,
):
    """Render the HTML email body from either an inline template or disk file."""
    template_vars: Dict[str, Any] = {
        "recipient": recipient_name,
        "sender_name": SENDER_NAME,
        "current_date": datetime.now().strftime("%Y-%m-%d"),
        "current_year": datetime.now().year,
    }
    if isinstance(recipient_data, dict):
        template_vars.update(recipient_data)

    env_kwargs = {"autoescape": select_autoescape(["html", "xml"])}

    try:
        if template_html and template_html.strip():
            env = Environment(loader=BaseLoader(), **env_kwargs)
            template = env.from_string(template_html)
        else:
            if not os.path.exists(HTML_TEMPLATE_FILE):
                return None
            template_dir = os.path.dirname(os.path.abspath(HTML_TEMPLATE_FILE)) or "."
            template_name = os.path.basename(HTML_TEMPLATE_FILE)
            env = Environment(loader=FileSystemLoader(template_dir), **env_kwargs)
            template = env.get_template(template_name)

        return template.render(template_vars)
    except Exception:
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

def send_single_email(
    recipient: str,
    recipient_email: str,
    subject: Optional[str],
    cc_list: Optional[List[str]],
    recipient_data: Optional[Dict[str, Any]],
    with_attachment: bool,
    template_payload: Optional[TemplatePayload] = None,
    template_subject_override: Optional[str] = None,
):
    """Build and send a single email using the provided template context."""
    if not all([SENDER_EMAIL, SENDER_PASSWORD]):
        raise HTTPException(status_code=500, detail="Email credentials not configured")

    cc_list = cc_list or []
    recipient_data = recipient_data or {}
    subject_to_use = _determine_subject(subject, template_payload, template_subject_override)

    msg = MIMEMultipart('mixed' if with_attachment else 'alternative')
    msg['Subject'] = subject_to_use
    msg['From'] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg['To'] = f"{recipient} <{recipient_email}>"
    if cc_list:
        msg['Cc'] = ', '.join(cc_list)

    html_source = template_payload["html"] if template_payload and template_payload.get("html") else None
    html_content = get_html_content(recipient, recipient_data, html_source)
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
    template_payload = _resolve_template_payload(
        request.template_id,
        request.template_html,
        request.template_subject,
    )
    result = send_single_email(
        request.recipient,
        request.recipient_email,
        request.subject,
        request.cc_list,
        request.recipient_data,
        request.with_attachment,
        template_payload,
        request.template_subject,
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
    
    template_payload = _resolve_template_payload(
        request.template_id,
        request.template_html,
        request.template_subject,
    )

    # Run in background
    background_tasks.add_task(
        process_bulk_emails,
        records,
        request.subject,
        request.cc_list,
        request.with_attachments,
        request.skip_sent,
        template_payload,
        request.template_subject,
    )
    
    return {
        "status": "started",
        "message": "Bulk email job started. Check /logs/ for progress.",
        "upload_id": request.upload_id,
        "row_count": len(records),
    }

def process_bulk_emails(
    records: List[Dict[str, Any]],
    subject: str,
    cc_list: Optional[List[str]],
    with_attachments: bool,
    skip_sent: bool,
    template_payload: Optional[TemplatePayload] = None,
    template_subject_override: Optional[str] = None,
):
    """Process bulk emails (runs in background)."""
    try:
        already_sent = get_sent_emails() if skip_sent else set()
        sent_count = 0
        skipped_count = 0
        cc_list = cc_list or []
        subject_to_use = _determine_subject(subject, template_payload, template_subject_override)

        for row in records:
            recipient_email = str(row.get('email', '') or '').strip()
            recipient = str(row.get('recipient', recipient_email) or '').strip()

            if not recipient_email:
                continue

            if skip_sent and recipient_email in already_sent:
                skipped_count += 1
                continue
            
            result = send_single_email(
                recipient,
                recipient_email,
                subject_to_use,
                cc_list,
                row,
                with_attachments,
                template_payload,
                template_subject_override,
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