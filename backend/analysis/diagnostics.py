#!/usr/bin/env python3
"""
Diagnostic script to analyze comments and identify potential issues
that might cause the analyzer to hang or fail.

Usage:
python diagnose_comments.py raw_data.json [--start 180] [--end 200]
"""

import json
import argparse
import os
import re
from typing import Dict, List, Any

def strip_html_tags(text):
    """Remove HTML tags from text."""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub('<.*?>', '', text)
    # Decode HTML entities
    import html
    clean = html.unescape(clean)
    return clean.strip()

def extract_comment_text(comment_data):
    """Extract text and metadata from a comment (same as analyzer)."""
    if isinstance(comment_data, dict) and 'id' in comment_data:
        comment_id = comment_data['id']
        
        if 'attributes' in comment_data and isinstance(comment_data['attributes'], dict):
            comment_text = strip_html_tags(comment_data['attributes'].get('comment', ''))
            title = comment_data['attributes'].get('title', '')
            category = comment_data['attributes'].get('category', '')
            
            # Look for attachment texts
            attachment_texts = comment_data['attributes'].get('attachment_texts', [])
            
            # Add attachment text if available
            if attachment_texts:
                for attachment in attachment_texts:
                    attachment_text = strip_html_tags(attachment.get('text', ''))
                    if attachment_text:
                        comment_text += f"\n\n[ATTACHMENT: {attachment.get('title', 'Untitled')}]\n"
                        comment_text += attachment_text
        else:
            comment_text = strip_html_tags(comment_data.get('comment', ''))
            title = comment_data.get('title', '')
            category = comment_data.get('category', '')
            attachment_texts = []
        
        return {
            'id': comment_id,
            'text': comment_text,
            'title': title,
            'category': category,
            'has_attachments': bool(attachment_texts),
            'raw_data': comment_data
        }
    return None

def analyze_comment_characteristics(comment_data):
    """Analyze a comment for potentially problematic characteristics."""
    extracted = extract_comment_text(comment_data)
    if not extracted:
        return None
    
    text = extracted['text']
    
    # Calculate various metrics
    characteristics = {
        'id': extracted['id'],
        'title': extracted['title'][:100] + '...' if len(extracted['title']) > 100 else extracted['title'],
        'category': extracted['category'],
        'has_attachments': extracted['has_attachments'],
        
        # Text metrics
        'text_length': len(text),
        'word_count': len(text.split()) if text else 0,
        'line_count': text.count('\n') + 1 if text else 0,
        'char_length': len(text),
        
        # Potential issues
        'is_empty': len(text.strip()) == 0,
        'has_very_long_lines': any(len(line) > 10000 for line in text.split('\n')),
        'has_unusual_chars': bool(re.search(r'[^\x00-\x7F]', text)),  # Non-ASCII
        'has_control_chars': bool(re.search(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', text)),
        'repetitive_content': len(set(text.split())) < len(text.split()) * 0.1 if text.split() else False,
        
        # Structure issues
        'has_malformed_json': False,  # We'll check this
        'missing_required_fields': not all(key in comment_data for key in ['id']),
        
        # Size warnings
        'very_large': len(text) > 50000,  # > 50KB
        'extremely_large': len(text) > 200000,  # > 200KB
        
        # Preview of content
        'text_preview': text[:200] + '...' if len(text) > 200 else text,
    }
    
    # Check for malformed JSON-like content
    try:
        if '{' in text and '}' in text:
            # Try to find JSON-like structures that might be malformed
            json_candidates = re.findall(r'\{[^{}]*\}', text)
            for candidate in json_candidates[:5]:  # Check first 5 candidates
                try:
                    json.loads(candidate)
                except json.JSONDecodeError:
                    characteristics['has_malformed_json'] = True
                    break
    except Exception:
        pass
    
    return characteristics

def find_problematic_comments(comments_data, start_idx=0, end_idx=None):
    """Find comments that might cause issues."""
    if end_idx is None:
        end_idx = len(comments_data)
    
    print(f"Analyzing comments {start_idx} to {end_idx-1}...")
    
    problematic = []
    all_characteristics = []
    
    for i in range(start_idx, min(end_idx, len(comments_data))):
        comment = comments_data[i]
        characteristics = analyze_comment_characteristics(comment)
        
        if characteristics:
            all_characteristics.append(characteristics)
            
            # Identify potentially problematic comments
            issues = []
            
            if characteristics['is_empty']:
                issues.append("Empty text")
            if characteristics['extremely_large']:
                issues.append(f"Extremely large ({characteristics['text_length']:,} chars)")
            elif characteristics['very_large']:
                issues.append(f"Very large ({characteristics['text_length']:,} chars)")
            if characteristics['has_very_long_lines']:
                issues.append("Very long lines (>10K chars)")
            if characteristics['has_control_chars']:
                issues.append("Control characters")
            if characteristics['has_malformed_json']:
                issues.append("Malformed JSON-like content")
            if characteristics['repetitive_content']:
                issues.append("Highly repetitive content")
            if characteristics['missing_required_fields']:
                issues.append("Missing required fields")
            
            if issues:
                characteristics['issues'] = issues
                problematic.append((i, characteristics))
    
    return problematic, all_characteristics

def generate_report(problematic_comments, all_characteristics, start_idx, end_idx):
    """Generate a diagnostic report."""
    print(f"\n{'='*60}")
    print(f"DIAGNOSTIC REPORT: Comments {start_idx} to {end_idx-1}")
    print(f"{'='*60}")
    
    print(f"\nTotal comments analyzed: {len(all_characteristics)}")
    print(f"Potentially problematic comments: {len(problematic_comments)}")
    
    if not problematic_comments:
        print("✅ No obviously problematic comments found in this range!")
        return
    
    # Summary statistics
    sizes = [c['text_length'] for c in all_characteristics]
    word_counts = [c['word_count'] for c in all_characteristics]
    
    print(f"\nSize Statistics:")
    print(f"  Average text length: {sum(sizes)/len(sizes):,.0f} characters")
    print(f"  Largest comment: {max(sizes):,} characters")
    print(f"  Average word count: {sum(word_counts)/len(word_counts):,.0f} words")
    print(f"  Max word count: {max(word_counts):,} words")
    
    # Detailed problematic comments
    print(f"\n{'='*60}")
    print("PROBLEMATIC COMMENTS DETAILS:")
    print(f"{'='*60}")
    
    for i, (comment_idx, characteristics) in enumerate(problematic_comments):
        print(f"\n--- Comment #{comment_idx} (Index {comment_idx}) ---")
        print(f"ID: {characteristics['id']}")
        print(f"Title: {characteristics['title']}")
        print(f"Category: {characteristics['category']}")
        print(f"Issues: {', '.join(characteristics['issues'])}")
        print(f"Text length: {characteristics['text_length']:,} characters")
        print(f"Word count: {characteristics['word_count']:,} words")
        print(f"Has attachments: {characteristics['has_attachments']}")
        
        if characteristics['text_length'] > 1000:
            print(f"Text preview: {characteristics['text_preview']}")
        else:
            print(f"Full text: {characteristics['text_preview']}")
        
        if i >= 10:  # Limit to first 10 problematic comments
            remaining = len(problematic_comments) - i - 1
            if remaining > 0:
                print(f"\n... and {remaining} more problematic comments")
            break
    
    # Specific recommendations
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS:")
    print(f"{'='*60}")
    
    large_comments = [c for _, c in problematic_comments if c['very_large'] or c['extremely_large']]
    if large_comments:
        print(f"• {len(large_comments)} comments are unusually large - consider text truncation")
    
    empty_comments = [c for _, c in problematic_comments if c['is_empty']]
    if empty_comments:
        print(f"• {len(empty_comments)} comments are empty - add empty text handling")
    
    control_char_comments = [c for _, c in problematic_comments if c['has_control_chars']]
    if control_char_comments:
        print(f"• {len(control_char_comments)} comments have control characters - add text cleaning")
    
    json_issues = [c for _, c in problematic_comments if c['has_malformed_json']]
    if json_issues:
        print(f"• {len(json_issues)} comments have malformed JSON - might confuse the LLM")

def main():
    parser = argparse.ArgumentParser(description='Diagnose comments for potential issues')
    parser.add_argument('input_file', help='Path to raw_data.json file')
    parser.add_argument('--start', type=int, default=180, help='Start index (default: 180)')
    parser.add_argument('--end', type=int, default=200, help='End index (default: 200)')
    parser.add_argument('--batch_size', type=int, default=10, help='Batch size to simulate (default: 10)')
    parser.add_argument('--show_all', action='store_true', help='Show all comments, not just problematic ones')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: File {args.input_file} not found")
        return
    
    print(f"Loading {args.input_file}...")
    with open(args.input_file, 'r', encoding='utf-8') as f:
        comments_data = json.load(f)
    
    print(f"Total comments in file: {len(comments_data)}")
    
    # Calculate which batch would contain the problematic area
    batch_num = args.start // args.batch_size
    batch_start = batch_num * args.batch_size
    batch_end = batch_start + args.batch_size
    
    print(f"Batch {batch_num + 1} would process comments {batch_start} to {batch_end - 1}")
    
    # Analyze the specified range
    problematic, all_chars = find_problematic_comments(comments_data, args.start, args.end)
    
    generate_report(problematic, all_chars, args.start, args.end)
    
    # Also check the exact batch that would be processed
    if batch_start != args.start or batch_end != args.end:
        print(f"\n{'='*60}")
        print(f"ALSO CHECKING EXACT BATCH RANGE: {batch_start} to {batch_end - 1}")
        print(f"{'='*60}")
        
        batch_problematic, batch_chars = find_problematic_comments(comments_data, batch_start, batch_end)
        
        if batch_problematic:
            print(f"\nFound {len(batch_problematic)} problematic comments in the exact batch:")
            for comment_idx, characteristics in batch_problematic:
                print(f"  Comment {comment_idx}: {characteristics['id']} - {', '.join(characteristics['issues'])}")
        else:
            print("\n✅ No obviously problematic comments in the exact batch range")
    
    # Show some general stats about the file
    print(f"\n{'='*60}")
    print("GENERAL FILE STATISTICS:")
    print(f"{'='*60}")
    
    sample_size = min(100, len(comments_data))
    sample_problematic, sample_chars = find_problematic_comments(comments_data, 0, sample_size)
    
    if sample_chars:
        sizes = [c['text_length'] for c in sample_chars]
        print(f"Sample of first {sample_size} comments:")
        print(f"  Average size: {sum(sizes)/len(sizes):,.0f} characters")
        print(f"  Largest: {max(sizes):,} characters")
        print(f"  Smallest: {min(sizes):,} characters")
        print(f"  Problematic in sample: {len(sample_problematic)}")

if __name__ == "__main__":
    main()