# Frontend Template Integration Guide

## Overview
The backend can now **fetch templates from your frontend** and use them to send emails to members.

## How It Works

```
┌─────────────┐         ┌─────────────┐         ┌──────────────┐
│   Frontend  │         │   Backend   │         │  Recipients  │
│  (Template  │         │ (Email API) │         │   (Members)  │
│   Storage)  │         │             │         │              │
└──────┬──────┘         └──────┬──────┘         └──────────────┘
       │                       │                        
       │   1. User clicks      │                        
       │   "Use this template" │                        
       │─────────────────────→ │                        
       │                       │                        
       │   2. Backend fetches  │                        
       │      template HTML    │                        
       │←─────────────────────│                        
       │                       │                        
       │                       │  3. Sends emails       
       │                       │─────────────────────→  
       │                       │     with template      
```

## Backend Configuration

### 1. Update `.env` file:
```env
# Your frontend API URL
FRONTEND_API_URL=http://localhost:3000/api
```

### 2. Your Frontend Must Provide This Endpoint:

**Endpoint:** `GET /api/templates/{template_name}`

**Response Format (Option 1 - JSON):**
```json
{
  "html_content": "<html>...your template...</html>",
  "name": "interview_email",
  "subject": "Interview Invitation"
}
```

**Response Format (Option 2 - Direct HTML):**
```
Content-Type: text/html

<html>
  <body>
    <h1>Hello {{recipient}}</h1>
    ...
  </body>
</html>
```

## Usage from Frontend

### When User Clicks "Use this template":

```javascript
// 1. Get upload_id from CSV upload
const uploadId = await uploadCSV(csvFile);

// 2. Send bulk email request with fetch_from_frontend flag
const response = await fetch('http://localhost:8000/emails/send-bulk', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    upload_id: uploadId,
    template_name: "cisco_interview_email",  // Template name in your frontend
    subject: "Interview Invitation",
    fetch_from_frontend: true,  // ← KEY: Tells backend to fetch from frontend
    with_attachments: false,
    skip_sent: true
  })
});

const result = await response.json();
// {
//   "status": "started",
//   "template_source": "frontend",  ← Confirms it fetched from frontend
//   "row_count": 10
// }
```

## Complete Example

### Frontend Button Handler:
```javascript
async function useTemplate() {
  // Get selected template name from your UI
  const templateName = document.getElementById('template-select').value;
  const subject = document.getElementById('email-subject').value;
  
  // Get upload_id from previous CSV upload
  const uploadId = localStorage.getItem('current_upload_id');
  
  try {
    const response = await fetch('http://localhost:8000/emails/send-bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        upload_id: uploadId,
        template_name: templateName,
        subject: subject,
        fetch_from_frontend: true,  // Fetch from frontend
        with_attachments: false,
        skip_sent: true
      })
    });
    
    const result = await response.json();
    
    if (result.status === 'started') {
      alert(`Sending ${result.row_count} emails using ${templateName}!`);
      console.log('Template source:', result.template_source); // "frontend"
    }
  } catch (error) {
    console.error('Failed to send emails:', error);
  }
}
```

## Template Priority

The backend fetches templates in this order:

1. **Frontend API** (if `fetch_from_frontend: true`)
   - Fetches from: `{FRONTEND_API_URL}/templates/{template_name}`
   
2. **Backend Local Storage** (if frontend fetch fails or `fetch_from_frontend: false`)
   - Uses templates uploaded via `POST /templates/upload-template`
   
3. **Default Template** (if nothing else works)
   - Falls back to `template.html`

## API Endpoints Updated

### POST /emails/send
```json
{
  "recipient": "John Doe",
  "recipient_email": "john@example.com",
  "subject": "Hello",
  "template_name": "welcome_email",
  "fetch_from_frontend": true  // ← NEW field
}
```

### POST /emails/send-bulk
```json
{
  "upload_id": "abc123",
  "template_name": "interview_email",
  "subject": "Interview Invitation",
  "fetch_from_frontend": true,  // ← NEW field
  "with_attachments": false
}
```

**Response includes template source:**
```json
{
  "status": "started",
  "upload_id": "abc123",
  "row_count": 50,
  "template_name": "interview_email",
  "template_source": "frontend"  // ← Shows where template came from
}
```

## Frontend API Requirements

Your frontend must implement:

```javascript
// Express.js example
app.get('/api/templates/:name', (req, res) => {
  const templateName = req.params.name;
  
  // Fetch from your database
  const template = await db.templates.findOne({ name: templateName });
  
  if (!template) {
    return res.status(404).json({ error: 'Template not found' });
  }
  
  // Return HTML content
  res.json({
    html_content: template.html,
    name: template.name,
    subject: template.subject
  });
});
```

## Testing

Test if your frontend endpoint works:

```bash
# From backend, test fetching from frontend
curl http://localhost:3000/api/templates/interview_email

# Should return:
{
  "html_content": "<html>...</html>",
  "name": "interview_email"
}
```

Then send a test email:

```bash
curl -X POST http://localhost:8000/emails/send \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "Test User",
    "recipient_email": "test@example.com",
    "subject": "Test",
    "template_name": "interview_email",
    "fetch_from_frontend": true
  }'
```

## Benefits

✅ **Single Source of Truth** - Templates stored only in frontend
✅ **Real-time Updates** - Changes in frontend instantly available
✅ **No Duplication** - No need to upload templates to backend
✅ **Flexibility** - Can still use backend templates as fallback

## Environment Variables

```env
# Required
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
SENDER_NAME=Your Name

# Frontend integration
FRONTEND_API_URL=http://localhost:3000/api  # Your frontend API URL

# Optional
REDIS_URL=redis://localhost:6379
```
