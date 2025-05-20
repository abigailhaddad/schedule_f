#!/usr/bin/env python3
"""
Quote Verification Tool for Comment Analysis

This script verifies whether key quotes extracted by the analysis tool
are actually present in the original comment text. It helps validate the 
accuracy of the LLM-based quote extraction.

Usage:
python verify_quotes.py [--results_dir PATH]
"""

import os
import json
import glob
import argparse
import difflib
import unicodedata
from pathlib import Path
from datetime import datetime
import re

def find_most_recent_results():
    """Find the most recent results directory with both raw_data.json and data.json."""
    results_base = os.path.join(os.getcwd(), "results")
    if not os.path.exists(results_base):
        return None
    
    # Find all results directories
    result_dirs = glob.glob(os.path.join(results_base, "results_*"))
    if not result_dirs:
        return None
    
    # Sort by creation time (newest first)
    result_dirs.sort(key=os.path.getctime, reverse=True)
    
    # Find the first one that has both raw_data.json and data.json
    for result_dir in result_dirs:
        raw_data_path = os.path.join(result_dir, "raw_data.json")
        data_path = os.path.join(result_dir, "data.json")
        if os.path.exists(raw_data_path) and os.path.exists(data_path):
            return result_dir
    
    return None

def clean_text(text):
    """Extract only lowercase letters for comparison, properly handling HTML entities."""
    if not text:
        return ""
    
    # First handle common HTML entities
    html_entities = {
        '&rsquo;': "'", '&lsquo;': "'", 
        '&rdquo;': '"', '&ldquo;': '"',
        '&mdash;': '-', '&ndash;': '-',
        '&nbsp;': ' ', '&amp;': '&',
        '&quot;': '"', '&apos;': "'",
        '&hellip;': '...', '&bull;': '•',
        '&gt;': '>', '&lt;': '<',
    }
    
    # Replace all HTML entities
    for entity, replacement in html_entities.items():
        text = text.replace(entity, replacement)
    
    # Also handle any other HTML entities (like &#39; etc.)
    text = re.sub(r'&[a-zA-Z]+;', '', text)  # Remove named entities
    text = re.sub(r'&#[0-9]+;', '', text)    # Remove numbered entities
    
    # Now strip EVERYTHING except lowercase letters
    letters_only = re.sub(r'[^a-z]', '', text.lower())
    
    return letters_only

def verify_quotes(raw_data_path, data_path, output_path=None):
    """Verify if quotes in data.json are present in the original comments."""
    print(f"Loading raw comments from {raw_data_path}...")
    with open(raw_data_path, 'r', encoding='utf-8') as f:
        raw_comments = json.load(f)
    
    print(f"Loading analyzed results from {data_path}...")
    with open(data_path, 'r', encoding='utf-8') as f:
        analysis_results = json.load(f)
    
    # Create a lookup for raw comments by ID
    raw_comments_by_id = {}
    for comment in raw_comments:
        comment_id = comment.get('id')
        if comment_id:
            # Extract main comment text
            comment_text = comment.get('attributes', {}).get('comment', '')
            
            # Check for attachments that might contain additional text
            attachments = comment.get('relationships', {}).get('attachments', {}).get('data', [])
            if attachments:
                # Note: In a complete implementation, you would fetch and parse attachment content
                comment_text += " [ATTACHMENT TEXT NOT INCLUDED]"
            
            raw_comments_by_id[comment_id] = comment_text
    
    # Verify each quote
    verification_results = []
    for item in analysis_results:
        comment_id = item.get('id')
        key_quote = item.get('key_quote', '')
        
        original_text = raw_comments_by_id.get(comment_id, '')
        
        # Skip if either is missing
        if not comment_id or not key_quote or not original_text:
            verification_results.append({
                'id': comment_id,
                'quote': key_quote,
                'verified': False,
                'reason': "Missing comment text or quote",
                'confidence': 0.0
            })
            continue
        
        # Extract only the letters from both texts
        letters_quote = clean_text(key_quote)
        letters_original = clean_text(original_text)
        
        # Create debugging info
        debug_info = {
            "original_quote": key_quote,
            "original_text_sample": original_text[:200] + "..." if len(original_text) > 200 else original_text,
            "letters_quote": letters_quote,
            "letters_original_sample": letters_original[:200] + "..." if len(letters_original) > 200 else letters_original,
        }
        
        # Check if all letters from the quote appear in sequence in the original
        is_match = letters_quote in letters_original
        
        if is_match:
            status = "Letters-only match"
            verified = True
            best_match_ratio = 1.0
            
            # Add index info for debugging
            quote_index = letters_original.find(letters_quote)
            debug_info["match_index"] = quote_index
            debug_info["match_context"] = letters_original[max(0, quote_index-10):min(len(letters_original), quote_index+len(letters_quote)+10)]
        else:
            # If no direct match, try fuzzy matching on letters only
            matcher = difflib.SequenceMatcher(None, letters_quote, letters_original)
            best_match_ratio = matcher.ratio()
            
            # Get the best match blocks for debugging
            match_blocks = matcher.get_matching_blocks()
            best_matches = []
            for block in match_blocks:
                if block.size > 5:  # Only record significant matches
                    best_matches.append({
                        "quote_start": block.a,
                        "orig_start": block.b,
                        "length": block.size,
                        "quote_text": letters_quote[block.a:block.a+block.size],
                        "orig_text": letters_original[block.b:block.b+block.size]
                    })
            debug_info["best_match_blocks"] = best_matches[:3]  # Show top 3 matches
            
            if best_match_ratio >= 0.8:
                status = f"Close letters match (similarity: {best_match_ratio:.2f})"
                verified = True
            else:
                status = f"No letters match (similarity: {best_match_ratio:.2f})"
                verified = False
        
        # Add debug info to status
        debug_status = f"{status}\nDEBUG INFO:\n"
        for key, value in debug_info.items():
            if isinstance(value, list):
                debug_status += f"- {key}:\n"
                for item in value:
                    debug_status += f"  - {item}\n"
            else:
                debug_status += f"- {key}: {value}\n"
        
        verification_results.append({
            'id': comment_id,
            'quote': key_quote,
            'verified': verified,
            'reason': debug_status if not verified else status,
            'confidence': best_match_ratio,
            'debug_info': debug_info
        })
    
    # Generate verification summary
    verified_count = sum(1 for r in verification_results if r['verified'])
    total_count = len(verification_results)
    
    if total_count == 0:
        verification_rate = 0
    else:
        verification_rate = (verified_count / total_count) * 100
    
    summary = {
        'total_quotes': total_count,
        'verified_quotes': verified_count,
        'verification_rate': f"{verification_rate:.1f}%",
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Create output text
    output_text = f"Quote Verification Results\n"
    output_text += f"========================\n\n"
    output_text += f"Date: {summary['timestamp']}\n"
    output_text += f"Total quotes examined: {summary['total_quotes']}\n"
    output_text += f"Verified quotes: {summary['verified_quotes']} ({summary['verification_rate']})\n\n"
    output_text += f"NOTE ON MATCHING: For verification purposes, this tool uses an extremely simplified approach:\n"
    output_text += f"1. Extract ONLY lowercase letters (a-z) from both texts, ignoring ALL other characters\n"
    output_text += f"2. Check if the letters from the quote appear in sequence in the original text\n"
    output_text += f"3. If no exact match, use fuzzy matching on letters only as a fallback\n\n"
    output_text += f"This approach completely ignores punctuation, spaces, numbers, Unicode characters,\n"
    output_text += f"HTML entities, and all other non-letter characters, focusing ONLY on the letter sequence.\n\n"
    
    # Group results by verification status
    output_text += "UNVERIFIED QUOTES\n"
    output_text += "----------------\n\n"
    unverified_count = 0
    
    for result in verification_results:
        if not result['verified']:
            unverified_count += 1
            output_text += f"Comment ID: {result['id']}\n"
            output_text += f"Quote: \"{result['quote']}\"\n"
            
            # Check for Unicode characters and HTML entities to help debugging
            has_unicode = any(ord(c) > 127 for c in result['quote'])
            has_html_entity = any(entity in result['quote'] for entity in ['&rsquo;', '&ldquo;', '&rdquo;', '&lsquo;', '&mdash;'])
            
            if has_unicode:
                output_text += f"Unicode characters detected in quote: "
                for char in result['quote']:
                    if ord(char) > 127:
                        output_text += f"'{char}' (\\u{ord(char):04x}) "
                output_text += "\n"
                
            if has_html_entity:
                output_text += f"HTML entities detected in quote: "
                for entity in ['&rsquo;', '&ldquo;', '&rdquo;', '&lsquo;', '&mdash;', '&ndash;', '&nbsp;']:
                    if entity in result['quote']:
                        output_text += f"{entity} "
                output_text += "\n"
            
            # Add detailed debugging information
            debug_info = result.get('debug_info', {})
            if debug_info:
                output_text += f"DEBUGGING INFORMATION:\n"
                output_text += f"Letters-only quote: {debug_info.get('letters_quote', '')}\n"
                output_text += f"Letters-only original sample: {debug_info.get('letters_original_sample', '')[:100]}...\n"
                
                # Show best match blocks if available
                match_blocks = debug_info.get('best_match_blocks', [])
                if match_blocks:
                    output_text += f"Best partial matches:\n"
                    for i, block in enumerate(match_blocks):
                        output_text += f"  Match {i+1}: '{block.get('quote_text', '')}' at position {block.get('quote_start', 0)} matches '{block.get('orig_text', '')}' at {block.get('orig_start', 0)}\n"
                
            output_text += f"Status: {result['reason']}\n\n"
    
    if unverified_count == 0:
        output_text += "No unverified quotes found!\n\n"
    
    # Include a sample of verified quotes
    output_text += "SAMPLE VERIFIED QUOTES\n"
    output_text += "--------------------\n\n"
    
    verified_results = [r for r in verification_results if r['verified']]
    sample_size = min(5, len(verified_results))
    
    for result in verified_results[:sample_size]:
        output_text += f"Comment ID: {result['id']}\n"
        output_text += f"Quote: \"{result['quote']}\"\n"
        
        # Check for Unicode characters and HTML entities to help debugging
        has_unicode = any(ord(c) > 127 for c in result['quote'])
        has_html_entity = any(entity in result['quote'] for entity in ['&rsquo;', '&ldquo;', '&rdquo;', '&lsquo;', '&mdash;'])
        
        if has_unicode:
            output_text += f"Unicode characters detected in quote: "
            for char in result['quote']:
                if ord(char) > 127:
                    output_text += f"'{char}' (\\u{ord(char):04x}) "
            output_text += "\n"
            
        if has_html_entity:
            output_text += f"HTML entities detected in quote: "
            for entity in ['&rsquo;', '&ldquo;', '&rdquo;', '&lsquo;', '&mdash;', '&ndash;', '&nbsp;']:
                if entity in result['quote']:
                    output_text += f"{entity} "
            output_text += "\n"
            
        output_text += f"Status: {result['reason']}\n\n"
    
    # Determine output path if not provided
    if not output_path:
        results_dir = os.path.dirname(data_path)
        output_path = os.path.join(results_dir, "quote_verification.txt")
    
    # Write the results
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_text)
    
    # Also save JSON results for programmatic use
    json_output_path = os.path.join(os.path.dirname(output_path), "quote_verification.json")
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': summary,
            'results': verification_results
        }, f, indent=2)
    
    print(f"Quote verification complete!")
    print(f"  - Total quotes: {summary['total_quotes']}")
    print(f"  - Verified quotes: {summary['verified_quotes']} ({summary['verification_rate']})")
    print(f"  - Results saved to: {output_path}")
    print(f"  - JSON data saved to: {json_output_path}")
    
    return output_path

def main():
    parser = argparse.ArgumentParser(description='Verify quotes in comment analysis')
    parser.add_argument('--results_dir', type=str, default=None,
                        help='Directory containing results (default: most recent)')
    
    args = parser.parse_args()
    
    # Find the results directory if not specified
    results_dir = args.results_dir
    if not results_dir:
        results_dir = find_most_recent_results()
        if not results_dir:
            print("Error: No results directory found. Please run the analysis first or specify a directory.")
            return 1
    
    # Check for required files
    raw_data_path = os.path.join(results_dir, "raw_data.json")
    data_path = os.path.join(results_dir, "data.json")
    
    if not os.path.exists(raw_data_path):
        print(f"Error: raw_data.json not found in {results_dir}")
        return 1
    
    if not os.path.exists(data_path):
        print(f"Error: data.json not found in {results_dir}")
        return 1
    
    # Run verification
    output_path = os.path.join(results_dir, "quote_verification.txt")
    verify_quotes(raw_data_path, data_path, output_path)
    
    return 0

if __name__ == "__main__":
    exit(main())