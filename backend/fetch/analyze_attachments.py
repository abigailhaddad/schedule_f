#!/usr/bin/env python3
"""
Analyze attachment text extraction from a results folder.
This script:
1. Extracts text from supported file types locally (PDF, DOCX, TXT)
2. Identifies attachments with minimal text
3. Re-extracts those using Gemini
4. Updates in-memory text map with Gemini results
"""

import os
import json
import base64
import argparse
import requests
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
from PyPDF2 import PdfReader
import docx

# Load environment variables
load_dotenv()

def extract_text_local(file_path):
    ext = file_path.lower().split('.')[-1]
    try:
        if ext == 'pdf':
            reader = PdfReader(file_path)
            return "\n".join(page.extract_text() or '' for page in reader.pages)
        elif ext == 'docx':
            doc = docx.Document(file_path)
            return "\n".join(para.text for para in doc.paragraphs)
        elif ext == 'txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        else:
            return ""
    except Exception as e:
        print(f"  → Local extraction failed for {file_path}: {e}")
        return ""

def extract_text_with_gemini(file_path, max_retries=5, base_delay=2.0, max_delay=60.0, interactive=False):
    """
    Extract text from file using Gemini API with exponential backoff retry logic.
    
    Args:
        file_path: Path to the file to extract text from
        max_retries: Maximum number of retry attempts (default: 5)
        base_delay: Base delay between retries in seconds (default: 2.0)
        max_delay: Maximum delay between retries in seconds (default: 60.0)
        interactive: Whether to prompt user for action after all retries fail (default: False)
    
    Returns:
        str: Extracted text from the file, or empty string if user chooses to skip
        
    Raises:
        ValueError: If GEMINI_API_KEY is not found
        RuntimeError: If all retry attempts fail and user chooses to abort
    """
    import time
    import random
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")

    # Check file size (Gemini has limits)
    file_size = os.path.getsize(file_path)
    if file_size > 10 * 1024 * 1024:  # 10MB limit
        raise RuntimeError(f"File too large for Gemini API: {file_size} bytes")

    # Read and encode file
    try:
        with open(file_path, "rb") as f:
            encoded_data = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"Failed to read file {file_path}: {e}")

    # Determine MIME type based on extension
    ext = file_path.lower().split('.')[-1]
    mime_types = {
        'pdf': 'application/pdf',
        'png': 'image/png', 
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'bmp': 'image/bmp',
        'tiff': 'image/tiff',
        'webp': 'image/webp'
    }
    mime_type = mime_types.get(ext, 'application/pdf')  # Default to PDF

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={gemini_api_key}"
    headers = {"Content-Type": "application/json"}

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": encoded_data
                        }
                    },
                    {
                        "text": "Extract all the text from this document. Return only the raw text content, including any tables, headers, footers, and all readable text. Do not include any explanations or formatting descriptions."
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,  # Lower temperature for more consistent extraction
            "maxOutputTokens": 8192  # Increase token limit for longer documents
        }
    }

    last_error = None
    
    for attempt in range(max_retries):
        try:
            print(f"  → Gemini attempt {attempt + 1}/{max_retries} for {os.path.basename(file_path)}")
            
            # Make the API call with timeout
            response = requests.post(url, headers=headers, json=data, timeout=120)
            
            if response.ok:
                response_json = response.json()
                
                # Extract text from response
                for candidate in response_json.get("candidates", []):
                    for part in candidate.get("content", {}).get("parts", []):
                        if "text" in part:
                            extracted_text = part["text"].strip()
                            if extracted_text:  # Make sure we got actual text
                                print(f"  → ✅ Gemini extracted {len(extracted_text)} chars")
                                return extracted_text
                
                # If we get here, response was OK but no text found
                last_error = RuntimeError("Gemini returned successful response but no text content")
                
            else:
                # API returned an error
                error_msg = f"Gemini API error {response.status_code}: {response.text[:500]}"
                last_error = RuntimeError(error_msg)
                
                # Check if this is a rate limit error (429) or server error (5xx)
                if response.status_code == 429:
                    print(f"  → ⏳ Rate limited, will retry...")
                elif 500 <= response.status_code < 600:
                    print(f"  → 🔧 Server error {response.status_code}, will retry...")
                elif 400 <= response.status_code < 500:
                    # Client errors (except rate limit) are usually not retryable
                    print(f"  → ❌ Client error {response.status_code}, will retry anyway...")
                else:
                    print(f"  → ❓ Unexpected status {response.status_code}, will retry...")
                    
        except requests.exceptions.Timeout:
            last_error = RuntimeError("Request timed out after 120 seconds")
            print(f"  → ⏰ Request timeout, will retry...")
            
        except requests.exceptions.ConnectionError:
            last_error = RuntimeError("Connection error")
            print(f"  → 🌐 Connection error, will retry...")
            
        except Exception as e:
            last_error = RuntimeError(f"Unexpected error: {str(e)}")
            print(f"  → 💥 Unexpected error: {e}, will retry...")
        
        # If this wasn't the last attempt, wait before retrying
        if attempt < max_retries - 1:
            # Exponential backoff with jitter
            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
            print(f"  → ⏸️  Waiting {delay:.1f}s before retry...")
            time.sleep(delay)
    
    # If we get here, all retries failed
    error_msg = f"Failed to extract text from {file_path} after {max_retries} attempts. Last error: {last_error}"
    print(f"  → ❌ {error_msg}")
    
    # If interactive mode, ask user what to do
    if interactive:
        print(f"\n🚨 Gemini extraction failed for {os.path.basename(file_path)} after {max_retries} attempts")
        print("Options:")
        print("1. Try again (retry with same settings)")
        print("2. Skip this file (continue without this content)")
        print("3. Abort pipeline (recommended - fix issues and retry)")
        
        while True:
            choice = input("Enter choice (1, 2, or 3): ").strip()
            if choice == "1":
                # Recursive call to try again
                print("  → Retrying extraction...")
                return extract_text_with_gemini(file_path, max_retries, base_delay, max_delay, interactive)
            elif choice == "2":
                print("  → ⚠️  Skipping file - content will be LOST")
                return ""  # Return empty string to skip
            elif choice == "3":
                print("  → 🛑 User chose to abort")
                raise RuntimeError(f"User aborted due to extraction failure: {error_msg}")
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
    else:
        # Non-interactive mode - just raise the error
        raise RuntimeError(error_msg)

def analyze_attachment_extraction(results_dir, abort_on_failures=True, interactive=False):
    attachments_dir = Path(results_dir).rglob('*.*')
    attachment_texts_map = {}
    files_with_minimal_text = []
    extracted_by_type = defaultdict(lambda: {'total': 0, 'with_text': 0, 'text_length': 0})

    print(f"Analyzing files in: {results_dir}")
    for path in attachments_dir:
        if path.is_file():
            file_path = str(path)
            ext = path.suffix[1:].lower()
            text = extract_text_local(file_path)
            text_length = len(text.strip())

            if text_length < 50:
                files_with_minimal_text.append(file_path)
            else:
                extracted_by_type[ext]['with_text'] += 1
                extracted_by_type[ext]['text_length'] += text_length

            extracted_by_type[ext]['total'] += 1
            attachment_texts_map[file_path] = text

    print(f"\nFiles needing Gemini re-extraction: {len(files_with_minimal_text)}")
    gemini_failures = []
    
    for file_path in files_with_minimal_text:
        try:
            new_text = extract_text_with_gemini(file_path, max_retries=5, interactive=interactive)
            attachment_texts_map[file_path] = new_text
            if new_text.strip():  # Only log if we got text (not skipped)
                print(f"  → {os.path.basename(file_path)}: extracted {len(new_text.strip())} chars from Gemini")
                # Update file type stats after Gemini extraction
                ext = Path(file_path).suffix[1:].lower()
                if len(new_text.strip()) >= 50:
                    extracted_by_type[ext]['with_text'] += 1
                    extracted_by_type[ext]['text_length'] += len(new_text.strip())
            else:
                print(f"  → {os.path.basename(file_path)}: skipped (user choice)")
        except Exception as e:
            gemini_failures.append((file_path, str(e)))
            print(f"  → ❌ CRITICAL: Gemini extraction failed for {file_path}: {e}")
    
    # Report and handle failures
    if gemini_failures:
        print(f"\n🚨 GEMINI EXTRACTION FAILURES: {len(gemini_failures)}")
        print("The following files could not be processed and their content will be LOST:")
        for file_path, error in gemini_failures:
            print(f"  ❌ {file_path}")
            print(f"     Error: {error}")
        
        if interactive:
            # Ask user how to proceed
            print(f"\nOptions:")
            print(f"1. Continue anyway (LOSE content from {len(gemini_failures)} files)")
            print(f"2. Abort pipeline (recommended - fix issues and retry)")
            choice = input("Enter choice (1 or 2): ").strip()
            
            if choice != "1":
                abort_on_failures = True
        
        if abort_on_failures:
            print("🛑 Aborting pipeline to preserve data integrity.")
            print("Please check:")
            print("  - GEMINI_API_KEY is correctly set")
            print("  - Internet connection is stable") 
            print("  - Gemini API quota is not exceeded")
            print("  - Files are not corrupted")
            print(f"To continue anyway, use: analyze_attachments.py --results_dir {results_dir} --continue-on-failures")
            raise RuntimeError(f"Pipeline aborted due to {len(gemini_failures)} Gemini extraction failures")
        else:
            print(f"⚠️  CONTINUING with {len(gemini_failures)} files LOST. Data will be incomplete!")

    # Save extracted text to .txt files alongside attachments
    print("\nSaving extracted text to files...")
    saved_count = 0
    for file_path, text in attachment_texts_map.items():
        if text.strip():  # Only save non-empty text
            text_file_path = Path(file_path).with_suffix('.extracted.txt')
            try:
                with open(text_file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                saved_count += 1
            except Exception as e:
                print(f"  → Failed to save text for {file_path}: {e}")
    
    print(f"✅ Saved {saved_count} extracted text files")

    print("\nExtraction complete. Summary:")
    for ext, stats in sorted(extracted_by_type.items(), key=lambda x: x[1]['total'], reverse=True):
        success_rate = (stats['with_text'] / stats['total'] * 100) if stats['total'] else 0
        avg_len = int(stats['text_length'] / stats['with_text']) if stats['with_text'] else 0
        print(f"{ext}: {stats['with_text']}/{stats['total']} ({success_rate:.1f}%) - Avg length: {avg_len} chars")
    
    return attachment_texts_map

def main():
    parser = argparse.ArgumentParser(description='Analyze and extract attachment text using local methods and Gemini fallback')
    parser.add_argument('--results_dir', type=str, required=True, help='Path to the results directory')
    parser.add_argument('--continue-on-failures', action='store_true', 
                       help='Continue processing even if Gemini extraction fails (NOT recommended - will lose data)')
    parser.add_argument('--interactive', action='store_true',
                       help='Ask user how to handle failures interactively')
    args = parser.parse_args()

    abort_on_failures = not args.continue_on_failures
    attachment_texts_map = analyze_attachment_extraction(
        args.results_dir, 
        abort_on_failures=abort_on_failures,
        interactive=args.interactive
    )
    return 0

if __name__ == "__main__":
    exit(main())
