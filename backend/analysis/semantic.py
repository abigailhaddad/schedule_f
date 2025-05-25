#!/usr/bin/env python3
"""
Streamlined Semantic Comment Clustering

This script performs semantic clustering on comments using only the comment text
and generates essential outputs: dendrogram, cluster visualization, and stance disagreement report.

Requirements:
- sentence-transformers
- scikit-learn
- numpy
- matplotlib
- seaborn

Usage:
python semantic_clustering.py [--input path/to/data.json] [--n_clusters 10]
"""

import os
import json
import glob
import argparse
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import re
from typing import List, Dict, Any, Optional, Tuple

# Core ML libraries
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import PCA
from scipy.cluster.hierarchy import dendrogram, linkage

def strip_html_tags(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def find_most_recent_data_file():
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
    
    return None

def load_comments(input_file: str) -> Tuple[List[Dict], List[str]]:
    """Load comments and extract only the comment text for clustering"""
    print(f"📖 Loading comments from {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    print(f"✅ Loaded {len(raw_data):,} raw comments")
    
    processed_comments = []
    comment_texts = []
    
    for comment_data in raw_data:
        # Extract just the comment text (original_comment field)
        comment_text = comment_data.get('original_comment', '').strip()
        
        if comment_text:
            processed_comments.append({
                'id': comment_data.get('id', ''),
                'text': comment_text,
                'stance': comment_data.get('stance', ''),
                'key_quote': comment_data.get('key_quote', ''),
                'rationale': comment_data.get('rationale', ''),
                'link': comment_data.get('link', ''),
                'title': comment_data.get('title', '')
            })
            comment_texts.append(comment_text)
    
    print(f"✅ Processed {len(processed_comments):,} non-empty comments")
    
    # Show stance distribution
    stance_counts = {}
    for comment in processed_comments:
        stance = comment['stance']
        stance_counts[stance] = stance_counts.get(stance, 0) + 1
    
    print(f"📊 Stance distribution:")
    for stance, count in sorted(stance_counts.items()):
        percentage = count / len(processed_comments) * 100
        print(f"   {stance}: {count:,} ({percentage:.1f}%)")
    
    return processed_comments, comment_texts

def create_embeddings(texts: List[str], model_name: str = "sentence-transformers/all-mpnet-base-v2") -> np.ndarray:
    """Create semantic embeddings for the texts"""
    print(f"🤖 Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    
    print(f"🔄 Creating embeddings for {len(texts):,} comments...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    
    print(f"✅ Created embeddings with shape: {embeddings.shape}")
    return embeddings

def perform_clustering(embeddings: np.ndarray, n_clusters: int) -> Tuple[np.ndarray, Any]:
    """Perform hierarchical clustering"""
    print(f"🌳 Performing hierarchical clustering with {n_clusters} clusters...")
    
    clustering = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
    cluster_labels = clustering.fit_predict(embeddings)
    
    # Create linkage matrix for dendrogram
    linkage_matrix = linkage(embeddings, method='ward')
    
    print(f"✅ Clustering complete. Cluster distribution:")
    unique, counts = np.unique(cluster_labels, return_counts=True)
    for cluster_id, count in zip(unique, counts):
        print(f"  Cluster {cluster_id}: {count:,} comments ({count/len(cluster_labels)*100:.1f}%)")
    
    return cluster_labels, linkage_matrix

def analyze_clusters(processed_comments: List[Dict], cluster_labels: np.ndarray) -> Tuple[Dict, Dict]:
    """Analyze cluster contents and find stance disagreements"""
    print(f"📊 Analyzing cluster contents and stance disagreements...")
    
    cluster_analysis = {}
    disagreement_analysis = {}
    
    # Stop words for keyword extraction
    stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'this', 
                  'that', 'with', 'have', 'will', 'from', 'they', 'been', 'said', 'each', 
                  'which', 'their', 'time', 'would', 'there', 'what', 'about', 'when', 
                  'many', 'some', 'these', 'make', 'like', 'into', 'him', 'has', 'two', 
                  'more', 'very', 'after', 'our', 'just', 'first', 'get', 'may', 'way', 
                  'use', 'her', 'than', 'call', 'who', 'now', 'find', 'long', 'down', 
                  'day', 'did', 'come', 'made', 'part', 'over', 'such', 'case', 'most', 
                  'only', 'could', 'where', 'much', 'too', 'very', 'still', 'being', 
                  'going', 'should', 'well', 'before', 'must', 'between', 'under', 
                  'never', 'same', 'another', 'while', 'last', 'might', 'great', 'since',
                  'against', 'right', 'three', 'next', 'even', 'both', 'through', 'during'}
    
    for cluster_id in np.unique(cluster_labels):
        cluster_mask = cluster_labels == cluster_id
        cluster_comments = [processed_comments[i] for i, mask in enumerate(cluster_mask) if mask]
        
        # Extract keywords
        cluster_text = " ".join([comment['text'] for comment in cluster_comments])
        words = re.findall(r'\b[a-zA-Z]{3,}\b', cluster_text.lower())
        word_freq = {}
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:15]
        
        # Analyze stance distribution
        stance_counts = {}
        for comment in cluster_comments:
            stance = comment.get('stance', 'Unknown')
            stance_counts[stance] = stance_counts.get(stance, 0) + 1
        
        # Find dominant stance and minority comments
        total_in_cluster = len(cluster_comments)
        if total_in_cluster > 0 and stance_counts:
            dominant_stance = max(stance_counts.keys(), key=lambda k: stance_counts[k])
            dominant_count = stance_counts[dominant_stance]
            purity = dominant_count / total_in_cluster
            
            # Identify minority comments (different stance than dominant)
            minority_comments = []
            for comment in cluster_comments:
                if comment.get('stance') != dominant_stance:
                    minority_comments.append({
                        'id': comment['id'],
                        'stance': comment.get('stance'),
                        'text': comment['text'],
                        'key_quote': comment.get('key_quote', ''),
                        'rationale': comment.get('rationale', ''),
                        'title': comment.get('title', ''),
                        'link': comment.get('link', '')
                    })
            
            cluster_analysis[cluster_id] = {
                'size': total_in_cluster,
                'keywords': [word for word, freq in top_words],
                'stance_distribution': stance_counts,
                'dominant_stance': dominant_stance,
                'purity': purity
            }
            
            disagreement_analysis[cluster_id] = {
                'dominant_stance': dominant_stance,
                'minority_comments': minority_comments,
                'disagreement_rate': len(minority_comments) / total_in_cluster if total_in_cluster > 0 else 0
            }
    
    return cluster_analysis, disagreement_analysis

def create_visualizations(embeddings: np.ndarray, cluster_labels: np.ndarray, 
                         linkage_matrix: np.ndarray, output_dir: str):
    """Create dendrogram and cluster visualization"""
    print(f"📊 Creating visualizations...")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Set up the plotting style
    plt.style.use('default')
    sns.set_palette("husl")
    
    # 1. Dendrogram
    plt.figure(figsize=(15, 8))
    dendrogram(linkage_matrix, truncate_mode='lastp', p=30, leaf_rotation=90, leaf_font_size=12)
    plt.title('Hierarchical Clustering Dendrogram (Last 30 Merges)')
    plt.xlabel('Sample Index or (Cluster Size)')
    plt.ylabel('Distance (Ward)')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'dendrogram.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. PCA cluster visualization
    print("  Creating PCA visualization...")
    pca = PCA(n_components=2)
    embeddings_2d = pca.fit_transform(embeddings)
    
    plt.figure(figsize=(12, 10))
    scatter = plt.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], c=cluster_labels, 
                         cmap='tab20', alpha=0.6, s=50)
    plt.colorbar(scatter)
    plt.title(f'Comments Clustering Visualization (PCA)\n{len(np.unique(cluster_labels))} Clusters')
    plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)')
    plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'clusters_visualization.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✅ Visualizations saved to: {output_dir}")

def create_report(cluster_analysis: Dict, disagreement_analysis: Dict, output_dir: str):
    """Create report with keywords and stance disagreements"""
    print(f"📝 Creating cluster report...")
    
    report_path = os.path.join(output_dir, 'cluster_report.txt')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("SEMANTIC CLUSTERING REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Sort clusters by size
        sorted_clusters = sorted(cluster_analysis.items(), 
                               key=lambda x: x[1]['size'], reverse=True)
        
        for cluster_id, analysis in sorted_clusters:
            f.write(f"CLUSTER {cluster_id}\n")
            f.write("-" * 40 + "\n")
            f.write(f"Size: {analysis['size']} comments\n")
            f.write(f"Keywords: {', '.join(analysis['keywords'][:10])}\n")
            f.write(f"Dominant Stance: {analysis['dominant_stance']} ({analysis['purity']*100:.1f}% purity)\n")
            
            # Stance distribution
            f.write("Stance Distribution:\n")
            for stance, count in sorted(analysis['stance_distribution'].items()):
                percentage = count / analysis['size'] * 100
                f.write(f"  {stance}: {count} ({percentage:.1f}%)\n")
            
            # Minority comments (different stance than dominant)
            disagreements = disagreement_analysis[cluster_id]
            if disagreements['minority_comments']:
                f.write(f"\nCOMMENTS WITH DIFFERENT STANCE (vs dominant '{disagreements['dominant_stance']}'):\n")
                f.write("~" * 60 + "\n")
                
                for i, comment in enumerate(disagreements['minority_comments'], 1):
                    f.write(f"\n{i}. Comment ID: {comment['id']}\n")
                    f.write(f"   Stance: {comment['stance']}\n")
                    f.write(f"   Title: {comment.get('title', 'N/A')}\n")
                    if comment.get('key_quote'):
                        f.write(f"   Key Quote: \"{comment['key_quote']}\"\n")
                    if comment.get('rationale'):
                        f.write(f"   LLM Rationale: {comment['rationale']}\n")
                    f.write(f"   Link: {comment.get('link', 'N/A')}\n")
                    f.write(f"   Full Text: {comment['text'][:500]}{'...' if len(comment['text']) > 500 else ''}\n")
                    f.write("-" * 40 + "\n")
            
            f.write("\n" + "=" * 80 + "\n\n")
    
    print(f"✅ Report saved to: {report_path}")

def update_data_with_clusters(input_file: str, processed_comments: List[Dict], cluster_labels: np.ndarray):
    """Update the original data.json file with cluster IDs"""
    try:
        # Load the original data
        with open(input_file, 'r') as f:
            original_data = json.load(f)
        
        # Create a mapping from comment ID to cluster ID
        cluster_mapping = {}
        for i, comment in enumerate(processed_comments):
            comment_id = comment.get('id')
            if comment_id:
                cluster_mapping[comment_id] = int(cluster_labels[i])
        
        # Update the original data with cluster IDs
        updated_count = 0
        for item in original_data:
            comment_id = item.get('id')
            if comment_id in cluster_mapping:
                item['cluster_id'] = cluster_mapping[comment_id]
                updated_count += 1
        
        # Save the updated data back to the file
        with open(input_file, 'w') as f:
            json.dump(original_data, f, indent=2)
        
        print(f"✅ Updated {updated_count} comments with cluster IDs in {input_file}")
        
    except Exception as e:
        print(f"❌ Error updating data.json with cluster IDs: {e}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Streamlined semantic clustering on comment text only')
    parser.add_argument('--input', type=str, help='Path to data.json file')
    parser.add_argument('--n_clusters', type=int, default=15, help='Number of clusters (default: 15)')
    parser.add_argument('--model', type=str, default='sentence-transformers/all-mpnet-base-v2',
                       help='Sentence transformer model to use')
    parser.add_argument('--output_dir', type=str, help='Output directory')
    
    args = parser.parse_args()
    
    # Find input file
    input_file = args.input
    if input_file is None:
        input_file = find_most_recent_data_file()
        if input_file is None:
            print("❌ Could not find data.json file. Please specify with --input")
            return
    
    # Set output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        input_dir = os.path.dirname(input_file)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(input_dir, f"clustering_{timestamp}")
    
    print(f"🚀 Starting semantic clustering...")
    print(f"📁 Input: {input_file}")
    print(f"📁 Output: {output_dir}")
    print(f"🎯 Number of clusters: {args.n_clusters}")
    
    # Load comments (only comment text will be used for clustering)
    processed_comments, comment_texts = load_comments(input_file)
    
    if len(processed_comments) == 0:
        print("❌ No valid comments found")
        return
    
    # Create embeddings from comment text only
    embeddings = create_embeddings(comment_texts, args.model)
    
    # Perform clustering
    cluster_labels, linkage_matrix = perform_clustering(embeddings, args.n_clusters)
    
    # Analyze clusters
    cluster_analysis, disagreement_analysis = analyze_clusters(processed_comments, cluster_labels)
    
    # Create visualizations (dendrogram and cluster plot)
    create_visualizations(embeddings, cluster_labels, linkage_matrix, output_dir)
    
    # Create report
    create_report(cluster_analysis, disagreement_analysis, output_dir)
    
    # Update original data.json with cluster IDs
    update_data_with_clusters(input_file, processed_comments, cluster_labels)
    
    print(f"\n✅ Clustering complete!")
    print(f"📊 {len(processed_comments):,} comments grouped into {args.n_clusters} clusters")
    print(f"📁 Output files:")
    print(f"   - {os.path.join(output_dir, 'dendrogram.png')}")
    print(f"   - {os.path.join(output_dir, 'clusters_visualization.png')}")
    print(f"   - {os.path.join(output_dir, 'cluster_report.txt')}")

if __name__ == "__main__":
    main()