# Frontend API Route Setup

## Create this file in your Next.js frontend project:

### File: `app/api/templates/[name]/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

export async function GET(
    request: NextRequest,
    { params }: { params: { name: string } }
) {
    try {
        const templateName = params.name;
        console.log('🔍 Backend requesting template:', templateName);
        
        // Path to your templates directory (adjust if needed)
        const templatesDir = path.join(process.cwd(), 'templates');
        
        // Read all template files
        const files = await fs.readdir(templatesDir);
        console.log('📁 Available templates:', files);
        
        // Find the template file that matches the requested name
        const templateFile = files.find(f => {
            const nameMatch = f.toLowerCase().includes(templateName.toLowerCase());
            const isJson = f.endsWith('.json');
            return nameMatch && isJson;
        });
        
        if (!templateFile) {
            console.log('❌ Template not found:', templateName);
            return NextResponse.json(
                { error: `Template "${templateName}" not found` },
                { status: 404 }
            );
        }
        
        console.log('✅ Found template file:', templateFile);
        
        // Read the template file
        const filePath = path.join(templatesDir, templateFile);
        const content = await fs.readFile(filePath, 'utf-8');
        const template = JSON.parse(content);
        
        // Return in the format expected by backend
        const response = {
            html_content: template.message,
            name: template.name,
            subject: template.subject
        };
        
        console.log('📤 Sending template to backend:', template.name);
        
        return NextResponse.json(response, {
            headers: {
                'Access-Control-Allow-Origin': 'http://localhost:8000',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            }
        });
    } catch (error) {
        console.error('❌ Error fetching template:', error);
        return NextResponse.json(
            { error: 'Failed to load template', details: String(error) },
            { status: 500 }
        );
    }
}

// Handle OPTIONS request for CORS
export async function OPTIONS() {
    return new NextResponse(null, {
        status: 200,
        headers: {
            'Access-Control-Allow-Origin': 'http://localhost:8000',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
    });
}
```

## File Structure:

Your Next.js project should look like this:

```
your-nextjs-app/
├── app/
│   ├── api/
│   │   └── templates/
│   │       ├── route.ts          (existing - lists all templates)
│   │       └── [name]/
│   │           └── route.ts      (NEW - fetch specific template)
│   └── ...
├── templates/                    (your template storage)
│   ├── template_1234.json
│   ├── cisco_interview_email_5678.json
│   └── ...
└── ...
```

## How to create it:

1. In your Next.js project root, navigate to `app/api/templates/`
2. Create a new folder called `[name]` (with square brackets)
3. Inside `[name]`, create a file called `route.ts`
4. Copy the code above into that file
5. Restart your Next.js dev server

## Testing:

After creating the file, test it by visiting:
- http://localhost:3000/api/templates/cisco_interview_email

You should see JSON response with `html_content`, `name`, and `subject`.

## Then in your React component:

Keep `fetch_from_frontend: true` in your useTemplate function. The backend will now be able to fetch templates from your frontend!
