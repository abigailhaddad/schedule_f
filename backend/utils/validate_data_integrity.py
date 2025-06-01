#!/usr/bin/env python3
"""
Validate data integrity across comments.csv, raw_data.json, and lookup_table.json
"""

import json
import pandas as pd
import os
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple

def load_data():
    """Load all data files."""
    print("Loading data files...")
    
    # Load comments.csv
    comments_df = pd.read_csv('comments.csv')
    print(f"  comments.csv: {len(comments_df)} rows")
    
    # Load raw_data.json
    with open('data/raw_data.json', 'r') as f:
        raw_data = json.load(f)
    print(f"  raw_data.json: {len(raw_data)} entries")
    
    # Load lookup_table.json
    with open('data/lookup_table.json', 'r') as f:
        lookup_table = json.load(f)
    print(f"  lookup_table.json: {len(lookup_table)} entries")
    
    return comments_df, raw_data, lookup_table

def validate_comment_id_uniqueness(lookup_table: List[Dict]) -> Dict:
    """Check that each comment ID appears in exactly one lookup entry."""
    print("\n🔍 Validating comment ID uniqueness...")
    
    comment_id_map = defaultdict(list)
    
    for i, entry in enumerate(lookup_table):
        lookup_id = entry.get('lookup_id', f'entry_{i}')
        comment_ids = entry.get('comment_ids', [])
        
        for comment_id in comment_ids:
            comment_id_map[comment_id].append(lookup_id)
    
    # Find duplicates
    duplicates = {cid: lookup_ids for cid, lookup_ids in comment_id_map.items() 
                 if len(lookup_ids) > 1}
    
    total_comment_ids = sum(len(entry.get('comment_ids', [])) for entry in lookup_table)
    unique_comment_ids = len(comment_id_map)
    
    print(f"  Total comment ID references: {total_comment_ids}")
    print(f"  Unique comment IDs: {unique_comment_ids}")
    print(f"  Duplicates found: {len(duplicates)}")
    
    if duplicates:
        print(f"  ❌ {len(duplicates)} comment IDs appear in multiple lookup entries:")
        for cid, lookup_ids in list(duplicates.items())[:5]:  # Show first 5
            print(f"    {cid}: {lookup_ids}")
        if len(duplicates) > 5:
            print(f"    ... and {len(duplicates) - 5} more")
    else:
        print("  ✅ All comment IDs are unique")
    
    return {
        'total_references': total_comment_ids,
        'unique_ids': unique_comment_ids,
        'duplicates': duplicates,
        'status': 'PASS' if not duplicates else 'FAIL'
    }

def validate_data_completeness(comments_df: pd.DataFrame, raw_data: List[Dict], 
                              lookup_table: List[Dict]) -> Dict:
    """Check that all comments from CSV are in raw_data and lookup_table."""
    print("\n🔍 Validating data completeness...")
    
    # Get comment IDs from each source
    csv_comment_ids = set(comments_df['Document ID'].astype(str))
    raw_data_ids = set(comment['id'] for comment in raw_data)
    
    # Get comment IDs from lookup table
    lookup_comment_ids = set()
    for entry in lookup_table:
        lookup_comment_ids.update(entry.get('comment_ids', []))
    
    print(f"  comments.csv: {len(csv_comment_ids)} comment IDs")
    print(f"  raw_data.json: {len(raw_data_ids)} comment IDs")
    print(f"  lookup_table.json: {len(lookup_comment_ids)} comment IDs")
    
    # Find missing IDs
    missing_from_raw = csv_comment_ids - raw_data_ids
    missing_from_lookup = csv_comment_ids - lookup_comment_ids
    extra_in_raw = raw_data_ids - csv_comment_ids
    extra_in_lookup = lookup_comment_ids - csv_comment_ids
    
    print(f"  Missing from raw_data: {len(missing_from_raw)}")
    print(f"  Missing from lookup_table: {len(missing_from_lookup)}")
    print(f"  Extra in raw_data: {len(extra_in_raw)}")
    print(f"  Extra in lookup_table: {len(extra_in_lookup)}")
    
    if missing_from_raw:
        print(f"    ❌ First 5 missing from raw_data: {list(missing_from_raw)[:5]}")
    if missing_from_lookup:
        print(f"    ❌ First 5 missing from lookup_table: {list(missing_from_lookup)[:5]}")
    if extra_in_raw:
        print(f"    ⚠️  First 5 extra in raw_data: {list(extra_in_raw)[:5]}")
    if extra_in_lookup:
        print(f"    ⚠️  First 5 extra in lookup_table: {list(extra_in_lookup)[:5]}")
    
    status = 'PASS'
    if missing_from_raw or missing_from_lookup:
        status = 'FAIL'
    elif extra_in_raw or extra_in_lookup:
        status = 'WARN'
    
    if status == 'PASS':
        print("  ✅ All comment IDs are properly represented")
    
    return {
        'csv_count': len(csv_comment_ids),
        'raw_data_count': len(raw_data_ids),
        'lookup_count': len(lookup_comment_ids),
        'missing_from_raw': missing_from_raw,
        'missing_from_lookup': missing_from_lookup,
        'extra_in_raw': extra_in_raw,
        'extra_in_lookup': extra_in_lookup,
        'status': status
    }

def validate_text_sources(lookup_table: List[Dict]) -> Dict:
    """Check text source consistency and attachment integration."""
    print("\n🔍 Validating text sources and attachment integration...")
    
    text_source_counts = Counter()
    attachment_integration_issues = []
    
    for entry in lookup_table:
        text_source = entry.get('text_source', 'unknown')
        text_source_counts[text_source] += 1
        
        # Check attachment integration
        has_attachment_in_source = 'attachment' in text_source
        has_attachment_text = bool(entry.get('attachment_text', '').strip())
        truncated_text = entry.get('truncated_text', '')
        has_attachment_marker = '--- ATTACHMENT CONTENT ---' in truncated_text
        
        if has_attachment_in_source and not (has_attachment_text or has_attachment_marker):
            attachment_integration_issues.append({
                'lookup_id': entry.get('lookup_id'),
                'text_source': text_source,
                'issue': 'text_source indicates attachment but no attachment content found'
            })
    
    print(f"  Text source breakdown:")
    for source, count in text_source_counts.most_common():
        print(f"    {source}: {count} entries")
    
    print(f"  Attachment integration issues: {len(attachment_integration_issues)}")
    if attachment_integration_issues:
        print(f"    ❌ First 3 issues:")
        for issue in attachment_integration_issues[:3]:
            print(f"      {issue['lookup_id']}: {issue['issue']}")
    else:
        print("  ✅ Attachment integration looks good")
    
    return {
        'text_source_counts': dict(text_source_counts),
        'attachment_issues': attachment_integration_issues,
        'status': 'PASS' if not attachment_integration_issues else 'WARN'
    }

def validate_truncation(lookup_table: List[Dict]) -> Dict:
    """Check text truncation consistency."""
    print("\n🔍 Validating text truncation...")
    
    truncation_stats = {
        'total_entries': len(lookup_table),
        'entries_with_truncated_text': 0,
        'entries_with_length_info': 0,
        'truncation_inconsistencies': []
    }
    
    for entry in lookup_table:
        truncated_text = entry.get('truncated_text', '')
        full_text_length = entry.get('full_text_length')
        truncated_text_length = entry.get('truncated_text_length')
        
        if truncated_text:
            truncation_stats['entries_with_truncated_text'] += 1
        
        if full_text_length is not None and truncated_text_length is not None:
            truncation_stats['entries_with_length_info'] += 1
            
            # Check consistency
            actual_truncated_length = len(truncated_text)
            if abs(actual_truncated_length - truncated_text_length) > 5:  # Allow small variance
                truncation_stats['truncation_inconsistencies'].append({
                    'lookup_id': entry.get('lookup_id'),
                    'recorded_length': truncated_text_length,
                    'actual_length': actual_truncated_length,
                    'difference': abs(actual_truncated_length - truncated_text_length)
                })
    
    print(f"  Entries with truncated text: {truncation_stats['entries_with_truncated_text']}")
    print(f"  Entries with length info: {truncation_stats['entries_with_length_info']}")
    print(f"  Truncation inconsistencies: {len(truncation_stats['truncation_inconsistencies'])}")
    
    if truncation_stats['truncation_inconsistencies']:
        print(f"    ❌ First 3 inconsistencies:")
        for issue in truncation_stats['truncation_inconsistencies'][:3]:
            print(f"      {issue['lookup_id']}: recorded={issue['recorded_length']}, actual={issue['actual_length']}")
    else:
        print("  ✅ Text truncation is consistent")
    
    truncation_stats['status'] = 'PASS' if not truncation_stats['truncation_inconsistencies'] else 'WARN'
    return truncation_stats

def validate_analysis_completeness(lookup_table: List[Dict]) -> Dict:
    """Check how many entries have been analyzed."""
    print("\n🔍 Validating analysis completeness...")
    
    total_entries = len(lookup_table)
    analyzed_entries = sum(1 for entry in lookup_table if entry.get('stance') is not None)
    unanalyzed_entries = total_entries - analyzed_entries
    
    # Check entries with attachments specifically
    attachment_entries = [entry for entry in lookup_table 
                         if 'attachment' in entry.get('text_source', '')]
    attachment_analyzed = sum(1 for entry in attachment_entries if entry.get('stance') is not None)
    attachment_unanalyzed = len(attachment_entries) - attachment_analyzed
    
    print(f"  Total entries: {total_entries}")
    print(f"  Analyzed entries: {analyzed_entries}")
    print(f"  Unanalyzed entries: {unanalyzed_entries}")
    print(f"  Attachment entries: {len(attachment_entries)}")
    print(f"  Attachment entries analyzed: {attachment_analyzed}")
    print(f"  Attachment entries unanalyzed: {attachment_unanalyzed}")
    
    if unanalyzed_entries == 0:
        print("  ✅ All entries have been analyzed")
        status = 'PASS'
    elif attachment_unanalyzed > 0:
        print(f"  ⚠️  {attachment_unanalyzed} attachment entries still need analysis")
        status = 'WARN'
    else:
        print(f"  ⚠️  {unanalyzed_entries} entries still need analysis")
        status = 'WARN'
    
    return {
        'total_entries': total_entries,
        'analyzed_entries': analyzed_entries,
        'unanalyzed_entries': unanalyzed_entries,
        'attachment_entries': len(attachment_entries),
        'attachment_analyzed': attachment_analyzed,
        'attachment_unanalyzed': attachment_unanalyzed,
        'status': status
    }

def main():
    print("🔎 Data Integrity Validation Report")
    print("=" * 50)
    
    try:
        # Load data
        comments_df, raw_data, lookup_table = load_data()
        
        # Run validations
        results = {}
        results['uniqueness'] = validate_comment_id_uniqueness(lookup_table)
        results['completeness'] = validate_data_completeness(comments_df, raw_data, lookup_table)
        results['text_sources'] = validate_text_sources(lookup_table)
        results['truncation'] = validate_truncation(lookup_table)
        results['analysis'] = validate_analysis_completeness(lookup_table)
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 SUMMARY")
        print("=" * 50)
        
        overall_status = 'PASS'
        for check_name, result in results.items():
            status = result.get('status', 'UNKNOWN')
            status_icon = {'PASS': '✅', 'WARN': '⚠️', 'FAIL': '❌'}.get(status, '❓')
            print(f"{status_icon} {check_name.title()}: {status}")
            
            if status == 'FAIL':
                overall_status = 'FAIL'
            elif status == 'WARN' and overall_status == 'PASS':
                overall_status = 'WARN'
        
        print(f"\n🎯 Overall Status: {overall_status}")
        
        if overall_status == 'PASS':
            print("✅ All data integrity checks passed!")
        elif overall_status == 'WARN':
            print("⚠️  Some warnings found - review recommended")
        else:
            print("❌ Critical issues found - action required")
        
        return 0 if overall_status == 'PASS' else 1
        
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())