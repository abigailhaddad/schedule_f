#!/usr/bin/env python3
"""
Comment Fetcher for Schedule F Proposal

This script fetches public comments on the proposed Schedule F rule from regulations.gov API.
It downloads comments and saves them to a JSON file.

Features:
- Downloads comments and attachments from regulations.gov API
- Extracts text from various attachment types (PDF, DOCX, DOC, RTF, TXT, etc.)
- Supports resuming from checkpoints for large downloads

Requirements:
- Python 3.8+
- requests
- tqdm
- python-dotenv
- PyPDF2 (for PDF extraction)
- python-docx and docx2txt (for Word documents)
- striprtf (for RTF files)

Quick usage:
1. Set REGS_API_KEY in environment or .env file
2. Run: python -m backend.fetch.fetch_comments

For more options:
python -m backend.fetch.fetch_comments --help
"""

import os
import json
import time
import argparse
import requests
import mimetypes
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

# Import from backend packages
from backend.utils.common import create_directory, create_timestamped_dir, get_latest_results_dir

# Define utility functions
def download_attachment_with_retry(url: str, output_dir: str, max_retries: int = 10, 
                               base_delay: float = 1.0, max_delay: float = 60.0) -> Optional[str]:
    """
    Download an attachment from a URL with exponential backoff retry logic.
    
    Args:
        url: URL of the attachment
        output_dir: Directory to save the attachment (should be the comment-specific subfolder)
        max_retries: Maximum number of retries
        base_delay: Base delay for exponential backoff (seconds)
        max_delay: Maximum delay for exponential backoff (seconds)
        
    Returns:
        Path to the downloaded file or None if download failed
    """
    import os
    import time
    import random
    import requests
    from urllib.parse import urlparse
    from typing import Optional
    
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get filename from URL
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    if not filename or filename == '':
        # Generate a random filename if none is found
        filename = f"attachment_{random.randint(10000, 99999)}.txt"
    
    # Make sure the filename is unique to avoid overwriting
    base_name, ext = os.path.splitext(filename)
    if not ext:  # If no extension, default to .txt
        ext = '.txt'
    
    # Add a timestamp to ensure uniqueness
    timestamp = int(time.time())
    unique_filename = f"{base_name}_{timestamp}{ext}"
    
    output_path = os.path.join(output_dir, unique_filename)
    
    print(f"Downloading from {url}")
    print(f"Target path: {output_path}")
    
    # Try downloading with exponential backoff
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Save the file
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            print(f"Successfully downloaded to: {output_path}")
            return output_path
            
        except requests.exceptions.RequestException as e:
            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
            print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            print(f"Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
    
    print(f"Failed to download attachment after {max_retries} attempts: {url}")
    return None

# Load environment variables
load_dotenv()

def get_mime_type(url: str, filename: str) -> str:
    """
    Determine MIME type from URL or filename.
    
    Args:
        url: The URL to the file
        filename: The filename extracted from the URL
        
    Returns:
        The MIME type as a string
    """
    # First try to get from the filename extension
    mime_type, _ = mimetypes.guess_type(filename)
    
    if not mime_type:
        # Try to extract from the URL if not found
        if '.pdf' in url.lower():
            mime_type = 'application/pdf'
        elif '.doc' in url.lower():
            mime_type = 'application/msword'
        elif '.docx' in url.lower():
            mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif '.xls' in url.lower():
            mime_type = 'application/vnd.ms-excel'
        elif '.xlsx' in url.lower():
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif '.ppt' in url.lower():
            mime_type = 'application/vnd.ms-powerpoint'
        elif '.pptx' in url.lower():
            mime_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        elif '.txt' in url.lower():
            mime_type = 'text/plain'
        elif '.rtf' in url.lower():
            mime_type = 'application/rtf'
        elif '.csv' in url.lower():
            mime_type = 'text/csv'
        elif '.html' in url.lower() or '.htm' in url.lower():
            mime_type = 'text/html'
        else:
            # Default to binary if we can't determine
            mime_type = 'application/octet-stream'
            
    return mime_type

def extract_text_from_file_basic_no_tesseract(file_path: str) -> str:
    """
    Smart basic text extraction - handles TXT, DOCX, PDF without OCR.
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    try:
        # Text files - simple and fast
        if ext in ['.txt', '.csv', '.log']:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                return text if text.strip() else "[EMPTY TEXT FILE]"
            except:
                # Try with different encoding
                with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
                    return f.read()
        
        # Microsoft Word documents
        elif ext in ['.docx']:
            try:
                from docx import Document
                doc = Document(file_path)
                text = []
                for paragraph in doc.paragraphs:
                    text.append(paragraph.text)
                result = '\n'.join(text)
                return result if result.strip() else "[EMPTY DOCX FILE]"
            except ImportError:
                return "[DOCX LIBRARY NOT AVAILABLE]"
            except Exception as e:
                return f"[DOCX EXTRACTION FAILED: {str(e)}]"
        
        # PDF files - simple extraction only
        elif ext == '.pdf':
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        try:
                            text += page.extract_text() + "\n"
                        except:
                            continue  # Skip problematic pages
                    return text.strip() if text.strip() else "[EMPTY PDF OR EXTRACTION FAILED]"
            except Exception as e:
                return f"[PDF EXTRACTION FAILED: {str(e)}]"
        
        # RTF files (common in government docs)
        elif ext == '.rtf':
            try:
                from striprtf.striprtf import rtf_to_text
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    rtf_content = f.read()
                text = rtf_to_text(rtf_content)
                return text if text.strip() else "[EMPTY RTF FILE]"
            except ImportError:
                return "[RTF LIBRARY NOT AVAILABLE]"
            except Exception as e:
                return f"[RTF EXTRACTION FAILED: {str(e)}]"
        
        # Unsupported file types (images, etc.)
        else:
            return f"[UNSUPPORTED FILE TYPE: {ext.upper()}]"
            
    except Exception as e:
        return f"[EXTRACTION ERROR: {str(e)}]"

def download_all_attachments(comments_data, output_dir: str):
    """
    Download all attachments for a list of comments using the existing infrastructure.
    This function reuses the existing extract_text_from_pdf and download_attachment functions
    to maintain consistency with the API path.
    
    Args:
        comments_data: List of comment objects
        output_dir: Directory to save attachments
        
    Returns:
        Updated list of comments with local paths to attachments and extracted text
    """
    import os
    
    total_attachments = sum(len(comment.get("attributes", {}).get("attachments", [])) 
                           for comment in comments_data)
    
    if total_attachments == 0:
        print("No attachments to download.")
        return comments_data
    
    print(f"Downloading {total_attachments} attachments...")
    
    # Create the main attachments directory
    attachments_base_dir = os.path.join(output_dir, "attachments")
    os.makedirs(attachments_base_dir, exist_ok=True)
    
    # Process each comment
    downloaded = 0
    failed = 0
    
    # Create progress bar for attachments
    attachment_pbar = tqdm(total=total_attachments, desc="Downloading attachments")
    
    for comment in comments_data:
        comment_id = comment.get("id", "unknown")
        # Sanitize comment_id to ensure it's a valid folder name
        comment_id = ''.join(c for c in comment_id if c.isalnum() or c in '-_')
        if not comment_id:
            comment_id = f"comment_{len(comments_data)}"
            
        attributes = comment.get("attributes", {})
        attachments = attributes.get("attachments", [])
        
        if not attachments:
            continue
        
        # Create a subfolder for this comment's attachments
        comment_attachments_dir = os.path.join(attachments_base_dir, comment_id)
        os.makedirs(comment_attachments_dir, exist_ok=True)
        
        # List to store attachment texts
        attachment_texts = []
        
        for i, attachment in enumerate(attachments):
            url = attachment.get("fileUrl")
            if url:
                
                # Determine file extension
                attachment_title = attachment.get("title", "")
                _, ext = os.path.splitext(url)
                is_pdf = ext.lower() == '.pdf' or '.pdf' in url.lower()
                
                # Create unique filename
                if not ext:
                    ext = '.pdf' if is_pdf else '.txt'
                
                # Create safe filename
                safe_title = "".join(c for c in attachment_title if c.isalnum() or c in " ._-").strip()
                safe_title = safe_title[:50] if safe_title else f"attachment_{i+1}"
                filename = f"{safe_title}{ext}"
                
                # Download the attachment using the existing function
                downloaded_path = download_attachment_with_retry(url, comment_attachments_dir)
                
                if downloaded_path:
                    # Update the attachment with local path
                    attachments[i]["localPath"] = downloaded_path
                    downloaded += 1
                    
                    # Smart extraction: try basic methods first, then Gemini if needed
                    try:
                        # Step 1: Try basic extraction first (free and fast)
                        print(f"    📄 Trying basic extraction for {safe_title}...")
                        basic_text = extract_text_from_file_basic_no_tesseract(downloaded_path)
                        
                        # Check if basic extraction was successful (>100 chars of real content)
                        clean_text = basic_text.strip() if basic_text else ""
                        is_good_extraction = (
                            len(clean_text) > 100 and 
                            not clean_text.startswith('[') and
                            not clean_text.upper().startswith('ERROR')
                        )
                        
                        if is_good_extraction:
                            # Basic extraction worked well - use it!
                            attachment_text = basic_text
                            print(f"    ✅ Basic extraction successful: {len(attachment_text)} characters")
                        else:
                            # Basic extraction failed or gave minimal text - try Gemini
                            print(f"    🤖 Basic extraction insufficient ({len(clean_text)} chars), trying Gemini...")
                            try:
                                from backend.utils.retry_gemini_attachments import extract_text_with_gemini
                                gemini_text = extract_text_with_gemini(downloaded_path, max_retries=1, timeout=30)
                                
                                if gemini_text and not gemini_text.startswith('[') and len(gemini_text.strip()) > len(clean_text):
                                    # Gemini gave better results
                                    attachment_text = gemini_text
                                    print(f"    ✅ Gemini extraction successful: {len(attachment_text)} characters")
                                else:
                                    # Gemini failed or wasn't better - use basic result
                                    attachment_text = basic_text
                                    print(f"    ⚠️  Using basic extraction result: {len(attachment_text)} characters")
                                    
                            except Exception as gemini_error:
                                print(f"    ❌ Gemini extraction failed: {gemini_error}")
                                attachment_text = basic_text
                                print(f"    📝 Using basic extraction fallback: {len(attachment_text)} characters")
                        
                        # Save extracted text immediately if we got good results
                        if attachment_text and len(attachment_text.strip()) > 50:
                            extracted_path = downloaded_path + '.extracted.txt'
                            with open(extracted_path, 'w', encoding='utf-8') as f:
                                f.write(attachment_text)
                            print(f"    💾 Saved extracted text to {os.path.basename(extracted_path)}")
                            
                        attachment_texts.append({
                            "id": f"{comment_id}_attachment_{i+1}",
                            "title": attachment_title or safe_title,
                            "text": attachment_text,
                            "file_path": downloaded_path,
                            "mime_type": get_mime_type(url, filename)
                        })
                        
                    except Exception as e:
                        print(f"    💥 All extraction methods failed for {filename}: {e}")
                        attachment_texts.append({
                            "id": f"{comment_id}_attachment_{i+1}",
                            "title": attachment_title or safe_title,
                            "text": f"[TEXT EXTRACTION FAILED: {str(e)}]",
                            "file_path": downloaded_path,
                            "mime_type": get_mime_type(url, filename)
                        })
                else:
                    failed += 1
                
                # Update progress bar for each attachment processed
                attachment_pbar.update(1)
        
        # Add attachment texts to the comment data
        if attachment_texts:
            attributes["attachment_texts"] = attachment_texts
    
    # Close progress bar
    attachment_pbar.close()
    
    if failed > 0:
        print(f"Downloaded {downloaded} attachments, {failed} failed.")
    else:
        print(f"Downloaded {downloaded} attachments successfully.")
    return comments_data

def read_comments_from_csv(csv_file_path: str, output_dir: str, limit: Optional[int] = None):
    """
    Read comments from a CSV file and save them to a JSON file.
    
    Args:
        csv_file_path: Path to the CSV file
        output_dir: Directory to save the output JSON file
        limit: Maximum number of comments to process
    
    Returns:
        Path to the output JSON file
    """
    import pandas as pd
    from pathlib import Path
        
    print(f"Reading comments from CSV file: {csv_file_path}")
    
    # Read the CSV file with error handling for malformed data
    try:
        df = pd.read_csv(csv_file_path)
    except pd.errors.ParserError as e:
        print(f"Warning: CSV parsing error: {e}")
        print("Attempting to read with quoting=csv.QUOTE_NONE...")
        import csv
        df = pd.read_csv(csv_file_path, quoting=csv.QUOTE_NONE, on_bad_lines='skip')
    
    # Skip the second row (first data row) which is not a real comment
    df = df.iloc[1:].reset_index(drop=True)
    
    # Apply limit if specified
    if limit is not None:
        df = df.head(limit)
    
    # Create a list of comments in the same format as the API output
    comments = []
    for idx, row in df.iterrows():
        # Extract the comment ID from the Document ID
        comment_id = str(row.get('Document ID', ''))
        if pd.isna(comment_id) or comment_id == '':
            comment_id = f"comment_{idx}"
        
        # Create a comment object with the same structure as the API output
        comment = {
            "id": comment_id,
            "attributes": {
                "title": str(row.get('Title', '')) if not pd.isna(row.get('Title', '')) else '',
                "commentOn": str(row.get('Comment on Document ID', '')) if not pd.isna(row.get('Comment on Document ID', '')) else '',
                "postedDate": str(row.get('Posted Date', '')) if not pd.isna(row.get('Posted Date', '')) else '',
                "receivedDate": str(row.get('Received Date', '')) if not pd.isna(row.get('Received Date', '')) else '',
                "submitterName": f"{str(row.get('First Name', '')) if not pd.isna(row.get('First Name', '')) else ''} {str(row.get('Last Name', '')) if not pd.isna(row.get('Last Name', '')) else ''}".strip(),
                "organization": str(row.get('Organization Name', '')) if not pd.isna(row.get('Organization Name', '')) else '',
                "city": str(row.get('City', '')) if not pd.isna(row.get('City', '')) else '',
                "state": str(row.get('State/Province', '')) if not pd.isna(row.get('State/Province', '')) else '',
                "country": str(row.get('Country', '')) if not pd.isna(row.get('Country', '')) else '',
                "comment": str(row.get('Comment', '')) if not pd.isna(row.get('Comment', '')) else '',
                "documentType": str(row.get('Document Type', '')) if not pd.isna(row.get('Document Type', '')) else '',
                "agencyId": str(row.get('Agency ID', '')) if not pd.isna(row.get('Agency ID', '')) else '',
                "category": str(row.get('Category', '')) if not pd.isna(row.get('Category', '')) else '',
                "attachmentCount": 0,  # Default to 0, will be updated if attachments are found
                "attachments": []  # Will be populated with attachment info if available
            }
        }
        
        # Only process Attachment Files - ignore Content Files
        attachment_files = row.get('Attachment Files', '')
        
        # Process attachment files - safely handle NaN or float values
        if not pd.isna(attachment_files) and attachment_files != '':
            attachment_files_str = str(attachment_files)
            if ',' in attachment_files_str:
                files = attachment_files_str.split(',')
                for file_url in files:
                    if file_url.strip():
                        file_name = Path(file_url.strip()).name
                        comment["attributes"]["attachments"].append({
                            "title": file_name,
                            "fileUrl": file_url.strip(),
                            "type": "attachment"
                        })
            else:
                # Single URL without commas
                file_url = attachment_files_str.strip()
                if file_url:
                    file_name = Path(file_url).name
                    comment["attributes"]["attachments"].append({
                        "title": file_name,
                        "fileUrl": file_url,
                        "type": "attachment"
                    })
        
        # Update attachment count
        comment["attributes"]["attachmentCount"] = len(comment["attributes"]["attachments"])
        
        comments.append(comment)
    
    # Save comments to a JSON file
    output_file = os.path.join(output_dir, "raw_data.json")
    with open(output_file, 'w') as f:
        json.dump(comments, f, indent=2)
    
    print(f"Saved {len(comments)} comments to {output_file}")
    
    return output_file

def main():
    """Parse arguments and run the script."""
    parser = argparse.ArgumentParser(description='Fetch comments from regulations.gov API with enhanced attachment handling')
    parser.add_argument('--document_id', type=str, default="OPM-2025-0004-0001",
                      help='Document ID to fetch comments for (default: OPM-2025-0004-0001)')
    parser.add_argument('--limit', type=int, default=None,
                      help='Limit number of comments to fetch (default: fetch all)')
    parser.add_argument('--output_dir', type=str, default=None,
                      help='Directory to save output (default: data/raw/fetch_TIMESTAMP)')
    parser.add_argument('--api_key', type=str, default=None,
                      help='API key for regulations.gov (default: use REGS_API_KEY from environment)')
    parser.add_argument('--no-attachments', action='store_true',
                      help='Do not download and extract text from attachments')
    parser.add_argument('--resume', action='store_true',
                      help='Resume from checkpoint if available')
    parser.add_argument('--csv_file', type=str, default=None,
                      help='Path to CSV file to import (instead of using the API)')
    
    args = parser.parse_args()
    
    try:
        # Handle CSV import mode
        if args.csv_file:
            if not os.path.exists(args.csv_file):
                print(f"Error: CSV file not found: {args.csv_file}")
                return 1
                
            # Create output directory if needed
            if args.output_dir is None:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                args.output_dir = os.path.join(project_root, "results", f"results_{timestamp}")
                
            os.makedirs(args.output_dir, exist_ok=True)
            
            # Read comments from CSV
            result_path = read_comments_from_csv(
                csv_file_path=args.csv_file,
                output_dir=args.output_dir,
                limit=args.limit
            )
        else:
            # Fetch comments using the API
            result_path = fetch_comments(
                document_id=args.document_id,
                output_dir=args.output_dir,
                limit=args.limit,
                api_key=args.api_key,
                download_attachments=not args.no_attachments,
                resume=args.resume
            )
        
        print(f"Successfully processed comments.")
        print(f"Output saved to: {result_path}")
    except Exception as e:
        print(f"Error processing comments: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

