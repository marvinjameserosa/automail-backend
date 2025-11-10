from typing import Dict
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/templates", tags=["templates"])

# Directory for storing uploaded templates
TEMPLATES_DIR = Path("templates")
TEMPLATES_DIR.mkdir(exist_ok=True)

# In-memory template store (for backward compatibility)
# Structure: { template_name: html_content_string }
# Now also supports file-based storage
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


@router.post("/upload-template", status_code=status.HTTP_201_CREATED)
async def upload_template(
    file: UploadFile = File(..., description="HTML template file"),
    name: str = Form(..., description="Template name")
):
    """
    Upload an HTML template file.
    
    - **file**: HTML template file (multipart/form-data)
    - **name**: Template name (will be saved as <name>.html)
    
    Returns the template_name and file_path.
    """
    # Validate file type
    if file.content_type not in ["text/html", "application/octet-stream"]:
        if not file.filename.endswith('.html'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only HTML files are allowed"
            )
    
    # Sanitize template name (remove any path traversal attempts)
    safe_name = name.replace('/', '_').replace('\\', '_').replace('..', '_')
    template_filename = f"{safe_name}.html"
    template_path = TEMPLATES_DIR / template_filename
    
    try:
        # Read and save the file
        content = await file.read()
        html_content = content.decode('utf-8')
        
        # Save to file
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Also store in memory for fast access
        template_store[safe_name] = html_content
        
        return {
            "message": f"Template '{safe_name}' uploaded successfully",
            "template_name": safe_name,
            "file_path": str(template_path.absolute())
        }
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be valid UTF-8 encoded HTML"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save template: {str(e)}"
        )


def _load_template_from_file(template_name: str) -> str:
    """Helper function to load template from file system."""
    template_path = TEMPLATES_DIR / f"{template_name}.html"
    
    if not template_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found"
        )
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read template: {str(e)}"
        )


@router.get("/{template_name}", response_class=Response)
async def get_template(template_name: str):
    """
    Retrieve an HTML template by name.
    Returns the raw HTML content with content-type: text/html.
    
    Checks both file system and in-memory store.
    """
    # Try in-memory store first
    if template_name in template_store:
        html_content = template_store[template_name]
        return Response(content=html_content, media_type="text/html")
    
    # Try loading from file system
    template_path = TEMPLATES_DIR / f"{template_name}.html"
    if template_path.exists():
        html_content = _load_template_from_file(template_name)
        # Cache in memory for future requests
        template_store[template_name] = html_content
        return Response(content=html_content, media_type="text/html")
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Template '{template_name}' not found"
    )


@router.get("/")
async def list_templates():
    """
    List all available template names from both file system and memory.
    """
    # Get templates from file system
    file_templates = set()
    if TEMPLATES_DIR.exists():
        for file_path in TEMPLATES_DIR.glob("*.html"):
            file_templates.add(file_path.stem)
    
    # Combine with in-memory templates
    all_templates = file_templates.union(set(template_store.keys()))
    
    return {
        "templates": sorted(list(all_templates)),
        "count": len(all_templates)
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
    Removes from both file system and memory.
    """
    deleted = False
    
    # Remove from in-memory store
    if template_name in template_store:
        del template_store[template_name]
        deleted = True
    
    # Remove from file system
    template_path = TEMPLATES_DIR / f"{template_name}.html"
    if template_path.exists():
        try:
            template_path.unlink()
            deleted = True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete template file: {str(e)}"
            )
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found"
        )
    
    return {
        "message": f"Template '{template_name}' deleted successfully"
    }


# Utility function for other modules to get template content
def get_template_content(template_name: str) -> str:
    """
    Utility function to get template content (for use by email service).
    Returns the HTML content as a string.
    Raises HTTPException if template not found.
    """
    # Try in-memory store first
    if template_name in template_store:
        return template_store[template_name]
    
    # Try loading from file system
    template_path = TEMPLATES_DIR / f"{template_name}.html"
    if template_path.exists():
        html_content = _load_template_from_file(template_name)
        # Cache in memory
        template_store[template_name] = html_content
        return html_content
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Template '{template_name}' not found"
    )
