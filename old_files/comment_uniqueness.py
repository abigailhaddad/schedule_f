
#!/usr/bin/env python3
"""
Comment Uniqueness Analyzer

This script analyzes how many unique comments exist when considering different
lengths of the comment text (full text vs first N characters).

Usage:
python comment_uniqueness_analyzer.py [--input path/to/data.json]
"""

import os
import json
import glob
import argparse
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter
import re
import sys
from io import StringIO

def strip_html_tags(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def find_most_recent_data_json():
    """Find the most recent data.json file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    results_base = os.path.join(project_root, "results")
    
    print(f"🔍 Looking for results in: {results_base}")
    
    if os.path.exists(results_base):
        result_dirs = glob.glob(os.path.join(results_base, "results_*"))
        print(f"📁 Found {len(result_dirs)} results directories")
        
        if result_dirs:
            result_dirs.sort(key=os.path.getctime, reverse=True)
            for result_dir in result_dirs:
                data_path = os.path.join(result_dir, "data.json")
                if os.path.exists(data_path):
                    print(f"✅ Most recent data.json: {data_path}")
                    return data_path
    
    # Fallback: look in current directory
    current_dir_file = "data.json"
    if os.path.exists(current_dir_file):
        print(f"📁 Found data.json in current directory")
        return current_dir_file
    
    return None

def extract_comment_text(comment_data):
    """Extract comment text from the 'comment' field inside 'attributes'"""
    if isinstance(comment_data, dict) and 'attributes' in comment_data:
        attributes = comment_data.get('attributes', {})
        if 'comment' in attributes:
            # Get the comment field and strip HTML tags
            text = strip_html_tags(attributes['comment'])
            return text.strip()
    
    return ""

def analyze_uniqueness_at_lengths(comments, truncate_lengths):
    """Analyze comment uniqueness at different truncation lengths"""
    results = {}
    
    # Add "full" to the analysis
    all_lengths = ['full'] + truncate_lengths
    
    for length in all_lengths:
        if length == 'full':
            # Use full comment text
            truncated_comments = comments
            label = "Full text"
        else:
            # Truncate to first N characters
            truncated_comments = [comment[:length] if len(comment) > length else comment 
                                for comment in comments]
            label = f"First {length} chars"
        
        # Count occurrences
        comment_counts = Counter(truncated_comments)
        
        # Calculate statistics
        total_comments = len(comments)
        unique_comments = len(comment_counts)
        duplicate_comments = total_comments - unique_comments
        uniqueness_rate = (unique_comments / total_comments * 100) if total_comments > 0 else 0
        
        # Find comments that appear more than once
        duplicated_texts = {text: count for text, count in comment_counts.items() if count > 1}
        total_duplicate_instances = sum(duplicated_texts.values())
        
        # Get distribution of duplicate counts
        duplicate_distribution = Counter(comment_counts.values())
        
        # Calculate token estimates (roughly 4 chars = 1 token)
        # For deduplication: only count unique comments
        total_chars_all = sum(len(comment) for comment in comments)
        total_tokens_all = total_chars_all / 4
        
        # For deduplication at this length: use full text of unique comments based on prefix
        unique_full_comments = []
        seen_prefixes = set()
        for i, comment in enumerate(comments):
            prefix = comment[:length] if length != 'full' else comment
            if prefix not in seen_prefixes:
                seen_prefixes.add(prefix)
                unique_full_comments.append(comment)
        
        total_chars_unique = sum(len(comment) for comment in unique_full_comments)
        total_tokens_unique = total_chars_unique / 4
        
        # For truncation: count truncated text
        total_chars_truncated = sum(len(tc) for tc in truncated_comments)
        total_tokens_truncated = total_chars_truncated / 4
        
        # Token savings
        dedup_token_savings = total_tokens_all - total_tokens_unique
        dedup_savings_pct = (dedup_token_savings / total_tokens_all * 100) if total_tokens_all > 0 else 0
        
        truncate_token_savings = total_tokens_all - total_tokens_truncated
        truncate_savings_pct = (truncate_token_savings / total_tokens_all * 100) if total_tokens_all > 0 else 0
        
        results[length] = {
            'label': label,
            'total_comments': total_comments,
            'unique_comments': unique_comments,
            'duplicate_comments': duplicate_comments,
            'uniqueness_rate': uniqueness_rate,
            'duplication_rate': 100 - uniqueness_rate,
            'unique_duplicate_texts': len(duplicated_texts),
            'total_duplicate_instances': total_duplicate_instances,
            'duplicate_distribution': duplicate_distribution,
            'top_duplicates': comment_counts.most_common(10),
            # Token analysis
            'total_tokens_all': total_tokens_all,
            'total_tokens_unique': total_tokens_unique,
            'total_tokens_truncated': total_tokens_truncated,
            'dedup_token_savings': dedup_token_savings,
            'dedup_savings_pct': dedup_savings_pct,
            'truncate_token_savings': truncate_token_savings,
            'truncate_savings_pct': truncate_savings_pct,
            'comments_kept_dedup': len(unique_full_comments),
            'comments_removed_dedup': total_comments - len(unique_full_comments)
        }
    
    return results

def print_uniqueness_report(results):
    """Print a detailed uniqueness report"""
    print("\n📊 COMMENT UNIQUENESS ANALYSIS")
    print("=" * 70)
    
    # Sort by length (full last)
    sorted_lengths = sorted(results.keys(), key=lambda x: (x == 'full', x))
    
    # Summary table
    print(f"\n{'Length':<20} {'Total':<10} {'Unique':<10} {'Duplicates':<12} {'Uniqueness %':<15}")
    print("-" * 70)
    
    for length in sorted_lengths:
        stats = results[length]
        print(f"{stats['label']:<20} {stats['total_comments']:<10,} {stats['unique_comments']:<10,} "
              f"{stats['duplicate_comments']:<12,} {stats['uniqueness_rate']:<15.1f}")
    
    # Token savings analysis
    print("\n\n💰 TOKEN SAVINGS ANALYSIS")
    print("=" * 70)
    
    # Get baseline tokens from full text
    baseline_tokens = results['full']['total_tokens_all']
    print(f"Baseline: {baseline_tokens:,.0f} tokens for all {results['full']['total_comments']:,} comments")
    
    print(f"\n{'Strategy':<30} {'Comments':<12} {'Tokens':<15} {'Savings':<15} {'% Saved':<10}")
    print("-" * 85)
    
    for length in sorted_lengths:
        stats = results[length]
        
        # Deduplication strategy
        if length != 'full':
            dedup_label = f"Dedup by first {length} chars"
        else:
            dedup_label = "Dedup by full text"
            
        print(f"{dedup_label:<30} {stats['comments_kept_dedup']:<12,} "
              f"{stats['total_tokens_unique']:<15,.0f} "
              f"{stats['dedup_token_savings']:<15,.0f} "
              f"{stats['dedup_savings_pct']:<10.1f}")
        
        # Truncation strategy (skip for full text)
        if length != 'full':
            trunc_label = f"Truncate at {length} chars"
            print(f"{trunc_label:<30} {stats['total_comments']:<12,} "
                  f"{stats['total_tokens_truncated']:<15,.0f} "
                  f"{stats['truncate_token_savings']:<15,.0f} "
                  f"{stats['truncate_savings_pct']:<10.1f}")
    
    # Detailed analysis for each length
    print("\n\n📝 DETAILED ANALYSIS BY LENGTH")
    print("=" * 70)
    
    for length in sorted_lengths:
        stats = results[length]
        print(f"\n{stats['label'].upper()}")
        print("-" * len(stats['label']))
        
        print(f"  Total comments: {stats['total_comments']:,}")
        print(f"  Unique comments: {stats['unique_comments']:,} ({stats['uniqueness_rate']:.1f}%)")
        print(f"  Duplicate comments: {stats['duplicate_comments']:,} ({stats['duplication_rate']:.1f}%)")
        
        # Token analysis
        print(f"\n  Token Analysis:")
        print(f"    All comments: {stats['total_tokens_all']:,.0f} tokens")
        if length != 'full':
            print(f"    After dedup (by {length} chars): {stats['total_tokens_unique']:,.0f} tokens "
                  f"({stats['dedup_savings_pct']:.1f}% saved)")
            print(f"    After truncation: {stats['total_tokens_truncated']:,.0f} tokens "
                  f"({stats['truncate_savings_pct']:.1f}% saved)")
        else:
            print(f"    After full dedup: {stats['total_tokens_unique']:,.0f} tokens "
                  f"({stats['dedup_savings_pct']:.1f}% saved)")
        
        # Show distribution of duplicates
        dist = stats['duplicate_distribution']
        if len(dist) > 1:  # If there are duplicates
            print(f"\n  Duplicate frequency distribution:")
            for count, freq in sorted(dist.items()):
                if count > 1:
                    print(f"    {freq:,} texts appear {count} times")
        
        # Show top duplicates
        if stats['unique_duplicate_texts'] > 0:
            print(f"\n  Top duplicated texts:")
            for i, (text, count) in enumerate(stats['top_duplicates'][:5], 1):
                if count > 1:
                    preview = text[:60] + "..." if len(text) > 60 else text
                    # Clean up for display
                    preview = preview.replace('\n', ' ').replace('\r', ' ')
                    preview = ' '.join(preview.split())
                    print(f"    {i}. '{preview}' ({count} times)")

def plot_uniqueness_analysis(results, output_dir=None):
    """Create visualizations for uniqueness analysis"""
    # Prepare data for plotting
    sorted_lengths = sorted([k for k in results.keys() if k != 'full'], key=int)
    all_lengths = sorted_lengths + ['full']
    
    labels = []
    uniqueness_rates = []
    unique_counts = []
    duplicate_counts = []
    
    for length in all_lengths:
        stats = results[length]
        labels.append(stats['label'])
        uniqueness_rates.append(stats['uniqueness_rate'])
        unique_counts.append(stats['unique_comments'])
        duplicate_counts.append(stats['duplicate_comments'])
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot 1: Uniqueness rate
    x_pos = np.arange(len(labels))
    bars = ax1.bar(x_pos, uniqueness_rates, color='steelblue', alpha=0.8)
    
    # Add value labels on bars
    for i, (bar, rate) in enumerate(zip(bars, uniqueness_rates)):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{rate:.1f}%', ha='center', va='bottom')
    
    ax1.set_xlabel('Comment Length')
    ax1.set_ylabel('Uniqueness Rate (%)')
    ax1.set_title('Comment Uniqueness by Text Length')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(labels, rotation=45, ha='right')
    ax1.set_ylim(0, 105)
    ax1.grid(axis='y', alpha=0.3)
    
    # Plot 2: Stacked bar chart of unique vs duplicate
    width = 0.6
    p1 = ax2.bar(x_pos, unique_counts, width, label='Unique', color='#2ecc71', alpha=0.8)
    p2 = ax2.bar(x_pos, duplicate_counts, width, bottom=unique_counts, label='Duplicates', color='#e74c3c', alpha=0.8)
    
    ax2.set_xlabel('Comment Length')
    ax2.set_ylabel('Number of Comments')
    ax2.set_title('Unique vs Duplicate Comments by Text Length')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(labels, rotation=45, ha='right')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    
    # Add count labels
    for i, (unique, dup) in enumerate(zip(unique_counts, duplicate_counts)):
        total = unique + dup
        # Label for unique portion
        if unique > 0:
            ax2.text(i, unique/2, f'{unique:,}', ha='center', va='center', fontsize=9)
        # Label for duplicate portion
        if dup > 0:
            ax2.text(i, unique + dup/2, f'{dup:,}', ha='center', va='center', fontsize=9, color='white')
    
    plt.tight_layout()
    
    if output_dir:
        plot_path = os.path.join(output_dir, 'comment_uniqueness_analysis.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"\n📊 Plot saved to: {plot_path}")
    
    plt.show()

def plot_token_savings(results, output_dir=None):
    """Create visualization for token savings analysis"""
    # Prepare data
    sorted_lengths = sorted([k for k in results.keys() if k != 'full'], key=int)
    
    lengths = []
    dedup_savings = []
    truncate_savings = []
    dedup_comments = []
    
    for length in sorted_lengths:
        stats = results[length]
        lengths.append(stats['label'])
        dedup_savings.append(stats['dedup_savings_pct'])
        truncate_savings.append(stats['truncate_savings_pct'])
        dedup_comments.append(stats['comments_kept_dedup'])
    
    # Also add full dedup
    lengths.append('Full dedup')
    dedup_savings.append(results['full']['dedup_savings_pct'])
    truncate_savings.append(0)  # No truncation for full
    dedup_comments.append(results['full']['comments_kept_dedup'])
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: Token savings comparison
    x = np.arange(len(lengths))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, dedup_savings, width, label='Deduplication', color='#3498db', alpha=0.8)
    bars2 = ax1.bar(x + width/2, truncate_savings[:-1] + [0], width, label='Truncation', color='#e74c3c', alpha=0.8)
    
    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        if height > 0:
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
    
    for bar in bars2:
        height = bar.get_height()
        if height > 0:
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
    
    ax1.set_xlabel('Strategy')
    ax1.set_ylabel('Token Savings (%)')
    ax1.set_title('Token Savings: Deduplication vs Truncation')
    ax1.set_xticks(x)
    ax1.set_xticklabels(lengths, rotation=45, ha='right')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    ax1.set_ylim(0, max(max(dedup_savings), max(truncate_savings)) * 1.1)
    
    # Plot 2: Comments retained with deduplication
    total_comments = results['full']['total_comments']
    retention_pct = [(c / total_comments * 100) for c in dedup_comments]
    
    bars = ax2.bar(x, retention_pct, color='#27ae60', alpha=0.8)
    
    # Add value labels
    for i, (bar, count) in enumerate(zip(bars, dedup_comments)):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{count:,}\n({height:.1f}%)', ha='center', va='bottom', fontsize=9)
    
    ax2.set_xlabel('Deduplication Strategy')
    ax2.set_ylabel('Comments Retained (%)')
    ax2.set_title(f'Comments Retained After Deduplication (Total: {total_comments:,})')
    ax2.set_xticks(x)
    ax2.set_xticklabels(lengths, rotation=45, ha='right')
    ax2.grid(axis='y', alpha=0.3)
    ax2.set_ylim(0, 105)
    
    plt.tight_layout()
    
    if output_dir:
        plot_path = os.path.join(output_dir, 'token_savings_analysis.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"\n📊 Token savings plot saved to: {plot_path}")
    
    plt.show()


def plot_token_savings(results, output_dir=None):
    """Create visualization for token savings analysis"""
    # Prepare data
    sorted_lengths = sorted([k for k in results.keys() if k != 'full'], key=int)
    
    lengths = []
    dedup_savings = []
    truncate_savings = []
    dedup_comments = []
    
    for length in sorted_lengths:
        stats = results[length]
        lengths.append(stats['label'])
        dedup_savings.append(stats['dedup_savings_pct'])
        truncate_savings.append(stats['truncate_savings_pct'])
        dedup_comments.append(stats['comments_kept_dedup'])
    
    # Also add full dedup
    lengths.append('Full dedup')
    dedup_savings.append(results['full']['dedup_savings_pct'])
    truncate_savings.append(0)  # No truncation for full
    dedup_comments.append(results['full']['comments_kept_dedup'])
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: Token savings comparison
    x = np.arange(len(lengths))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, dedup_savings, width, label='Deduplication', color='#3498db', alpha=0.8)
    bars2 = ax1.bar(x + width/2, truncate_savings[:-1] + [0], width, label='Truncation', color='#e74c3c', alpha=0.8)
    
    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        if height > 0:
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
    
    for bar in bars2:
        height = bar.get_height()
        if height > 0:
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
    
    ax1.set_xlabel('Strategy')
    ax1.set_ylabel('Token Savings (%)')
    ax1.set_title('Token Savings: Deduplication vs Truncation')
    ax1.set_xticks(x)
    ax1.set_xticklabels(lengths, rotation=45, ha='right')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    ax1.set_ylim(0, max(max(dedup_savings), max(truncate_savings)) * 1.1)
    
    # Plot 2: Comments retained with deduplication
    total_comments = results['full']['total_comments']
    retention_pct = [(c / total_comments * 100) for c in dedup_comments]
    
    bars = ax2.bar(x, retention_pct, color='#27ae60', alpha=0.8)
    
    # Add value labels
    for i, (bar, count) in enumerate(zip(bars, dedup_comments)):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{count:,}\n({height:.1f}%)', ha='center', va='bottom', fontsize=9)
    
    ax2.set_xlabel('Deduplication Strategy')
    ax2.set_ylabel('Comments Retained (%)')
    ax2.set_title(f'Comments Retained After Deduplication (Total: {total_comments:,})')
    ax2.set_xticks(x)
    ax2.set_xticklabels(lengths, rotation=45, ha='right')
    ax2.grid(axis='y', alpha=0.3)
    ax2.set_ylim(0, 105)
    
    plt.tight_layout()
    
    if output_dir:
        plot_path = os.path.join(output_dir, 'token_savings_analysis.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"\n📊 Token savings plot saved to: {plot_path}")
    
    plt.show()

def save_report_to_file(results, output_dir):
    """Save the uniqueness report to a text file"""
    # Capture the print output
    old_stdout = sys.stdout
    sys.stdout = report_buffer = StringIO()
    
    # Generate the report
    print_uniqueness_report(results)
    
    # Get the report content
    report_content = report_buffer.getvalue()
    
    # Restore stdout
    sys.stdout = old_stdout
    
    # Save to file
    report_path = os.path.join(output_dir, 'comment_uniqueness_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n📄 Report saved to: {report_path}")
    
    # Also print the report to console
    print(report_content)

    
def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(description='Analyze comment uniqueness at different text lengths')
    parser.add_argument('--input', type=str, help='Path to input JSON file (default: auto-detect)')
    parser.add_argument('--lengths', type=int, nargs='+', default=[25, 50, 100, 200, 500],
                       help='Character lengths to analyze (default: 25 50 100 200 500)')
    parser.add_argument('--no-plots', action='store_true', help='Skip showing plots')
    parser.add_argument('--no-save', action='store_true', help='Skip saving plots')
    
    args = parser.parse_args()
    
    # Find input file
    input_file = args.input
    if input_file is None:
        input_file = find_most_recent_data_json()
        if input_file is None:
            print("❌ Could not find data.json file.")
            print("Please specify the path with --input parameter")
            return
    
    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return
    
    # Load data
    print(f"📖 Loading data from {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return
    
    print(f"✅ Loaded {len(data):,} records")
    
    # Extract all comment texts
    print("📝 Extracting comment texts...")
    comments = []
    for item in data:
        text = extract_comment_text(item)
        if text:  # Only include non-empty comments
            comments.append(text)
    
    print(f"✅ Extracted {len(comments):,} non-empty comments")
    
    # Analyze uniqueness at different lengths
    print(f"🔍 Analyzing uniqueness at lengths: {args.lengths} + full text...")
    results = analyze_uniqueness_at_lengths(comments, args.lengths)
    
    # Save and print report
    output_dir = os.path.dirname(input_file)
    save_report_to_file(results, output_dir)
    
    # Create visualizations
    if not args.no_plots or not args.no_save:
        output_dir = os.path.dirname(input_file) if not args.no_save else None
        plot_uniqueness_analysis(results, output_dir)
        plot_token_savings(results, output_dir)
    
    print("\n✅ Analysis complete!")

if __name__ == "__main__":
    main()