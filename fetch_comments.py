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

def get_comment_detail(comment_id, api_key):
    """Fetch full detail for a single comment, including attachments."""
    url = f"https://api.regulations.gov/v4/comments/{comment_id}?include=attachments"
    response = requests.get(url, headers=get_headers(api_key))
    response.raise_for_status()
    return response.json()["data"]

def get_all_comment_details(comment_ids, api_key):
    """Retrieve full comment detail for a list of comment IDs."""
    comments = []
    total = len(comment_ids)
    
    # Create progress bar
    pbar = tqdm(total=total, desc="Fetching comment details")
    
    for i, comment_id in enumerate(comment_ids, 1):
        try:
            comment = get_comment_detail(comment_id, api_key)
            comments.append(comment)
            pbar.update(1)
        except Exception as e:
            pbar.write(f"Failed to retrieve {comment_id}: {e}")
        
        # Add a retry mechanism for rate limiting
        if i % 50 == 0:
            pbar.write(f"Taking a short break after {i} requests...")
            time.sleep(2)  # Take a longer break every 50 requests
        else:
            time.sleep(0.3)  # Slightly longer delay between individual requests
    
    pbar.close()
    return comments

def save_json(data, filename):
    """Save data to a JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(data)} comments to {filename}")
    return filename

def fetch_comments(document_id, output_dir=None, limit=None, api_key=None):
    """Main function to fetch comments and save to a JSON file."""
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
    
    # Use API key from environment if not provided
    if api_key is None:
        api_key = os.environ.get("REGS_API_KEY")
        if not api_key:
            raise ValueError("API key not found. Please set REGS_API_KEY in your environment or .env file.")
    
    print(f"Fetching objectId for document ID: {document_id}")
    object_id = get_object_id(document_id, api_key)
    print(f"Using objectId: {object_id}")

    limit_msg = f"up to {limit}" if limit else "all"
    print(f"Fetching {limit_msg} comment IDs...")
    comment_ids = get_comment_ids(object_id, api_key, limit=limit)

    print(f"Fetching full comment details for {len(comment_ids)} comments...")
    full_comments = get_all_comment_details(comment_ids, api_key)

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
    return save_json(full_comments, output_path)

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
    
    args = parser.parse_args()
    
    try:
        result_path = fetch_comments(
            document_id=args.document_id,
            output_dir=args.output_dir,
            limit=args.limit,
            api_key=args.api_key
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