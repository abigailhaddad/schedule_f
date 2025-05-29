#!/usr/bin/env python3
"""
Hierarchical Clustering with Elbow Method

This script performs hierarchical clustering on the analyzed lookup table,
first creating 2-5 main clusters using the elbow method, then recursively
clustering each main cluster.

Usage:
python hierarchical_clustering.py [--input analyzed_lookup_table.json]
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
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import cdist, pdist

def strip_html_tags(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def find_most_recent_lookup_table():
    """Find the most recent analyzed_lookup_table.json file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    # Look in data directory first
    data_dir = os.path.join(project_root, "data")
    if os.path.exists(data_dir):
        # Check for lookup_table_corrected.json
        lookup_file = os.path.join(data_dir, "lookup_table_corrected.json")
        if os.path.exists(lookup_file):
            print(f"✅ Found: {lookup_file}")
            return lookup_file
    
    # Fall back to results directories
    search_paths = [
        project_root,
        os.path.join(project_root, "results"),
    ]
    
    results_base = os.path.join(project_root, "results")
    if os.path.exists(results_base):
        result_dirs = glob.glob(os.path.join(results_base, "results_*"))
        search_paths.extend(result_dirs)
    
    candidates = []
    for search_path in search_paths:
        if os.path.exists(search_path):
            lookup_file = os.path.join(search_path, "analyzed_lookup_table.json")
            if os.path.exists(lookup_file):
                candidates.append(lookup_file)
    
    if candidates:
        candidates.sort(key=os.path.getctime, reverse=True)
        print(f"✅ Most recent: {candidates[0]}")
        return candidates[0]
    
    return None

def load_lookup_table(input_file: str) -> Tuple[List[Dict], List[str], List[str]]:
    """Load analyzed lookup table and extract texts for clustering"""
    print(f"📖 Loading lookup table from {input_file}...")
    
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
    
    return processed_entries, comment_texts, lookup_ids

def create_embeddings(texts: List[str], model_name: str = "sentence-transformers/all-mpnet-base-v2") -> np.ndarray:
    """Create semantic embeddings for the texts"""
    print(f"🤖 Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    
    print(f"🔄 Creating embeddings for {len(texts):,} unique texts...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    
    print(f"✅ Created embeddings with shape: {embeddings.shape}")
    return embeddings

def calculate_wcss(embeddings: np.ndarray, k_range: range) -> List[float]:
    """Calculate Within-Cluster Sum of Squares for different k values"""
    wcss = []
    
    for k in k_range:
        clustering = AgglomerativeClustering(n_clusters=k, linkage='ward')
        cluster_labels = clustering.fit_predict(embeddings)
        
        # Calculate WCSS
        cluster_centers = []
        for i in range(k):
            cluster_mask = cluster_labels == i
            if np.any(cluster_mask):
                center = embeddings[cluster_mask].mean(axis=0)
                cluster_centers.append(center)
        
        # Calculate sum of squared distances
        total_wcss = 0
        for i, label in enumerate(cluster_labels):
            distance = np.linalg.norm(embeddings[i] - cluster_centers[label])
            total_wcss += distance ** 2
        
        wcss.append(total_wcss)
        print(f"  k={k}: WCSS = {total_wcss:.2f}")
    
    return wcss

def find_elbow_point(wcss: List[float], k_range: range) -> int:
    """Find the elbow point using the elbow method"""
    # Calculate the differences and second differences
    diffs = np.diff(wcss)
    diffs2 = np.diff(diffs)
    
    # Find the point with maximum curvature (most negative second derivative)
    # Add 2 because we lose 2 indices from double differentiation
    elbow_idx = np.argmin(diffs2) + 2
    
    # Ensure we're within the valid range
    elbow_k = list(k_range)[min(elbow_idx, len(k_range) - 1)]
    
    return elbow_k

def plot_elbow_curve(wcss: List[float], k_range: range, elbow_k: int, output_dir: str, prefix: str = ""):
    """Plot the elbow curve"""
    plt.figure(figsize=(10, 6))
    plt.plot(list(k_range), wcss, 'b-', marker='o', markersize=8)
    plt.axvline(x=elbow_k, color='r', linestyle='--', label=f'Elbow at k={elbow_k}')
    plt.xlabel('Number of Clusters (k)')
    plt.ylabel('Within-Cluster Sum of Squares (WCSS)')
    plt.title(f'{prefix}Elbow Method for Optimal k')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    filename = f'{prefix.lower().replace(" ", "_")}elbow_curve.png' if prefix else 'elbow_curve.png'
    plt.savefig(os.path.join(output_dir, filename), dpi=300, bbox_inches='tight')
    plt.close()

def perform_hierarchical_clustering(embeddings: np.ndarray, n_clusters: int) -> Tuple[np.ndarray, Any]:
    """Perform hierarchical clustering"""
    print(f"🌳 Performing hierarchical clustering with {n_clusters} clusters...")
    
    clustering = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
    cluster_labels = clustering.fit_predict(embeddings)
    
    # Create linkage matrix for dendrogram
    linkage_matrix = linkage(embeddings, method='ward')
    
    print(f"✅ Clustering complete. Cluster distribution:")
    unique, counts = np.unique(cluster_labels, return_counts=True)
    for cluster_id, count in zip(unique, counts):
        print(f"  Cluster {cluster_id}: {count:,} texts ({count/len(cluster_labels)*100:.1f}%)")
    
    return cluster_labels, linkage_matrix

def analyze_cluster_content(processed_entries: List[Dict], cluster_mask: np.ndarray) -> Dict:
    """Analyze the content of a single cluster"""
    cluster_entries = [e for i, e in enumerate(processed_entries) if cluster_mask[i]]
    
    # Calculate total comments in cluster
    total_comments = sum(entry.get('comment_count', 0) for entry in cluster_entries)
    
    # Extract keywords
    stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'this', 
                  'that', 'with', 'have', 'will', 'from', 'they', 'been', 'said', 'each', 
                  'which', 'their', 'time', 'would', 'there', 'what', 'about', 'when'}
    
    cluster_text = " ".join([entry['truncated_text'] for entry in cluster_entries])
    words = re.findall(r'\b[a-zA-Z]{3,}\b', cluster_text.lower())
    word_freq = {}
    for word in words:
        if word not in stop_words:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Analyze stance distribution
    stance_counts = {}
    for entry in cluster_entries:
        stance = entry.get('stance', 'Unknown')
        count = entry.get('comment_count', 0)
        stance_counts[stance] = stance_counts.get(stance, 0) + count
    
    # Find dominant stance
    if stance_counts:
        dominant_stance = max(stance_counts.keys(), key=lambda k: stance_counts[k])
        purity = stance_counts[dominant_stance] / total_comments if total_comments > 0 else 0
    else:
        dominant_stance = "Unknown"
        purity = 0
    
    return {
        'unique_texts': len(cluster_entries),
        'total_comments': total_comments,
        'keywords': [word for word, freq in top_words],
        'stance_distribution': stance_counts,
        'dominant_stance': dominant_stance,
        'purity': purity,
        'entries': cluster_entries
    }

def recursive_clustering(embeddings: np.ndarray, processed_entries: List[Dict], 
                        cluster_labels: np.ndarray, cluster_id: int, 
                        output_dir: str, level: int = 0, parent_id: str = "") -> Dict:
    """Recursively cluster a subset of data"""
    cluster_mask = cluster_labels == cluster_id
    cluster_embeddings = embeddings[cluster_mask]
    cluster_entries = [e for i, e in enumerate(processed_entries) if cluster_mask[i]]
    
    # Analyze current cluster
    analysis = analyze_cluster_content(processed_entries, cluster_mask)
    
    # Create cluster ID with letter notation
    if parent_id:
        # For subclusters, add letters (a, b, c, etc.)
        cluster_id_str = f"{parent_id}{chr(97 + cluster_id)}"  # 97 is 'a' in ASCII
    else:
        # For main clusters, just use the number
        cluster_id_str = str(cluster_id)
    
    result = {
        'level': level,
        'cluster_id': cluster_id_str,
        'analysis': analysis,
        'subclusters': []
    }
    
    # Decide if we should subcluster
    min_cluster_size = 30  # Minimum size to consider subclustering
    
    # Calculate semantic diversity using variance in embeddings
    if len(cluster_entries) >= min_cluster_size and level < 2:
        # Calculate the variance of embeddings as a measure of semantic diversity
        embedding_variance = np.var(cluster_embeddings, axis=0).mean()
        
        # Higher variance = more diverse = more likely to benefit from subclustering
        # Threshold based on empirical observation (can be tuned)
        min_variance_threshold = 0.0004  # Adjusted based on observed variances
        
        should_subcluster = embedding_variance > min_variance_threshold
        
        print(f"{'  ' * level}  Semantic variance: {embedding_variance:.4f} (threshold: {min_variance_threshold})")
        
        if should_subcluster:
            print(f"\n{'  ' * level}📊 Subclustering Cluster {result['cluster_id']} ({len(cluster_entries)} texts)...")
            
            # Use elbow method for subclusters (2-5 clusters)
            k_range = range(2, min(6, len(cluster_entries)))
            
            if len(k_range) > 1:
                print(f"{'  ' * level}  Finding optimal k using elbow method...")
                wcss = calculate_wcss(cluster_embeddings, k_range)
                optimal_k = find_elbow_point(wcss, k_range)
                
                # Plot elbow curve
                plot_elbow_curve(wcss, k_range, optimal_k, output_dir, 
                               prefix=f"Cluster {cluster_id_str} ")
                
                print(f"{'  ' * level}  Optimal k: {optimal_k}")
                
                # Perform subclustering
                sub_labels, _ = perform_hierarchical_clustering(cluster_embeddings, optimal_k)
                
                # Recursively analyze subclusters
                for sub_id in range(optimal_k):
                    sub_result = recursive_clustering(
                        cluster_embeddings, cluster_entries, sub_labels, sub_id,
                        output_dir, level + 1, result['cluster_id']
                    )
                    result['subclusters'].append(sub_result)
    
    return result

def create_hierarchical_visualization(clustering_results: List[Dict], processed_entries: List[Dict], 
                                    embeddings: np.ndarray, output_dir: str):
    """Create visualization of hierarchical clustering results"""
    print("📊 Creating hierarchical visualization...")
    
    # Perform PCA for 2D visualization
    pca = PCA(n_components=2)
    embeddings_2d = pca.fit_transform(embeddings)
    
    # Create hierarchical labels for coloring
    hierarchical_labels = np.zeros(len(processed_entries))
    
    def assign_labels(results, offset=0):
        for i, result in enumerate(results):
            # Find entries in this cluster
            cluster_entries = result['analysis']['entries']
            for entry in cluster_entries:
                idx = next(j for j, e in enumerate(processed_entries) 
                          if e['lookup_id'] == entry['lookup_id'])
                hierarchical_labels[idx] = offset + i
            
            # Process subclusters
            if result['subclusters']:
                sub_offset = offset + len(results)
                assign_labels(result['subclusters'], sub_offset)
    
    assign_labels(clustering_results)
    
    # Create visualization
    plt.figure(figsize=(12, 10))
    scatter = plt.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], 
                         c=hierarchical_labels, cmap='tab20', alpha=0.6, s=50)
    plt.colorbar(scatter)
    plt.title(f'Hierarchical Clustering Visualization (PCA)\n{len(clustering_results)} Main Clusters')
    plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)')
    plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'hierarchical_clusters_visualization.png'), 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    return embeddings_2d

def create_hierarchical_report(clustering_results: List[Dict], output_dir: str):
    """Create detailed report of hierarchical clustering results"""
    print("📝 Creating hierarchical clustering report...")
    
    report_path = os.path.join(output_dir, 'hierarchical_cluster_report.txt')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("HIERARCHICAL CLUSTERING REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("Method: Elbow method with recursive subclustering\n\n")
        
        def write_cluster_info(result, f, indent=""):
            cluster_id = result['cluster_id']
            analysis = result['analysis']
            
            f.write(f"{indent}CLUSTER {cluster_id}\n")
            f.write(f"{indent}{'-' * 40}\n")
            f.write(f"{indent}Level: {result['level']}\n")
            f.write(f"{indent}Unique texts: {analysis['unique_texts']}\n")
            f.write(f"{indent}Total comments: {analysis['total_comments']}\n")
            f.write(f"{indent}Keywords: {', '.join(analysis['keywords'])}\n")
            f.write(f"{indent}Dominant stance: {analysis['dominant_stance']} ({analysis['purity']*100:.1f}% purity)\n")
            
            # Stance distribution
            f.write(f"{indent}Stance distribution:\n")
            for stance, count in sorted(analysis['stance_distribution'].items()):
                percentage = count / analysis['total_comments'] * 100 if analysis['total_comments'] > 0 else 0
                f.write(f"{indent}  {stance}: {count} ({percentage:.1f}%)\n")
            
            # Show examples of dominant stance
            dominant_examples = [e for e in analysis['entries'] if e.get('stance') == analysis['dominant_stance']][:3]
            if dominant_examples:
                f.write(f"\n{indent}EXAMPLES OF DOMINANT STANCE ({analysis['dominant_stance']}):\n")
                f.write(f"{indent}{'~' * 60}\n")
                for i, entry in enumerate(dominant_examples, 1):
                    f.write(f"{indent}{i}. Lookup ID: {entry['lookup_id']}\n")
                    f.write(f"{indent}   Comment IDs: {', '.join(entry.get('comment_ids', [])[:3])}")
                    if len(entry.get('comment_ids', [])) > 3:
                        f.write(f" (and {len(entry['comment_ids'])-3} more)")
                    f.write("\n")
                    if entry.get('key_quote'):
                        f.write(f"{indent}   Key Quote: \"{entry['key_quote']}\"\n")
                    text_preview = entry['truncated_text'][:200]
                    if len(entry['truncated_text']) > 200:
                        text_preview += "..."
                    f.write(f"{indent}   Text Preview: {text_preview}\n")
                    f.write(f"{indent}   {'-' * 40}\n")
            
            # Show deviations (minority stances)
            minority_examples = [e for e in analysis['entries'] if e.get('stance') != analysis['dominant_stance']]
            if minority_examples:
                f.write(f"\n{indent}DEVIATIONS FROM DOMINANT STANCE:\n")
                f.write(f"{indent}{'!' * 60}\n")
                for i, entry in enumerate(minority_examples[:5], 1):  # Show up to 5 deviations
                    f.write(f"{indent}{i}. Lookup ID: {entry['lookup_id']}\n")
                    f.write(f"{indent}   STANCE: {entry.get('stance', 'Unknown')} (vs dominant: {analysis['dominant_stance']})\n")
                    f.write(f"{indent}   Comment Count: {entry.get('comment_count', 0)}\n")
                    f.write(f"{indent}   Comment IDs: {', '.join(entry.get('comment_ids', [])[:3])}")
                    if len(entry.get('comment_ids', [])) > 3:
                        f.write(f" (and {len(entry['comment_ids'])-3} more)")
                    f.write("\n")
                    if entry.get('key_quote'):
                        f.write(f"{indent}   Key Quote: \"{entry['key_quote']}\"\n")
                    if entry.get('rationale'):
                        f.write(f"{indent}   LLM Rationale: {entry['rationale']}\n")
                    text_preview = entry['truncated_text'][:200]
                    if len(entry['truncated_text']) > 200:
                        text_preview += "..."
                    f.write(f"{indent}   Text Preview: {text_preview}\n")
                    f.write(f"{indent}   {'-' * 40}\n")
                if len(minority_examples) > 5:
                    f.write(f"{indent}   ... and {len(minority_examples) - 5} more deviations\n")
            
            f.write("\n")
            
            # Write subclusters
            if result['subclusters']:
                f.write(f"{indent}SUBCLUSTERS:\n")
                f.write(f"{indent}{'~' * 40}\n\n")
                for subcluster in result['subclusters']:
                    write_cluster_info(subcluster, f, indent + "  ")
            
            f.write(f"{indent}{'=' * 60}\n\n")
        
        # Write main clusters
        for result in clustering_results:
            write_cluster_info(result, f)
    
    print(f"✅ Report saved to: {report_path}")

def update_lookup_table_with_hierarchical_clusters(input_file: str, clustering_results: List[Dict], 
                                                 embeddings_2d: np.ndarray, processed_entries: List[Dict]) -> str:
    """Update lookup table with hierarchical cluster IDs"""
    try:
        # Load the original lookup table
        with open(input_file, 'r') as f:
            original_lookup_table = json.load(f)
        
        # Create mapping from lookup_id to cluster info
        cluster_mapping = {}
        
        def process_cluster_results(results, parent_id=""):
            for result in results:
                cluster_id = result['cluster_id']
                for entry in result['analysis']['entries']:
                    lookup_id = entry['lookup_id']
                    # Find the index in processed_entries
                    idx = next((i for i, e in enumerate(processed_entries) 
                               if e['lookup_id'] == lookup_id), None)
                    
                    if idx is not None:
                        cluster_mapping[lookup_id] = {
                            'cluster_id': cluster_id,
                            'pca_x': float(embeddings_2d[idx, 0]),
                            'pca_y': float(embeddings_2d[idx, 1])
                        }
                
                # Process subclusters
                if result['subclusters']:
                    process_cluster_results(result['subclusters'])
        
        process_cluster_results(clustering_results)
        
        # Update original lookup table
        updated_count = 0
        for entry in original_lookup_table:
            lookup_id = entry.get('lookup_id')
            if lookup_id in cluster_mapping:
                mapping_data = cluster_mapping[lookup_id]
                entry['cluster_id'] = mapping_data['cluster_id']
                entry['pca_x'] = mapping_data['pca_x']
                entry['pca_y'] = mapping_data['pca_y']
                updated_count += 1
        
        # Save updated lookup table
        with open(input_file, 'w') as f:
            json.dump(original_lookup_table, f, indent=2)
        
        print(f"✅ Updated {updated_count} entries with hierarchical cluster IDs")
        print(f"✅ Updated lookup table: {input_file}")
        
        return input_file
        
    except Exception as e:
        print(f"❌ Error updating lookup table: {e}")
        return input_file

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Hierarchical clustering with elbow method')
    parser.add_argument('--input', type=str, help='Path to lookup table JSON file')
    parser.add_argument('--model', type=str, default='sentence-transformers/all-mpnet-base-v2',
                       help='Sentence transformer model to use')
    parser.add_argument('--output_dir', type=str, help='Output directory')
    parser.add_argument('--sample', type=int, help='Sample N entries for testing (default: use all)')
    
    args = parser.parse_args()
    
    # Find input file
    input_file = args.input
    if input_file is None:
        input_file = find_most_recent_lookup_table()
        if input_file is None:
            print("❌ Could not find lookup table file. Please specify with --input")
            return
    
    # Set output directory
    if args.output_dir:
        # If output_dir is provided (from pipeline), create cluster subdirectory
        output_dir = os.path.join(args.output_dir, "cluster")
    else:
        # Standalone run - create timestamped directory
        input_dir = os.path.dirname(input_file)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(input_dir, f"hierarchical_clustering_{timestamp}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🚀 Starting hierarchical clustering with elbow method...")
    print(f"📁 Input: {input_file}")
    print(f"📁 Output: {output_dir}")
    
    # Load lookup table
    processed_entries, comment_texts, lookup_ids = load_lookup_table(input_file)
    
    if len(processed_entries) == 0:
        print("❌ No valid entries found in lookup table")
        return
    
    # Sample if requested
    if args.sample and args.sample < len(processed_entries):
        print(f"\n📊 Sampling {args.sample} entries for testing...")
        # Random sample
        import random
        random.seed(42)  # For reproducibility
        indices = random.sample(range(len(processed_entries)), args.sample)
        processed_entries = [processed_entries[i] for i in indices]
        comment_texts = [comment_texts[i] for i in indices]
        lookup_ids = [lookup_ids[i] for i in indices]
        print(f"✅ Using {len(processed_entries)} sampled entries")
    
    # Create embeddings
    embeddings = create_embeddings(comment_texts, args.model)
    
    # Find optimal number of main clusters using elbow method (2-5)
    print("\n🔍 Finding optimal number of main clusters using elbow method...")
    k_range = range(2, 6)
    wcss = calculate_wcss(embeddings, k_range)
    optimal_k = find_elbow_point(wcss, k_range)
    
    # Plot main elbow curve
    plot_elbow_curve(wcss, k_range, optimal_k, output_dir, prefix="Main ")
    
    print(f"\n✅ Optimal number of main clusters: {optimal_k}")
    
    # Perform main clustering
    main_labels, linkage_matrix = perform_hierarchical_clustering(embeddings, optimal_k)
    
    # Create dendrogram for main clusters
    plt.figure(figsize=(15, 8))
    dendrogram(linkage_matrix, truncate_mode='lastp', p=30, leaf_rotation=90, leaf_font_size=12)
    plt.title('Hierarchical Clustering Dendrogram (Main Clusters)')
    plt.xlabel('Sample Index or (Cluster Size)')
    plt.ylabel('Distance (Ward)')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'main_dendrogram.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # Perform recursive clustering on each main cluster
    clustering_results = []
    for cluster_id in range(optimal_k):
        print(f"\n🔍 Analyzing main cluster {cluster_id}...")
        result = recursive_clustering(embeddings, processed_entries, main_labels, 
                                    cluster_id, output_dir)
        clustering_results.append(result)
    
    # Create visualizations
    embeddings_2d = create_hierarchical_visualization(clustering_results, processed_entries, 
                                                    embeddings, output_dir)
    
    # Create report
    create_hierarchical_report(clustering_results, output_dir)
    
    # Update lookup table
    update_lookup_table_with_hierarchical_clusters(input_file, clustering_results, 
                                                 embeddings_2d, processed_entries)
    
    # Summary statistics
    total_clusters = len(clustering_results)
    total_subclusters = sum(len(r['subclusters']) for r in clustering_results)
    
    print(f"\n✅ Hierarchical clustering complete!")
    print(f"📊 Created {total_clusters} main clusters")
    print(f"📊 Created {total_subclusters} subclusters")
    print(f"📁 Output files:")
    print(f"   - {os.path.join(output_dir, 'main_elbow_curve.png')}")
    print(f"   - {os.path.join(output_dir, 'main_dendrogram.png')}")
    print(f"   - {os.path.join(output_dir, 'hierarchical_clusters_visualization.png')}")
    print(f"   - {os.path.join(output_dir, 'hierarchical_cluster_report.txt')}")
    print(f"   - {input_file} (updated with cluster IDs)")

if __name__ == "__main__":
    main()