"""
PDF Page Splitter

This script splits a multi-page PDF into individual pages. Each new page is
named using the corresponding value from the 'recipient' column in a CSV file.

Requirements:
    pip install PyPDF2 pandas

Usage:
    python pdf_splitter.py
"""

import os
import pandas as pd
from PyPDF2 import PdfReader, PdfWriter
import re
from pathlib import Path

def sanitize_filename(filename):
    """Removes invalid characters from a string to make it a safe filename."""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', ' ', filename.strip())
    return filename[:100]

def split_pdf_by_recipient(pdf_path, csv_path, output_dir="split_pages"):
    """
    Splits a PDF into single pages, naming each file from a CSV 'recipient' column.

    Args:
        pdf_path (str): Path to the source multi-page PDF file.
        csv_path (str): Path to the CSV file with a 'recipient' column.
        output_dir (str): Directory where the output files will be saved.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        return
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found: {csv_path}")
        return
    
    Path(output_dir).mkdir(exist_ok=True)
    
    try:
        # Read the CSV and PDF files.
        df = pd.read_csv(csv_path)
        pdf_reader = PdfReader(pdf_path)
        total_pages = len(pdf_reader.pages)
        
        # Ensure the 'recipient' column exists.
        if 'recipient' not in df.columns:
            print("Error: 'recipient' column not found in CSV!")
            print(f"Available columns: {list(df.columns)}")
            return
        
        # Get the list of recipients from the dataframe.
        recipients = df['recipient'].fillna('Unknown_Recipient').astype(str).tolist()
        
        print(f"PDF has {total_pages} pages.")
        print(f"CSV has {len(recipients)} recipients.")
        
        # Warn if the number of pages and recipients do not match.
        if len(recipients) < total_pages:
            print(f"Warning: CSV has fewer recipients ({len(recipients)}) than PDF pages ({total_pages}).")
        elif len(recipients) > total_pages:
            print(f"Warning: CSV has more recipients ({len(recipients)}) than PDF pages ({total_pages}).")
        
        # Process each page in the PDF.
        for page_num in range(total_pages):
            pdf_writer = PdfWriter()
            pdf_writer.add_page(pdf_reader.pages[page_num])
            
            # Assign a name from the CSV or a default name if list is short.
            if page_num < len(recipients):
                recipient_name = recipients[page_num]
            else:
                recipient_name = f"Page_{page_num + 1}_No_Recipient"
            
            # Sanitize the name and create the output file path.
            safe_filename = sanitize_filename(recipient_name)
            output_filename = f"{safe_filename}.pdf"
            output_path = os.path.join(output_dir, output_filename)
            
            # Write the single page to a new PDF file.
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            print(f"Page {page_num + 1}: '{recipient_name}' -> '{output_filename}'")
        
        print(f"\nCompleted! All pages saved to the '{output_dir}' directory.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return

def main():
    """Defines file paths and runs the PDF splitting process."""
    
    # --- Configuration ---
    pdf_file = "input.pdf"
    csv_file = "names.csv"
    output_folder = "split_pages"
    
    print("PDF Page Splitter")
    print("=" * 40)
    
    # Run with configured paths or ask for user input if files are not found.
    if os.path.exists(pdf_file) and os.path.exists(csv_file):
        split_pdf_by_recipient(pdf_file, csv_file, output_folder)
    else:
        print("Default files not found. Please provide file paths.")
        
        pdf_path = input("Enter PDF file path: ").strip().strip('"')
        csv_path = input("Enter CSV file path: ").strip().strip('"')
        
        if not os.path.exists(pdf_path) or not os.path.exists(csv_path):
            print("Error: One or both files could not be found.")
            return
            
        output_dir_input = input("Enter output directory (default: 'split_pages'): ").strip()
        if output_dir_input:
            output_folder = output_dir_input
        
        split_pdf_by_recipient(pdf_path, csv_path, output_folder)

if __name__ == "__main__":
    main()