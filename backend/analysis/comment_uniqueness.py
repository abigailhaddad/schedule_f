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
            'top_duplicates': comment_counts.most_common(10)
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
        print(f"  Unique texts that appear >1 time: {stats['unique_duplicate_texts']:,}")
        print(f"  Total instances of duplicated texts: {stats['total_duplicate_instances']:,}")
        
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

def create_uniqueness_curve(results, output_dir=None):
    """Create a line plot showing how uniqueness changes with text length"""
    # Get numeric lengths and sort them
    numeric_lengths = [k for k in results.keys() if k != 'full' and isinstance(k, int)]
    numeric_lengths.sort()
    
    # Add some intermediate points if needed
    all_points = numeric_lengths + ['full']
    
    x_values = []
    y_values = []
    labels = []
    
    for i, length in enumerate(all_points):
        if length == 'full':
            # Use a large number for x-axis but label it as "Full"
            x_values.append(max(numeric_lengths) * 1.5)
            labels.append('Full')
        else:
            x_values.append(length)
            labels.append(str(length))
        
        y_values.append(results[length]['uniqueness_rate'])
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    
    # Plot the line
    plt.plot(x_values[:-1], y_values[:-1], 'o-', linewidth=2, markersize=8, color='steelblue', label='Truncated text')
    
    # Add the "full" point with a different marker
    plt.plot(x_values[-1], y_values[-1], 'o', markersize=10, color='darkgreen', label='Full text')
    
    # Add value labels
    for x, y, label in zip(x_values, y_values, labels):
        plt.annotate(f'{y:.1f}%', xy=(x, y), xytext=(0, 10), 
                    textcoords='offset points', ha='center', fontsize=9)
    
    plt.xlabel('Characters Used')
    plt.ylabel('Uniqueness Rate (%)')
    plt.title('Comment Uniqueness vs Text Length Used')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Set x-axis labels
    plt.xticks(x_values, labels)
    
    # Set y-axis limits
    plt.ylim(min(y_values) - 5, 100)
    
    plt.tight_layout()
    
    if output_dir:
        plot_path = os.path.join(output_dir, 'uniqueness_curve.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"📊 Uniqueness curve saved to: {plot_path}")
    
    plt.show()

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
    
    # Print report
    print_uniqueness_report(results)
    
    # Create visualizations
    if not args.no_plots or not args.no_save:
        output_dir = os.path.dirname(input_file) if not args.no_save else None
        plot_uniqueness_analysis(results, output_dir)
        create_uniqueness_curve(results, output_dir)
    
    print("\n✅ Analysis complete!")

if __name__ == "__main__":
    main()