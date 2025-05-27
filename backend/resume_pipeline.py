#!/usr/bin/env python3
"""
Resume-Aware Pipeline

This script handles the resume workflow for the new lookup table architecture.
It validates truncation consistency, finds new comments, appends them to raw_data,
updates the lookup table, and only runs analysis on new content.

Usage:
python resume_pipeline.py --csv comments.csv [--raw_data raw_data.json] [--lookup_table lookup_table.json] [--truncate 500]
"""

import json
import os
import argparse
import logging
from typing import List, Dict, Any, Set, Optional
from datetime import datetime
import pandas as pd

# Add the parent directory to path for imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our existing modules
from backend.fetch.fetch_comments import read_comments_from_csv
from backend.analysis.create_lookup_table import normalize_text_for_dedup, extract_and_combine_text
from backend.analysis.analyze_lookup_table import analyze_lookup_table_batch, CommentAnalyzer

# Initial logger setup (will be reconfigured with file handler in main)
logger = logging.getLogger(__name__)

def setup_logging(output_dir: str):
    """Set up logging with file handler in the output directory."""
    log_file = os.path.join(output_dir, 'resume_pipeline.log')
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Set up new handlers
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ],
        force=True  # Override existing configuration
    )
    logger.info(f"📝 Logging to: {log_file}")

def validate_truncation_consistency(lookup_table_file: str, requested_truncation: Optional[int]) -> int:
    """
    Validate that the requested truncation level matches the existing lookup table.
    Returns the validated truncation level.
    """
    logger.info(f"🔍 Validating truncation consistency...")
    
    if not os.path.exists(lookup_table_file):
        logger.info(f"No existing lookup table found, using requested truncation: {requested_truncation}")
        return requested_truncation
    
    try:
        with open(lookup_table_file, 'r') as f:
            lookup_table = json.load(f)
        
        if not lookup_table:
            logger.info(f"Empty lookup table, using requested truncation: {requested_truncation}")
            return requested_truncation
        
        # Find the maximum truncated text length in existing lookup table
        max_length = max(entry.get('truncated_text_length', 0) for entry in lookup_table)
        
        # Check if we have a mix of truncated and non-truncated entries
        has_long_entries = any(entry.get('full_text_length', 0) > max_length for entry in lookup_table)
        
        if requested_truncation is None:
            if has_long_entries:
                logger.error(f"❌ Existing lookup table has truncated entries (max: {max_length} chars)")
                logger.error(f"   Cannot resume without truncation. Use --truncate {max_length}")
                raise ValueError("Truncation level required for consistency")
            logger.info(f"✅ No truncation needed (existing max: {max_length} chars)")
            return None
        
        if max_length != requested_truncation:
            logger.error(f"❌ Truncation level mismatch!")
            logger.error(f"   Existing lookup table: {max_length} chars")
            logger.error(f"   Requested: {requested_truncation} chars")
            logger.error(f"   Use --truncate {max_length} to resume")
            raise ValueError("Truncation level mismatch")
        
        logger.info(f"✅ Truncation level consistent: {requested_truncation} chars")
        return requested_truncation
        
    except Exception as e:
        logger.error(f"Error validating truncation: {e}")
        raise

def load_comment_ids_from_csv(csv_file: str) -> Set[str]:
    """Load comment IDs from CSV file."""
    logger.info(f"📖 Loading comment IDs from CSV: {csv_file}")
    
    try:
        # Try parsing with Python csv module which handles embedded quotes better
        import csv
        comment_ids = set()
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Try both 'Comment ID' and 'Document ID' columns
                comment_id = row.get('Comment ID') or row.get('Document ID')
                if comment_id:
                    comment_ids.add(comment_id)
        
        logger.info(f"✅ Found {len(comment_ids):,} comment IDs in CSV")
        return comment_ids
        
    except Exception as e:
        logger.error(f"Error loading CSV with csv module: {e}")
        # Fallback to pandas with error handling
        try:
            logger.info("Trying pandas with error recovery...")
            # Try to read either Comment ID or Document ID column
            try:
                df = pd.read_csv(csv_file, usecols=['Comment ID'], on_bad_lines='skip', encoding='utf-8')
                comment_ids = set(df['Comment ID'].astype(str).tolist())
            except KeyError:
                df = pd.read_csv(csv_file, usecols=['Document ID'], on_bad_lines='skip', encoding='utf-8')
                comment_ids = set(df['Document ID'].astype(str).tolist())
            logger.info(f"✅ Found {len(comment_ids):,} comment IDs in CSV (pandas fallback)")
            return comment_ids
        except Exception as e2:
            logger.error(f"All CSV parsing methods failed: {e2}")
            raise

def load_comment_ids_from_raw_data(raw_data_file: str) -> Set[str]:
    """Load comment IDs from raw_data.json file."""
    if not os.path.exists(raw_data_file):
        logger.info(f"No existing raw_data.json found")
        return set()
    
    logger.info(f"📖 Loading comment IDs from raw_data: {raw_data_file}")
    
    try:
        with open(raw_data_file, 'r') as f:
            raw_data = json.load(f)
        
        comment_ids = set(item['id'] for item in raw_data if 'id' in item)
        logger.info(f"✅ Found {len(comment_ids):,} comment IDs in raw_data")
        return comment_ids
    except Exception as e:
        logger.error(f"Error loading raw_data: {e}")
        raise

def find_new_comment_ids(csv_file: str, raw_data_file: str) -> Set[str]:
    """Find comment IDs that are in CSV but not in raw_data."""
    csv_ids = load_comment_ids_from_csv(csv_file)
    raw_ids = load_comment_ids_from_raw_data(raw_data_file)
    
    new_ids = csv_ids - raw_ids
    
    logger.info(f"📊 Comment ID analysis:")
    logger.info(f"   CSV file: {len(csv_ids):,} comments")
    logger.info(f"   Raw data: {len(raw_ids):,} comments") 
    logger.info(f"   New to fetch: {len(new_ids):,} comments")
    
    return new_ids

def fetch_and_append_new_comments(new_comment_ids: Set[str], csv_file: str, 
                                 raw_data_file: str, output_dir: str) -> str:
    """
    Fetch new comments (with attachments) and append to raw_data.json.
    Returns path to updated raw_data.json.
    """
    if not new_comment_ids:
        logger.info("No new comments to fetch")
        return raw_data_file
    
    logger.info(f"🔄 Fetching {len(new_comment_ids):,} new comments with attachments...")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a filtered CSV with only new comment IDs
    try:
        df = pd.read_csv(csv_file, on_bad_lines='skip')
    except Exception as e:
        logger.error(f"Error reading CSV with pandas: {e}")
        logger.info("Trying CSV module instead...")
        
        # Use csv module as fallback
        import csv
        import tempfile
        
        # Read with csv module and write clean version
        rows = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames
            for row in reader:
                rows.append(row)
        
        # Create dataframe from clean data
        df = pd.DataFrame(rows)
        logger.info(f"Successfully read {len(df)} rows with csv module")
    
    # Try both column names
    if 'Comment ID' in df.columns:
        comment_col = 'Comment ID'
        new_comments_df = df[df['Comment ID'].astype(str).isin(new_comment_ids)]
    elif 'Document ID' in df.columns:
        comment_col = 'Document ID'
        new_comments_df = df[df['Document ID'].astype(str).isin(new_comment_ids)]
    else:
        raise ValueError("Neither 'Comment ID' nor 'Document ID' found in CSV columns")
    
    logger.info(f"📊 Filtering CSV:")
    logger.info(f"   Total rows in CSV: {len(df)}")
    logger.info(f"   Using column: {comment_col}")
    logger.info(f"   New comment IDs to find: {len(new_comment_ids)}")
    logger.info(f"   Matching rows found: {len(new_comments_df)}")
    
    if len(new_comments_df) == 0:
        logger.warning("❌ No matching rows found in CSV!")
        logger.info(f"   First few CSV IDs: {df[comment_col].astype(str).head().tolist()}")
        logger.info(f"   New comment IDs: {list(new_comment_ids)}")
        return raw_data_file
    
    # Save filtered CSV
    temp_csv = os.path.join(output_dir, 'new_comments_temp.csv')
    new_comments_df.to_csv(temp_csv, index=False)
    
    try:
        # Use existing fetch logic to get comments with attachments
        logger.info(f"Fetching comments from filtered CSV...")
        
        # Create a temporary directory for the fetch operation
        temp_output_dir = os.path.join(output_dir, 'temp_fetch')
        os.makedirs(temp_output_dir, exist_ok=True)
        
        # Fetch new comments to a temporary file
        raw_data_file_from_csv = read_comments_from_csv(temp_csv, temp_output_dir, limit=len(new_comment_ids))
        
        # Load the generated raw data
        with open(raw_data_file_from_csv, 'r') as f:
            new_raw_data = json.load(f)
        
        # Append to existing raw_data or create new one
        if os.path.exists(raw_data_file):
            with open(raw_data_file, 'r') as f:
                existing_raw_data = json.load(f)
            logger.info(f"Loaded {len(existing_raw_data):,} existing comments from {raw_data_file}")
        else:
            existing_raw_data = []
            logger.info(f"No existing raw_data.json found at {raw_data_file}, creating new file")
        
        existing_raw_data.extend(new_raw_data)
        
        # Save updated raw_data back to the original location
        with open(raw_data_file, 'w') as f:
            json.dump(existing_raw_data, f, indent=2)
        
        # Clean up temporary files
        os.remove(raw_data_file_from_csv)
        os.rmdir(temp_output_dir)
        
        logger.info(f"✅ Appended {len(new_raw_data):,} new comments to raw_data")
        logger.info(f"✅ Total comments in raw_data: {len(existing_raw_data):,}")
        
        # Cleanup temp file
        os.remove(temp_csv)
        
        return raw_data_file
        
    except Exception as e:
        logger.error(f"Error fetching new comments: {e}")
        # Cleanup temp file
        if os.path.exists(temp_csv):
            os.remove(temp_csv)
        raise

def update_lookup_table_with_new_comments(new_comment_ids: Set[str], raw_data_file: str, 
                                        lookup_table_file: str, truncation: Optional[int]) -> str:
    """
    Update lookup table with new comments, adding them to existing patterns or creating new entries.
    Returns path to updated lookup table.
    """
    if not new_comment_ids:
        logger.info("No new comments to add to lookup table")
        return lookup_table_file
    
    logger.info(f"🔄 Updating lookup table with {len(new_comment_ids):,} new comments...")
    
    # Load existing lookup table or create empty one
    if os.path.exists(lookup_table_file):
        with open(lookup_table_file, 'r') as f:
            lookup_table = json.load(f)
        logger.info(f"Loaded existing lookup table with {len(lookup_table)} entries")
    else:
        lookup_table = []
        logger.info("Creating new lookup table")
    
    # Load raw data to get the new comments
    with open(raw_data_file, 'r') as f:
        raw_data = json.load(f)
    
    # Filter to only new comments
    new_comments = [item for item in raw_data if item['id'] in new_comment_ids]
    logger.info(f"Processing {len(new_comments)} new comments for lookup table")
    
    # Create mapping of normalized text to existing lookup entries
    existing_text_map = {}
    for i, entry in enumerate(lookup_table):
        # Normalize the existing truncated text
        normalized = normalize_text_for_dedup(entry['truncated_text'])
        existing_text_map[normalized] = i
    
    # Process each new comment
    added_to_existing = 0
    new_entries_created = 0
    
    # Find the highest existing lookup ID to avoid conflicts
    max_id = 0
    for entry in lookup_table:
        lookup_id = entry.get('lookup_id', 'lookup_000000')
        # Extract number from lookup_XXXXXX format
        try:
            id_num = int(lookup_id.split('_')[1])
            max_id = max(max_id, id_num)
        except (IndexError, ValueError):
            continue
    next_lookup_id = max_id + 1
    
    for comment_data in new_comments:
        try:
            comment_id = comment_data['id']
            
            # Extract and normalize text for this comment
            text_result = extract_and_combine_text(comment_data, truncation)
            truncated_text = text_result['truncated_text']
            
            if not truncated_text.strip():
                logger.warning(f"Comment {comment_id} has empty text, skipping")
                continue
            
            normalized_text = normalize_text_for_dedup(truncated_text)
            
            # Check if this text pattern already exists
            if normalized_text in existing_text_map:
                # Add to existing entry
                existing_idx = existing_text_map[normalized_text]
                lookup_table[existing_idx]['comment_ids'].append(comment_id)
                lookup_table[existing_idx]['comment_count'] += 1
                added_to_existing += 1
                logger.debug(f"Added {comment_id} to existing pattern {lookup_table[existing_idx]['lookup_id']}")
            else:
                # Create new lookup entry
                new_entry = {
                    'lookup_id': f"lookup_{next_lookup_id:06d}",
                    'truncated_text': truncated_text,
                    'text_source': text_result['text_source'],
                    'comment_ids': [comment_id],
                    'comment_count': 1,
                    # Analysis fields (to be filled later or preserved)
                    'stance': None,
                    'key_quote': None,
                    'rationale': None,
                    'themes': None,
                    'corrected': False  # New entries haven't been manually corrected
                }
                
                lookup_table.append(new_entry)
                existing_text_map[normalized_text] = len(lookup_table) - 1
                new_entries_created += 1
                next_lookup_id += 1
                logger.debug(f"Created new pattern {new_entry['lookup_id']} for {comment_id}")
                
        except Exception as e:
            logger.error(f"Error processing comment {comment_data.get('id', 'unknown')}: {e}")
            continue
    
    # Sort lookup table by comment count (most common first)
    lookup_table.sort(key=lambda x: (-x['comment_count'], x['lookup_id']))
    
    # Save updated lookup table
    with open(lookup_table_file, 'w') as f:
        json.dump(lookup_table, f, indent=2)
    
    logger.info(f"✅ Lookup table updated:")
    logger.info(f"   Added to existing patterns: {added_to_existing}")
    logger.info(f"   New patterns created: {new_entries_created}")
    logger.info(f"   Total lookup entries: {len(lookup_table)}")
    
    return lookup_table_file

def count_unanalyzed_entries(lookup_table_file: str) -> int:
    """Count how many lookup entries need LLM analysis."""
    if not os.path.exists(lookup_table_file):
        return 0
    
    with open(lookup_table_file, 'r') as f:
        lookup_table = json.load(f)
    
    unanalyzed = len([entry for entry in lookup_table if entry.get('stance') is None])
    return unanalyzed

def main():
    """Main resume pipeline function."""
    parser = argparse.ArgumentParser(description='Resume-aware pipeline for lookup table workflow')
    parser.add_argument('--csv', type=str, required=True,
                       help='Path to comments.csv file')
    parser.add_argument('--raw_data', type=str, default='raw_data.json',
                       help='Path to raw_data.json file (default: raw_data.json)')
    parser.add_argument('--lookup_table', type=str, default='lookup_table.json',
                       help='Path to lookup_table.json file (default: lookup_table.json)')
    parser.add_argument('--output_dir', type=str, default='.',
                       help='Output directory (default: current directory)')
    parser.add_argument('--truncate', type=int, default=None,
                       help='Truncate text to this many characters')
    parser.add_argument('--model', type=str, default='gpt-4o-mini',
                       help='LLM model for analysis (default: gpt-4o-mini)')
    parser.add_argument('--n_clusters', type=int, default=15,
                       help='Number of clusters for semantic analysis (default: 15)')
    parser.add_argument('--skip_analysis', action='store_true',
                       help='Skip LLM analysis (only update data)')
    parser.add_argument('--skip_clustering', action='store_true',
                       help='Skip clustering (only do data update and LLM analysis)')
    
    args = parser.parse_args()
    
    # Setup paths
    # Input paths - where to read existing data from
    input_raw_data_path = args.raw_data
    input_lookup_table_path = args.lookup_table
    
    # Output paths - where to save updated data
    output_raw_data_path = os.path.join(args.output_dir, os.path.basename(args.raw_data))
    output_lookup_table_path = os.path.join(args.output_dir, os.path.basename(args.lookup_table))
    
    logger.info(f"🚀 Starting resume-aware pipeline...")
    logger.info(f"📁 CSV file: {args.csv}")
    logger.info(f"📁 Input raw data: {input_raw_data_path}")
    logger.info(f"📁 Input lookup table: {input_lookup_table_path}")
    logger.info(f"📁 Output directory: {args.output_dir}")
    
    # Validate input files exist
    if not os.path.exists(input_raw_data_path):
        logger.error(f"❌ Input raw data file not found: {input_raw_data_path}")
        raise FileNotFoundError(f"Raw data file not found: {input_raw_data_path}")
    
    if not os.path.exists(input_lookup_table_path):
        logger.error(f"❌ Input lookup table file not found: {input_lookup_table_path}")
        raise FileNotFoundError(f"Lookup table file not found: {input_lookup_table_path}")
    
    # Show initial stats
    logger.info(f"\n📊 Initial data check:")
    with open(input_raw_data_path, 'r') as f:
        existing_raw_data = json.load(f)
    logger.info(f"   Existing raw_data.json: {len(existing_raw_data):,} comments")
    
    with open(input_lookup_table_path, 'r') as f:
        existing_lookup = json.load(f)
    logger.info(f"   Existing lookup table: {len(existing_lookup):,} entries")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Set up logging with output directory
    setup_logging(args.output_dir)
    
    try:
        # Step 1: Validate truncation consistency
        validated_truncation = validate_truncation_consistency(input_lookup_table_path, args.truncate)
        
        # Step 2: Find new comment IDs (compare CSV with input raw data)
        new_comment_ids = find_new_comment_ids(args.csv, input_raw_data_path)
        
        # Initialize counters for summary
        added_to_existing = 0
        new_entries_created = 0
        unanalyzed_count = 0
        
        # Copy existing files to output directory first
        logger.info(f"\n=== Preparing output directory ===")
        if os.path.exists(input_raw_data_path):
            import shutil
            shutil.copy2(input_raw_data_path, output_raw_data_path)
            logger.info(f"✅ Copied raw_data.json to output directory")
        
        if os.path.exists(input_lookup_table_path):
            import shutil
            shutil.copy2(input_lookup_table_path, output_lookup_table_path)
            logger.info(f"✅ Copied lookup table to output directory")
        
        # Fetch and append new comments with attachments
        if new_comment_ids:
            logger.info(f"\n=== STEP 1: Fetching {len(new_comment_ids):,} New Comments ===")
            fetch_and_append_new_comments(new_comment_ids, args.csv, output_raw_data_path, args.output_dir)
        else:
            logger.info(f"\n=== STEP 1: No New Comments to Fetch ===")
            logger.info(f"   All comments from CSV already exist in raw_data.json")
        
        # Update lookup table with new comments
        logger.info(f"\n=== STEP 2: Updating Lookup Table ===")
        
        # Load the existing lookup table that was copied
        with open(output_lookup_table_path, 'r') as f:
            lookup_table = json.load(f)
        logger.info(f"   Starting with {len(lookup_table)} existing entries")
        
        # Only process new comments if any were fetched
        if new_comment_ids:
            # Import necessary functions
            from .analysis.create_lookup_table import extract_and_combine_text, normalize_text_for_dedup
            
            # Load the complete raw data to get the new comments
            with open(output_raw_data_path, 'r') as f:
                complete_raw_data = json.load(f)
            
            # Get just the new comments
            new_comments = [c for c in complete_raw_data if c.get('id') in new_comment_ids]
            logger.info(f"   Processing {len(new_comments)} new comments")
            
            # Create mapping of normalized text to existing lookup entries
            existing_text_map = {}
            for i, entry in enumerate(lookup_table):
                normalized = normalize_text_for_dedup(entry['truncated_text'])
                existing_text_map[normalized] = i
            
            # Process each new comment
            added_to_existing = 0
            new_entries_created = 0
            
            # Find the highest existing lookup ID
            max_id = 0
            for entry in lookup_table:
                lookup_id = entry.get('lookup_id', 'lookup_000000')
                try:
                    id_num = int(lookup_id.split('_')[1])
                    max_id = max(max_id, id_num)
                except (IndexError, ValueError):
                    continue
            next_lookup_id = max_id + 1
            
            for comment_data in new_comments:
                try:
                    comment_id = comment_data['id']
                    
                    # Extract and normalize text
                    text_result = extract_and_combine_text(comment_data, validated_truncation)
                    truncated_text = text_result['truncated_text']
                    
                    if not truncated_text.strip():
                        logger.warning(f"Comment {comment_id} has empty text, skipping")
                        continue
                    
                    normalized_text = normalize_text_for_dedup(truncated_text)
                    
                    # Check if this text pattern already exists
                    if normalized_text in existing_text_map:
                        # Add to existing entry
                        existing_idx = existing_text_map[normalized_text]
                        if comment_id not in lookup_table[existing_idx]['comment_ids']:
                            lookup_table[existing_idx]['comment_ids'].append(comment_id)
                            lookup_table[existing_idx]['comment_count'] += 1
                            added_to_existing += 1
                    else:
                        # Create new lookup entry
                        new_entry = {
                            'lookup_id': f"lookup_{next_lookup_id:06d}",
                            'truncated_text': truncated_text,
                            'text_source': text_result['text_source'],
                            'comment_ids': [comment_id],
                            'comment_count': 1,
                            'stance': None,
                            'key_quote': None,
                            'rationale': None,
                            'themes': None,
                            'corrected': False
                        }
                        
                        lookup_table.append(new_entry)
                        existing_text_map[normalized_text] = len(lookup_table) - 1
                        new_entries_created += 1
                        next_lookup_id += 1
                        
                except Exception as e:
                    logger.error(f"Error processing comment {comment_data.get('id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"   Added to existing entries: {added_to_existing}")
            logger.info(f"   New entries created: {new_entries_created}")
        
        # Sort lookup table by comment count (most common first)
        lookup_table.sort(key=lambda x: (-x['comment_count'], x['lookup_id']))
        
        # Save the updated lookup table
        with open(output_lookup_table_path, 'w') as f:
            json.dump(lookup_table, f, indent=2)
        
        logger.info(f"✅ Lookup table saved with {len(lookup_table)} entries")
        
        # Report on new entries
        if new_comment_ids:
            new_entries = sum(1 for entry in lookup_table 
                            if any(cid in new_comment_ids for cid in entry.get('comment_ids', [])))
            logger.info(f"   Including {new_entries} entries with new comments")
        
        # Step 6: Run LLM analysis on unanalyzed entries
        if not args.skip_analysis:
            unanalyzed_count = count_unanalyzed_entries(output_lookup_table_path)
            if unanalyzed_count > 0:
                logger.info(f"\n=== STEP 3: LLM Analysis ({unanalyzed_count} entries) ===")
                
                # Initialize analyzer
                analyzer = CommentAnalyzer(model=args.model)
                
                # Load lookup table
                with open(output_lookup_table_path, 'r') as f:
                    lookup_table_to_analyze = json.load(f)
                
                # Analyze unanalyzed entries
                analyzed_lookup_table = analyze_lookup_table_batch(
                    lookup_table=lookup_table_to_analyze,
                    analyzer=analyzer,
                    batch_size=5,
                    use_parallel=True,
                    checkpoint_file=f"{output_lookup_table_path}.checkpoint"
                )
                
                # Save analyzed lookup table back to the original file
                with open(output_lookup_table_path, 'w') as f:
                    json.dump(analyzed_lookup_table, f, indent=2)
                
                logger.info(f"✅ Analysis complete, saved to {output_lookup_table_path}")
            else:
                logger.info(f"\n=== STEP 3: No LLM Analysis Needed ===")
        else:
            logger.info(f"\n=== STEP 3: Skipping LLM Analysis ===")
        
        # Step 6: Run clustering
        n_entries = 0  # Initialize for use in final summary
        if not args.skip_clustering:
            logger.info(f"\n=== STEP 4: Semantic Clustering ===")
            
            # Check how many entries we have for clustering
            with open(output_lookup_table_path, 'r') as f:
                lookup_table = json.load(f)
            
            n_entries = len(lookup_table)
            # Ensure we don't request more clusters than entries
            n_clusters = min(args.n_clusters, n_entries)
            
            if n_entries == 0:
                logger.info("No entries to cluster, skipping clustering")
            elif n_entries < 2:
                logger.info("Only 1 entry, skipping clustering")
            else:
                logger.info(f"Clustering {n_entries} entries into {n_clusters} clusters")
                
                # Import and run clustering
                import sys
                import subprocess
                
                # Get absolute path to the semantic_lookup script
                script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                semantic_script = os.path.join(script_dir, 'backend', 'analysis', 'semantic_lookup.py')
                
                clustering_cmd = [
                    sys.executable, 
                    semantic_script,
                    '--input', output_lookup_table_path,
                    '--n_clusters', str(n_clusters)
                ]
                
                result = subprocess.run(clustering_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info("✅ Clustering complete")
                    logger.info(result.stdout)
                else:
                    logger.error("❌ Clustering failed")
                    logger.error(result.stderr)
        else:
            logger.info(f"\n=== STEP 4: Skipping Clustering ===")
        
        # Step 7: Quote verification (always run if analysis was performed)
        if not args.skip_analysis:
            logger.info(f"\n=== STEP 5: Quote Verification ===")
            
            # Import and run quote verification
            from backend.analysis.verify_lookup_quotes import verify_lookup_quotes
            
            # Use the lookup table path
            verification_output = output_lookup_table_path.replace('.json', '_quote_verification.json')
            text_report_output = output_lookup_table_path.replace('.json', '_quote_verification.txt')
            
            logger.info(f"Verifying quotes in {output_lookup_table_path}...")
            verification_results = verify_lookup_quotes(output_lookup_table_path, verification_output, text_report_output)
            
            if verification_results:
                logger.info(f"✅ Quote verification complete")
                logger.info(f"   Verification rate: {verification_results.get('verification_rate', 0)}%")
                logger.info(f"   Exact matches: {verification_results.get('exact_match_rate', 0)}%")
                logger.info(f"   Quotes not found: {verification_results.get('quotes_not_found', 0)} ({round(verification_results.get('quotes_not_found', 0) / max(1, verification_results.get('entries_with_quotes', 1)) * 100, 1)}%)")
                logger.info(f"   Results saved to: {verification_output}")
                logger.info(f"   Text report: {verification_output.replace('.json', '.txt')}")
            else:
                logger.error("❌ Quote verification failed")
        
        # Step 8: Create merged data.json
        logger.info(f"\n=== STEP 6: Creating Merged data.json ===")
        from backend.utils.merge_lookup_to_raw import merge_lookup_to_raw
        
        # Use the clustered file if clustering was done, otherwise use the base lookup table
        if not args.skip_clustering and n_entries >= 2:
            lookup_for_merge = output_lookup_table_path.replace('.json', '_clustered.json')
        else:
            lookup_for_merge = output_lookup_table_path
            
        output_data_path = os.path.join(args.output_dir, 'data.json')
        merge_lookup_to_raw(output_raw_data_path, lookup_for_merge, output_data_path)
        logger.info(f"✅ Created merged data.json")
        
        # Step 9: Validate output
        logger.info(f"\n=== STEP 7: Validating Pipeline Output ===")
        from backend.utils.validate_pipeline_output import validate_pipeline_output, print_validation_summary
        
        validation_results = validate_pipeline_output(
            csv_file=args.csv,
            raw_data_file=output_raw_data_path,
            data_file=output_data_path,
            lookup_table_file=output_lookup_table_path
        )
        
        # Print validation summary
        print_validation_summary(validation_results)
        
        if not validation_results['valid']:
            logger.error("❌ Pipeline validation failed! Check errors above.")
        
        # Final summary with better visibility
        logger.info(f"\n{'='*60}")
        logger.info(f"🎉 RESUME PIPELINE COMPLETE!")
        logger.info(f"{'='*60}")
        
        # Show what was processed
        logger.info(f"\n📊 Processing Summary:")
        logger.info(f"   New comments fetched: {len(new_comment_ids):,}")
        if new_comment_ids:
            logger.info(f"   New unique patterns: {new_entries_created:,}")
            logger.info(f"   Comments added to existing patterns: {added_to_existing:,}")
        
        if not args.skip_analysis and unanalyzed_count > 0:
            logger.info(f"   Entries analyzed: {unanalyzed_count:,}")
        
        logger.info(f"\n📁 Output files in {args.output_dir}:")
        logger.info(f"   - {os.path.basename(output_raw_data_path)} (raw comment data)")
        logger.info(f"   - {os.path.basename(output_lookup_table_path)} (deduplicated patterns with analysis)")
        logger.info(f"   - data.json (merged data for frontend)")
        if not args.skip_analysis:
            logger.info(f"   - {os.path.basename(output_lookup_table_path.replace('.json', '_quote_verification.json'))}")
            logger.info(f"   - {os.path.basename(output_lookup_table_path.replace('.json', '_quote_verification.txt'))}")
        if not args.skip_clustering and n_entries >= 2:
            logger.info(f"   - {os.path.basename(output_lookup_table_path.replace('.json', '_clustered.json'))} (with clustering)")
            logger.info(f"   - cluster_report.txt")
            logger.info(f"   - clusters_visualization.png")
            logger.info(f"   - dendrogram.png")
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    main()