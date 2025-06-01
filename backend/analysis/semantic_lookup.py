#!/usr/bin/env python3
"""
Semantic Clustering for Lookup Table

This script performs semantic clustering on the analyzed lookup table.
It clusters the unique deduplicated texts and adds clustering results
back to the lookup table structure.

Requirements:
- sentence-transformers
- scikit-learn
- numpy
- matplotlib
- seaborn

Usage:
python semantic_lookup.py [--input lookup_table.json] [--n_clusters 15]
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
from sklearn.metrics import silhouette_score
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from scipy.spatial.distance import pdist

def strip_html_tags(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def find_most_recent_lookup_table():
    """Find the most recent lookup_table.json file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    # Look in project root and results directories
    search_paths = [
        project_root,
        os.path.join(project_root, "results"),
        os.path.join(project_root, "data"),  # Also check data directory
    ]
    
    # Also check results subdirectories
    results_base = os.path.join(project_root, "results")
    if os.path.exists(results_base):
        result_dirs = glob.glob(os.path.join(results_base, "results_*"))
        search_paths.extend(result_dirs)
    
    print(f"🔍 Looking for lookup_table.json files...")
    
    candidates = []
    for search_path in search_paths:
        if os.path.exists(search_path):
            lookup_file = os.path.join(search_path, "lookup_table.json")
            if os.path.exists(lookup_file):
                candidates.append(lookup_file)
                print(f"📁 Found: {lookup_file}")
    
    if candidates:
        # Sort by modification time, newest first
        candidates.sort(key=os.path.getctime, reverse=True)
        print(f"✅ Most recent: {candidates[0]}")
        return candidates[0]
    
    return None

def load_lookup_table(input_file: str) -> Tuple[List[Dict], List[str], List[str]]:
    """Load analyzed lookup table and extract texts for clustering"""
    print(f"📖 Loading analyzed lookup table from {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lookup_data = json.load(f)
    
    print(f"✅ Loaded {len(lookup_data):,} lookup entries")
    
    processed_entries = []
    comment_texts = []
    lookup_ids = []
    
    for entry in lookup_data:
        # Extract the truncated text for clustering
        text = entry.get('truncated_text', '').strip()
        lookup_id = entry.get('lookup_id', '')
        
        if text and lookup_id:
            processed_entries.append(entry)
            comment_texts.append(text)
            lookup_ids.append(lookup_id)
    
    print(f"✅ Processed {len(processed_entries):,} entries with valid text")
    
    # Show analysis status
    analyzed_count = len([e for e in processed_entries if e.get('stance')])
    total_comments = sum(e.get('comment_count', 0) for e in processed_entries)
    
    print(f"📊 Analysis status:")
    print(f"   Analyzed entries: {analyzed_count:,}/{len(processed_entries):,} ({analyzed_count/len(processed_entries)*100:.1f}%)")
    print(f"   Total comments represented: {total_comments:,}")
    
    # Show stance distribution if available
    if analyzed_count > 0:
        stance_counts = {}
        for entry in processed_entries:
            if entry.get('stance'):
                stance = entry['stance']
                count = entry.get('comment_count', 0)
                stance_counts[stance] = stance_counts.get(stance, 0) + count
        
        if stance_counts:
            print(f"📊 Stance distribution:")
            for stance, count in sorted(stance_counts.items()):
                percentage = count / total_comments * 100
                print(f"   {stance}: {count:,} ({percentage:.1f}%)")
    
    return processed_entries, comment_texts, lookup_ids

def create_embeddings(texts: List[str], model_name: str = "sentence-transformers/all-mpnet-base-v2") -> np.ndarray:
    """Create semantic embeddings for the texts"""
    print(f"🤖 Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    
    print(f"🔄 Creating embeddings for {len(texts):,} unique texts...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    
    print(f"✅ Created embeddings with shape: {embeddings.shape}")
    return embeddings

def find_optimal_clusters(embeddings: np.ndarray, min_clusters: int = 3, max_clusters: int = 15) -> int:
    """Find optimal number of clusters using silhouette score with smart search"""
    print(f"🔍 Finding optimal number of clusters...")
    
    # First, do a coarse search with larger steps
    coarse_range = [3, 5, 8, 12, 15, 20]
    coarse_scores = {}
    
    print("  Stage 1: Coarse search...")
    for n_clusters in coarse_range:
        if n_clusters >= len(embeddings):
            break
        clustering = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
        cluster_labels = clustering.fit_predict(embeddings)
        score = silhouette_score(embeddings, cluster_labels)
        coarse_scores[n_clusters] = score
        print(f"    {n_clusters} clusters: silhouette score = {score:.3f}")
    
    # Find the best region from coarse search
    best_coarse = max(coarse_scores.keys(), key=lambda k: coarse_scores[k])
    
    # Do a fine search around the best coarse result
    fine_min = max(2, best_coarse - 3)
    fine_max = min(best_coarse + 3, len(embeddings) - 1)
    
    print(f"\n  Stage 2: Fine search around {best_coarse} clusters...")
    fine_scores = {}
    
    for n_clusters in range(fine_min, fine_max + 1):
        if n_clusters in coarse_scores:
            fine_scores[n_clusters] = coarse_scores[n_clusters]
        else:
            clustering = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
            cluster_labels = clustering.fit_predict(embeddings)
            score = silhouette_score(embeddings, cluster_labels)
            fine_scores[n_clusters] = score
            print(f"    {n_clusters} clusters: silhouette score = {score:.3f}")
    
    # Find optimal from fine search
    optimal_clusters = max(fine_scores.keys(), key=lambda k: fine_scores[k])
    
    print(f"\n✅ Optimal number of clusters: {optimal_clusters} (silhouette score: {fine_scores[optimal_clusters]:.3f})")
    return optimal_clusters

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
        print(f"  Cluster {cluster_id}: {count:,} unique texts ({count/len(cluster_labels)*100:.1f}%)")
    
    return cluster_labels, linkage_matrix

def extract_subclusters_from_dendrogram(linkage_matrix: np.ndarray, n_main_clusters: int, 
                                       gap_threshold: float = 1.5) -> Tuple[np.ndarray, np.ndarray]:
    """Extract natural subclusters by finding gaps in the dendrogram
    
    Args:
        linkage_matrix: The hierarchical clustering linkage matrix
        n_main_clusters: Number of main clusters
        gap_threshold: Ratio to identify significant gaps (default: 1.5 = 50% increase)
    """
    print(f"🌿 Extracting natural subclusters from dendrogram...")
    
    # Get main clusters
    main_clusters = fcluster(linkage_matrix, n_main_clusters, criterion='maxclust') - 1  # 0-indexed
    
    # Analyze the dendrogram to find natural breaks
    distances = linkage_matrix[:, 2]
    
    # Calculate the rate of change in distances
    distance_diffs = np.diff(distances)
    distance_ratios = distances[1:] / distances[:-1]
    
    # Find significant gaps (where distance increases by more than threshold)
    significant_gaps = np.where(distance_ratios > gap_threshold)[0]
    
    # Find the gap that gives us a reasonable number of clusters (between main clusters and too many)
    main_cluster_height = distances[len(distances) - n_main_clusters]
    
    # Look for the most significant gap that would give us more than main clusters
    best_gap_idx = None
    best_gap_ratio = 0
    
    for gap_idx in significant_gaps:
        if gap_idx > len(distances) - 50:  # Don't create too many clusters
            n_clusters_at_gap = len(distances) - gap_idx
            if n_clusters_at_gap > n_main_clusters:
                gap_ratio = distance_ratios[gap_idx]
                if gap_ratio > best_gap_ratio:
                    best_gap_ratio = gap_ratio
                    best_gap_idx = gap_idx
    
    # If we found a good gap, use it; otherwise fall back to a reasonable default
    if best_gap_idx is not None:
        n_fine_clusters = len(distances) - best_gap_idx
        print(f"  Found natural gap at height {distances[best_gap_idx]:.3f} (ratio: {best_gap_ratio:.2f})")
    else:
        # Fall back to sqrt of data size as a reasonable number
        n_fine_clusters = min(int(np.sqrt(len(distances))), n_main_clusters * 5)
        print(f"  No significant gaps found, using {n_fine_clusters} clusters")
    
    # Get fine clusters
    fine_clusters = fcluster(linkage_matrix, n_fine_clusters, criterion='maxclust') - 1  # 0-indexed
    print(f"  Total natural clusters: {len(np.unique(fine_clusters))}")
    
    # Create subcluster labels within each main cluster
    subcluster_labels = np.zeros_like(main_clusters)
    total_subclusters = 0
    
    for main_id in np.unique(main_clusters):
        main_mask = main_clusters == main_id
        fine_in_main = fine_clusters[main_mask]
        
        # Remap fine cluster IDs to subcluster IDs (0, 1, 2, ...)
        unique_fine = np.unique(fine_in_main)
        for sub_id, fine_id in enumerate(unique_fine):
            subcluster_labels[main_mask & (fine_clusters == fine_id)] = sub_id
        
        total_subclusters += len(unique_fine)
        print(f"  Cluster {main_id}: {len(unique_fine)} natural subclusters")
        for sub_id in range(min(len(unique_fine), 10)):  # Show max 10 subclusters
            count = np.sum((main_clusters == main_id) & (subcluster_labels == sub_id))
            if sub_id < 26:  # Only use a-z
                print(f"    Subcluster {main_id}{chr(97+sub_id)}: {count} texts")
            else:
                print(f"    Subcluster {main_id}{sub_id}: {count} texts (numeric label)")
        if len(unique_fine) > 10:
            print(f"    ... and {len(unique_fine) - 10} more subclusters")
    
    return main_clusters, subcluster_labels

def analyze_clusters(processed_entries: List[Dict], cluster_labels: np.ndarray) -> Tuple[Dict, Dict]:
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
        cluster_entries = [processed_entries[i] for i, mask in enumerate(cluster_mask) if mask]
        
        # Calculate total comments in cluster (accounting for duplicates)
        total_comments_in_cluster = sum(entry.get('comment_count', 0) for entry in cluster_entries)
        
        # Extract keywords from all texts in cluster
        cluster_text = " ".join([entry['truncated_text'] for entry in cluster_entries])
        words = re.findall(r'\b[a-zA-Z]{3,}\b', cluster_text.lower())
        word_freq = {}
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:15]
        
        # Analyze stance distribution (weighted by occurrence count)
        stance_counts = {}
        stance_entries = {}  # Track entries by stance
        
        for entry in cluster_entries:
            stance = entry.get('stance', 'Unknown')
            count = entry.get('comment_count', 0)
            stance_counts[stance] = stance_counts.get(stance, 0) + count
            
            if stance not in stance_entries:
                stance_entries[stance] = []
            stance_entries[stance].append(entry)
        
        # Find dominant stance and minority entries
        if total_comments_in_cluster > 0 and stance_counts:
            dominant_stance = max(stance_counts.keys(), key=lambda k: stance_counts[k])
            dominant_count = stance_counts[dominant_stance]
            purity = dominant_count / total_comments_in_cluster
            
            # Identify minority entries (different stance than dominant)
            minority_entries = []
            for stance, entries in stance_entries.items():
                if stance != dominant_stance:
                    for entry in entries:
                        minority_entries.append({
                            'lookup_id': entry['lookup_id'],
                            'stance': entry.get('stance'),
                            'comment_count': entry.get('comment_count', 0),
                            'text': entry['truncated_text'],
                            'key_quote': entry.get('key_quote', ''),
                            'rationale': entry.get('rationale', ''),
                            'comment_ids': entry.get('comment_ids', [])
                        })
            
            cluster_analysis[cluster_id] = {
                'unique_texts': len(cluster_entries),
                'total_comments': total_comments_in_cluster,
                'keywords': [word for word, freq in top_words],
                'stance_distribution': stance_counts,
                'dominant_stance': dominant_stance,
                'purity': purity
            }
            
            disagreement_analysis[cluster_id] = {
                'dominant_stance': dominant_stance,
                'minority_entries': minority_entries,
                'disagreement_rate': len(minority_entries) / len(cluster_entries) if len(cluster_entries) > 0 else 0,
                'minority_comment_count': sum(e['comment_count'] for e in minority_entries)
            }
    
    return cluster_analysis, disagreement_analysis

def create_visualizations(embeddings: np.ndarray, cluster_labels: np.ndarray, 
                         linkage_matrix: np.ndarray, output_dir: str) -> np.ndarray:
    """Create dendrogram and cluster visualization, return PCA coordinates"""
    print(f"📊 Creating visualizations...")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Set up the plotting style
    plt.style.use('default')
    sns.set_palette("husl")
    
    # 1. Dendrogram
    plt.figure(figsize=(15, 8))
    dendrogram(linkage_matrix, truncate_mode='lastp', p=30, leaf_rotation=90, leaf_font_size=12)
    plt.title('Hierarchical Clustering Dendrogram (Last 30 Merges)\nBased on Deduplicated Lookup Table')
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
    plt.title(f'Deduplicated Comments Clustering Visualization (PCA)\n{len(np.unique(cluster_labels))} Clusters from {len(embeddings)} Unique Texts')
    plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)')
    plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'clusters_visualization.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✅ Visualizations saved to: {output_dir}")
    
    # Return the 2D coordinates for adding to lookup table
    return embeddings_2d

def create_report(cluster_analysis: Dict, disagreement_analysis: Dict, output_dir: str):
    """Create report with keywords and stance disagreements"""
    print(f"📝 Creating cluster report...")
    
    report_path = os.path.join(output_dir, 'cluster_report.txt')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("SEMANTIC CLUSTERING REPORT (DEDUPLICATED)\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("NOTE: This clustering was performed on deduplicated unique texts.\n")
        f.write("Each cluster may represent multiple duplicate comments.\n\n")
        
        # Sort clusters by total comment count (not unique texts)
        sorted_clusters = sorted(cluster_analysis.items(), 
                               key=lambda x: x[1]['total_comments'], reverse=True)
        
        for cluster_id, analysis in sorted_clusters:
            f.write(f"CLUSTER {cluster_id}\n")
            f.write("-" * 40 + "\n")
            f.write(f"Unique texts: {analysis['unique_texts']}\n")
            f.write(f"Total comments: {analysis['total_comments']} (including duplicates)\n")
            f.write(f"Keywords: {', '.join(analysis['keywords'][:10])}\n")
            f.write(f"Dominant Stance: {analysis['dominant_stance']} ({analysis['purity']*100:.1f}% purity)\n")
            
            # Stance distribution
            f.write("Stance Distribution (by comment count):\n")
            for stance, count in sorted(analysis['stance_distribution'].items()):
                percentage = count / analysis['total_comments'] * 100
                f.write(f"  {stance}: {count} ({percentage:.1f}%)\n")
            
            # Minority entries (different stance than dominant)
            disagreements = disagreement_analysis[cluster_id]
            if disagreements['minority_entries']:
                f.write(f"\nENTRIES WITH DIFFERENT STANCE (vs dominant '{disagreements['dominant_stance']}'):\n")
                f.write(f"Minority comment count: {disagreements['minority_comment_count']}\n")
                f.write("~" * 60 + "\n")
                
                for i, entry in enumerate(disagreements['minority_entries'], 1):
                    f.write(f"\n{i}. Lookup ID: {entry['lookup_id']}\n")
                    f.write(f"   Stance: {entry['stance']}\n")
                    f.write(f"   Comment Count: {entry['comment_count']}\n")
                    f.write(f"   Comment IDs: {', '.join(entry['comment_ids'][:5])}")
                    if len(entry['comment_ids']) > 5:
                        f.write(f" (and {len(entry['comment_ids'])-5} more)")
                    f.write("\n")
                    if entry.get('key_quote'):
                        f.write(f"   Key Quote: \"{entry['key_quote']}\"\n")
                    if entry.get('rationale'):
                        f.write(f"   LLM Rationale: {entry['rationale']}\n")
                    f.write(f"   Text: {entry['text'][:500]}{'...' if len(entry['text']) > 500 else ''}\n")
                    f.write("-" * 40 + "\n")
            
            f.write("\n" + "=" * 80 + "\n\n")
    
    print(f"✅ Report saved to: {report_path}")

def update_lookup_table_with_clusters(input_file: str, processed_entries: List[Dict], 
                                    cluster_labels: np.ndarray, pca_coordinates: np.ndarray = None,
                                    subcluster_labels: np.ndarray = None) -> str:
    """Update the lookup table with cluster IDs and PCA coordinates"""
    try:
        # Load the original lookup table
        with open(input_file, 'r') as f:
            original_lookup_table = json.load(f)
        
        # Create a mapping from lookup_id to cluster data
        cluster_mapping = {}
        for i, entry in enumerate(processed_entries):
            lookup_id = entry.get('lookup_id')
            if lookup_id and i < len(cluster_labels):
                # If we have subclusters, use combined format like "0a", otherwise just the number
                if subcluster_labels is not None and i < len(subcluster_labels):
                    cluster_id = f"{int(cluster_labels[i])}{chr(97+int(subcluster_labels[i]))}"
                else:
                    cluster_id = int(cluster_labels[i])
                
                mapping_data = {'cluster_id': cluster_id}
                if pca_coordinates is not None and i < len(pca_coordinates):
                    mapping_data['pca_x'] = float(pca_coordinates[i, 0])
                    mapping_data['pca_y'] = float(pca_coordinates[i, 1])
                cluster_mapping[lookup_id] = mapping_data
        
        # Update the original lookup table with cluster data
        updated_count = 0
        for entry in original_lookup_table:
            lookup_id = entry.get('lookup_id')
            if lookup_id in cluster_mapping:
                mapping_data = cluster_mapping[lookup_id]
                entry['cluster_id'] = mapping_data['cluster_id']
                if 'pca_x' in mapping_data:
                    entry['pca_x'] = mapping_data['pca_x']
                    entry['pca_y'] = mapping_data['pca_y']
                updated_count += 1
        
        # Save the updated lookup table back to the original file
        # This ensures cluster_id is added to the main lookup table
        with open(input_file, 'w') as f:
            json.dump(original_lookup_table, f, indent=2)
        
        coords_msg = " and PCA coordinates" if pca_coordinates is not None else ""
        subcluster_msg = " (with subclusters)" if subcluster_labels is not None else ""
        print(f"✅ Updated {updated_count} entries with cluster IDs{subcluster_msg}{coords_msg}")
        print(f"✅ Updated lookup table: {input_file}")
        
        return input_file
        
    except Exception as e:
        print(f"❌ Error updating lookup table with cluster data: {e}")
        return input_file

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Semantic clustering on deduplicated lookup table')
    parser.add_argument('--input', type=str, help='Path to lookup_table.json file')
    parser.add_argument('--n_clusters', type=int, default=None, help='Number of clusters (default: auto-detect)')
    parser.add_argument('--auto_clusters', action='store_true', help='Automatically find optimal number of clusters')
    parser.add_argument('--subclusters', action='store_true', help='Extract natural subclusters from dendrogram')
    parser.add_argument('--gap_threshold', type=float, default=1.5, 
                       help='Ratio to identify significant gaps in dendrogram (default: 1.5 = 50% increase)')
    parser.add_argument('--model', type=str, default='sentence-transformers/all-mpnet-base-v2',
                       help='Sentence transformer model to use')
    parser.add_argument('--output_dir', type=str, help='Output directory')
    
    args = parser.parse_args()
    
    # Find input file
    input_file = args.input
    if input_file is None:
        input_file = find_most_recent_lookup_table()
        if input_file is None:
            print("❌ Could not find lookup_table.json file. Please specify with --input")
            return
    
    # Set output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        input_dir = os.path.dirname(input_file)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(input_dir, f"clustering_{timestamp}")
    
    print(f"🚀 Starting semantic clustering on deduplicated lookup table...")
    print(f"📁 Input: {input_file}")
    print(f"📁 Output: {output_dir}")
    
    # Load lookup table
    processed_entries, comment_texts, lookup_ids = load_lookup_table(input_file)
    
    if len(processed_entries) == 0:
        print("❌ No valid entries found in lookup table")
        return
    
    # Create embeddings from unique texts only
    embeddings = create_embeddings(comment_texts, args.model)
    
    # Determine number of clusters
    if args.n_clusters is None or args.auto_clusters:
        n_clusters = find_optimal_clusters(embeddings)
    else:
        n_clusters = args.n_clusters
        print(f"🎯 Using specified number of clusters: {n_clusters}")
    
    # Perform clustering
    cluster_labels, linkage_matrix = perform_clustering(embeddings, n_clusters)
    
    # Extract subclusters if requested
    subcluster_labels = None
    if args.subclusters:
        main_clusters, subcluster_labels = extract_subclusters_from_dendrogram(
            linkage_matrix, n_clusters, args.gap_threshold
        )
        # For analysis, we'll use the main clusters
        cluster_labels = main_clusters
    
    # Analyze clusters
    cluster_analysis, disagreement_analysis = analyze_clusters(processed_entries, cluster_labels)
    
    # Create visualizations and get PCA coordinates
    pca_coordinates = create_visualizations(embeddings, cluster_labels, linkage_matrix, output_dir)
    
    # Create report
    create_report(cluster_analysis, disagreement_analysis, output_dir)
    
    # Update lookup table with cluster data and PCA coordinates
    clustered_file = update_lookup_table_with_clusters(input_file, processed_entries, cluster_labels, pca_coordinates, subcluster_labels)
    
    # Calculate efficiency stats
    total_original_comments = sum(entry.get('comment_count', 0) for entry in processed_entries)
    
    print(f"\n✅ Clustering complete!")
    print(f"📊 {len(processed_entries):,} unique texts clustered into {n_clusters} clusters")
    print(f"📊 Representing {total_original_comments:,} total comments")
    print(f"🚀 Efficiency: Clustered {len(processed_entries):,} texts instead of {total_original_comments:,} comments")
    print(f"⚡ Speed improvement: ~{total_original_comments/len(processed_entries):.1f}x faster")
    print(f"📁 Output files:")
    print(f"   - {os.path.join(output_dir, 'dendrogram.png')}")
    print(f"   - {os.path.join(output_dir, 'clusters_visualization.png')}")
    print(f"   - {os.path.join(output_dir, 'cluster_report.txt')}")
    print(f"   - {clustered_file}")

if __name__ == "__main__":
    main()