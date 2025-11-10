from typing import Dict
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter(prefix="/templates", tags=["templates"])

# In-memory template store
# Structure: { template_name: html_content_string }
# For production, consider using a database or file storage
template_store: Dict[str, str] = {}

# Pydantic model for creating/updating templates
class TemplateCreate(BaseModel):
    name: str
    html_content: str

# Initialize with a default template (cisco_interview_email)
template_store["cisco_interview_email"] = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interview Invitation</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f4f4f4; padding: 20px; border-radius: 5px;">
        <h2 style="color: #0066cc;">Interview Invitation</h2>
        
        <p>Dear {{ recipient }},</p>
        
        <p>Thank you for your interest in joining our team. We are pleased to invite you for an interview.</p>
        
        <p>Please review the attached document for more details about the interview process and schedule.</p>
        
        <p>If you have any questions, please don't hesitate to reach out.</p>
        
        <p>Best regards,<br>
        {{ sender_name }}</p>
        
        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
        
        <p style="font-size: 12px; color: #666;">
            This email was sent on {{ current_date }}<br>
            &copy; {{ current_year }} All rights reserved.
        </p>
    </div>
</body>
</html>
"""


@router.get("/{template_name}", response_class=Response)
async def get_template(template_name: str):
    """
    Retrieve an HTML template by name.
    Returns the raw HTML content with content-type: text/html.
    """
    if template_name not in template_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found"
        )
    
    html_content = template_store[template_name]
    return Response(content=html_content, media_type="text/html")


@router.get("/")
async def list_templates():
    """
    List all available template names.
    """
    return {
        "templates": list(template_store.keys()),
        "count": len(template_store)
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_template(template: TemplateCreate):
    """
    Create a new HTML template or update an existing one.
    """
    template_store[template.name] = template.html_content
    return {
        "message": f"Template '{template.name}' created successfully",
        "name": template.name
    }


@router.delete("/{template_name}")
async def delete_template(template_name: str):
    """
    Delete an HTML template by name.
    """
    if template_name not in template_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found"
        )
    
    del template_store[template_name]
    return {
        "message": f"Template '{template_name}' deleted successfully"
    }
