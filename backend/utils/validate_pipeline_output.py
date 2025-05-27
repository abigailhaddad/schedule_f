#!/usr/bin/env python3
"""
Validation utilities for pipeline output
"""

import json
import os
import logging
import pandas as pd
from typing import Dict, List, Tuple, Set

logger = logging.getLogger(__name__)

def validate_pipeline_output(csv_file: str, raw_data_file: str, data_file: str, 
                           lookup_table_file: str, exclude_ids: Set[str] = None) -> Dict[str, any]:
    """
    Validate pipeline output for consistency and completeness.
    
    Args:
        csv_file: Path to comments CSV file
        raw_data_file: Path to raw_data.json
        data_file: Path to data.json (merged file)
        lookup_table_file: Path to lookup table JSON
        exclude_ids: Set of comment IDs to exclude from validation (e.g., {'OPM-2025-0004-0001'})
    
    Returns:
        Dictionary with validation results and any issues found
    """
    if exclude_ids is None:
        exclude_ids = {'OPM-2025-0004-0001'}  # Default exclusion
    
    results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'stats': {}
    }
    
    try:
        # 1. Load and count CSV rows
        logger.info("Loading CSV file...")
        csv_ids = set()
        try:
            # Try with csv module first (handles quotes better)
            import csv
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    comment_id = row.get('Comment ID') or row.get('Document ID')
                    if comment_id and comment_id not in exclude_ids:
                        csv_ids.add(comment_id)
            csv_count = len(csv_ids)
        except Exception as e:
            # Fallback to pandas
            df = pd.read_csv(csv_file, on_bad_lines='skip')
            if 'Comment ID' in df.columns:
                csv_ids = set(df['Comment ID'].astype(str)) - exclude_ids
            else:
                csv_ids = set(df['Document ID'].astype(str)) - exclude_ids
            csv_count = len(csv_ids)
        
        results['stats']['csv_count'] = csv_count
        results['stats']['csv_ids'] = csv_ids
        
        # 2. Load and validate raw_data.json
        logger.info("Loading raw_data.json...")
        with open(raw_data_file, 'r') as f:
            raw_data = json.load(f)
        raw_count = len(raw_data)
        raw_ids = {item['id'] for item in raw_data if item.get('id') not in exclude_ids}
        results['stats']['raw_data_count'] = raw_count
        
        # 3. Load and validate data.json
        logger.info("Loading data.json...")
        with open(data_file, 'r') as f:
            data = json.load(f)
        data_count = len(data)
        data_ids = {item['id'] for item in data if item.get('id') not in exclude_ids}
        results['stats']['data_count'] = data_count
        
        # 4. Load lookup table
        logger.info("Loading lookup table...")
        with open(lookup_table_file, 'r') as f:
            lookup_table = json.load(f)
        lookup_count = len(lookup_table)
        results['stats']['lookup_entries'] = lookup_count
        
        # Collect all comment IDs from lookup table
        lookup_comment_ids = set()
        for entry in lookup_table:
            for comment_id in entry.get('comment_ids', []):
                if comment_id not in exclude_ids:
                    lookup_comment_ids.add(comment_id)
        
        results['stats']['comments_in_lookup'] = len(lookup_comment_ids)
        
        # VALIDATION CHECKS
        
        # Check 1: CSV count matches raw_data and data counts
        if csv_count != raw_count:
            results['errors'].append(
                f"CSV has {csv_count} comments but raw_data.json has {raw_count} "
                f"(difference: {abs(csv_count - raw_count)})"
            )
            results['valid'] = False
            
            # Find missing comments
            missing_from_raw = csv_ids - raw_ids
            if missing_from_raw:
                results['errors'].append(
                    f"Comments in CSV but not in raw_data: {sorted(list(missing_from_raw))[:10]}"
                    + (" ..." if len(missing_from_raw) > 10 else "")
                )
        
        if raw_count != data_count:
            results['errors'].append(
                f"raw_data.json has {raw_count} comments but data.json has {data_count}"
            )
            results['valid'] = False
        
        # Check 2: All comment IDs are in lookup table
        missing_from_lookup = raw_ids - lookup_comment_ids
        if missing_from_lookup:
            results['errors'].append(
                f"{len(missing_from_lookup)} comments not found in lookup table: "
                f"{sorted(list(missing_from_lookup))[:10]}"
                + (" ..." if len(missing_from_lookup) > 10 else "")
            )
            results['valid'] = False
        
        # Check 3: All lookup entries have LLM analysis
        unanalyzed_entries = []
        partially_analyzed = []
        
        for entry in lookup_table:
            lookup_id = entry.get('lookup_id', 'unknown')
            
            # Check if entry has all required analysis fields
            if entry.get('stance') is None:
                unanalyzed_entries.append(lookup_id)
            elif not all([
                entry.get('key_quote') is not None,
                entry.get('rationale') is not None,
                entry.get('themes') is not None
            ]):
                partially_analyzed.append(lookup_id)
        
        if unanalyzed_entries:
            results['errors'].append(
                f"{len(unanalyzed_entries)} lookup entries have no analysis: "
                f"{unanalyzed_entries[:10]}"
                + (" ..." if len(unanalyzed_entries) > 10 else "")
            )
            results['valid'] = False
        
        if partially_analyzed:
            results['warnings'].append(
                f"{len(partially_analyzed)} lookup entries have incomplete analysis: "
                f"{partially_analyzed[:10]}"
                + (" ..." if len(partially_analyzed) > 10 else "")
            )
        
        # Additional stats
        results['stats']['total_analyzed'] = lookup_count - len(unanalyzed_entries)
        results['stats']['analysis_rate'] = (
            (lookup_count - len(unanalyzed_entries)) / lookup_count * 100 
            if lookup_count > 0 else 0
        )
        
        # Check data.json has lookup fields
        data_without_lookup = [
            item['id'] for item in data 
            if not item.get('lookup_id') or item.get('stance') is None
        ]
        if data_without_lookup:
            results['warnings'].append(
                f"{len(data_without_lookup)} entries in data.json missing lookup data"
            )
        
    except Exception as e:
        results['valid'] = False
        results['errors'].append(f"Validation error: {str(e)}")
        logger.error(f"Validation error: {e}", exc_info=True)
    
    return results


def print_validation_summary(results: Dict[str, any]):
    """Print a formatted summary of validation results."""
    print("\n" + "=" * 60)
    print("📊 PIPELINE OUTPUT VALIDATION")
    print("=" * 60)
    
    # Stats
    stats = results.get('stats', {})
    print(f"\n📈 Statistics:")
    print(f"   CSV comments: {stats.get('csv_count', 'N/A'):,}")
    print(f"   Raw data comments: {stats.get('raw_data_count', 'N/A'):,}")
    print(f"   Data.json comments: {stats.get('data_count', 'N/A'):,}")
    print(f"   Lookup table entries: {stats.get('lookup_entries', 'N/A'):,}")
    print(f"   Comments in lookup: {stats.get('comments_in_lookup', 'N/A'):,}")
    print(f"   Analyzed entries: {stats.get('total_analyzed', 'N/A'):,} "
          f"({stats.get('analysis_rate', 0):.1f}%)")
    
    # Validation result
    print(f"\n{'✅ VALIDATION PASSED' if results['valid'] else '❌ VALIDATION FAILED'}")
    
    # Errors
    if results.get('errors'):
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"   - {error}")
    
    # Warnings
    if results.get('warnings'):
        print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
        for warning in results['warnings']:
            print(f"   - {warning}")
    
    print("\n" + "=" * 60)
    
    return results['valid']