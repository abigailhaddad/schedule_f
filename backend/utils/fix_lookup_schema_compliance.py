#!/usr/bin/env python3
"""
Fix schema compliance issues in lookup_table.json by populating missing fields
"""

import json
import os
import logging
from typing import Dict, List, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_raw_data_mapping(raw_data_path: str) -> Dict[str, Dict]:
    """Load raw data and create a mapping by comment ID."""
    logger.info(f"Loading raw data from {raw_data_path}")
    
    with open(raw_data_path, 'r') as f:
        raw_data = json.load(f)
    
    # Create mapping: comment_id -> comment_data
    raw_data_map = {}
    for comment in raw_data:
        comment_id = comment['id']
        raw_data_map[comment_id] = comment
    
    logger.info(f"Loaded {len(raw_data_map):,} raw data entries")
    return raw_data_map

def extract_text_from_comment(comment_data: Dict, attachments_dir: str) -> Dict[str, str]:
    """Extract comment text and attachment text for a comment."""
    comment_id = comment_data['id']
    
    # Get comment text
    comment_text = comment_data.get('attributes', {}).get('comment', '')
    
    # Get attachment text
    attachment_texts = []
    comment_attachments_dir = os.path.join(attachments_dir, comment_id)
    
    if os.path.exists(comment_attachments_dir):
        # Find all .extracted.txt files
        for filename in sorted(os.listdir(comment_attachments_dir)):
            if filename.endswith('.extracted.txt'):
                extracted_path = os.path.join(comment_attachments_dir, filename)
                try:
                    with open(extracted_path, 'r', encoding='utf-8') as f:
                        attachment_text = f.read().strip()
                        if attachment_text and not attachment_text.startswith('['):  # Skip error messages
                            attachment_texts.append(attachment_text)
                except Exception as e:
                    logger.warning(f"Could not read attachment {extracted_path}: {e}")
    
    attachment_text = '\n\n--- NEXT ATTACHMENT ---\n\n'.join(attachment_texts)
    
    return {
        'comment_text': comment_text,
        'attachment_text': attachment_text
    }

def fix_lookup_entry(entry: Dict, raw_data_map: Dict[str, Dict], attachments_dir: str) -> Dict:
    """Fix a single lookup entry by populating missing fields."""
    
    # If all required fields are present, return as-is
    required_fields = ['comment_text', 'attachment_text', 'full_text_length', 'truncated_text_length']
    if all(field in entry for field in required_fields):
        return entry
    
    # Get comment IDs for this entry
    comment_ids = entry.get('comment_ids', [])
    if not comment_ids:
        logger.warning(f"Entry {entry.get('lookup_id')} has no comment_ids")
        return entry
    
    # Extract text from all comments in this entry
    all_comment_texts = []
    all_attachment_texts = []
    
    for comment_id in comment_ids:
        if comment_id in raw_data_map:
            text_data = extract_text_from_comment(raw_data_map[comment_id], attachments_dir)
            
            comment_text = text_data['comment_text']
            attachment_text = text_data['attachment_text']
            
            if comment_text:
                all_comment_texts.append(comment_text)
            if attachment_text:
                all_attachment_texts.append(attachment_text)
    
    # Combine texts
    combined_comment_text = '\n\n'.join(all_comment_texts)
    combined_attachment_text = '\n\n--- NEXT ATTACHMENT ---\n\n'.join(all_attachment_texts)
    
    # Create full text (same logic as in the pipeline)
    full_text_parts = []
    if combined_comment_text:
        full_text_parts.append(combined_comment_text)
    if combined_attachment_text:
        full_text_parts.append('--- ATTACHMENT CONTENT ---')
        full_text_parts.append(combined_attachment_text)
    
    full_text = '\n\n'.join(full_text_parts)
    
    # Update entry with missing fields
    entry['comment_text'] = combined_comment_text
    entry['attachment_text'] = combined_attachment_text
    entry['full_text_length'] = len(full_text)
    entry['truncated_text_length'] = len(entry.get('truncated_text', ''))
    
    return entry

def main():
    # Paths
    lookup_table_path = 'data/lookup_table.json'
    raw_data_path = 'data/raw_data.json'
    attachments_dir = 'data/attachments'
    
    # Load data
    logger.info("Loading lookup table...")
    with open(lookup_table_path, 'r') as f:
        lookup_table = json.load(f)
    
    logger.info(f"Loaded {len(lookup_table):,} lookup entries")
    
    # Load raw data mapping
    raw_data_map = load_raw_data_mapping(raw_data_path)
    
    # Find entries missing required fields
    required_fields = ['comment_text', 'attachment_text', 'full_text_length', 'truncated_text_length']
    missing_fields_entries = []
    
    for i, entry in enumerate(lookup_table):
        if any(field not in entry for field in required_fields):
            missing_fields_entries.append((i, entry))
    
    logger.info(f"Found {len(missing_fields_entries):,} entries missing required fields")
    
    if not missing_fields_entries:
        logger.info("All entries already have required fields!")
        return
    
    # Fix entries
    logger.info("Fixing missing fields...")
    fixed_count = 0
    
    for i, (index, entry) in enumerate(missing_fields_entries):
        try:
            fixed_entry = fix_lookup_entry(entry, raw_data_map, attachments_dir)
            lookup_table[index] = fixed_entry
            fixed_count += 1
            
            if (i + 1) % 100 == 0:
                logger.info(f"Fixed {i + 1:,}/{len(missing_fields_entries):,} entries")
                
        except Exception as e:
            logger.error(f"Error fixing entry {entry.get('lookup_id')}: {e}")
    
    logger.info(f"Successfully fixed {fixed_count:,} entries")
    
    # Save updated lookup table
    logger.info("Saving updated lookup table...")
    with open(lookup_table_path, 'w') as f:
        json.dump(lookup_table, f, indent=2)
    
    logger.info("✅ Schema compliance fix complete!")
    
    # Verify fix worked
    logger.info("Verifying fix...")
    still_missing = 0
    for entry in lookup_table:
        if any(field not in entry for field in required_fields):
            still_missing += 1
    
    if still_missing == 0:
        logger.info("✅ All entries now have required fields!")
    else:
        logger.warning(f"⚠️ {still_missing} entries still missing fields")

if __name__ == "__main__":
    main()