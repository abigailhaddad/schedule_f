#!/usr/bin/env python3
"""
Quote Verifier for Schedule F Analysis

This script verifies that key quotes extracted by the analysis tool are actually 
present in the original comment text. This helps validate the accuracy of the AI's
quote extraction.

Requirements:
- Python 3.8+

Usage:
python -m backend.analysis.verify_quotes --help
"""

import os
import json
import argparse
import glob
import re
from typing import Dict, List, Tuple, Optional, Union

# Import from backend packages
from backend.utils.common import strip_html_tags, get_latest_results_dir

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
    
    # Remove non-alphanumeric chars for looser matching
    # text = re.sub(r'[^\w\s]', '', text)
    
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
            # This is approximate due to the cleaning
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

def verify_quotes(data_file: str, output_file: Optional[str] = None) -> Dict:
    """
    Verify quotes in analyzed comments and generate a report.
    
    Args:
        data_file: Path to the analyzed data file (data.json)
        output_file: Path to save verification results
        
    Returns:
        Dictionary with verification results
    """
    print(f"Loading analyzed data from {data_file}...")
    
    with open(data_file, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: {data_file} is not valid JSON")
            return {}
    
    if not data:
        print("No data found in file")
        return {}
    
    print(f"Loaded {len(data)} analyzed comments")
    
    # Initialize results
    results = {
        "total_comments": len(data),
        "comments_with_quotes": 0,
        "quotes_found_exact": 0,
        "quotes_found_similar": 0,
        "quotes_not_found": 0,
        "verification_rate": 0,
        "problematic_quotes": []
    }
    
    # Verify each comment
    for i, comment in enumerate(data):
        if i % 10 == 0:
            print(f"Verifying comment {i+1}/{len(data)}...")
        
        # Skip comments without quotes or text
        if not comment.get("key_quote") or not comment.get("comment"):
            continue
        
        results["comments_with_quotes"] += 1
        
        # Get the key quote and comment text
        quote = comment.get("key_quote", "").strip()
        comment_text = comment.get("comment", "").strip()
        
        # Verify the quote
        found_exact, match_text, position = find_quote_in_text(quote, comment_text)
        
        if found_exact:
            results["quotes_found_exact"] += 1
        elif match_text:
            results["quotes_found_similar"] += 1
            # Add to problematic quotes for review
            results["problematic_quotes"].append({
                "id": comment.get("id", f"comment_{i}"),
                "title": comment.get("title", ""),
                "quote": quote,
                "match_info": match_text,
                "match_type": "similar"
            })
        else:
            results["quotes_not_found"] += 1
            # Add to problematic quotes
            results["problematic_quotes"].append({
                "id": comment.get("id", f"comment_{i}"),
                "title": comment.get("title", ""),
                "quote": quote,
                "match_info": "Not found in comment text",
                "match_type": "not_found"
            })
    
    # Calculate verification rate
    total_quotes = results["quotes_found_exact"] + results["quotes_found_similar"] + results["quotes_not_found"]
    if total_quotes > 0:
        results["verification_rate"] = round((results["quotes_found_exact"] + results["quotes_found_similar"]) / total_quotes * 100, 1)
    
    # Print summary
    print("\n===== Quote Verification Results =====")
    print(f"Total comments: {results['total_comments']}")
    print(f"Comments with quotes: {results['comments_with_quotes']}")
    print(f"Quotes found (exact): {results['quotes_found_exact']} ({round(results['quotes_found_exact']/total_quotes*100, 1)}%)")
    print(f"Quotes found (similar): {results['quotes_found_similar']} ({round(results['quotes_found_similar']/total_quotes*100, 1)}%)")
    print(f"Quotes not found: {results['quotes_not_found']} ({round(results['quotes_not_found']/total_quotes*100, 1)}%)")
    print(f"Overall verification rate: {results['verification_rate']}%")
    
    # Save results
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed verification results saved to {output_file}")
    
    return results

def main():
    """Parse arguments and run the verification."""
    parser = argparse.ArgumentParser(description='Verify quotes in analyzed comments')
    parser.add_argument('--input', type=str, default=None,
                        help='Path to input JSON file with analyzed comments (default: auto-detect most recent data.json)')
    parser.add_argument('--output', type=str, default=None,
                        help='Path to save verification results (default: quote_verification.json in same directory as input)')
    
    args = parser.parse_args()
    
    # Auto-detect most recent data.json if no input file specified
    input_file = args.input
    if input_file is None:
        # Try to find the most recent results directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        results_base = os.path.join(project_root, "data", "results")
        
        if os.path.exists(results_base):
            latest_dir = get_latest_results_dir(results_base)
            if latest_dir:
                data_path = os.path.join(latest_dir, "data.json")
                if os.path.exists(data_path):
                    input_file = data_path
                    print(f"Auto-detected most recent data file: {input_file}")
        
        # If still not found, look in processed directory
        if input_file is None:
            processed_dir = os.path.join(project_root, "data", "processed")
            if os.path.exists(processed_dir):
                analysis_files = glob.glob(os.path.join(processed_dir, "comment_analysis_*.json"))
                if analysis_files:
                    # Sort by creation time (newest first)
                    analysis_files.sort(key=os.path.getctime, reverse=True)
                    input_file = analysis_files[0]
                    print(f"Auto-detected most recent analysis file: {input_file}")
        
        # If still not found, look in the current directory
        if input_file is None:
            for file in ["data.json", "comments_analyzed.json", "analyzed_comments.json"]:
                if os.path.exists(file):
                    input_file = file
                    print(f"Using {file} from current directory")
                    break
    
    # Check if input file exists
    if not input_file or not os.path.exists(input_file):
        print("Error: No valid input file specified or found")
        print("Please provide a path to an analyzed comments file with --input")
        return 1
    
    # Set default output file if not provided
    if args.output is None:
        output_dir = os.path.dirname(input_file)
        output_file = os.path.join(output_dir, "quote_verification.json")
    else:
        output_file = args.output
    
    # Verify quotes
    verify_quotes(input_file, output_file)
    return 0

if __name__ == "__main__":
    exit(main()) 