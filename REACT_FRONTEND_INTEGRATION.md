# Frontend-Backend Template Integration

## Your Frontend Setup

Based on your React code, you have templates stored via `/api/templates` endpoint. 
To enable the backend to fetch these templates, we need to ensure proper integration.

## Integration Steps

### 1. **Update Your Frontend API Route** (Next.js)

Your existing `/api/templates` endpoint needs to support:
- GET `/api/templates` - List all templates ✅ (already exists)
- GET `/api/templates/{name}` - Get specific template by name (ADD THIS)

Create or update: `app/api/templates/[name]/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

const TEMPLATES_DIR = path.join(process.cwd(), 'templates');

export async function GET(
  request: NextRequest,
  { params }: { params: { name: string } }
) {
  try {
    const templateName = params.name;
    
    // List all template files
    const files = await fs.readdir(TEMPLATES_DIR);
    
    // Find template file that matches the name
    const matchingFile = files.find(file => {
      const nameWithoutExt = file.replace('.html', '');
      return nameWithoutExt.toLowerCase() === templateName.toLowerCase() ||
             file === `${templateName}.html`;
    });
    
    if (!matchingFile) {
      return NextResponse.json(
        { error: 'Template not found' },
        { status: 404 }
      );
    }
    
    // Read the template file
    const filePath = path.join(TEMPLATES_DIR, matchingFile);
    const content = await fs.readFile(filePath, 'utf-8');
    
    // Parse the template to extract subject and message
    const subjectMatch = content.match(/<!-- SUBJECT: (.*?) -->/);
    const subject = subjectMatch ? subjectMatch[1] : 'Email Subject';
    
    // Remove metadata comments to get clean HTML
    const message = content
      .replace(/<!-- SUBJECT: .*? -->\n?/, '')
      .replace(/<!-- ID: .*? -->\n?/, '')
      .trim();
    
    // Return template data in format expected by backend
    return NextResponse.json({
      success: true,
      name: templateName,
      subject: subject,
      html_content: message,  // Backend expects this field
      message: message,       // Also include this for compatibility
      filename: matchingFile
    });
    
  } catch (error) {
    console.error('Error fetching template:', error);
    return NextResponse.json(
      { error: 'Failed to fetch template' },
      { status: 500 }
    );
  }
}
```

### 2. **Update Backend `.env` File**

```env
SENDER_NAME=Carl Melvin Erosa
SENDER_EMAIL=carlmelvinerosa3@gmail.com
SENDER_PASSWORD=mcucbbuzuagvspqo

# Frontend API URL - UPDATE THIS to match your frontend
FRONTEND_API_URL=http://localhost:3000/api

# Optional Redis configuration
REDIS_URL=redis://localhost:6379
```

### 3. **Update Your "Use this template" Button**

In your `TemplateEditor` component, add this function:

```typescript
async function useTemplate() {
  if (!selectedId) {
    alert('Please select a template first');
    return;
  }
  
  const template = templates.find(t => t.id === selectedId);
  if (!template) return;
  
  try {
    // Step 1: Upload CSV with recipients (you need to implement CSV upload UI)
    const uploadId = await uploadCSVFile(); // Your CSV upload function
    
    // Step 2: Send bulk emails using this template
    const response = await fetch('http://localhost:8000/emails/send-bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        upload_id: uploadId,
        template_name: template.name,  // Name of the template
        subject: template.subject,
        fetch_from_frontend: true,     // ← KEY: Tells backend to fetch from frontend
        with_attachments: false,
        skip_sent: true
      })
    });
    
    const result = await response.json();
    
    if (result.status === 'started') {
      alert(`✅ Sending ${result.row_count} emails using template "${template.name}"!`);
      console.log('Email job started:', result);
    } else {
      alert('❌ Failed to send emails: ' + (result.detail || 'Unknown error'));
    }
    
  } catch (error) {
    console.error('Error using template:', error);
    alert('Failed to send emails. Make sure the backend is running.');
  }
}

// Helper function to upload CSV (implement based on your UI)
async function uploadCSVFile(): Promise<string> {
  // Option 1: If you already have CSV uploaded, get the upload_id
  const uploadId = localStorage.getItem('current_upload_id');
  if (uploadId) return uploadId;
  
  // Option 2: Prompt user to upload CSV
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.csv';
  
  return new Promise((resolve, reject) => {
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) {
        reject(new Error('No file selected'));
        return;
      }
      
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        const response = await fetch('http://localhost:8000/upload-csv', {
          method: 'POST',
          body: formData
        });
        
        const data = await response.json();
        if (data.upload_id) {
          // Optionally store for future use
          localStorage.setItem('current_upload_id', data.upload_id);
          resolve(data.upload_id);
        } else {
          reject(new Error('Failed to upload CSV'));
        }
      } catch (error) {
        reject(error);
      }
    };
    
    input.click();
  });
}
```

### 4. **Update the "Use this template" Button in JSX**

Replace the button in your return statement:

```tsx
<button 
  onClick={useTemplate}
  className="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg cursor-pointer"
>
  Use this template
</button>
```

### 5. **Test the Integration**

**Test Step 1:** Verify frontend API works

```bash
# Test if backend can fetch template from frontend
curl http://localhost:3000/api/templates/cisco_interview_email
```

Expected response:
```json
{
  "success": true,
  "name": "cisco_interview_email",
  "subject": "Interview Email",
  "html_content": "<html>...</html>",
  "message": "<html>...</html>"
}
```

**Test Step 2:** Test backend fetching from frontend

```bash
# Upload a test CSV
curl -F "file=@test.csv" http://localhost:8000/upload-csv

# Use the returned upload_id to send emails
curl -X POST http://localhost:8000/emails/send-bulk \
  -H "Content-Type: application/json" \
  -d '{
    "upload_id": "YOUR_UPLOAD_ID_HERE",
    "template_name": "cisco_interview_email",
    "subject": "Test Email",
    "fetch_from_frontend": true,
    "with_attachments": false
  }'
```

## Complete Flow Diagram

```
┌──────────────────┐
│  User Interface  │
│  (React)         │
└────────┬─────────┘
         │
         │ 1. Click "Use this template"
         ↓
┌──────────────────┐
│  Frontend        │
│  - Get template  │
│  - Upload CSV    │
│  - Call backend  │
└────────┬─────────┘
         │
         │ 2. POST /emails/send-bulk
         │    {
         │      template_name: "...",
         │      fetch_from_frontend: true
         │    }
         ↓
┌──────────────────┐
│  Backend API     │
│  (FastAPI)       │
└────────┬─────────┘
         │
         │ 3. GET frontend/api/templates/{name}
         ↓
┌──────────────────┐
│  Frontend API    │
│  Returns HTML    │
└────────┬─────────┘
         │
         │ 4. Return template HTML
         ↓
┌──────────────────┐
│  Backend         │
│  - Render with   │
│    Jinja2        │
│  - Send emails   │
└────────┬─────────┘
         │
         │ 5. Send to recipients
         ↓
┌──────────────────┐
│  Recipients      │
│  Receive emails  │
└──────────────────┘
```

## Summary

✅ **What you need to do:**

1. Create `/api/templates/[name]/route.ts` in your Next.js app
2. Update the "Use this template" button to call backend
3. Ensure backend `.env` has `FRONTEND_API_URL=http://localhost:3000/api`
4. Test the integration

✅ **What the backend does:**

- Fetches template from your frontend when `fetch_from_frontend: true`
- Falls back to local templates if frontend is unavailable
- Sends emails to all recipients in the CSV

Your templates stay in your frontend, and the backend just fetches them when needed! 🎉
