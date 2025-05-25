#!/usr/bin/env python3
"""
Quote Verifier for Lookup Table Analysis

This script verifies that key quotes extracted by the lookup table analysis tool are actually 
present in the original truncated text. This helps validate the accuracy of the AI's
quote extraction in the deduplicated workflow.

Requirements:
- Python 3.8+

Usage:
python -m backend.analysis.verify_lookup_quotes --input lookup_table_analyzed.json
"""

import os
import json
import argparse
import re
from typing import Dict, List, Tuple, Optional

def clean_for_comparison(text: str) -> str:
    """
    Clean text for comparison purposes by normalizing whitespace and punctuation.
    
    Args:
        text: The text to clean
        
    Returns:
        Cleaned text suitable for fuzzy matching
    """
    if not text:
        return ""
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Normalize common punctuation variations
    text = text.replace(''', "'").replace(''', "'")
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace('—', '-').replace('–', '-')
    
    return text.strip().lower()

def normalize_quotes(text: str) -> str:
    """Normalize quotation marks to standard ASCII quotes."""
    if not text:
        return ""
    
    # Replace curly quotes with straight quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    # Replace other quote-like characters
    text = text.replace('„', '"').replace('‟', '"')
    text = text.replace('‹', '<').replace('›', '>')
    text = text.replace('«', '"').replace('»', '"')
    
    return text

def find_quote_in_text(quote: str, full_text: str) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Find a quote in the full text, with some flexibility for variations.
    
    Args:
        quote: The quote to search for
        full_text: The full text to search in
        
    Returns:
        Tuple of (found_exact, matched_text, position)
    """
    if not quote or not full_text:
        return False, None, None
    
    # Try exact match first
    if quote in full_text:
        position = full_text.find(quote)
        return True, quote, position
    
    # Normalize and try again
    normalized_quote = normalize_quotes(quote)
    normalized_text = normalize_quotes(full_text)
    
    if normalized_quote in normalized_text:
        position = normalized_text.find(normalized_quote)
        return True, normalized_quote, position
    
    # Clean for more flexible comparison
    clean_quote = clean_for_comparison(quote)
    clean_text = clean_for_comparison(full_text)
    
    # Try a more flexible match
    if len(clean_quote) > 20:  # Only for substantial quotes
        if clean_quote in clean_text:
            position = clean_text.find(clean_quote)
            # Extract the matching section from the original text
            approx_start = max(0, position - 10)
            approx_end = min(len(clean_text), position + len(clean_quote) + 10)
            context = clean_text[approx_start:approx_end]
            
            return False, f"Found similar (not exact): {context}", position
    
    # Check if at least 80% of the words in the quote appear together in the text
    quote_words = set(clean_quote.split())
    if len(quote_words) > 5:  # Only for quotes with several words
        text_chunks = [clean_for_comparison(chunk) for chunk in re.split(r'[.!?]', full_text)]
        
        for i, chunk in enumerate(text_chunks):
            chunk_words = set(chunk.split())
            common_words = quote_words.intersection(chunk_words)
            
            if len(common_words) >= 0.8 * len(quote_words):
                return False, f"Found partial match in sentence {i+1}: {chunk}", -1
    
    return False, None, None

def verify_lookup_quotes(lookup_table_file: str, output_file: Optional[str] = None) -> Dict:
    """
    Verify quotes in analyzed lookup table and generate a report.
    
    Args:
        lookup_table_file: Path to the analyzed lookup table file (lookup_table_analyzed.json)
        output_file: Path to save verification results
        
    Returns:
        Dictionary with verification results
    """
    print(f"Loading analyzed lookup table from {lookup_table_file}...")
    
    with open(lookup_table_file, 'r', encoding='utf-8') as f:
        try:
            lookup_table = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: {lookup_table_file} is not valid JSON")
            return {}
    
    if not lookup_table:
        print("No data found in lookup table")
        return {}
    
    print(f"Loaded {len(lookup_table)} lookup entries")
    
    # Initialize results
    results = {
        "total_lookup_entries": len(lookup_table),
        "entries_with_quotes": 0,
        "quotes_found_exact": 0,
        "quotes_found_similar": 0,
        "quotes_not_found": 0,
        "verification_rate": 0,
        "total_comments_represented": sum(entry.get('comment_count', 0) for entry in lookup_table),
        "problematic_quotes": []
    }
    
    # Verify each lookup entry
    for i, entry in enumerate(lookup_table):
        if i % 10 == 0:
            print(f"Verifying lookup entry {i+1}/{len(lookup_table)}...")
        
        # Skip entries without quotes or text
        if not entry.get("key_quote") or not entry.get("truncated_text"):
            continue
        
        results["entries_with_quotes"] += 1
        
        # Get the key quote and truncated text
        quote = entry.get("key_quote", "").strip()
        truncated_text = entry.get("truncated_text", "").strip()
        
        # Verify the quote
        found_exact, match_text, position = find_quote_in_text(quote, truncated_text)
        
        if found_exact:
            results["quotes_found_exact"] += 1
        elif match_text:
            results["quotes_found_similar"] += 1
            # Add to problematic quotes for review
            results["problematic_quotes"].append({
                "lookup_id": entry.get("lookup_id", f"lookup_{i}"),
                "comment_count": entry.get("comment_count", 0),
                "comment_ids": entry.get("comment_ids", []),
                "quote": quote,
                "truncated_text": truncated_text[:200] + "..." if len(truncated_text) > 200 else truncated_text,
                "match_info": match_text,
                "match_type": "similar"
            })
        else:
            results["quotes_not_found"] += 1
            # Add to problematic quotes
            results["problematic_quotes"].append({
                "lookup_id": entry.get("lookup_id", f"lookup_{i}"),
                "comment_count": entry.get("comment_count", 0),
                "comment_ids": entry.get("comment_ids", []),
                "quote": quote,
                "truncated_text": truncated_text[:200] + "..." if len(truncated_text) > 200 else truncated_text,
                "match_info": "Not found in truncated text",
                "match_type": "not_found"
            })
    
    # Calculate verification rate
    total_quotes = results["quotes_found_exact"] + results["quotes_found_similar"] + results["quotes_not_found"]
    if total_quotes > 0:
        results["verification_rate"] = round((results["quotes_found_exact"] + results["quotes_found_similar"]) / total_quotes * 100, 1)
        results["exact_match_rate"] = round(results["quotes_found_exact"] / total_quotes * 100, 1)
    
    # Calculate percentage of quotes that couldn't be found
    unverified_percentage = round(results["quotes_not_found"] / total_quotes * 100, 1) if total_quotes > 0 else 0
    
    # Print summary
    print("\n===== Lookup Table Quote Verification Results =====")
    print(f"Total lookup entries: {results['total_lookup_entries']}")
    print(f"Total comments represented: {results['total_comments_represented']}")
    print(f"Lookup entries with quotes: {results['entries_with_quotes']}")
    print(f"Quotes found (exact): {results['quotes_found_exact']} ({results.get('exact_match_rate', 0)}%)")
    print(f"Quotes found (similar): {results['quotes_found_similar']} ({round(results['quotes_found_similar']/total_quotes*100, 1) if total_quotes > 0 else 0}%)")
    print(f"Quotes NOT found: {results['quotes_not_found']} ({unverified_percentage}%)")
    print(f"Overall verification rate: {results['verification_rate']}%")
    
    # Print problematic quotes
    if results["problematic_quotes"]:
        print(f"\n===== {len(results['problematic_quotes'])} Problematic Quotes =====")
        for i, problem in enumerate(results["problematic_quotes"], 1):
            print(f"\n{i}. {problem['lookup_id']} (represents {problem['comment_count']} comments)")
            print(f"   Quote: \"{problem['quote']}\"")
            print(f"   Issue: {problem['match_info']}")
            print(f"   Comment IDs: {', '.join(problem['comment_ids'][:3])}{'...' if len(problem['comment_ids']) > 3 else ''}")
            if problem['match_type'] == 'not_found':
                print(f"   Text sample: {problem['truncated_text']}")
    
    # Save results
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed verification results saved to {output_file}")
    
    return results

def main():
    """Parse arguments and run the verification."""
    parser = argparse.ArgumentParser(description='Verify quotes in analyzed lookup table')
    parser.add_argument('--input', type=str, required=True,
                        help='Path to analyzed lookup table JSON file (lookup_table_analyzed.json)')
    parser.add_argument('--output', type=str, default=None,
                        help='Path to save verification results (default: lookup_quote_verification.json in same directory as input)')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} does not exist")
        return 1
    
    # Set default output file if not provided
    if args.output is None:
        output_dir = os.path.dirname(args.input)
        output_file = os.path.join(output_dir, "lookup_quote_verification.json")
    else:
        output_file = args.output
    
    # Verify quotes
    verify_lookup_quotes(args.input, output_file)
    return 0

if __name__ == "__main__":
    exit(main())