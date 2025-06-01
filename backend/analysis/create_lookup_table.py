#!/usr/bin/env python3
"""
Create Deduplicated Lookup Table

This script creates a deduplicated lookup table from raw_data.json.
It combines comment text with attachment text, truncates as needed,
and groups duplicate comments by normalized text content.

Usage:
python create_lookup_table.py [--input raw_data.json] [--output lookup_table.json] [--truncate 500]
"""

import json
import os
import argparse
import logging
from typing import List, Dict, Any, Optional
import re

# Import config constants
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.config import DEFAULT_RAW_DATA, DEFAULT_LOOKUP_TABLE

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def extract_and_combine_text(comment_data: Dict[str, Any], truncate_chars: Optional[int] = None) -> Dict[str, str]:
    """
    Extract comment text and attachment text, combine them, and optionally truncate.
    
    Args:
        comment_data: Raw comment data from raw_data.json
        truncate_chars: If specified, truncate combined text to this many characters
    
    Returns:
        Dict with 'full_text', 'truncated_text', and 'text_source'
    """
    try:
        # Extract basic comment info
        comment_id = comment_data.get('id', 'unknown')
        
        # Get comment text from attributes
        attributes = comment_data.get('attributes', {})
        comment_text = attributes.get('comment', '').strip()
        
        # Start with comment text
        full_text = comment_text
        text_sources = ['comment']
        
        # Add attachment text if available
        attachment_text = ""
        if 'attachment_texts' in attributes and attributes['attachment_texts']:
            # Combine all attachment texts
            attachment_parts = []
            for att in attributes['attachment_texts']:
                if isinstance(att, dict) and 'text' in att:
                    text = att['text'].strip()
                    if text:
                        attachment_parts.append(text)
            
            if attachment_parts:
                attachment_text = "\n\n--- NEXT ATTACHMENT ---\n\n".join(attachment_parts)
                
                if full_text:
                    full_text += f"\n\n--- ATTACHMENT CONTENT ---\n{attachment_text}"
                else:
                    full_text = attachment_text
                text_sources.append('attachments')
        
        # Create truncated version if needed
        if truncate_chars and len(full_text) > truncate_chars:
            truncated_text = full_text[:truncate_chars].strip()
            # Try to end at a word boundary
            if ' ' in truncated_text:
                last_space = truncated_text.rfind(' ')
                if last_space > truncate_chars * 0.8:  # Don't truncate too aggressively
                    truncated_text = truncated_text[:last_space]
            truncated_text += "..."
        else:
            truncated_text = full_text
        
        return {
            'full_text': full_text,
            'truncated_text': truncated_text,
            'text_source': '+'.join(text_sources),
            'comment_text': comment_text,
            'attachment_text': attachment_text
        }
        
    except Exception as e:
        logger.error(f"Error extracting text from comment {comment_data.get('id', 'unknown')}: {e}")
        return {
            'full_text': '',
            'truncated_text': '',
            'text_source': 'error',
            'comment_text': '',
            'attachment_text': ''
        }

def normalize_text_for_dedup(text: str) -> str:
    """
    Normalize text for duplicate detection.
    
    Args:
        text: Text to normalize
    
    Returns:
        Normalized text for comparison
    """
    if not text:
        return ""
    
    # Convert to lowercase and strip whitespace
    normalized = text.lower().strip()
    
    # Remove extra whitespace (multiple spaces, newlines, tabs)
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Remove common formatting that might vary
    normalized = re.sub(r'[""''""„"«»]', '"', normalized)  # Normalize quotes
    normalized = re.sub(r'[—–−]', '-', normalized)  # Normalize dashes
    
    return normalized

def create_lookup_table(raw_data: List[Dict[str, Any]], truncate_chars: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Create deduplicated lookup table from raw comment data.
    
    Args:
        raw_data: List of comment data from raw_data.json
        truncate_chars: If specified, truncate text to this many characters
    
    Returns:
        List of lookup table entries
    """
    logger.info(f"Creating lookup table from {len(raw_data)} comments...")
    if truncate_chars:
        logger.info(f"Truncating text to {truncate_chars} characters")
    
    # Dictionary to group comments by normalized text
    text_groups: Dict[str, Dict[str, Any]] = {}
    
    for i, comment_data in enumerate(raw_data):
        try:
            comment_id = comment_data.get('id', f'unknown_{i}')
            
            # Extract and combine text
            text_result = extract_and_combine_text(comment_data, truncate_chars)
            full_text = text_result['full_text']
            truncated_text = text_result['truncated_text']
            text_source = text_result['text_source']
            
            # Skip empty comments
            if not truncated_text.strip():
                logger.warning(f"Comment {comment_id} has empty text after processing")
                continue
            
            # Normalize for duplicate detection
            normalized_text = normalize_text_for_dedup(truncated_text)
            
            if not normalized_text:
                logger.warning(f"Comment {comment_id} has empty normalized text")
                continue
            
            # Group comments by normalized text
            if normalized_text not in text_groups:
                text_groups[normalized_text] = {
                    'truncated_text': truncated_text,  # Keep the original case/formatting
                    'text_source': text_source,
                    'comment_text': text_result['comment_text'],
                    'attachment_text': text_result['attachment_text'],
                    'comment_ids': [],
                    'full_text_length': len(full_text),
                    'truncated_text_length': len(truncated_text)
                }
            
            text_groups[normalized_text]['comment_ids'].append(comment_id)
            
        except Exception as e:
            logger.error(f"Error processing comment {i}: {e}")
            continue
    
    # Convert to lookup table format
    lookup_table = []
    lookup_id_counter = 1
    
    for normalized_text, group_data in text_groups.items():
        lookup_entry = {
            'lookup_id': f"lookup_{lookup_id_counter:06d}",
            'truncated_text': group_data['truncated_text'],
            'text_source': group_data['text_source'],
            'comment_text': group_data['comment_text'],
            'attachment_text': group_data['attachment_text'],
            'comment_ids': group_data['comment_ids'],
            'comment_count': len(group_data['comment_ids']),
            'full_text_length': group_data['full_text_length'],
            'truncated_text_length': group_data['truncated_text_length'],
            # LLM analysis fields (to be filled later)
            'stance': None,
            'key_quote': None,
            'rationale': None,
            'themes': None,
            # Clustering fields (to be filled later)
            'cluster_id': None,
            'pca_x': None,
            'pca_y': None
        }
        
        lookup_table.append(lookup_entry)
        lookup_id_counter += 1
    
    # Sort by comment count (most common first) then by lookup_id
    lookup_table.sort(key=lambda x: (-x['comment_count'], x['lookup_id']))
    
    return lookup_table

def print_stats(lookup_table: List[Dict[str, Any]], original_count: int):
    """Print statistics about the lookup table."""
    
    total_unique_texts = len(lookup_table)
    total_comment_instances = sum(entry['comment_count'] for entry in lookup_table)
    
    logger.info(f"\n=== LOOKUP TABLE STATISTICS ===")
    logger.info(f"Original comments: {original_count:,}")
    logger.info(f"Unique text patterns: {total_unique_texts:,}")
    logger.info(f"Total comment instances: {total_comment_instances:,}")
    logger.info(f"Deduplication ratio: {total_comment_instances / total_unique_texts:.2f}:1")
    logger.info(f"API call reduction: {((total_comment_instances - total_unique_texts) / total_comment_instances * 100):.1f}%")
    
    # Show top duplicates
    top_duplicates = [entry for entry in lookup_table if entry['comment_count'] > 1][:10]
    if top_duplicates:
        logger.info(f"\nTop {len(top_duplicates)} most common duplicates:")
        for i, entry in enumerate(top_duplicates, 1):
            text_preview = entry['truncated_text'][:100] + "..." if len(entry['truncated_text']) > 100 else entry['truncated_text']
            logger.info(f"{i:2d}. {entry['comment_count']:3d} copies: {text_preview}")
    
    # Show text source distribution
    source_counts = {}
    for entry in lookup_table:
        source = entry['text_source']
        source_counts[source] = source_counts.get(source, 0) + entry['comment_count']
    
    logger.info(f"\nText source distribution:")
    for source, count in sorted(source_counts.items()):
        percentage = count / total_comment_instances * 100
        logger.info(f"  {source}: {count:,} ({percentage:.1f}%)")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Create deduplicated lookup table from raw comment data')
    parser.add_argument('--input', type=str, default=DEFAULT_RAW_DATA,
                       help=f'Input raw data file (default: {DEFAULT_RAW_DATA})')
    parser.add_argument('--output', type=str, default=DEFAULT_LOOKUP_TABLE,
                       help=f'Output lookup table file (default: {DEFAULT_LOOKUP_TABLE})')
    parser.add_argument('--truncate', type=int, default=None,
                       help='Truncate text to this many characters (default: no truncation)')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input):
        logger.error(f"Input file not found: {args.input}")
        return
    
    logger.info(f"Creating lookup table from {args.input}")
    logger.info(f"Output will be saved to {args.output}")
    
    # Load raw data
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        logger.info(f"Loaded {len(raw_data)} comments from {args.input}")
    except Exception as e:
        logger.error(f"Error loading {args.input}: {e}")
        return
    
    # Create lookup table
    try:
        lookup_table = create_lookup_table(raw_data, args.truncate)
        
        # Print statistics
        print_stats(lookup_table, len(raw_data))
        
        # Save lookup table
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(lookup_table, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✅ Lookup table saved to {args.output}")
        logger.info(f"Created {len(lookup_table)} unique text entries from {len(raw_data)} comments")
        
    except Exception as e:
        logger.error(f"Error creating lookup table: {e}")
        return

if __name__ == "__main__":
    main()