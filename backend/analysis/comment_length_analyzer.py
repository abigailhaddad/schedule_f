#!/usr/bin/env python3
"""
Comment Length Analyzer

This script analyzes the length distribution of comments in the raw_data.json file
to help determine what semantic model to use for clustering.

Usage:
python comment_length_analyzer.py [--input path/to/file.json]
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

def find_most_recent_raw_data():
    """Find the most recent raw_data.json file"""
    # Get the directory where this script is located (backend/analysis/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Go up two levels to get to project root: backend/analysis/ -> backend/ -> root/
    project_root = os.path.dirname(os.path.dirname(script_dir))
    results_base = os.path.join(project_root, "results")
    
    print(f"🔍 Looking for results in: {results_base}")
    
    if os.path.exists(results_base):
        # Find the most recent results directory with raw_data.json
        result_dirs = glob.glob(os.path.join(results_base, "results_*"))
        print(f"📁 Found {len(result_dirs)} results directories")
        
        if result_dirs:
            # Sort by creation time (newest first)
            result_dirs.sort(key=os.path.getctime, reverse=True)
            for result_dir in result_dirs:
                raw_data_path = os.path.join(result_dir, "raw_data.json")
                if os.path.exists(raw_data_path):
                    print(f"✅ Most recent raw_data.json: {raw_data_path}")
                    return raw_data_path
                else:
                    print(f"⚠️  No raw_data.json in {result_dir}")
    else:
        print(f"❌ Results directory not found: {results_base}")
    
    # Fallback: look in project root
    current_dir_file = os.path.join(project_root, "raw_data.json")
    if os.path.exists(current_dir_file):
        print(f"📁 Fallback: found raw_data.json in project root")
        return current_dir_file
    
    return None

def extract_comment_text(comment_data):
    """Extract comment text from the JSON structure"""
    if isinstance(comment_data, dict) and 'attributes' in comment_data:
        attributes = comment_data['attributes']
        comment_text = strip_html_tags(attributes.get('comment', ''))
        
        # Add attachment text if available
        attachment_texts = attributes.get('attachment_texts', [])
        if attachment_texts:
            for attachment in attachment_texts:
                attachment_text = strip_html_tags(attachment.get('text', ''))
                if attachment_text:
                    comment_text += f"\n\n{attachment_text}"
        
        return comment_text
    elif isinstance(comment_data, dict) and 'comment' in comment_data:
        return strip_html_tags(comment_data.get('comment', ''))
    
    return ""

def analyze_lengths_from_text(all_comments):
    """Analyze comment lengths from a list of comment texts"""
    lengths = []
    word_counts = []
    char_counts = []
    empty_comments = 0
    
    for text in all_comments:
        if not text.strip():
            empty_comments += 1
            continue
            
        # Character count
        char_count = len(text)
        char_counts.append(char_count)
        
        # Word count (rough)
        word_count = len(text.split())
        word_counts.append(word_count)
        
        # Token estimate (rough approximation: ~4 chars per token)
        token_estimate = char_count / 4
        lengths.append(token_estimate)
    
    if not lengths:
        return None
    
    # Calculate statistics
    stats = {
        'total_comments': len(all_comments),
        'non_empty_comments': len(lengths),
        'empty_comments': empty_comments,
        'char_stats': {
            'min': min(char_counts),
            'max': max(char_counts),
            'mean': np.mean(char_counts),
            'median': np.median(char_counts),
            'std': np.std(char_counts),
            'percentiles': {
                '25th': np.percentile(char_counts, 25),
                '75th': np.percentile(char_counts, 75),
                '90th': np.percentile(char_counts, 90),
                '95th': np.percentile(char_counts, 95),
                '99th': np.percentile(char_counts, 99)
            }
        },
        'word_stats': {
            'min': min(word_counts),
            'max': max(word_counts),
            'mean': np.mean(word_counts),
            'median': np.median(word_counts),
            'std': np.std(word_counts),
            'percentiles': {
                '25th': np.percentile(word_counts, 25),
                '75th': np.percentile(word_counts, 75),
                '90th': np.percentile(word_counts, 90),
                '95th': np.percentile(word_counts, 95),
                '99th': np.percentile(word_counts, 99)
            }
        },
        'token_estimates': {
            'min': min(lengths),
            'max': max(lengths),
            'mean': np.mean(lengths),
            'median': np.median(lengths),
            'std': np.std(lengths),
            'percentiles': {
                '25th': np.percentile(lengths, 25),
                '75th': np.percentile(lengths, 75),
                '90th': np.percentile(lengths, 90),
                '95th': np.percentile(lengths, 95),
                '99th': np.percentile(lengths, 99)
            }
        }
    }
    
    return stats, char_counts, word_counts, lengths

def analyze_duplicates_with_stance(all_comments, analyzed_data, prefix_lengths=[25, 50, 100]):
    """Analyze comment duplicates by first N characters and their relationship to stance"""
    print(f"\n🔍 DUPLICATE ANALYSIS:")
    print(f"=" * 50)
    
    duplicate_stats = {}
    
    for n in prefix_lengths:
        print(f"\nAnalyzing duplicates by first {n} characters...")
        
        # Get first n characters of each comment and track stance 
        prefixes = []
        prefix_to_stances = {}  # Map prefix to list of stances
        
        for i, comment_text in enumerate(all_comments):
            prefix = comment_text[:n] if len(comment_text) >= n else comment_text
            prefixes.append(prefix)
            
            # Get stance from analyzed data (same index since we're using data.json throughout)
            stance = 'Unknown'
            if i < len(analyzed_data) and isinstance(analyzed_data[i], dict):
                stance = analyzed_data[i].get('stance', 'Unknown')
            
            if prefix not in prefix_to_stances:
                prefix_to_stances[prefix] = []
            prefix_to_stances[prefix].append(stance)
        
        # Count occurrences of each prefix
        prefix_counts = Counter(prefixes)
        
        # Find duplicates (prefixes that appear more than once)
        duplicates = {prefix: count for prefix, count in prefix_counts.items() if count > 1}
        
        total_duplicate_comments = sum(duplicates.values())
        unique_duplicate_prefixes = len(duplicates)
        
        # Analyze stance distribution for duplicates vs unique comments
        stance_analysis = analyze_stance_duplicates(prefix_counts, prefix_to_stances, duplicates)
        
        duplicate_stats[n] = {
            'total_comments': len(all_comments),
            'unique_prefixes': len(prefix_counts),
            'duplicate_prefixes': unique_duplicate_prefixes,
            'total_duplicate_comments': total_duplicate_comments,
            'duplicate_rate': total_duplicate_comments / len(all_comments) * 100,
            'prefix_counts': prefix_counts,
            'duplicates': duplicates,
            'stance_analysis': stance_analysis,
            'prefix_to_stances': prefix_to_stances  # Add this for plotting
        }
        
        print(f"  Total comments: {len(all_comments):,}")
        print(f"  Unique {n}-char prefixes: {len(prefix_counts):,}")
        print(f"  Duplicate prefixes: {unique_duplicate_prefixes:,}")
        print(f"  Comments with duplicate prefixes: {total_duplicate_comments:,} ({total_duplicate_comments/len(all_comments)*100:.1f}%)")
        
        # Show stance analysis
        if stance_analysis:
            print(f"\n  📊 STANCE vs DUPLICATES:")
            print(f"    Unique comments by stance:")
            for stance, count in stance_analysis['unique_by_stance'].items():
                total_stance = stance_analysis['total_by_stance'].get(stance, 0)
                pct = count / total_stance * 100 if total_stance > 0 else 0
                print(f"      {stance}: {count:,} unique / {total_stance:,} total ({pct:.1f}% unique)")
        
        # Show top duplicates
        if duplicates:
            top_duplicates = sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"  Top duplicate prefixes:")
            for i, (prefix, count) in enumerate(top_duplicates, 1):
                preview = prefix[:40] + "..." if len(prefix) > 40 else prefix
                stance_info = ""
                if prefix in prefix_to_stances:
                    stance_counts = Counter(prefix_to_stances[prefix])
                    stance_info = f" [{', '.join(f'{s}:{c}' for s, c in stance_counts.most_common(3))}]"
                print(f"    {i}. '{preview}' ({count} occurrences{stance_info})")
    
    return duplicate_stats

def analyze_stance_duplicates(prefix_counts, prefix_to_stances, duplicates):
    """Analyze the relationship between stance and duplicate status"""
    stance_stats = {
        'total_by_stance': Counter(),
        'unique_by_stance': Counter(),
        'duplicate_by_stance': Counter()
    }
    
    # Count total comments by stance
    for prefix, stances in prefix_to_stances.items():
        for stance in stances:
            stance_stats['total_by_stance'][stance] += 1
            
            # Count unique vs duplicate by stance
            if prefix_counts[prefix] == 1:  # Unique prefix
                stance_stats['unique_by_stance'][stance] += 1
            else:  # Duplicate prefix
                stance_stats['duplicate_by_stance'][stance] += 1
    
    return stance_stats

def plot_duplicate_analysis(duplicate_stats, output_dir=None):
    """Create visualizations for duplicate analysis with stance-colored stacked bars"""
    # Focus on 50-character duplicates for the main visualization
    if 50 not in duplicate_stats or not duplicate_stats[50]['duplicates']:
        print("No duplicates found for visualization")
        return
    
    # Get stance mapping data
    prefix_to_stances = duplicate_stats[50].get('prefix_to_stances', {})
    
    duplicates_50 = duplicate_stats[50]['duplicates']
    # Filter to only show actual duplicates (count > 1) and get top 15
    actual_duplicates = [(prefix, count) for prefix, count in duplicates_50.items() if count > 1]
    top_duplicates = sorted(actual_duplicates, key=lambda x: x[1], reverse=True)[:15]
    
    if not top_duplicates:
        print("No duplicates found for 50-character prefixes")
        return
    
    # Define stance colors
    stance_colors = {
        'Against': '#e74c3c',      # Red
        'For': '#27ae60',          # Green  
        'Neutral/Unclear': '#f39c12',  # Orange
        'Unknown': '#95a5a6'       # Gray
    }
    
    labels = []
    stance_data = {}  # Will store stance counts for each prefix
    
    for prefix, count in top_duplicates:
        # Get first 50 characters and clean up for display
        display_prefix = prefix[:50]
        display_prefix = display_prefix.replace('\n', ' ').replace('\r', ' ')
        display_prefix = ' '.join(display_prefix.split())
        
        if len(display_prefix) > 47:
            display_prefix = display_prefix[:47] + "..."
        
        labels.append(display_prefix)
        
        # Get actual stance counts for this prefix
        if prefix in prefix_to_stances:
            stance_counts = Counter(prefix_to_stances[prefix])
            stance_data[prefix] = {
                'Against': stance_counts.get('Against', 0),
                'For': stance_counts.get('For', 0),
                'Neutral/Unclear': stance_counts.get('Neutral/Unclear', 0),
                'Unknown': stance_counts.get('Unknown', 0)
            }
        else:
            # Fallback if no stance data
            stance_data[prefix] = {'Against': 0, 'For': 0, 'Neutral/Unclear': 0, 'Unknown': count}
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Prepare data for stacked bars
    y_pos = range(len(labels))
    
    # Create stacked horizontal bars
    bottoms = [0] * len(labels)
    
    for stance, color in stance_colors.items():
        counts = []
        for prefix, _ in top_duplicates:
            count = stance_data[prefix].get(stance, 0)
            counts.append(count)
        
        # Only create bars if there's data for this stance
        if any(counts):
            bars = ax.barh(y_pos, counts, left=bottoms, color=color, alpha=0.8, label=stance)
            
            # Update bottoms for stacking
            bottoms = [b + c for b, c in zip(bottoms, counts)]
    
    # If no stance data, fall back to simple bars
    if all(b == 0 for b in bottoms):
        print("No stance information available, showing simple count bars")
        counts = [count for prefix, count in top_duplicates]
        ax.barh(y_pos, counts, color='steelblue', alpha=0.7)
        bottoms = counts
    
    # Customize the plot
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel('Number of Comments with This Prefix')
    ax.set_title('Top Duplicate Comment Prefixes by Stance (First 50 Characters)', fontsize=14, pad=20)
    
    # Add count labels on the bars
    for i, total_count in enumerate(bottoms):
        if total_count > 0:
            ax.text(total_count + 0.1, i, str(int(total_count)), va='center', fontsize=9)
    
    # Invert y-axis so highest counts are at top
    ax.invert_yaxis()
    
    # Add legend if we have stance data
    if any(stance in stance_colors for stance in stance_colors if any(stance_data[prefix].get(stance, 0) for prefix, _ in top_duplicates)):
        ax.legend(loc='lower right')
    
    # Add grid for easier reading
    ax.grid(axis='x', alpha=0.3)
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Add summary text
    total_duplicates = sum(count for _, count in top_duplicates)
    total_comments = duplicate_stats[50]['total_comments']
    duplicate_rate = total_duplicates / total_comments * 100
    
    fig.text(0.02, 0.02, 
             f"Total comments: {total_comments:,} | Comments with duplicate prefixes: {total_duplicates:,} ({duplicate_rate:.1f}%)",
             fontsize=10, style='italic')
    
    if output_dir:
        plot_path = os.path.join(output_dir, 'comment_duplicate_analysis.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"📊 Duplicate analysis plot saved to: {plot_path}")
    
    plt.show()

def recommend_models(stats):
    """Recommend semantic models based on length statistics"""
    recommendations = []
    
    max_tokens = stats['token_estimates']['max']
    p95_tokens = stats['token_estimates']['percentiles']['95th']
    median_tokens = stats['token_estimates']['median']
    
    print(f"\n🤖 MODEL RECOMMENDATIONS:")
    print(f"=" * 50)
    
    # Short context models (good for most comments)
    if median_tokens <= 256:
        recommendations.append({
            'model': 'sentence-transformers/all-MiniLM-L6-v2',
            'max_tokens': 256,
            'dimensions': 384,
            'reason': 'Fast, lightweight, good for short texts'
        })
        recommendations.append({
            'model': 'sentence-transformers/all-mpnet-base-v2',
            'max_tokens': 384,
            'dimensions': 768,
            'reason': 'Better quality, still efficient for most comments'
        })
    
    # Medium context models
    if p95_tokens <= 512:
        recommendations.append({
            'model': 'sentence-transformers/all-MiniLM-L12-v2',
            'max_tokens': 512,
            'dimensions': 384,
            'reason': 'Good balance for medium-length comments'
        })
    
    # Long context models
    if max_tokens > 512:
        recommendations.append({
            'model': 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
            'max_tokens': 512,
            'dimensions': 768,
            'reason': 'Handles longer texts well (will truncate longest comments)'
        })
        
        if max_tokens > 1000:
            recommendations.append({
                'model': 'sentence-transformers/gtr-t5-large',
                'max_tokens': 512,
                'dimensions': 768,
                'reason': 'High quality but slower, good for complex clustering'
            })
    
    # OpenAI options
    recommendations.append({
        'model': 'text-embedding-3-small (OpenAI API)',
        'max_tokens': 8192,
        'dimensions': 1536,
        'reason': 'Handles all comment lengths, requires API key'
    })
    
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['model']}")
        print(f"   Max tokens: {rec['max_tokens']}, Dimensions: {rec['dimensions']}")
        print(f"   Why: {rec['reason']}")
        print()
    
    return recommendations

def plot_distributions(char_counts, word_counts, token_estimates, output_dir=None):
    """Create distribution plots"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Comment Length Distributions', fontsize=16)
    
    # Character count histogram
    axes[0, 0].hist(char_counts, bins=50, alpha=0.7, color='blue')
    axes[0, 0].set_title('Character Count Distribution')
    axes[0, 0].set_xlabel('Characters')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].axvline(np.median(char_counts), color='red', linestyle='--', label=f'Median: {np.median(char_counts):.0f}')
    axes[0, 0].legend()
    
    # Word count histogram
    axes[0, 1].hist(word_counts, bins=50, alpha=0.7, color='green')
    axes[0, 1].set_title('Word Count Distribution')
    axes[0, 1].set_xlabel('Words')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].axvline(np.median(word_counts), color='red', linestyle='--', label=f'Median: {np.median(word_counts):.0f}')
    axes[0, 1].legend()
    
    # Token estimate histogram
    axes[1, 0].hist(token_estimates, bins=50, alpha=0.7, color='purple')
    axes[1, 0].set_title('Token Estimate Distribution')
    axes[1, 0].set_xlabel('Estimated Tokens')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].axvline(np.median(token_estimates), color='red', linestyle='--', label=f'Median: {np.median(token_estimates):.0f}')
    axes[1, 0].legend()
    
    # Box plot comparison
    box_data = [char_counts, word_counts, [t*4 for t in token_estimates]]  # Scale tokens back to chars for comparison
    axes[1, 1].boxplot(box_data, labels=['Characters', 'Words', 'Est. Tokens×4'])
    axes[1, 1].set_title('Length Comparison (Box Plot)')
    axes[1, 1].set_ylabel('Count')
    
    plt.tight_layout()
    
    if output_dir:
        plot_path = os.path.join(output_dir, 'comment_length_analysis.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"📊 Plot saved to: {plot_path}")
    
    plt.show()

def print_detailed_stats(stats):
    """Print detailed statistics"""
    print(f"\n📊 DETAILED STATISTICS:")
    print(f"=" * 50)
    print(f"Total comments: {stats['total_comments']:,}")
    print(f"Non-empty comments: {stats['non_empty_comments']:,}")
    print(f"Empty comments: {stats['empty_comments']:,}")
    
    print(f"\n📝 CHARACTER COUNTS:")
    char_stats = stats['char_stats']
    print(f"  Range: {char_stats['min']:,} - {char_stats['max']:,}")
    print(f"  Mean: {char_stats['mean']:.0f}")
    print(f"  Median: {char_stats['median']:.0f}")
    print(f"  Std Dev: {char_stats['std']:.0f}")
    print(f"  25th percentile: {char_stats['percentiles']['25th']:.0f}")
    print(f"  75th percentile: {char_stats['percentiles']['75th']:.0f}")
    print(f"  90th percentile: {char_stats['percentiles']['90th']:.0f}")
    print(f"  95th percentile: {char_stats['percentiles']['95th']:.0f}")
    print(f"  99th percentile: {char_stats['percentiles']['99th']:.0f}")
    
    print(f"\n🔤 WORD COUNTS:")
    word_stats = stats['word_stats']
    print(f"  Range: {word_stats['min']:,} - {word_stats['max']:,}")
    print(f"  Mean: {word_stats['mean']:.0f}")
    print(f"  Median: {word_stats['median']:.0f}")
    print(f"  Std Dev: {word_stats['std']:.0f}")
    print(f"  95th percentile: {word_stats['percentiles']['95th']:.0f}")
    
    print(f"\n🎯 TOKEN ESTIMATES (chars ÷ 4):")
    token_stats = stats['token_estimates']
    print(f"  Range: {token_stats['min']:.0f} - {token_stats['max']:.0f}")
    print(f"  Mean: {token_stats['mean']:.0f}")
    print(f"  Median: {token_stats['median']:.0f}")
    print(f"  95th percentile: {token_stats['percentiles']['95th']:.0f}")

def find_most_recent_data_json():
    """Find the most recent data.json file (analyzed comments)"""
    # Get the directory where this script is located (backend/analysis/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Go up two levels to get to project root: backend/analysis/ -> backend/ -> root/
    project_root = os.path.dirname(os.path.dirname(script_dir))
    results_base = os.path.join(project_root, "results")
    
    print(f"🔍 Looking for results in: {results_base}")
    
    if os.path.exists(results_base):
        # Find the most recent results directory with data.json
        result_dirs = glob.glob(os.path.join(results_base, "results_*"))
        print(f"📁 Found {len(result_dirs)} results directories")
        
        if result_dirs:
            # Sort by creation time (newest first)
            result_dirs.sort(key=os.path.getctime, reverse=True)
            for result_dir in result_dirs:
                data_path = os.path.join(result_dir, "data.json")
                if os.path.exists(data_path):
                    print(f"✅ Most recent data.json: {data_path}")
                    return data_path
                else:
                    print(f"⚠️  No data.json in {result_dir}")
    else:
        print(f"❌ Results directory not found: {results_base}")
    
    return None

def analyze_comment_lengths(input_file=None, show_plots=True, save_plots=True):
    """Main analysis function - now uses data.json (analyzed comments) throughout"""
    # Find input file if not provided - look for data.json instead of raw_data.json
    if input_file is None:
        input_file = find_most_recent_data_json()
        if input_file is None:
            print("❌ Could not find data.json file.")
            print("Please specify the path with --input parameter")
            print("Note: This analyzer now requires analyzed comments (data.json) with stance information")
            return None
        print(f"📁 Found most recent analyzed file: {input_file}")
    
    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return None
    
    # Load the analyzed data (contains both text and stance information)
    print(f"📖 Loading analyzed comments from {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            analyzed_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None
    
    print(f"✅ Loaded {len(analyzed_data):,} analyzed comments with stance data")
    
    # Extract comment texts and create parallel structure for analysis
    all_comments = []
    for comment in analyzed_data:
        if isinstance(comment, dict):
            # Try different fields where comment text might be stored
            text = comment.get('original_comment', '') or comment.get('comment', '') or comment.get('text', '')
            if text:
                all_comments.append(text.strip())
            else:
                all_comments.append('')  # Empty comment
        else:
            all_comments.append('')
    
    print(f"📝 Extracted text from {len([c for c in all_comments if c])} non-empty comments")
    
    # Analyze lengths using the extracted text
    print("🔍 Analyzing comment lengths...")
    result = analyze_lengths_from_text(all_comments)
    
    if result is None:
        print("❌ No valid comments found for analysis")
        return None
    
    stats, char_counts, word_counts, token_estimates = result
    
    # Print statistics
    print_detailed_stats(stats)
    
    # Analyze duplicates using both text and stance data
    duplicate_stats = analyze_duplicates_with_stance(all_comments, analyzed_data)
    
    # Get model recommendations
    recommendations = recommend_models(stats)
    
    # Create plots
    if show_plots or save_plots:
        output_dir = os.path.dirname(input_file) if save_plots else None
        plot_distributions(char_counts, word_counts, token_estimates, output_dir)
        plot_duplicate_analysis(duplicate_stats, output_dir)
    
    return {
        'stats': stats,
        'duplicate_stats': duplicate_stats,
        'recommendations': recommendations,
        'input_file': input_file
    }

def analyze_lengths(comments_data):
    """Analyze comment lengths and return statistics"""
    lengths = []
    word_counts = []
    char_counts = []
    all_comments = []  # Store all comment texts
    empty_comments = 0
    
    for comment in comments_data:
        text = extract_comment_text(comment)
        
        if not text.strip():
            empty_comments += 1
            continue
            
        all_comments.append(text.strip())
        
        # Character count
        char_count = len(text)
        char_counts.append(char_count)
        
        # Word count (rough)
        word_count = len(text.split())
        word_counts.append(word_count)
        
        # Token estimate (rough approximation: ~4 chars per token)
        token_estimate = char_count / 4
        lengths.append(token_estimate)
    
    if not lengths:
        return None
    
    # Calculate statistics
    stats = {
        'total_comments': len(comments_data),
        'non_empty_comments': len(lengths),
        'empty_comments': empty_comments,
        'char_stats': {
            'min': min(char_counts),
            'max': max(char_counts),
            'mean': np.mean(char_counts),
            'median': np.median(char_counts),
            'std': np.std(char_counts),
            'percentiles': {
                '25th': np.percentile(char_counts, 25),
                '75th': np.percentile(char_counts, 75),
                '90th': np.percentile(char_counts, 90),
                '95th': np.percentile(char_counts, 95),
                '99th': np.percentile(char_counts, 99)
            }
        },
        'word_stats': {
            'min': min(word_counts),
            'max': max(word_counts),
            'mean': np.mean(word_counts),
            'median': np.median(word_counts),
            'std': np.std(word_counts),
            'percentiles': {
                '25th': np.percentile(word_counts, 25),
                '75th': np.percentile(word_counts, 75),
                '90th': np.percentile(word_counts, 90),
                '95th': np.percentile(word_counts, 95),
                '99th': np.percentile(word_counts, 99)
            }
        },
        'token_estimates': {
            'min': min(lengths),
            'max': max(lengths),
            'mean': np.mean(lengths),
            'median': np.median(lengths),
            'std': np.std(lengths),
            'percentiles': {
                '25th': np.percentile(lengths, 25),
                '75th': np.percentile(lengths, 75),
                '90th': np.percentile(lengths, 90),
                '95th': np.percentile(lengths, 95),
                '99th': np.percentile(lengths, 99)
            }
        }
    }
    
    return stats, char_counts, word_counts, lengths, all_comments

def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(description='Analyze comment lengths and duplicates with stance information')
    parser.add_argument('--input', type=str, help='Path to input JSON file (default: auto-detect most recent data.json)')
    parser.add_argument('--no-plots', action='store_true', help='Skip showing plots')
    parser.add_argument('--no-save', action='store_true', help='Skip saving plots')
    
    args = parser.parse_args()
    
    show_plots = not args.no_plots
    save_plots = not args.no_save
    
    print("🚀 Starting comment length and duplicate analysis...")
    
    result = analyze_comment_lengths(
        input_file=args.input,
        show_plots=show_plots,
        save_plots=save_plots
    )
    
    if result:
        print(f"\n✅ Analysis complete!")
        print(f"📁 Analyzed file: {result['input_file']}")
        print(f"🎯 Key insight: {result['stats']['token_estimates']['percentiles']['95th']:.0f} tokens covers 95% of comments")
        
        # Show duplicate summary
        if 'duplicate_stats' in result and 50 in result['duplicate_stats']:
            dup_stats = result['duplicate_stats'][50]
            print(f"🔁 Duplicates: {dup_stats['duplicate_rate']:.1f}% of comments share first 50 characters")
    else:
        print("❌ Analysis failed")

if __name__ == "__main__":
    main()