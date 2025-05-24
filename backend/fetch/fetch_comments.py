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
def get_headers(api_key):
    """Return headers with API key for regulations.gov API."""
    return {"X-Api-Key": api_key}

def get_object_id(document_id, api_key):
    """Fetch the internal objectId for a documentId."""
    url = f"https://api.regulations.gov/v4/documents/{document_id}"
    response = requests.get(url, headers=get_headers(api_key))
    response.raise_for_status()
    return response.json()["data"]["attributes"]["objectId"]

def get_comment_ids(object_id, api_key, limit=None, page_size=250):
    """Retrieve comment IDs for a document with optional limit."""
    comment_ids = []
    page = 1
    total_pages = None
    pbar = None
    base_url = "https://api.regulations.gov/v4"
    
    while (total_pages is None or page <= total_pages) and (limit is None or len(comment_ids) < limit):
        url = (
            f"{base_url}/comments?"
            f"filter[commentOnId]={object_id}&"
            f"page[size]={page_size}&"
            f"page[number]={page}&"
            f"sort=lastModifiedDate"
        )
        response = requests.get(url, headers=get_headers(api_key))
        response.raise_for_status()
        response_data = response.json()
        
        # Get total pages information if we don't have it yet
        if total_pages is None and 'meta' in response_data:
            total_count = response_data['meta'].get('totalElements', 0)
            total_pages = response_data['meta'].get('totalPages', 0)
            print(f"Found {total_count} total comments across {total_pages} pages")
            
            # Initialize progress bar after we know the total
            if limit is None:
                pbar = tqdm(total=total_count, desc="Fetching comment IDs")
            else:
                pbar = tqdm(total=min(total_count, limit), desc="Fetching comment IDs")
        
        data = response_data.get("data", [])
        if not data:
            break
            
        ids = [item["id"] for item in data]
        
        # If we have a limit, only take what we need
        if limit is not None and len(comment_ids) + len(ids) > limit:
            ids = ids[:limit - len(comment_ids)]
        
        comment_ids.extend(ids)
        
        if pbar:
            pbar.update(len(ids))
        
        # Break if we've reached the limit
        if limit is not None and len(comment_ids) >= limit:
            break
            
        page += 1
        time.sleep(0.5)  # Slightly longer delay to be gentle on the API
    
    if pbar:
        pbar.close()
    
    print(f"Retrieved a total of {len(comment_ids)} comment IDs")
    return comment_ids

def save_json(data, filename):
    """Save data to a JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(data)} comments to {filename}")
    return filename

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


def extract_text_from_excel(file_path: str) -> str:
    """Extract text from a Microsoft Excel file."""
    try:
        import pandas as pd
        
        # Read all sheets
        excel_file = pd.ExcelFile(file_path)
        sheets = excel_file.sheet_names
        
        text = ""
        for sheet in sheets:
            df = pd.read_excel(file_path, sheet_name=sheet)
            text += f"Sheet: {sheet}\n"
            text += df.to_string(index=False) + "\n\n"
            
        return text
    except ImportError:
        return "[EXCEL TEXT EXTRACTION FAILED - pandas not installed]"
    except Exception as e:
        return f"[EXCEL TEXT EXTRACTION FAILED: {str(e)}]"

def extract_text_from_powerpoint(file_path: str) -> str:
    """Extract text from a Microsoft PowerPoint file."""
    try:
        from pptx import Presentation
        
        text = ""
        prs = Presentation(file_path)
        
        for slide in prs.slides:
            text += "SLIDE\n"
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
            text += "\n"
            
        return text
    except ImportError:
        return "[POWERPOINT TEXT EXTRACTION FAILED - python-pptx not installed]"
    except Exception as e:
        return f"[POWERPOINT TEXT EXTRACTION FAILED: {str(e)}]"

def extract_text_from_text_file(file_path: str) -> str:
    """Extract text from a plain text file (txt, csv, html, etc.)."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        return f"[TEXT FILE EXTRACTION FAILED: {str(e)}]"


def extract_text_from_file(file_path: str) -> str:
    """
    Extract text from various file types with enhanced PDF and image support.
    Returns empty string for unsupported formats instead of error messages.
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    try:
        # PDF files - enhanced with multiple extraction methods
        if ext == '.pdf':
            return extract_text_from_pdf_enhanced(file_path)
            
        # Image files - OCR processing
        elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']:
            return extract_text_from_image_ocr(file_path)
            
        # Microsoft Word documents
        elif ext in ['.doc', '.docx']:
            return extract_text_from_word(file_path)
            
        # Microsoft Excel files
        elif ext in ['.xls', '.xlsx']:
            return extract_text_from_excel(file_path)
            
        # Microsoft PowerPoint files
        elif ext in ['.ppt', '.pptx']:
            return extract_text_from_powerpoint(file_path)
            
        # Text files, CSV, etc.
        elif ext in ['.txt', '.csv', '.md', '.json', '.xml', '.html', '.htm']:
            return extract_text_from_text_file(file_path)
            
        # RTF files
        elif ext == '.rtf':
            return extract_text_from_rtf(file_path)
            
        # Unsupported format - return empty string instead of error message
        else:
            return ""
            
    except Exception as e:
        print(f"Text extraction failed for {file_path}: {e}")
        return ""

def extract_text_from_pdf_enhanced(file_path: str) -> str:
    """
    Enhanced PDF text extraction with multiple methods and OCR fallback.
    """
    # Method 1: Try pdfplumber (good for complex layouts)
    text = extract_pdf_with_pdfplumber(file_path)
    if text and len(text.strip()) > 50:
        return text
    
    # Method 2: Try PyMuPDF (handles more edge cases)
    text = extract_pdf_with_pymupdf(file_path)
    if text and len(text.strip()) > 50:
        return text
    
    # Method 3: Try PyPDF2 (fallback)
    text = extract_pdf_with_pypdf2(file_path)
    if text and len(text.strip()) > 50:
        return text
    
    # Method 4: OCR fallback for scanned PDFs
    print(f"PDF text extraction minimal, trying OCR for {file_path}")
    return extract_pdf_with_ocr(file_path)

def extract_pdf_with_pdfplumber(file_path: str) -> str:
    """Extract text using pdfplumber library."""
    try:
        import pdfplumber
        
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except ImportError:
        return ""
    except Exception as e:
        print(f"pdfplumber extraction failed: {e}")
        return ""

def extract_pdf_with_pymupdf(file_path: str) -> str:
    """Extract text using PyMuPDF (fitz) library."""
    try:
        import fitz  # PyMuPDF
        
        text = ""
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            if page_text:
                text += page_text + "\n"
        doc.close()
        return text
    except ImportError:
        return ""
    except Exception as e:
        print(f"PyMuPDF extraction failed: {e}")
        return ""

def extract_pdf_with_pypdf2(file_path: str) -> str:
    """Extract text using PyPDF2 library (original method)."""
    try:
        import PyPDF2
        
        text = ""
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                page_text = reader.pages[page_num].extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except ImportError:
        return ""
    except Exception as e:
        print(f"PyPDF2 extraction failed: {e}")
        return ""

def extract_pdf_with_ocr(file_path: str) -> str:
    """Convert PDF pages to images and perform OCR."""
    try:
        import fitz  # PyMuPDF for PDF to image conversion
        
        text = ""
        doc = fitz.open(file_path)
        
        for page_num in range(min(len(doc), 10)):  # Limit to first 10 pages for performance
            page = doc.load_page(page_num)
            # Convert to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scaling for better OCR
            img_data = pix.tobytes("png")
            
            # Perform OCR on the image data
            page_text = ocr_image_data(img_data)
            if page_text:
                text += page_text + "\n"
        
        doc.close()
        return text
    except ImportError:
        print("PyMuPDF not available for PDF OCR")
        return ""
    except Exception as e:
        print(f"PDF OCR failed: {e}")
        return ""
    


def is_coherent_english_text(text: str) -> bool:
    """
    Check if extracted text looks like coherent English, focusing on detecting OCR gibberish.
    Allows short coherent text like "yeah, no" but rejects garbled OCR output.
    
    Args:
        text: The extracted text to check
    
    Returns:
        True if text appears to be coherent English, False if it's gibberish
    """
    if not text or len(text.strip()) < 2:
        return False
    
    text = text.strip()
    
    # Quick pass for very short text - just check it's not mostly symbols
    if len(text) <= 20:
        alpha_chars = sum(1 for c in text if c.isalpha())
        if alpha_chars < 2:  # At least 2 letters
            return False
        weird_chars = sum(1 for c in text if c in '@#$%^&*~`|\\{}[]<>')
        if weird_chars > 2:  # Too many weird symbols
            return False
        return True
    
    # For longer text, do more comprehensive checks
    words = text.split()
    if len(words) == 0:
        return False
    
    # Check 1: Ratio of alphabetic characters should be reasonable
    alpha_chars = sum(1 for c in text if c.isalpha())
    total_chars = len(text)
    alpha_ratio = alpha_chars / total_chars if total_chars > 0 else 0
    
    if alpha_ratio < 0.5:  # Less than 50% alphabetic characters
        return False
    
    # Check 2: Average word length should be reasonable (1-20 characters)
    clean_words = [word.strip(string.punctuation) for word in words if word.strip(string.punctuation)]
    if not clean_words:
        return False
        
    avg_word_length = sum(len(word) for word in clean_words) / len(clean_words)
    if avg_word_length < 1 or avg_word_length > 20:
        return False
    
    # Check 3: Not too many single-character "words" (common in OCR failures)
    single_char_words = sum(1 for word in clean_words if len(word) == 1)
    if len(clean_words) > 5 and single_char_words / len(clean_words) > 0.4:  # More than 40% single chars
        return False
    
    # Check 4: Shouldn't have excessive weird characters
    weird_chars = sum(1 for c in text if c in '@#$%^&*~`|\\{}[]<>')
    if weird_chars > len(text) * 0.15:  # More than 15% weird characters
        return False
    
    # Check 5: For longer text, should have some common English words
    if len(words) >= 10:
        common_words = {'the', 'and', 'to', 'of', 'a', 'in', 'is', 'it', 'you', 'that', 'he', 'was', 'for', 'on', 'are', 'as', 'with', 'his', 'they', 'i', 'at', 'be', 'this', 'have', 'from', 'or', 'one', 'had', 'by', 'word', 'but', 'not', 'what', 'all', 'were', 'we', 'when', 'your', 'can', 'said', 'there', 'each', 'which', 'she', 'do', 'how', 'their', 'if', 'will', 'up', 'other', 'about', 'out', 'many', 'then', 'them', 'these', 'so', 'some', 'her', 'would', 'make', 'like', 'into', 'him', 'has', 'two', 'more', 'very', 'know', 'just', 'first', 'get', 'over', 'think', 'also', 'back', 'after', 'use', 'work', 'life', 'only', 'new', 'way', 'may', 'say', 'no', 'yes', 'good', 'bad', 'well', 'see', 'come', 'go', 'take', 'give'}
        
        # Convert to lowercase and remove punctuation for comparison
        clean_words_lower = [word.lower().strip(string.punctuation) for word in words]
        common_word_count = sum(1 for word in clean_words_lower if word in common_words)
        common_word_ratio = common_word_count / len(words)
        
        if common_word_ratio < 0.05:  # Less than 5% common words in longer text
            return False
    
    # Check 6: Shouldn't be mostly repeated characters or patterns
    repeated_char_pattern = re.findall(r'(.)\1{4,}', text)  # 5+ same chars in a row
    if len(repeated_char_pattern) > 3:
        return False
    
    # Check 7: Detect common OCR garbage patterns
    # Too many isolated letters with spaces
    isolated_letters = re.findall(r'\b[a-zA-Z]\b', text)
    if len(words) > 5 and len(isolated_letters) > len(words) * 0.3:
        return False
    
    return True


def extract_text_from_image_ocr(file_path: str) -> str:
    """Extract text from image files using OCR."""
    try:
        with open(file_path, 'rb') as f:
            img_data = f.read()
        return ocr_image_data(img_data)
    except Exception as e:
        print(f"Image OCR failed for {file_path}: {e}")
        return ""

def ocr_image_data(image_data: bytes) -> str:
    """
    Perform OCR on image data using the best available OCR library.
    Tries EasyOCR first, then falls back to Tesseract.
    """
    # Method 1: Try EasyOCR (often better accuracy)
    text = ocr_with_easyocr(image_data)
    if text and len(text.strip()) > 10:
        return text
    
    # Method 2: Try Tesseract OCR
    text = ocr_with_tesseract(image_data)
    if text and len(text.strip()) > 10:
        return text
    
    return ""

def ocr_with_easyocr(image_data: bytes) -> str:
    """Perform OCR using EasyOCR library."""
    try:
        import easyocr
        import numpy as np
        from PIL import Image
        import io
        
        # Convert bytes to PIL Image, then to numpy array
        image = Image.open(io.BytesIO(image_data))
        
        # Convert PIL Image to RGB if it's not already
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array (EasyOCR expects this format)
        image_array = np.array(image)
        
        # Initialize EasyOCR reader (English only for performance)
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)  # Set gpu=True if you have CUDA
        
        # Perform OCR
        results = reader.readtext(image_array)
        
        # Extract text from results
        text = ""
        for (bbox, detected_text, confidence) in results:
            if confidence > 0.5:  # Only include high-confidence text
                text += detected_text + " "
        
        return text.strip()
    except ImportError:
        return ""
    except Exception as e:
        print(f"EasyOCR failed: {e}")
        return ""

def ocr_with_tesseract(image_data: bytes) -> str:
    """Perform OCR using Tesseract via pytesseract."""
    try:
        import pytesseract
        from PIL import Image
        import io
        
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Preprocess image for better OCR
        image = preprocess_image_for_ocr(image)
        
        # Perform OCR
        text = pytesseract.image_to_string(image, config='--psm 6')
        
        return text.strip()
    except ImportError:
        print("pytesseract not available")
        return ""
    except Exception as e:
        print(f"Tesseract OCR failed: {e}")
        return ""

def preprocess_image_for_ocr(image):
    """Preprocess PIL Image for better OCR results."""
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        
        # Convert to grayscale if not already
        if image.mode != 'L':
            image = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        # Apply slight blur to reduce noise
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        return image
    except Exception as e:
        print(f"Image preprocessing failed: {e}")
        return image  # Return original if preprocessing fails

def extract_text_from_word(file_path: str) -> str:
    """Extract text from Microsoft Word documents (no change, keeping existing logic)."""
    try:
        # For .docx files
        if file_path.endswith('.docx'):
            # First try with python-docx
            try:
                import docx
                doc = docx.Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs if para.text])
                # If we got meaningful text, return it
                if text and len(text.strip()) > 10:
                    return text
                # Otherwise, fall back to docx2txt which sometimes works better
                print(f"python-docx extracted minimal text, trying docx2txt for {file_path}")
            except Exception as e:
                print(f"python-docx failed: {e}, trying docx2txt for {file_path}")
            
            # Try with docx2txt as a fallback for .docx files too
            try:
                import docx2txt
                text = docx2txt.process(file_path)
                return text
            except Exception as e:
                print(f"docx2txt failed for .docx file: {e}")
                return ""
            
        # For .doc files (older format)
        elif file_path.endswith('.doc'):
            try:
                import docx2txt
                text = docx2txt.process(file_path)
                return text
            except Exception as e:
                print(f"docx2txt failed for .doc file: {e}")
                return ""
                
    except Exception as e:
        print(f"Word extraction completely failed: {e}")
        return ""

def extract_text_from_rtf(file_path: str) -> str:
    """Extract text from RTF files (keeping existing logic but return empty string on failure)."""
    try:
        from striprtf.striprtf import rtf_to_text
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            rtf = f.read()
            text = rtf_to_text(rtf)
            return text
    except UnicodeDecodeError:
        # If UTF-8 fails, try with latin-1 which is more permissive
        try:
            with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
                rtf = f.read()
                text = rtf_to_text(rtf)
                return text
        except Exception as e:
            print(f"RTF extraction failed with latin-1 encoding: {e}")
            return ""
    except ImportError:
        print("striprtf not available for RTF extraction")
        return ""
    except Exception as e:
        print(f"RTF extraction failed: {e}")
        return ""

def get_comment_detail(comment_id: str, api_key: str, download_attachments: bool = True, attachments_dir: Optional[str] = None) -> Dict:
    """
    Fetch full detail for a single comment, including all types of attachments.
    Enhanced to handle and extract text from various file formats.
    """
    url = f"https://api.regulations.gov/v4/comments/{comment_id}?include=attachments"
    response = requests.get(url, headers=get_headers(api_key))
    response.raise_for_status()
    
    data = response.json()
    comment_data = data["data"]
    
    # Handle attachments if included
    if download_attachments and "included" in data:
        attachments = [item for item in data["included"] if item["type"] == "attachments"]
        
        if attachments:
            # Create attachments directory for this comment if it doesn't exist
            if not attachments_dir:
                attachments_dir = os.path.join(os.getcwd(), "attachments", comment_id)
            else:
                # Make sure we have a comment-specific subdirectory
                attachments_dir = os.path.join(attachments_dir, comment_id)
            
            # Create the directory
            os.makedirs(attachments_dir, exist_ok=True)
        
        # Process each attachment
        attachment_texts = []
        for attachment in attachments:
            try:
                # Get attachment details
                attachment_id = attachment["id"]
                attachment_title = attachment.get("attributes", {}).get("title", "Untitled")
                attachment_format = attachment.get("attributes", {}).get("fileFormats", [{}])[0]
                
                # Get download URL
                format_url = attachment_format.get("fileUrl", "")
                if not format_url:
                    print(f"No download URL for attachment {attachment_id}")
                    continue
                
                # Determine file extension from URL
                from urllib.parse import urlparse
                parsed_url = urlparse(format_url)
                filename = os.path.basename(parsed_url.path)
                
                # If no filename found, try to get it from content-disposition
                if not filename or filename == '':
                    filename = f"{attachment_id}_{int(time.time())}"
                
                # Get MIME type and set appropriate extension if missing
                content_type = attachment_format.get("format", "")
                mime_type = get_mime_type(format_url, filename)
                
                # Add extension if missing
                name, ext = os.path.splitext(filename)
                if not ext:
                    # Map MIME types to extensions
                    ext_map = {
                        'application/pdf': '.pdf',
                        'application/msword': '.doc',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                        'application/vnd.ms-excel': '.xls',
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
                        'application/vnd.ms-powerpoint': '.ppt',
                        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
                        'text/plain': '.txt',
                        'application/rtf': '.rtf',
                        'text/csv': '.csv',
                        'text/html': '.html'
                    }
                    ext = ext_map.get(mime_type, '.bin')
                    filename = f"{name}{ext}"
                
                # Create safe filename
                safe_title = "".join(c for c in attachment_title if c.isalnum() or c in " ._-").strip()
                safe_title = safe_title[:50]  # Limit length
                output_path = os.path.join(attachments_dir, f"{attachment_id}_{safe_title}{ext}")
                
                # Download the attachment
                print(f"Downloading attachment: {filename}")
                downloaded_path = download_attachment_with_retry(format_url, attachments_dir)
                
                if downloaded_path:
                    # Extract text from the file based on its type
                    print(f"Extracting text from {os.path.basename(downloaded_path)}")
                    try:
                        raw_text = extract_text_from_file(downloaded_path)
                        text_ok = is_coherent_english_text(raw_text) if raw_text else False

                        if raw_text and text_ok:
                            attachment_texts.append({
                            "id": attachment_id,
                            "title": attachment_title,
                            "text": raw_text,
                            "file_path": downloaded_path,
                            "mime_type": mime_type
                                })
                        else:
                            print(f"Skipping incoherent or empty text for attachment: {attachment_title}")

                    except Exception as e:
                        print(f"Error extracting text from {filename}: {e}")
                        attachment_texts.append({
                            "id": attachment_id,
                            "title": attachment_title,
                            "text": f"[TEXT EXTRACTION FAILED: {str(e)}]",
                            "file_path": downloaded_path,
                            "mime_type": mime_type
                        })
            except Exception as e:
                print(f"Error processing attachment {attachment.get('id', 'unknown')}: {e}")
        
        # Add attachment texts to the comment data
        if attachment_texts:
            # Add attachments to the comment data
            if "attributes" not in comment_data:
                comment_data["attributes"] = {}
            comment_data["attributes"]["attachment_texts"] = attachment_texts
    
    return comment_data

def get_all_comment_details(comment_ids: List[str], api_key: str, download_attachments: bool = True, 
                          attachments_base_dir: Optional[str] = None, checkpoint_file: Optional[str] = None, 
                          resume: bool = False) -> List[Dict]:
    """Enhanced version of get_all_comment_details with better attachment handling."""
    # The implementation is the same as the original, but it uses our enhanced get_comment_detail function
    comments = []
    already_processed = set()
    total = len(comment_ids)
    
    # Set up attachments base directory
    if download_attachments:
        if attachments_base_dir is None:
            attachments_base_dir = os.path.join(os.getcwd(), "attachments")
        os.makedirs(attachments_base_dir, exist_ok=True)
    
    # Check if we should resume from a checkpoint
    if resume and checkpoint_file and os.path.exists(checkpoint_file):
        try:
            print(f"Resuming from checkpoint: {checkpoint_file}")
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
                comments = checkpoint_data.get('comments', [])
                already_processed = set(checkpoint_data.get('processed_ids', []))
                print(f"Loaded {len(comments)} comments from checkpoint")
                print(f"Skipping {len(already_processed)} already processed comment IDs")
        except Exception as e:
            print(f"Error loading checkpoint, starting from beginning: {e}")
            comments = []
            already_processed = set()
    
    # Filter out already processed comments
    comment_ids_to_process = [cid for cid in comment_ids if cid not in already_processed]
    
    # Create progress bar
    pbar = tqdm(total=len(comment_ids_to_process), desc="Fetching comment details")
    
    for i, comment_id in enumerate(comment_ids_to_process, 1):
        try:
            # Set up an attachments directory for this comment
            if download_attachments:
                attachments_dir = os.path.join(attachments_base_dir, comment_id)
            else:
                attachments_dir = None
                
            # Get the comment details with attachments
            comment = get_comment_detail(
                comment_id, 
                api_key, 
                download_attachments=download_attachments,
                attachments_dir=attachments_dir
            )
            comments.append(comment)
            already_processed.add(comment_id)
            pbar.update(1)
            
            # Save checkpoint every 10 comments
            if checkpoint_file and i % 10 == 0:
                with open(checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'comments': comments,
                        'processed_ids': list(already_processed)
                    }, f)
                pbar.write(f"Checkpoint saved after processing {i} comments")
                
        except Exception as e:
            pbar.write(f"Failed to retrieve {comment_id}: {e}")
        
        # Add a retry mechanism for rate limiting
        if i % 50 == 0:
            pbar.write(f"Taking a short break after {i} requests...")
            time.sleep(2)  # Take a longer break every 50 requests
        else:
            time.sleep(0.3)  # Slightly longer delay between individual requests
    
    pbar.close()
    
    # Save final checkpoint
    if checkpoint_file:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump({
                'comments': comments,
                'processed_ids': list(already_processed)
            }, f)
        print(f"Final checkpoint saved with {len(comments)} comments")
    
    return comments

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
                output_path = os.path.join(comment_attachments_dir, filename)
                
                # Download the attachment using the existing function
                downloaded_path = download_attachment_with_retry(url, comment_attachments_dir)
                
                if downloaded_path:
                    # Update the attachment with local path
                    attachments[i]["localPath"] = downloaded_path
                    downloaded += 1
                    
                    # Extract text from any supported file type
                    try:
                        # Use the generic extraction function for all file types
                        attachment_text = extract_text_from_file(downloaded_path)
                        attachment_texts.append({
                            "id": f"{comment_id}_attachment_{i+1}",
                            "title": attachment_title or safe_title,
                            "text": attachment_text,
                            "file_path": downloaded_path,
                            "mime_type": get_mime_type(url, filename)
                        })
                    except Exception as e:
                        print(f"Error extracting text from {filename}: {e}")
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

def fetch_comments(document_id: str, output_dir: Optional[str] = None, limit: Optional[int] = None, 
                 api_key: Optional[str] = None, download_attachments: bool = True, resume: bool = False) -> str:
    """
    Enhanced function to fetch comments with better attachment handling.
    
    Args are the same as the original function, but uses our enhanced versions of underlying functions.
    """
    # Set default output directory
    if output_dir is None:
        # Check if we're being called by the pipeline
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if os.path.exists(os.path.join(project_root, "backend", "pipeline.py")):
            # Create a timestamped directory in the results folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(project_root, "results", f"results_{timestamp}")
        else:
            # Fallback to the original behavior
            output_dir = os.path.join(project_root, "results", "raw")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(output_dir, f"fetch_{timestamp}")
    
    # Create directory if needed
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Set up checkpoint file
    checkpoint_file = os.path.join(output_dir, "fetch_checkpoint.json")
    
    # Use API key from environment if not provided
    if api_key is None:
        api_key = os.environ.get("REGS_API_KEY")
        if not api_key:
            raise ValueError("API key not found. Please set REGS_API_KEY in your environment or .env file.")
    
    # Check for existing checkpoint file
    if resume and os.path.exists(checkpoint_file):
        # Check if we have a complete raw_data.json file
        if os.path.exists(os.path.join(output_dir, "raw_data.json")):
            print(f"Found completed raw_data.json in {output_dir}, skipping fetch")
            return os.path.join(output_dir, "raw_data.json")
            
        # Load the checkpoint to get saved state
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
            saved_state = checkpoint_data.get('saved_state', {})
            
            # Check if we've already fetched the object_id and comment_ids
            object_id = saved_state.get('object_id')
            comment_ids = saved_state.get('comment_ids', [])
            
            if object_id and comment_ids:
                print(f"Resuming fetch using existing object_id and {len(comment_ids)} comment_ids")
            else:
                # Get the object_id and comment_ids again
                print(f"Fetching objectId for document ID: {document_id}")
                object_id = get_object_id(document_id, api_key)
                
                limit_msg = f"up to {limit}" if limit else "all"
                print(f"Fetching {limit_msg} comment IDs...")
                comment_ids = get_comment_ids(object_id, api_key, limit=limit)
                
                # Save to checkpoint
                with open(checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'saved_state': {
                            'object_id': object_id,
                            'comment_ids': comment_ids
                        },
                        'comments': [],
                        'processed_ids': []
                    }, f)
    else:
        # Start fresh
        print(f"Fetching objectId for document ID: {document_id}")
        object_id = get_object_id(document_id, api_key)
        print(f"Using objectId: {object_id}")

        limit_msg = f"up to {limit}" if limit else "all"
        print(f"Fetching {limit_msg} comment IDs...")
        comment_ids = get_comment_ids(object_id, api_key, limit=limit)
        
        # Initialize checkpoint
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump({
                'saved_state': {
                    'object_id': object_id,
                    'comment_ids': comment_ids
                },
                'comments': [],
                'processed_ids': []
            }, f)

    # Set up attachments directory if downloading attachments
    if download_attachments:
        attachments_dir = os.path.join(output_dir, "attachments")
        print(f"Will download attachments to: {attachments_dir}")
    else:
        attachments_dir = None
        print("Attachment downloading is disabled")

    print(f"Fetching full comment details for {len(comment_ids)} comments...")
    full_comments = get_all_comment_details(
        comment_ids, 
        api_key, 
        download_attachments=download_attachments,
        attachments_base_dir=attachments_dir,
        checkpoint_file=checkpoint_file,
        resume=resume
    )

    print(f"Saving to JSON...")
    # Use raw_data.json name when run from pipeline
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if os.path.exists(os.path.join(project_root, "backend", "pipeline.py")) or \
       os.path.basename(os.path.dirname(output_dir)).startswith("results_"):
        filename = "raw_data.json"
    else:
        # Use original naming convention
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comments_{document_id}_{timestamp}.json"
    
    output_path = os.path.join(output_dir, filename)
    result_path = save_json(full_comments, output_path)
    
    # Clean up checkpoint file since we have successfully saved the output
    try:
        os.remove(checkpoint_file)
        print(f"Checkpoint file removed: {checkpoint_file}")
    except Exception as e:
        print(f"Failed to remove checkpoint file: {e}")
    
    return result_path


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
    import numpy as np
    
    print(f"Reading comments from CSV file: {csv_file_path}")
    
    # Read the CSV file normally to get the headers
    df = pd.read_csv(csv_file_path)
    
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

if __name__ == "__main__":
    exit(main())