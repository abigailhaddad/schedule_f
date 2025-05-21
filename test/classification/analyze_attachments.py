#!/usr/bin/env python3
"""
Analyze attachment text extraction from a results folder.

This script:
1. Analyzes a results directory to find all attachments
2. Checks if text extraction was successful for each attachment type
3. Reports statistics on extraction success by file type
"""

import os
import json
import argparse
from collections import defaultdict


def analyze_attachment_extraction(results_dir):
    """
    Analyze attachment text extraction for a given results directory.
    
    Args:
        results_dir: Path to the results directory
    
    Returns:
        Statistics on attachment text extraction
    """
    # Find raw_data.json file
    raw_data_path = os.path.join(results_dir, "raw_data.json")
    if not os.path.exists(raw_data_path):
        print(f"Error: raw_data.json not found in {results_dir}")
        return
    
    print(f"Analyzing attachment text extraction in: {results_dir}")
    
    # Load the data
    with open(raw_data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Count file types
    file_types = defaultdict(int)
    extracted_by_type = defaultdict(lambda: {'total': 0, 'with_text': 0, 'text_length': 0})
    
    # Track all attachments (downloaded)
    total_attachments = 0
    for item in data:
        if 'attributes' in item and 'attachments' in item['attributes']:
            for att in item['attributes'].get('attachments', []):
                if 'localPath' in att:
                    path = att['localPath']
                    ext = path.split('.')[-1].lower() if '.' in path else 'unknown'
                    file_types[ext] += 1
                    total_attachments += 1

    # Track text extraction success
    for item in data:
        if 'attributes' in item and 'attachment_texts' in item['attributes']:
            for att in item['attributes'].get('attachment_texts', []):
                if 'file_path' in att:
                    path = att['file_path']
                    ext = path.split('.')[-1].lower() if '.' in path else 'unknown'
                    text = att.get('text', '')
                    has_text = text and len(text.strip()) > 20  # More than 20 chars is considered successful
                    
                    extracted_by_type[ext]['total'] += 1
                    if has_text:
                        extracted_by_type[ext]['with_text'] += 1
                        extracted_by_type[ext]['text_length'] += len(text)
    
    # Print results
    print("\n=== ATTACHMENT FILE TYPES FOUND ===")
    print(f"Total attachments downloaded: {total_attachments}")
    for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
        print(f"{ext}: {count} files")
    
    print("\n=== TEXT EXTRACTION SUCCESS BY FILE TYPE ===")
    for ext, stats in sorted(extracted_by_type.items(), key=lambda x: x[1]['total'], reverse=True):
        if stats['total'] > 0:
            success_rate = (stats['with_text'] / stats['total'] * 100)
            avg_length = int(stats['text_length'] / stats['with_text']) if stats['with_text'] > 0 else 0
            print(f"{ext}: {stats['with_text']}/{stats['total']} ({success_rate:.1f}%) - Avg length: {avg_length} chars")
    
    return {
        'file_types': dict(file_types),
        'extraction_stats': {k: dict(v) for k, v in extracted_by_type.items()}
    }


def main():
    """Parse arguments and run the script."""
    parser = argparse.ArgumentParser(description='Analyze attachment text extraction')
    parser.add_argument('--results_dir', type=str, default=None,
                      help='Path to the results directory (default: auto-detect latest)')
    
    args = parser.parse_args()
    
    # Auto-detect latest results directory if not specified
    if args.results_dir is None:
        results_base = '/Users/abigailhaddad/Documents/repos/regs/results'
        result_dirs = [d for d in os.listdir(results_base) if d.startswith('results_')]
        if not result_dirs:
            print("Error: No results directories found")
            return 1
        
        # Sort by name (which includes timestamp) and get the latest
        result_dirs.sort(reverse=True)
        latest_dir = os.path.join(results_base, result_dirs[0])
        results_dir = latest_dir
    else:
        results_dir = args.results_dir
    
    # Run the analysis
    analyze_attachment_extraction(results_dir)
    
    return 0


if __name__ == "__main__":
    exit(main())