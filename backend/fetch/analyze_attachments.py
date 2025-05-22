#!/usr/bin/env python3
"""
Analyze attachment text extraction from a results folder.

This script:
1. Analyzes a results directory to find all attachments
2. Checks if text extraction was successful for each attachment type
3. Reports statistics on extraction success by file type
4. Copies problematic files to organized folders for manual review
"""

import os
import json
import argparse
import shutil
import re
import string
from collections import defaultdict
from pathlib import Path


def is_coherent_english_text(text: str) -> bool:
    """
    Check if extracted text looks like coherent English, focusing on detecting OCR gibberish.
    Allows short coherent text like "yeah, no" but rejects garbled OCR output.
    
    Args:
        text: The extracted text to check
    
    Returns:
        True if text appears to be coherent English, False if it's gibberish
    """
    if not text or len(text.strip()) < 2:
        return False
    
    text = text.strip()
    
    # Quick pass for very short text - just check it's not mostly symbols
    if len(text) <= 20:
        alpha_chars = sum(1 for c in text if c.isalpha())
        if alpha_chars < 2:  # At least 2 letters
            return False
        weird_chars = sum(1 for c in text if c in '@#$%^&*~`|\\{}[]<>')
        if weird_chars > 2:  # Too many weird symbols
            return False
        return True
    
    # For longer text, do more comprehensive checks
    words = text.split()
    if len(words) == 0:
        return False
    
    # Check 1: Ratio of alphabetic characters should be reasonable
    alpha_chars = sum(1 for c in text if c.isalpha())
    total_chars = len(text)
    alpha_ratio = alpha_chars / total_chars if total_chars > 0 else 0
    
    if alpha_ratio < 0.5:  # Less than 50% alphabetic characters
        return False
    
    # Check 2: Average word length should be reasonable (1-20 characters)
    clean_words = [word.strip(string.punctuation) for word in words if word.strip(string.punctuation)]
    if not clean_words:
        return False
        
    avg_word_length = sum(len(word) for word in clean_words) / len(clean_words)
    if avg_word_length < 1 or avg_word_length > 20:
        return False
    
    # Check 3: Not too many single-character "words" (common in OCR failures)
    single_char_words = sum(1 for word in clean_words if len(word) == 1)
    if len(clean_words) > 5 and single_char_words / len(clean_words) > 0.4:  # More than 40% single chars
        return False
    
    # Check 4: Shouldn't have excessive weird characters
    weird_chars = sum(1 for c in text if c in '@#$%^&*~`|\\{}[]<>')
    if weird_chars > len(text) * 0.15:  # More than 15% weird characters
        return False
    
    # Check 5: For longer text, should have some common English words
    if len(words) >= 10:
        common_words = {'the', 'and', 'to', 'of', 'a', 'in', 'is', 'it', 'you', 'that', 'he', 'was', 'for', 'on', 'are', 'as', 'with', 'his', 'they', 'i', 'at', 'be', 'this', 'have', 'from', 'or', 'one', 'had', 'by', 'word', 'but', 'not', 'what', 'all', 'were', 'we', 'when', 'your', 'can', 'said', 'there', 'each', 'which', 'she', 'do', 'how', 'their', 'if', 'will', 'up', 'other', 'about', 'out', 'many', 'then', 'them', 'these', 'so', 'some', 'her', 'would', 'make', 'like', 'into', 'him', 'has', 'two', 'more', 'very', 'know', 'just', 'first', 'get', 'over', 'think', 'also', 'back', 'after', 'use', 'work', 'life', 'only', 'new', 'way', 'may', 'say', 'no', 'yes', 'good', 'bad', 'well', 'see', 'come', 'go', 'take', 'give'}
        
        # Convert to lowercase and remove punctuation for comparison
        clean_words_lower = [word.lower().strip(string.punctuation) for word in words]
        common_word_count = sum(1 for word in clean_words_lower if word in common_words)
        common_word_ratio = common_word_count / len(words)
        
        if common_word_ratio < 0.05:  # Less than 5% common words in longer text
            return False
    
    # Check 6: Shouldn't be mostly repeated characters or patterns
    repeated_char_pattern = re.findall(r'(.)\1{4,}', text)  # 5+ same chars in a row
    if len(repeated_char_pattern) > 3:
        return False
    
    # Check 7: Detect common OCR garbage patterns
    # Too many isolated letters with spaces
    isolated_letters = re.findall(r'\b[a-zA-Z]\b', text)
    if len(words) > 5 and len(isolated_letters) > len(words) * 0.3:
        return False
    
    return True


def sanitize_filename(filename):
    """Sanitize a filename for safe filesystem use."""
    # Replace problematic characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Limit length to avoid filesystem issues
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200-len(ext)] + ext
    
    return filename


def copy_problematic_files(results_dir, files_with_minimal_text, attachment_texts_map):
    """
    Copy files with no text or minimal text to organized folders.
    
    Args:
        results_dir: Path to the results directory
        files_with_minimal_text: List of files with extraction issues
        attachment_texts_map: Mapping of file paths to extracted text
    """
    # Create analysis folder in the results directory
    analysis_dir = os.path.join(results_dir, "text_extraction_analysis")
    no_text_dir = os.path.join(analysis_dir, "no_text")
    small_text_dir = os.path.join(analysis_dir, "small_text")
    
    # Create directories if they don't exist
    os.makedirs(no_text_dir, exist_ok=True)
    os.makedirs(small_text_dir, exist_ok=True)
    
    print(f"\n=== COPYING PROBLEMATIC FILES ===")
    print(f"Analysis folder: {analysis_dir}")
    
    copied_no_text = 0
    copied_small_text = 0
    failed_copies = []
    
    for file_info in files_with_minimal_text:
        original_path = file_info['path']
        text_length = file_info['length']
        ext = file_info['ext']
        
        # Check if original file exists
        if not os.path.exists(original_path):
            failed_copies.append(f"File not found: {original_path}")
            continue
        
        try:
            # Get the base filename
            base_filename = os.path.basename(original_path)
            
            if text_length == 0:
                # No text extracted - copy to no_text folder
                dest_path = os.path.join(no_text_dir, base_filename)
                
                # Handle filename conflicts
                counter = 1
                while os.path.exists(dest_path):
                    name, extension = os.path.splitext(base_filename)
                    dest_path = os.path.join(no_text_dir, f"{name}_{counter}{extension}")
                    counter += 1
                
                shutil.copy2(original_path, dest_path)
                copied_no_text += 1
                
            else:
                # Small amount of text - copy to small_text folder with text info
                extracted_text = attachment_texts_map.get(original_path, "")
                
                # Create a descriptive filename that includes text preview
                text_preview = extracted_text.strip().replace('\n', ' ').replace('\r', ' ')[:100]
                text_preview = sanitize_filename(text_preview)
                
                name, extension = os.path.splitext(base_filename)
                if text_preview:
                    new_filename = f"{name}__TEXT__{text_preview}__{text_length}chars{extension}"
                else:
                    new_filename = f"{name}__NO_READABLE_TEXT__{text_length}chars{extension}"
                
                new_filename = sanitize_filename(new_filename)
                dest_path = os.path.join(small_text_dir, new_filename)
                
                # Handle filename conflicts
                counter = 1
                while os.path.exists(dest_path):
                    name_part, ext_part = os.path.splitext(new_filename)
                    dest_path = os.path.join(small_text_dir, f"{name_part}_{counter}{ext_part}")
                    counter += 1
                
                shutil.copy2(original_path, dest_path)
                
                # Also create a text file with the full extracted text
                text_file_path = dest_path + ".extracted_text.txt"
                with open(text_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Original file: {original_path}\n")
                    f.write(f"Text length: {text_length} characters\n")
                    f.write(f"File extension: {ext}\n")
                    f.write("=" * 50 + "\n")
                    f.write("EXTRACTED TEXT:\n")
                    f.write("=" * 50 + "\n")
                    f.write(extracted_text if extracted_text else "(no text extracted)")
                
                copied_small_text += 1
                
        except Exception as e:
            failed_copies.append(f"Failed to copy {original_path}: {str(e)}")
    
    # Report results
    print(f"Files copied to no_text folder: {copied_no_text}")
    print(f"Files copied to small_text folder: {copied_small_text}")
    
    if failed_copies:
        print(f"\nFailed to copy {len(failed_copies)} files:")
        for failure in failed_copies:
            print(f"  {failure}")
    
    # Create summary file
    summary_path = os.path.join(analysis_dir, "analysis_summary.txt")
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("TEXT EXTRACTION ANALYSIS SUMMARY\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"Analysis date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Results directory: {results_dir}\n\n")
        f.write(f"Files with no text extraction: {copied_no_text}\n")
        f.write(f"Files with minimal text extraction: {copied_small_text}\n")
        f.write(f"Total problematic files: {len(files_with_minimal_text)}\n\n")
        
        if failed_copies:
            f.write("FAILED COPIES:\n")
            for failure in failed_copies:
                f.write(f"  {failure}\n")
    
    print(f"\nAnalysis summary saved to: {summary_path}")


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

    # Track text extraction success and build text mapping
    files_with_minimal_text = []  # List to store files with failed or minimal text extraction
    attachment_texts_map = {}  # Map file paths to their extracted text
    MIN_TEXT_LENGTH = 50  # Threshold for minimal text (less than 50 characters)
    
    for item in data:
        if 'attributes' in item and 'attachment_texts' in item['attributes']:
            for att in item['attributes'].get('attachment_texts', []):
                if 'file_path' in att:
                    path = att['file_path']
                    ext = path.split('.')[-1].lower() if '.' in path else 'unknown'
                    text = att.get('text', '')
                    text_length = len(text.strip()) if text else 0
                    
                    # Store the text for later use
                    attachment_texts_map[path] = text
                    
                    # Check if text looks like coherent English
                    is_coherent = is_coherent_english_text(text) if text else False
                    
                    # If text is incoherent, treat it as no text
                    if text and not is_coherent:
                        print(f"Incoherent text detected, treating as no text: {path}")
                        text = ""
                        text_length = 0
                        # Update the mapping to empty for copying purposes
                        attachment_texts_map[path] = ""
                    
                    has_text = text and text_length > 20  # More than 20 chars is considered successful
                    
                    extracted_by_type[ext]['total'] += 1
                    if has_text:
                        extracted_by_type[ext]['with_text'] += 1
                        extracted_by_type[ext]['text_length'] += text_length
                    
                    # Check if text extraction failed or was minimal
                    if text_length < MIN_TEXT_LENGTH:
                        files_with_minimal_text.append({
                            'path': path,
                            'length': text_length,
                            'ext': ext
                        })
    
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
    
    # Print files with failed or minimal text extraction
    print(f"\n=== FILES WITH FAILED OR MINIMAL TEXT EXTRACTION (< {MIN_TEXT_LENGTH} chars) ===")
    print(f"Total files with minimal or no text: {len(files_with_minimal_text)}")
    
    # Sort by file extension and then by text length
    for file_info in sorted(files_with_minimal_text, key=lambda x: (x['ext'], x['length'])):
        print(f"{file_info['ext']}: {file_info['path']} ({file_info['length']} chars)")
    
    # Copy problematic files to organized folders
    if files_with_minimal_text:
        copy_problematic_files(results_dir, files_with_minimal_text, attachment_texts_map)
    
    return {
        'file_types': dict(file_types),
        'extraction_stats': {k: dict(v) for k, v in extracted_by_type.items()},
        'files_with_minimal_text': files_with_minimal_text
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