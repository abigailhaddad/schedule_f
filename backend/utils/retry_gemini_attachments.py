#!/usr/bin/env python3
"""
Retry Gemini text extraction for attachments that failed or have minimal text.
Updates the lookup table and triggers re-analysis and re-clustering if successful.
"""

import json
import os
import time
import base64
import argparse
import logging
import signal
from pathlib import Path
from typing import List, Dict, Set, Tuple
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for graceful shutdown
shutdown_requested = False
current_stats = {"processed": 0, "failed": 0, "skipped": 0}

def signal_handler(signum, frame):
    """Handle graceful shutdown on SIGINT."""
    global shutdown_requested
    logger.info("🛑 Shutdown requested, finishing current batch...")
    shutdown_requested = True

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

def is_text_minimal(text: str, threshold: int = 100) -> bool:
    """Check if extracted text is minimal."""
    if not text:
        return True
    cleaned = text.strip()
    return len(cleaned) < threshold

def find_failed_attachments(results_dir: str) -> List[Dict]:
    """Find attachments with minimal or no text extraction."""
    attachments_dir = os.path.join(results_dir, "attachments")
    failed_attachments = []
    
    if not os.path.exists(attachments_dir):
        logger.error(f"Attachments directory not found: {attachments_dir}")
        return []
    
    # Scan all attachment directories
    for comment_dir in os.listdir(attachments_dir):
        comment_path = os.path.join(attachments_dir, comment_dir)
        if not os.path.isdir(comment_path):
            continue
            
        # Check each attachment
        for filename in os.listdir(comment_path):
            if filename.endswith('.extracted.txt'):
                continue  # Skip extracted text files
                
            file_path = os.path.join(comment_path, filename)
            extracted_path = file_path + '.extracted.txt'
            
            # Check if it's an image or PDF that needs text extraction
            ext = filename.lower().split('.')[-1]
            if ext not in ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp']:
                continue
            
            # Check if extraction exists and has meaningful content
            needs_extraction = False
            existing_text = ""
            
            if os.path.exists(extracted_path):
                with open(extracted_path, 'r', encoding='utf-8') as f:
                    existing_text = f.read()
                if is_text_minimal(existing_text):
                    needs_extraction = True
            else:
                needs_extraction = True
            
            if needs_extraction:
                failed_attachments.append({
                    'comment_id': comment_dir,
                    'file_path': file_path,
                    'extracted_path': extracted_path,
                    'existing_text': existing_text,
                    'file_type': ext
                })
    
    return failed_attachments

def extract_text_with_gemini(file_path: str, max_retries: int = 2, timeout: int = 30) -> str:
    """Extract text from file using Gemini API with improved error handling and retries."""
    global current_stats
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")
    
    # Check file size (skip files > 5MB - more aggressive)
    file_size = os.path.getsize(file_path)
    if file_size > 5 * 1024 * 1024:  # 5MB limit
        logger.warning(f"Skipping large file {file_path} ({file_size / 1024 / 1024:.1f}MB)")
        current_stats["skipped"] += 1
        return "[FILE TOO LARGE - SKIPPED]"
    
    # Skip files with problematic extensions that often hang
    ext = file_path.lower().split('.')[-1]
    problematic_extensions = {'exe', 'zip', 'rar', 'tar', 'gz', 'bin', 'iso'}
    if ext in problematic_extensions:
        logger.warning(f"Skipping problematic file type: {file_path}")
        current_stats["skipped"] += 1
        return "[PROBLEMATIC FILE TYPE - SKIPPED]"
    
    logger.debug(f"Processing {file_path} ({file_size / 1024:.1f}KB)")
    
    # Read file and encode to base64
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        current_stats["failed"] += 1
        return "[FILE READ ERROR]"
    
    base64_data = base64.b64encode(file_data).decode('utf-8')
    
    # Determine MIME type
    ext = file_path.lower().split('.')[-1]
    mime_types = {
        'pdf': 'application/pdf',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'bmp': 'image/bmp'
    }
    mime_type = mime_types.get(ext, 'application/octet-stream')
    
    # Prepare Gemini API request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}"
    
    payload = {
        "contents": [{
            "parts": [
                {
                    "text": "Extract all text from this document. For images, perform OCR. For PDFs, extract all text content. Return only the extracted text without any formatting or explanation."
                },
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": base64_data
                    }
                }
            ]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192
        }
    }
    
    # Retry logic with exponential backoff
    for attempt in range(max_retries):
        if shutdown_requested:
            logger.info("Shutdown requested, aborting extraction")
            return "[EXTRACTION ABORTED]"
            
        try:
            logger.debug(f"Attempt {attempt + 1}/{max_retries} for {os.path.basename(file_path)}")
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text']
            current_stats["processed"] += 1
            logger.debug(f"✅ Successfully extracted {len(text)} chars from {os.path.basename(file_path)}")
            return text.strip()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Rate limited - shorter backoff, fail faster
                wait_time = min(15, (2 ** attempt) * 3)  # 3s, 6s, max 15s
                logger.warning(f"Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            elif e.response.status_code in [500, 502, 503, 504]:
                # Server error - fail faster
                logger.warning(f"Server error {e.response.status_code}, skipping file")
                break  # Don't retry on server errors, just skip
            else:
                logger.error(f"Gemini API error {e.response.status_code}: {e.response.text}")
                break
                
        except requests.exceptions.Timeout:
            logger.warning(f"⏰ Timeout after {timeout}s for {os.path.basename(file_path)} - SKIPPING")
            break  # Don't retry timeouts, just skip the file
            
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error: {e} - SKIPPING")
            break  # Don't retry connection errors, just skip
            
        except Exception as e:
            logger.error(f"Unexpected error extracting text from {file_path}: {e}")
            break
    
    # If we get here, all retries failed
    current_stats["failed"] += 1
    logger.error(f"❌ Failed to extract text from {file_path} after {max_retries} attempts")
    return "[EXTRACTION FAILED]"

def update_lookup_table(results_dir: str, updated_comments: Set[str]) -> bool:
    """Update lookup table entries for comments with newly extracted attachment text."""
    if not updated_comments:
        return False
        
    lookup_path = os.path.join(results_dir, "lookup_table.json")
    raw_data_path = os.path.join(results_dir, "raw_data.json")
    
    if not os.path.exists(lookup_path) or not os.path.exists(raw_data_path):
        logger.error("Lookup table or raw data not found")
        return False
    
    # Load data
    with open(lookup_path, 'r') as f:
        lookup_table = json.load(f)
    
    with open(raw_data_path, 'r') as f:
        raw_data = json.load(f)
    
    # Create comment ID to raw data mapping
    raw_data_map = {comment['id']: comment for comment in raw_data}
    
    # Track which lookup entries need updating
    updated_lookup_ids = set()
    
    # Update lookup table entries
    for entry in lookup_table:
        needs_update = False
        
        # Check if any of the comments this entry represents were updated
        for comment_id in entry['comment_ids']:
            if comment_id in updated_comments:
                needs_update = True
                break
        
        if needs_update:
            # Reconstruct the combined text for this lookup entry
            combined_texts = []
            
            for comment_id in entry['comment_ids']:
                if comment_id in raw_data_map:
                    comment = raw_data_map[comment_id]
                    
                    # Get comment text
                    comment_text = comment['attributes'].get('comment', '')
                    if comment_text:
                        combined_texts.append(comment_text)
                    
                    # Get attachment text
                    attachments_dir = os.path.join(results_dir, "attachments", comment_id)
                    if os.path.exists(attachments_dir):
                        for filename in sorted(os.listdir(attachments_dir)):
                            if filename.endswith('.extracted.txt'):
                                extracted_path = os.path.join(attachments_dir, filename)
                                with open(extracted_path, 'r', encoding='utf-8') as f:
                                    attachment_text = f.read().strip()
                                    if attachment_text:
                                        combined_texts.append(attachment_text)
            
            # Update the truncated text
            new_combined_text = '\n\n'.join(combined_texts)
            truncate_length = 1000  # Default truncation length
            
            if len(new_combined_text) > truncate_length:
                entry['truncated_text'] = new_combined_text[:truncate_length]
            else:
                entry['truncated_text'] = new_combined_text
            
            # Determine text source
            has_comment = any(raw_data_map[cid]['attributes'].get('comment', '') 
                            for cid in entry['comment_ids'] if cid in raw_data_map)
            has_attachment = any(
                os.path.exists(os.path.join(results_dir, "attachments", cid))
                for cid in entry['comment_ids']
            )
            
            if has_comment and has_attachment:
                entry['text_source'] = 'both'
            elif has_attachment:
                entry['text_source'] = 'attachment'
            else:
                entry['text_source'] = 'comment'
            
            updated_lookup_ids.add(entry['lookup_id'])
    
    # Save updated lookup table
    with open(lookup_path, 'w') as f:
        json.dump(lookup_table, f, indent=2)
    
    logger.info(f"Updated {len(updated_lookup_ids)} lookup table entries")
    return len(updated_lookup_ids) > 0

def trigger_reanalysis(results_dir: str, updated_lookup_ids: Set[str]) -> bool:
    """Trigger LLM analysis for updated lookup entries."""
    # This would need to be implemented based on your analysis pipeline
    # For now, we'll just log what would happen
    logger.info(f"Would trigger re-analysis for {len(updated_lookup_ids)} lookup entries")
    return True

def process_attachments_in_batches(failed_attachments: List[Dict], batch_size: int = 5, delay: float = 2.0) -> Tuple[List[Dict], Dict]:
    """Process attachments in small batches with progress tracking and graceful shutdown."""
    global shutdown_requested, current_stats
    
    # Reset stats
    current_stats = {"processed": 0, "failed": 0, "skipped": 0}
    
    total_attachments = len(failed_attachments)
    successfully_processed = []
    
    logger.info(f"🔄 Processing {total_attachments} attachments in batches of {batch_size}")
    logger.info(f"⏱️  Delay between batches: {delay}s")
    logger.info("💡 Press Ctrl+C to gracefully stop after current batch")
    
    for i in range(0, total_attachments, batch_size):
        if shutdown_requested:
            logger.info(f"🛑 Shutdown requested. Processed {current_stats['processed']}/{total_attachments} attachments")
            break
            
        batch = failed_attachments[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_attachments + batch_size - 1) // batch_size
        
        logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} attachments)")
        
        # Process batch
        for j, attachment in enumerate(batch):
            if shutdown_requested:
                break
                
            file_path = attachment['file_path']
            logger.info(f"  📄 [{i+j+1}/{total_attachments}] {os.path.basename(file_path)}")
            
            try:
                # Extract text with timeout
                extracted_text = extract_text_with_gemini(file_path, max_retries=2, timeout=90)
                
                if extracted_text and not extracted_text.startswith('['):  # Not an error message
                    # Save extracted text
                    extracted_path = file_path + '.extracted.txt'
                    with open(extracted_path, 'w', encoding='utf-8') as f:
                        f.write(extracted_text)
                    
                    attachment['extracted_text'] = extracted_text
                    attachment['extraction_status'] = 'success'
                    successfully_processed.append(attachment)
                    logger.info(f"    ✅ Extracted {len(extracted_text)} characters")
                else:
                    attachment['extraction_status'] = 'failed'
                    logger.warning(f"    ❌ Extraction failed: {extracted_text}")
                    
            except Exception as e:
                current_stats["failed"] += 1
                attachment['extraction_status'] = 'error'
                attachment['error'] = str(e)
                logger.error(f"    💥 Error processing {os.path.basename(file_path)}: {e}")
        
        # Progress summary
        progress_pct = ((i + len(batch)) / total_attachments) * 100
        logger.info(f"📊 Progress: {progress_pct:.1f}% | ✅ {current_stats['processed']} | ❌ {current_stats['failed']} | ⏭️ {current_stats['skipped']}")
        
        # Delay between batches (except last batch)
        if i + batch_size < total_attachments and not shutdown_requested:
            logger.info(f"⏸️  Waiting {delay}s before next batch...")
            time.sleep(delay)
    
    # Final summary
    logger.info(f"🏁 Processing complete!")
    logger.info(f"   📊 Total processed: {current_stats['processed']}")
    logger.info(f"   ✅ Successful: {len(successfully_processed)}")
    logger.info(f"   ❌ Failed: {current_stats['failed']}")
    logger.info(f"   ⏭️  Skipped: {current_stats['skipped']}")
    
    return successfully_processed, current_stats

def main():
    parser = argparse.ArgumentParser(description='Retry Gemini extraction for failed attachments')
    parser.add_argument('results_dir', help='Path to results directory')
    parser.add_argument('--max-retries', type=int, default=100,
                       help='Maximum number of attachments to retry (default: 100)')
    parser.add_argument('--delay', type=float, default=2.0,
                       help='Delay between batches in seconds (default: 2.0)')
    parser.add_argument('--batch-size', type=int, default=5,
                       help='Number of attachments to process per batch (default: 5)')
    parser.add_argument('--threshold', type=int, default=100,
                       help='Minimum text length threshold (default: 100)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.results_dir):
        logger.error(f"Results directory not found: {args.results_dir}")
        return 1
    
    # Find attachments that need retry
    logger.info(f"Scanning for failed attachments in {args.results_dir}")
    failed_attachments = find_failed_attachments(args.results_dir)
    
    if not failed_attachments:
        logger.info("No failed attachments found!")
        return 0
    
    logger.info(f"Found {len(failed_attachments)} attachments needing text extraction")
    
    # Limit retries
    if len(failed_attachments) > args.max_retries:
        logger.info(f"Limiting to first {args.max_retries} attachments")
        failed_attachments = failed_attachments[:args.max_retries]
    
    # Process attachments in batches
    successfully_processed, stats = process_attachments_in_batches(
        failed_attachments, 
        batch_size=args.batch_size, 
        delay=args.delay
    )
    
    # Collect updated comment IDs
    updated_comments = set()
    for attachment in successfully_processed:
        updated_comments.add(attachment['comment_id'])
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Extraction complete: {len(successfully_processed)}/{len(failed_attachments)} successful")
    
    if len(successfully_processed) == 0:
        logger.info("No successful extractions, skipping updates")
        return 0
    
    # Update lookup table
    logger.info(f"\nUpdating lookup table for {len(updated_comments)} comments...")
    if update_lookup_table(args.results_dir, updated_comments):
        logger.info("✅ Lookup table updated successfully")
        
        # Save list of updated comments for potential re-analysis
        updated_file = os.path.join(args.results_dir, "gemini_retry_updated.json")
        with open(updated_file, 'w') as f:
            json.dump({
                'updated_comments': list(updated_comments),
                'extraction_count': len(successfully_processed),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'stats': stats
            }, f, indent=2)
        
        logger.info(f"💾 Saved update info to {updated_file}")
        logger.info("\n🔄 Next steps:")
        logger.info("  1. Run analysis on updated entries")
        logger.info("  2. Re-run clustering if needed")
    
    return 0

if __name__ == "__main__":
    exit(main())