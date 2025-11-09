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
  ```

  > **Note:** For Gmail, you must generate an "App Password" to use here, not your regular login password.

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

### Deactivating the Virtual Environment

When you are finished working, you can deactivate the environment by simply typing:

```bash
deactivate
```
