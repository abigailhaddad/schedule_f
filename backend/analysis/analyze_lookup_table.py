#!/usr/bin/env python3
"""
Analyze Lookup Table with LLM

This script takes a lookup table (created by create_lookup_table.py) and adds
LLM analysis (stance, key_quote, rationale, themes) to each unique text entry.

Usage:
python analyze_lookup_table.py [--input lookup_table.json] [--output lookup_table.json]
"""

import json
import os
import argparse
import logging
import time
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime
import concurrent.futures

# Import the analysis components from the utility module
from ..utils.comment_analyzer import CommentAnalyzer, TimeoutException
from ..config import DEFAULT_MODEL, DEFAULT_BATCH_SIZE, DEFAULT_TIMEOUT, DEFAULT_LOOKUP_TABLE

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def analyze_lookup_entry(entry: Dict[str, Any], analyzer: CommentAnalyzer, max_retries: int = 3) -> Dict[str, Any]:
    """
    Analyze a single lookup table entry with LLM.
    
    Args:
        entry: Lookup table entry to analyze
        analyzer: CommentAnalyzer instance
        max_retries: Maximum number of retries for failed analyses
    
    Returns:
        Updated entry with LLM analysis fields filled
    """
    lookup_id = entry.get('lookup_id', 'unknown')
    text = entry.get('truncated_text', '')
    
    if not text.strip():
        logger.warning(f"Entry {lookup_id} has empty text")
        entry.update({
            'stance': '',
            'key_quote': '',
            'rationale': 'Error: Empty text',
            'themes': ''
        })
        return entry
    
    # Check if already analyzed
    if entry.get('stance') is not None:
        logger.debug(f"Entry {lookup_id} already analyzed, skipping")
        return entry
    
    logger.debug(f"Analyzing entry {lookup_id} ({entry['comment_count']} comments)")
    
    retry_delay = 5  # Start with 5 second delay
    
    for attempt in range(max_retries):
        try:
            # Analyze with the existing analyzer
            analysis = analyzer.analyze(text, lookup_id)
            
            # Update entry with analysis results
            entry.update({
                'stance': analysis.get('stance', ''),
                'key_quote': analysis.get('key_quote', ''),
                'rationale': analysis.get('rationale', ''),
                'themes': ', '.join(analysis.get('themes', [])) if analysis.get('themes') else ''
            })
            
            logger.debug(f"Successfully analyzed {lookup_id}")
            return entry
            
        except TimeoutException as e:
            logger.error(f"Timeout analyzing {lookup_id} (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to analyze {lookup_id} after {max_retries} attempts due to timeout")
                entry.update({
                    'stance': '',
                    'key_quote': '',
                    'rationale': 'Error: Analysis timeout',
                    'themes': ''
                })
                return entry
                
        except Exception as e:
            logger.error(f"Error analyzing {lookup_id} (attempt {attempt+1}/{max_retries}): {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to analyze {lookup_id} after {max_retries} attempts: {e}")
                entry.update({
                    'stance': '',
                    'key_quote': '',
                    'rationale': f'Error: {str(e)}',
                    'themes': ''
                })
                return entry
    
    return entry

def save_checkpoint(lookup_table: List[Dict[str, Any]], checkpoint_file: str):
    """Save checkpoint of current progress."""
    try:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(lookup_table, f, indent=2, ensure_ascii=False)
        logger.info(f"Checkpoint saved to {checkpoint_file}")
    except Exception as e:
        logger.error(f"Failed to save checkpoint: {e}")

def load_checkpoint(checkpoint_file: str) -> Optional[List[Dict[str, Any]]]:
    """Load checkpoint if it exists."""
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded checkpoint from {checkpoint_file}")
            return data
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    return None

def count_analyzed_entries(lookup_table: List[Dict[str, Any]]) -> int:
    """Count how many entries have been analyzed."""
    analyzed = 0
    for entry in lookup_table:
        if entry.get('stance') is not None:
            analyzed += 1
    return analyzed

def analyze_lookup_table_batch(lookup_table: List[Dict[str, Any]], 
                              analyzer: CommentAnalyzer,
                              batch_size: int = 5,
                              use_parallel: bool = True,
                              checkpoint_file: str = None) -> List[Dict[str, Any]]:
    """
    Analyze lookup table entries in batches.
    
    Args:
        lookup_table: List of lookup table entries
        analyzer: CommentAnalyzer instance
        batch_size: Number of entries to process in parallel
        use_parallel: Whether to use parallel processing
        checkpoint_file: File to save checkpoints to
    
    Returns:
        Updated lookup table with analysis results
    """
    total_entries = len(lookup_table)
    analyzed_count = count_analyzed_entries(lookup_table)
    
    logger.info(f"Starting analysis of {total_entries} lookup entries")
    logger.info(f"Already analyzed: {analyzed_count}")
    logger.info(f"Remaining to analyze: {total_entries - analyzed_count}")
    
    if analyzed_count == total_entries:
        logger.info("All entries already analyzed!")
        return lookup_table
    
    # Process entries
    checkpoint_interval = 50  # Save checkpoint every 50 entries
    processed_since_checkpoint = 0
    
    for i in range(0, total_entries, batch_size):
        batch = lookup_table[i:i + batch_size]
        
        # Filter out already analyzed entries
        unanalyzed_batch = [entry for entry in batch if entry.get('stance') is None]
        
        if not unanalyzed_batch:
            continue
        
        logger.info(f"Processing batch {i//batch_size + 1}: entries {i+1}-{min(i+batch_size, total_entries)} ({len(unanalyzed_batch)} unanalyzed)")
        
        if use_parallel and len(unanalyzed_batch) > 1:
            # Parallel processing
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(batch_size, len(unanalyzed_batch))) as executor:
                # Submit tasks
                future_to_entry = {
                    executor.submit(analyze_lookup_entry, entry, analyzer): entry 
                    for entry in unanalyzed_batch
                }
                
                # Collect results with timeout
                for future in concurrent.futures.as_completed(future_to_entry, timeout=300):  # 5 min timeout
                    try:
                        result = future.result(timeout=60)  # 1 min timeout per task
                        # Update the original entry in the lookup table
                        original_entry = future_to_entry[future]
                        original_entry.update(result)
                        
                    except concurrent.futures.TimeoutError:
                        entry = future_to_entry[future]
                        lookup_id = entry.get('lookup_id', 'unknown')
                        logger.error(f"Timeout processing entry {lookup_id} in parallel")
                        
                        # Add error analysis
                        entry.update({
                            'stance': '',
                            'key_quote': '',
                            'rationale': 'Error: Processing timeout',
                            'themes': ''
                        })
                        
                    except Exception as e:
                        entry = future_to_entry[future]
                        lookup_id = entry.get('lookup_id', 'unknown')
                        logger.error(f"Error processing entry {lookup_id}: {e}")
                        
                        # Add error analysis
                        entry.update({
                            'stance': '',
                            'key_quote': '',
                            'rationale': f'Error: {str(e)}',
                            'themes': ''
                        })
        else:
            # Sequential processing
            for entry in unanalyzed_batch:
                try:
                    updated_entry = analyze_lookup_entry(entry, analyzer)
                    entry.update(updated_entry)
                except Exception as e:
                    lookup_id = entry.get('lookup_id', 'unknown')
                    logger.error(f"Error processing entry {lookup_id}: {e}")
                    entry.update({
                        'stance': '',
                        'key_quote': '',
                        'rationale': f'Error: {str(e)}',
                        'themes': ''
                    })
        
        processed_since_checkpoint += len(unanalyzed_batch)
        
        # Save checkpoint periodically
        if checkpoint_file and processed_since_checkpoint >= checkpoint_interval:
            save_checkpoint(lookup_table, checkpoint_file)
            processed_since_checkpoint = 0
            
            # Show progress
            current_analyzed = count_analyzed_entries(lookup_table)
            progress = current_analyzed / total_entries * 100
            logger.info(f"Progress: {current_analyzed}/{total_entries} ({progress:.1f}%) analyzed")
    
    # Final checkpoint
    if checkpoint_file:
        save_checkpoint(lookup_table, checkpoint_file)
    
    final_analyzed = count_analyzed_entries(lookup_table)
    logger.info(f"Analysis complete! {final_analyzed}/{total_entries} entries analyzed")
    
    return lookup_table

def print_analysis_stats(lookup_table: List[Dict[str, Any]]):
    """Print statistics about the analyzed lookup table."""
    total_entries = len(lookup_table)
    analyzed_entries = count_analyzed_entries(lookup_table)
    total_comments = sum(entry['comment_count'] for entry in lookup_table)
    
    logger.info(f"\n=== ANALYSIS STATISTICS ===")
    logger.info(f"Total lookup entries: {total_entries:,}")
    logger.info(f"Analyzed entries: {analyzed_entries:,}")
    logger.info(f"Analysis completion: {analyzed_entries/total_entries*100:.1f}%")
    logger.info(f"Total comments represented: {total_comments:,}")
    
    # Count stance distribution
    stance_counts = {}
    for entry in lookup_table:
        if entry.get('stance'):
            stance = entry['stance']
            count = entry['comment_count']
            stance_counts[stance] = stance_counts.get(stance, 0) + count
    
    if stance_counts:
        logger.info(f"\nStance distribution (by comment count):")
        for stance, count in sorted(stance_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total_comments * 100
            logger.info(f"  {stance}: {count:,} ({percentage:.1f}%)")
    
    # Count errors
    error_entries = [entry for entry in lookup_table if entry.get('rationale', '').startswith('Error:')]
    if error_entries:
        error_comments = sum(entry['comment_count'] for entry in error_entries)
        logger.info(f"\nErrors: {len(error_entries)} entries ({error_comments:,} comments)")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Analyze lookup table with LLM')
    parser.add_argument('--input', type=str, default=DEFAULT_LOOKUP_TABLE,
                       help=f'Input lookup table file (default: {DEFAULT_LOOKUP_TABLE})')
    parser.add_argument('--output', type=str, default=None,
                       help='Output analyzed lookup table file (default: overwrite input file)')
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL,
                       help=f'LLM model to use (default: {DEFAULT_MODEL})')
    parser.add_argument('--batch_size', type=int, default=DEFAULT_BATCH_SIZE,
                       help=f'Number of entries to process in parallel (default: {DEFAULT_BATCH_SIZE})')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT,
                       help=f'Timeout for each API call in seconds (default: {DEFAULT_TIMEOUT})')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from checkpoint if available')
    parser.add_argument('--no_parallel', action='store_true',
                       help='Disable parallel processing (use sequential)')
    
    args = parser.parse_args()
    
    # Default output to input file if not specified
    if args.output is None:
        args.output = args.input
    
    # Check if input file exists
    if not os.path.exists(args.input):
        logger.error(f"Input file not found: {args.input}")
        return
    
    logger.info(f"Analyzing lookup table from {args.input}")
    logger.info(f"Output will be saved to {args.output}")
    logger.info(f"Using model: {args.model}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Timeout: {args.timeout} seconds")
    logger.info(f"Parallel processing: {not args.no_parallel}")
    
    # Load or resume lookup table
    checkpoint_file = f"{args.output}.checkpoint"
    lookup_table = None
    
    if args.resume:
        lookup_table = load_checkpoint(checkpoint_file)
    
    if not lookup_table:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                lookup_table = json.load(f)
            logger.info(f"Loaded {len(lookup_table)} lookup entries from {args.input}")
        except Exception as e:
            logger.error(f"Error loading {args.input}: {e}")
            return
    
    # Initialize analyzer
    try:
        analyzer = CommentAnalyzer(model=args.model, timeout_seconds=args.timeout)
        logger.info(f"Initialized analyzer with model {args.model}")
    except Exception as e:
        logger.error(f"Failed to initialize analyzer: {e}")
        return
    
    # Analyze lookup table
    try:
        start_time = datetime.now()
        
        analyzed_lookup_table = analyze_lookup_table_batch(
            lookup_table=lookup_table,
            analyzer=analyzer,
            batch_size=args.batch_size,
            use_parallel=not args.no_parallel,
            checkpoint_file=checkpoint_file
        )
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Print statistics
        print_analysis_stats(analyzed_lookup_table)
        
        # Save final results
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(analyzed_lookup_table, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✅ Analysis complete!")
        logger.info(f"Results saved to {args.output}")
        logger.info(f"Total time: {duration}")
        
        # Clean up checkpoint
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            logger.info(f"Cleaned up checkpoint file")
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return

if __name__ == "__main__":
    main()