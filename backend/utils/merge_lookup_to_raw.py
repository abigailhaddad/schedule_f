#!/usr/bin/env python3
"""
Script to merge raw_data.json with lookup_table_corrected.json
Creates a data.json file with row-level data including LLM info
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define lookup fields with their default values
LOOKUP_FIELDS = {
    'lookup_id': None,
    'truncated_text': None,
    'text_source': None,
    'comment_count': None,
    'stance': None,
    'key_quote': None,
    'rationale': None,
    'themes': [],
    'corrected': False
}

def load_json_file(filepath: Path) -> Any:
    """Load JSON data from file"""
    logger.info(f"Loading {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_lookup_mapping(lookup_data: List[Dict]) -> Dict[str, Dict]:
    """Create a mapping from comment_id to lookup info"""
    logger.info("Creating lookup mapping...")
    mapping = {}
    duplicate_ids = []
    
    for lookup_entry in lookup_data:
        # Extract fields using the defined LOOKUP_FIELDS as reference
        lookup_info = {}
        for field, default_value in LOOKUP_FIELDS.items():
            lookup_info[field] = lookup_entry.get(field, default_value)
        
        # Map to all comment IDs associated with this lookup entry
        comment_ids = lookup_entry.get('comment_ids', [])
        if not comment_ids:
            logger.warning(f"Lookup entry {lookup_entry.get('lookup_id')} has no comment_ids")
        
        for comment_id in comment_ids:
            if comment_id in mapping:
                duplicate_ids.append(comment_id)
                logger.warning(f"Comment ID {comment_id} appears in multiple lookup entries")
            mapping[comment_id] = lookup_info
    
    if duplicate_ids:
        logger.error(f"Found {len(set(duplicate_ids))} comment IDs that appear in multiple lookup entries")
        raise ValueError(f"Duplicate comment IDs found in lookup table: {list(set(duplicate_ids))[:10]}")
    
    logger.info(f"Created mapping for {len(mapping)} comments")
    return mapping

def merge_data(raw_data: List[Dict], lookup_mapping: Dict[str, Dict]) -> List[Dict]:
    """Merge raw data with lookup information"""
    logger.info("Merging data...")
    merged_data = []
    matched_count = 0
    unmatched_comments = []
    
    # Track all comment IDs from raw data
    raw_comment_ids = set()
    
    for comment in raw_data:
        comment_id = comment.get('id')
        if not comment_id:
            logger.error(f"Comment without ID found: {comment}")
            raise ValueError("Found comment without ID in raw_data")
        
        raw_comment_ids.add(comment_id)
        merged_comment = comment.copy()
        
        # Add lookup info if available
        if comment_id in lookup_mapping:
            merged_comment.update(lookup_mapping[comment_id])
            matched_count += 1
        else:
            # Track unmatched comments
            unmatched_comments.append(comment_id)
            # Add empty lookup fields for comments without lookup data
            merged_comment.update(LOOKUP_FIELDS.copy())
        
        merged_data.append(merged_comment)
    
    # Check for lookup entries that don't have corresponding raw data
    lookup_comment_ids = set(lookup_mapping.keys())
    orphaned_lookup_ids = lookup_comment_ids - raw_comment_ids
    
    # Report any issues
    if unmatched_comments:
        logger.warning(f"Found {len(unmatched_comments)} comments in raw_data without lookup entries:")
        for i, comment_id in enumerate(unmatched_comments[:10]):  # Show first 10
            logger.warning(f"  - {comment_id}")
        if len(unmatched_comments) > 10:
            logger.warning(f"  ... and {len(unmatched_comments) - 10} more")
    
    if orphaned_lookup_ids:
        logger.error(f"Found {len(orphaned_lookup_ids)} lookup entries without corresponding raw data:")
        for i, comment_id in enumerate(list(orphaned_lookup_ids)[:10]):  # Show first 10
            logger.error(f"  - {comment_id}")
        if len(orphaned_lookup_ids) > 10:
            logger.error(f"  ... and {len(orphaned_lookup_ids) - 10} more")
        raise ValueError(f"Found {len(orphaned_lookup_ids)} lookup entries that reference non-existent comments")
    
    logger.info(f"Merged {len(merged_data)} comments, {matched_count} with lookup data")
    if unmatched_comments:
        logger.info(f"Note: {len(unmatched_comments)} comments have no lookup data (this may be expected)")
    
    return merged_data

def main():
    """Main function to merge raw data with lookup table"""
    # Define file paths
    base_dir = Path(__file__).parent.parent.parent
    data_dir = base_dir / 'data'
    
    raw_data_path = data_dir / 'raw_data.json'
    lookup_path = data_dir / 'lookup_table_corrected.json'
    output_path = data_dir / 'data.json'
    
    try:
        # Load data
        raw_data = load_json_file(raw_data_path)
        lookup_data = load_json_file(lookup_path)
        
        # Create lookup mapping
        lookup_mapping = create_lookup_mapping(lookup_data)
        
        # Merge data
        merged_data = merge_data(raw_data, lookup_mapping)
        
        # Save merged data
        logger.info(f"Saving merged data to {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)
        
        logger.info("Merge completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during merge: {e}")
        raise

if __name__ == "__main__":
    main()