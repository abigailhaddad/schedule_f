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

def analyze_lengths(comments_data):
    """Analyze comment lengths and return statistics"""
    lengths = []
    word_counts = []
    char_counts = []
    empty_comments = 0
    
    for comment in comments_data:
        text = extract_comment_text(comment)
        
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
    
    return stats, char_counts, word_counts, lengths

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

def analyze_comment_lengths(input_file=None, show_plots=True, save_plots=True):
    """Main analysis function"""
    # Find input file if not provided
    if input_file is None:
        input_file = find_most_recent_raw_data()
        if input_file is None:
            print("❌ Could not find raw_data.json file.")
            print("Please specify the path with --input parameter")
            return None
        print(f"📁 Found most recent file: {input_file}")
    
    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return None
    
    # Load the data
    print(f"📖 Loading data from {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            comments_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None
    
    print(f"✅ Loaded {len(comments_data):,} comments")
    
    # Analyze lengths
    print("🔍 Analyzing comment lengths...")
    result = analyze_lengths(comments_data)
    
    if result is None:
        print("❌ No valid comments found for analysis")
        return None
    
    stats, char_counts, word_counts, token_estimates = result
    
    # Print statistics
    print_detailed_stats(stats)
    
    # Get model recommendations
    recommendations = recommend_models(stats)
    
    # Create plots
    if show_plots or save_plots:
        output_dir = os.path.dirname(input_file) if save_plots else None
        plot_distributions(char_counts, word_counts, token_estimates, output_dir)
    
    return {
        'stats': stats,
        'recommendations': recommendations,
        'input_file': input_file
    }

def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(description='Analyze comment lengths for semantic model selection')
    parser.add_argument('--input', type=str, help='Path to input JSON file (default: auto-detect most recent raw_data.json)')
    parser.add_argument('--no-plots', action='store_true', help='Skip showing plots')
    parser.add_argument('--no-save', action='store_true', help='Skip saving plots')
    
    args = parser.parse_args()
    
    show_plots = not args.no_plots
    save_plots = not args.no_save
    
    print("🚀 Starting comment length analysis...")
    
    result = analyze_comment_lengths(
        input_file=args.input,
        show_plots=show_plots,
        save_plots=save_plots
    )
    
    if result:
        print(f"\n✅ Analysis complete!")
        print(f"📁 Analyzed file: {result['input_file']}")
        print(f"🎯 Key insight: {result['stats']['token_estimates']['percentiles']['95th']:.0f} tokens covers 95% of comments")
    else:
        print("❌ Analysis failed")

if __name__ == "__main__":
    main()