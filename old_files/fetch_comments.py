#!/usr/bin/env python3
"""
Comment Fetcher for Schedule F Proposal

This script fetches public comments on the proposed Schedule F rule from regulations.gov API.
It downloads comments and saves them to a JSON file.

Requirements:
- Python 3.8+
- requests
- tqdm
- python-dotenv

Quick usage:
1. Set REGS_API_KEY in environment or .env file
2. Run: python fetch_comments.py

For more options:
python fetch_comments.py --help
"""

import os
import json
import time
import argparse
import requests
from dotenv import load_dotenv
from tqdm import tqdm
from datetime import datetime
from pathlib import Path

# Load environment variables
load_dotenv()

def create_directory(directory_path):
    """Create a directory if it doesn't exist."""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Created directory: {directory_path}")
    return directory_path

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

def download_attachment(url, output_path, api_key):
    """Download an attachment file from the given URL."""
    try:
        # Make sure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Download the file
        response = requests.get(url, headers=get_headers(api_key), stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return output_path
    except Exception as e:
        print(f"Error downloading attachment: {e}")
        return None

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file using PyPDF2."""
    try:
        import PyPDF2
        
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                text += reader.pages[page_num].extract_text() + "\n"
        
        return text
    except ImportError:
        print("PyPDF2 not installed. Install it using: pip install PyPDF2")
        return "[PDF TEXT EXTRACTION FAILED - PyPDF2 not installed]"
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_path}: {e}")
        return f"[PDF TEXT EXTRACTION FAILED: {str(e)}]"

def get_comment_detail(comment_id, api_key, download_attachments=True, attachments_dir=None):
    """Fetch full detail for a single comment, including attachments."""
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
                
                # Determine file extension
                content_type = attachment_format.get("format", "")
                extension = ".pdf" if "pdf" in content_type.lower() else ".txt"
                
                # Create safe filename
                safe_title = "".join(c for c in attachment_title if c.isalnum() or c in " ._-").strip()
                safe_title = safe_title[:50]  # Limit length
                filename = f"{attachment_id}_{safe_title}{extension}"
                output_path = os.path.join(attachments_dir, filename)
                
                # Download the attachment
                print(f"Downloading attachment: {filename}")
                downloaded_path = download_attachment(format_url, output_path, api_key)
                
                # Extract text if it's a PDF and download was successful
                if downloaded_path and extension == ".pdf":
                    print(f"Extracting text from PDF: {filename}")
                    try:
                        attachment_text = extract_text_from_pdf(output_path)
                        attachment_texts.append({
                            "id": attachment_id,
                            "title": attachment_title,
                            "text": attachment_text,
                            "file_path": output_path
                        })
                    except Exception as e:
                        print(f"Error extracting text from PDF {filename}: {e}")
                        attachment_texts.append({
                            "id": attachment_id,
                            "title": attachment_title,
                            "text": f"[TEXT EXTRACTION FAILED: {str(e)}]",
                            "file_path": output_path
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

def get_all_comment_details(comment_ids, api_key, download_attachments=True, attachments_base_dir=None, 
                          checkpoint_file=None, resume=False):
    """Retrieve full comment detail for a list of comment IDs with checkpoint support."""
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

def save_json(data, filename):
    """Save data to a JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(data)} comments to {filename}")
    return filename

def fetch_comments(document_id, output_dir=None, limit=None, api_key=None, download_attachments=True, resume=False):
    """Main function to fetch comments and save to a JSON file with checkpoint support."""
    # Set default output directory
    if output_dir is None:
        # Check if we're being called by the pipeline
        if os.path.basename(os.getcwd()) == "regs" and (
            os.path.exists(os.path.join(os.getcwd(), "pipeline.py")) or 
            os.path.exists(os.path.join(os.getcwd(), "analyze_comments.py"))
        ):
            # Create a timestamped directory in the results folder when running standalone
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(os.getcwd(), "results", f"results_{timestamp}")
        else:
            # Fallback to the original behavior
            output_dir = os.path.join(os.getcwd(), "data", "raw")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(output_dir, f"fetch_{timestamp}")
    
    # Create directory if needed
    create_directory(output_dir)
    
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
    if os.path.exists(os.path.join(os.path.dirname(output_dir), "pipeline.py")) or \
       os.path.exists(os.path.join(os.path.dirname(output_dir), "analyze_comments.py")) or \
       os.path.basename(output_dir).startswith("results_"):
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

def main():
    """Parse arguments and run the script."""
    parser = argparse.ArgumentParser(description='Fetch comments from regulations.gov API')
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
    
    args = parser.parse_args()
    
    try:
        result_path = fetch_comments(
            document_id=args.document_id,
            output_dir=args.output_dir,
            limit=args.limit,
            api_key=args.api_key,
            download_attachments=not args.no_attachments,
            resume=args.resume
        )
        print(f"Successfully fetched comments. Output saved to: {result_path}")
    except Exception as e:
        print(f"Error fetching comments: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())