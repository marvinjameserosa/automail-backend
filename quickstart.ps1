# Quick Start Script for HTML Template Email System (PowerShell)
# This script demonstrates the complete workflow

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "HTML Template Email System - Quick Start" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$BaseUrl = "http://localhost:8000"

Write-Host "Step 1: Create a sample HTML template..." -ForegroundColor Yellow
$templateContent = @"
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Welcome Email</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #4CAF50; color: white; padding: 20px; border-radius: 5px;">
        <h1>Welcome {{ recipient }}!</h1>
    </div>
    <div style="padding: 20px;">
        <p>Dear {{ recipient }},</p>
        <p>Thank you for joining us. Your position: <strong>{{ Position }}</strong></p>
        <p>Start Date: {{ StartDate }}</p>
        <p>Best regards,<br>{{ sender_name }}</p>
    </div>
    <div style="margin-top: 20px; font-size: 12px; color: #666;">
        <p>Sent on {{ current_date }} | © {{ current_year }} Company Name</p>
    </div>
</body>
</html>
"@
$templateContent | Out-File -FilePath "sample_template.html" -Encoding UTF8
Write-Host "✅ Created sample_template.html" -ForegroundColor Green

Write-Host ""
Write-Host "Step 2: Upload the template to the backend..." -ForegroundColor Yellow
$uploadUrl = "$BaseUrl/templates/upload-template"
$form = @{
    file = Get-Item -Path "sample_template.html"
    name = "welcome_email"
}
try {
    $uploadResponse = Invoke-RestMethod -Uri $uploadUrl -Method Post -Form $form
    $uploadResponse | ConvertTo-Json -Depth 10
    Write-Host "✅ Template uploaded" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to upload template: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Step 3: Create a sample CSV file..." -ForegroundColor Yellow
$csvContent = @"
recipient,email,Position,StartDate
Alice Johnson,alice@example.com,Software Engineer,2025-11-20
Bob Williams,bob@example.com,Product Manager,2025-11-22
Carol Davis,carol@example.com,Data Scientist,2025-11-25
"@
$csvContent | Out-File -FilePath "sample_data.csv" -Encoding UTF8
Write-Host "✅ Created sample_data.csv" -ForegroundColor Green

Write-Host ""
Write-Host "Step 4: Upload the CSV to get an upload_id..." -ForegroundColor Yellow
$csvUrl = "$BaseUrl/upload-csv"
$csvForm = @{
    file = Get-Item -Path "sample_data.csv"
}
try {
    $csvResponse = Invoke-RestMethod -Uri $csvUrl -Method Post -Form $csvForm
    $csvResponse | ConvertTo-Json -Depth 10
    $uploadId = $csvResponse.upload_id
    Write-Host "✅ CSV uploaded with ID: $uploadId" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to upload CSV: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 5: Send bulk emails using the custom template..." -ForegroundColor Yellow
$sendUrl = "$BaseUrl/emails/send-bulk"
$emailPayload = @{
    upload_id = $uploadId
    subject = "Welcome to Our Team!"
    template_name = "welcome_email"
    with_attachments = $false
    skip_sent = $true
} | ConvertTo-Json

try {
    $sendResponse = Invoke-RestMethod -Uri $sendUrl -Method Post -Body $emailPayload -ContentType "application/json"
    $sendResponse | ConvertTo-Json -Depth 10
    Write-Host "✅ Bulk email job started" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to send emails: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Step 6: List all available templates..." -ForegroundColor Yellow
try {
    $listResponse = Invoke-RestMethod -Uri "$BaseUrl/templates/" -Method Get
    $listResponse | ConvertTo-Json -Depth 10
    Write-Host "✅ Templates listed" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to list templates: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ Complete! Emails are being sent in the background." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Cleanup commands:" -ForegroundColor Yellow
Write-Host "  Remove-Item sample_template.html, sample_data.csv" -ForegroundColor Gray
Write-Host "  Invoke-RestMethod -Uri '$BaseUrl/templates/welcome_email' -Method Delete" -ForegroundColor Gray
Write-Host ""
Write-Host "Check email_log.csv for sending status." -ForegroundColor Yellow
