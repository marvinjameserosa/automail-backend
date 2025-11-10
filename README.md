# Bulk Certificate Generator & Emailer

This project provides a two-step Python pipeline to automate the distribution of personalized documents, such as certificates.

1.  **PDF Splitter (`pdf_splitter.py`)**: Splits a single, multi-page PDF into individual files, naming each one according to a list of recipients in a CSV.
2.  **Auto Emailer (`auto_email.py`)**: Sends personalized HTML emails to a list of recipients, attaching their corresponding PDF file. It includes logging to prevent duplicate sends and can be run with or without attachments.

---

## Setup and Installation

### 1. What is a Virtual Environment?

A virtual environment is an isolated space on your computer for Python projects. It ensures that the packages you install for this project don't interfere with other projects. The following steps will guide you through creating and using one.

### 2. Create the Virtual Environment

Open your terminal or command prompt in the project's root directory and run the following command. This creates a folder named `venv` which will contain the environment.

```bash
python -m venv venv
```

### 3. Activate the Virtual Environment

You must activate the environment before installing packages or running the scripts.

- **On Windows:**

  ```bash
  .\venv\Scripts\activate
  ```

- **On macOS and Linux:**
  ```bash
  source venv/bin/activate
  ```

Your terminal prompt should now change to show `(venv)` at the beginning, indicating the environment is active.

### 4. Install Required Packages

With the virtual environment active, install all the necessary packages from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

---

## Workflow: Step-by-Step Guide

### Step 1: Prepare Your Files

Make sure the following files and folders are set up in your project directory:

- **`.env`**: A file to store your credentials securely. **This file should never be shared or committed to Git.**

  ```
  SENDER_EMAIL=your_email@gmail.com
  SENDER_PASSWORD=your_app_password
  SENDER_NAME=Your Organization Name
  FRONTEND_BASE_URL=http://localhost:3000
  ENABLE_FRONTEND_TEMPLATE_FETCH=true
  # FRONTEND_TEMPLATES_ENDPOINT=http://localhost:3000/api/templates
  # FRONTEND_TEMPLATE_TIMEOUT=5.0
  ```

  > **Note:** For Gmail, you must generate an "App Password" to use here, not your regular login password.

  When `ENABLE_FRONTEND_TEMPLATE_FETCH` is set to `true`, the backend will retrieve HTML templates from your Next.js frontend instance. `FRONTEND_BASE_URL` is used to derive the templates API endpoint (`/api/templates` by default), but you can override it directly with `FRONTEND_TEMPLATES_ENDPOINT` if the frontend is hosted elsewhere. `FRONTEND_TEMPLATE_TIMEOUT` controls the network timeout (in seconds) for these requests.

- **`input.pdf`**: The master PDF file containing all certificates, one per page.

- **`names.csv`**: A CSV file used by the PDF splitter. The order of names must match the order of pages in `input.pdf`.
  _Required column: `recipient`_

  ```csv
  recipient
  John Doe
  Jane Smith
  ```

- **`result.csv`**: A CSV file used by the emailer.
  _Required columns: `recipient`, `email`_
  _You can add extra columns (like `course_name`) to use in the email template._

  ```csv
  recipient,email,course_name
  John Doe,john.doe@example.com,Introduction to Python
  Jane Smith,jane.smith@example.com,Advanced Data Science
  ```

- **`template.html`**: The HTML template for the email body. You can use `{{ }}` to insert variables from your `result.csv`.
  ```html
  <!DOCTYPE html>
  <html>
    <body>
      <p>Hi {{ recipient }},</p>
      <p>Thank you for completing the {{ course_name }} course!</p>
      <p>Please find your certificate attached.</p>
      <p>Best regards,<br />{{ sender_name }}</p>
    </body>
  </html>
  ```

### Step 2: Run the PDF Splitter

Execute the `pdf_splitter.py` script. This will read `input.pdf` and `names.csv`, then create a `split_pages/` directory containing the individual, named PDF files.

```bash
python pdf_splitter.py
```

### Step 3: Configure and Run the Auto Emailer

Before running, open `auto_email.py` and configure the settings at the top of the file:

```python
# --- Email Content & Mode ---
SUBJECT = "Your Certificate of Completion"
CC_EMAIL_LIST = [] # e.g., ["admin@example.com"]

# Set to True to attach PDFs, False to send without.
SEND_WITH_ATTACHMENTS = True
```

Once configured, run the script to send the emails:

```bash
python auto_email.py
```

The script will log its progress in `email_log.csv` and will automatically skip any email addresses that have already been sent successfully.

## API Integration with the Frontend Template Editor

The FastAPI service can now consume templates managed in the Next.js frontend (`automail-frontend/public/templates`). Each template file is exposed through the frontend API with an identifier matching the filename (minus `.html`). When triggering email sends through the backend APIs you can either:

- Reference a stored template by `template_id` (for example, `"icpep-partnership-acceptance-email"`), or
- Provide raw HTML via `template_html` if you want to send ad-hoc content.

Both `/emails/send` and `/emails/send-bulk` accept the following optional fields in the JSON body:

- `template_id`: string identifier from the frontend template library.
- `template_html`: inline HTML content to render with Jinja.
- `template_subject`: subject override that replaces the placeholder subject when one is not provided.

Example payload for `/emails/send`:

```json
{
  "recipient": "Jane Doe",
  "recipient_email": "jane@example.com",
  "template_id": "icpep-partnership-acceptance-email",
  "recipient_data": {
    "company": "ACME Corp"
  },
  "with_attachment": false
}
```

For bulk jobs, include the same template fields alongside `upload_id`. The backend fetches the HTML once, then renders it for every row in the uploaded dataset.

### Deactivating the Virtual Environment

When you are finished working, you can deactivate the environment by simply typing:

```bash
deactivate
```
