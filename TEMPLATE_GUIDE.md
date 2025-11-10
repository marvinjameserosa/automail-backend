# HTML Template Upload and Email Integration

This backend supports HTML template management and integration with bulk email sending.

## Features

### 1. **Template Upload** - `POST /upload-template`
Upload HTML email templates with Jinja2 variable support.

**Request:**
```bash
curl -F "file=@template.html" -F "name=interview_invite" \
  http://localhost:8000/templates/upload-template
```

**Response:**
```json
{
  "message": "Template 'interview_invite' uploaded successfully",
  "template_name": "interview_invite",
  "file_path": "/path/to/templates/interview_invite.html"
}
```

### 2. **Get Template** - `GET /templates/{template_name}`
Retrieve an HTML template by name.

**Request:**
```bash
curl http://localhost:8000/templates/interview_invite
```

**Response:** Raw HTML content with `Content-Type: text/html`

### 3. **List Templates** - `GET /templates/`
List all available templates.

**Request:**
```bash
curl http://localhost:8000/templates/
```

**Response:**
```json
{
  "templates": ["interview_invite", "welcome_email"],
  "count": 2
}
```

### 4. **Delete Template** - `DELETE /templates/{template_name}`
Delete a template.

**Request:**
```bash
curl -X DELETE http://localhost:8000/templates/interview_invite
```

### 5. **Send Bulk Emails with Template** - `POST /emails/send-bulk`
Send bulk emails using a custom template.

**Request:**
```bash
# First, upload CSV
UPLOAD_ID=$(curl -s -F "file=@candidates.csv" \
  "http://localhost:8000/upload-csv" | jq -r '.upload_id')

# Then send bulk emails with template
curl -X POST "http://localhost:8000/emails/send-bulk" \
  -H "Content-Type: application/json" \
  -d "{
    \"upload_id\": \"$UPLOAD_ID\",
    \"subject\": \"Interview Invitation\",
    \"template_name\": \"interview_invite\",
    \"with_attachments\": false,
    \"skip_sent\": true
  }"
```

**Response:**
```json
{
  "status": "started",
  "message": "Bulk email job started. Check /logs/ for progress.",
  "upload_id": "abc123",
  "row_count": 10,
  "template_name": "interview_invite"
}
```

## Template Variables

Your HTML templates can use Jinja2 variables:

### Default Variables:
- `{{ recipient }}` - Recipient name
- `{{ sender_name }}` - Sender name (from .env)
- `{{ current_date }}` - Current date (YYYY-MM-DD)
- `{{ current_year }}` - Current year

### CSV Column Variables:
Any column from your CSV will be available as a variable.

**Example CSV:**
```csv
recipient,email,Position,InterviewDate,Location
John Doe,john@example.com,Software Engineer,2025-11-15,Office A
```

**Available variables:** `{{ Position }}`, `{{ InterviewDate }}`, `{{ Location }}`

## Example HTML Template

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Interview Invitation</title>
</head>
<body>
    <h1>Interview Invitation</h1>
    <p>Dear {{ recipient }},</p>
    <p>You are invited for the position of {{ Position }}.</p>
    <p>Date: {{ InterviewDate }}</p>
    <p>Location: {{ Location }}</p>
    <p>Best regards,<br>{{ sender_name }}</p>
    <p><small>© {{ current_year }}</small></p>
</body>
</html>
```

## Running the Server

### Development Mode:
```bash
uvicorn app.main:app --reload --port 8000
```

### Production Mode (Docker):
```bash
docker-compose up --build
```

## Testing

Run the comprehensive test suite:
```bash
python test_template_upload_integration.py
```

This will test:
- ✅ Template upload
- ✅ Template retrieval
- ✅ Template listing
- ✅ CSV upload
- ✅ Bulk email with custom template
- ✅ Template deletion

## File Storage

Templates are stored in:
- **File system:** `./templates/` directory
- **In-memory cache:** For fast retrieval

Both storage methods are synchronized automatically.

## Docker Support

The backend is fully compatible with Docker deployment:

```bash
# Build and run
docker-compose up --build

# The templates directory will persist across container restarts
```

## Environment Variables

Required in `.env`:
```env
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
SENDER_NAME=Your Name
REDIS_URL=redis://localhost:6379  # Optional
```

## API Compatibility

All existing endpoints remain compatible:
- `POST /upload-csv` - Upload CSV files
- `POST /emails/send` - Send single email
- `POST /emails/send-bulk` - Send bulk emails (now with template support)

The `template_name` parameter is **optional** in email endpoints. If not provided, the default `template.html` will be used.
