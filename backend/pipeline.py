#!/usr/bin/env python3
"""
Main Pipeline for Schedule F Comment Analysis

This script orchestrates the complete analysis pipeline using the new lookup table approach:
1. Fetch comments from CSV → raw_data.json
2. Create deduplicated lookup table → lookup_table.json  
3. Run LLM analysis on unique texts → lookup_table_analyzed.json
4. Run semantic clustering → lookup_table_analyzed_clustered.json

Usage:
python pipeline.py --csv comments.csv [--output_dir output] [--truncate 500] [--model gpt-4o-mini]
"""

import json
import os
import argparse
import logging
from typing import Optional
from datetime import datetime

# Initial logger setup (will be reconfigured with file handler in main)
logger = logging.getLogger(__name__)

def setup_logging(output_dir: str):
    """Set up logging with file handler in the output directory."""
    log_file = os.path.join(output_dir, 'pipeline.log')
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Set up new handlers
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ],
        force=True  # Override existing configuration
    )
    logger.info(f"📝 Logging to: {log_file}")

def main():
    """Main pipeline orchestration function."""
    parser = argparse.ArgumentParser(description='Schedule F comment analysis pipeline')
    parser.add_argument('--csv', type=str, required=True,
                       help='Path to comments.csv file')
    parser.add_argument('--output_dir', type=str, default='.',
                       help='Output directory (default: current directory)')
    parser.add_argument('--truncate', type=int, default=None,
                       help='Truncate text to this many characters')
    parser.add_argument('--model', type=str, default='gpt-4o-mini',
                       help='LLM model for analysis (default: gpt-4o-mini)')
    parser.add_argument('--n_clusters', type=int, default=15,
                       help='Number of clusters for semantic analysis (default: 15)')
    parser.add_argument('--skip_analysis', action='store_true',
                       help='Skip LLM analysis (only create lookup table)')
    parser.add_argument('--skip_clustering', action='store_true',
                       help='Skip clustering (only do data fetching and LLM analysis)')
    
    args = parser.parse_args()
    
    # Setup paths
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Set up logging with output directory
    setup_logging(args.output_dir)
    
    raw_data_path = os.path.join(args.output_dir, 'raw_data.json')
    lookup_table_path = os.path.join(args.output_dir, 'lookup_table.json')
    
    logger.info(f"🚀 Starting Schedule F analysis pipeline...")
    logger.info(f"📁 CSV file: {args.csv}")
    logger.info(f"📁 Output directory: {args.output_dir}")
    logger.info(f"🎯 Truncation: {args.truncate or 'None'}")
    logger.info(f"🤖 Model: {args.model}")
    
    try:
        # Step 1: Fetch comments from CSV
        logger.info(f"\n=== STEP 1: Fetching Comments from CSV ===")
        from .fetch.fetch_comments import read_comments_from_csv
        
        logger.info(f"Reading comments from {args.csv}...")
        raw_data_file = read_comments_from_csv(args.csv, args.output_dir)
        logger.info(f"✅ Raw comments saved to {raw_data_file}")
        
        # Step 2: Create lookup table
        logger.info(f"\n=== STEP 2: Creating Deduplicated Lookup Table ===")
        from .analysis.create_lookup_table import create_lookup_table
        
        logger.info(f"Creating lookup table from {raw_data_file}...")
        
        # Load raw data
        with open(raw_data_file, 'r') as f:
            raw_data = json.load(f)
            
        # Create lookup table
        lookup_table = create_lookup_table(raw_data, args.truncate)
        
        # Save lookup table
        with open(lookup_table_path, 'w') as f:
            json.dump(lookup_table, f, indent=2)
            
        logger.info(f"✅ Lookup table saved to {lookup_table_path}")
        
        # Get stats (lookup_table is already loaded)
        
        total_comments = sum(entry.get('comment_count', 0) for entry in lookup_table)
        unique_texts = len(lookup_table)
        dedup_efficiency = round((1 - unique_texts / total_comments) * 100, 1) if total_comments > 0 else 0
        
        logger.info(f"📊 Deduplication stats:")
        logger.info(f"   Total comments: {total_comments:,}")
        logger.info(f"   Unique text patterns: {unique_texts:,}")
        logger.info(f"   Deduplication efficiency: {dedup_efficiency}%")
        
        # Step 3: LLM Analysis
        analyzed_path = lookup_table_path
        if not args.skip_analysis:
            logger.info(f"\n=== STEP 3: LLM Analysis ({unique_texts} unique texts) ===")
            from .analysis.analyze_lookup_table import analyze_lookup_table_batch
            from .utils.comment_analyzer import CommentAnalyzer
            
            # Initialize analyzer
            analyzer = CommentAnalyzer(model=args.model)
            
            # Analyze lookup table
            analyzed_lookup_table = analyze_lookup_table_batch(
                lookup_table=lookup_table,
                analyzer=analyzer,
                batch_size=5,
                use_parallel=True,
                checkpoint_file=f"{lookup_table_path}.checkpoint"
            )
            
            # Save analyzed lookup table back to the original file
            with open(lookup_table_path, 'w') as f:
                json.dump(analyzed_lookup_table, f, indent=2)
            
            logger.info(f"✅ Analysis complete, saved to {lookup_table_path}")
        else:
            logger.info(f"\n=== STEP 3: Skipping LLM Analysis ===")
        
        # Step 4: Semantic Clustering
        if not args.skip_clustering and unique_texts >= 2:
            logger.info(f"\n=== STEP 4: Semantic Clustering ===")
            
            # Ensure we don't request more clusters than entries
            n_clusters = min(args.n_clusters, unique_texts)
            logger.info(f"Clustering {unique_texts} entries into {n_clusters} clusters")
            
            # Import and run clustering
            import sys
            import subprocess
            
            # Get absolute path to the semantic_lookup script
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            semantic_script = os.path.join(script_dir, 'backend', 'analysis', 'semantic_lookup.py')
            
            clustering_cmd = [
                sys.executable, 
                semantic_script,
                '--input', lookup_table_path,
                '--n_clusters', str(n_clusters)
            ]
            
            result = subprocess.run(clustering_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Clustering complete")
                logger.info(result.stdout)
            else:
                logger.error("❌ Clustering failed")
                logger.error(result.stderr)
        elif unique_texts < 2:
            logger.info(f"\n=== STEP 4: Skipping Clustering (too few entries: {unique_texts}) ===")
        else:
            logger.info(f"\n=== STEP 4: Skipping Clustering ===")
        
        # Step 5: Quote verification (always run if analysis was performed)
        if not args.skip_analysis and unique_texts > 0:
            logger.info(f"\n=== STEP 5: Quote Verification ===")
            
            # Import and run quote verification
            from .analysis.verify_lookup_quotes import verify_lookup_quotes
            
            # Use the lookup table path for verification
            verification_output = lookup_table_path.replace('.json', '_quote_verification.json')
            
            logger.info(f"Verifying quotes in {lookup_table_path}...")
            verification_results = verify_lookup_quotes(lookup_table_path, verification_output)
            
            if verification_results:
                logger.info(f"✅ Quote verification complete")
                logger.info(f"   Verification rate: {verification_results.get('verification_rate', 0)}%")
                logger.info(f"   Exact matches: {verification_results.get('exact_match_rate', 0)}%")
                logger.info(f"   Quotes not found: {verification_results.get('quotes_not_found', 0)} ({round(verification_results.get('quotes_not_found', 0) / max(1, verification_results.get('entries_with_quotes', 1)) * 100, 1)}%)")
                logger.info(f"   Results saved to: {verification_output}")
                logger.info(f"   Text report: {verification_output.replace('.json', '.txt')}")
            else:
                logger.error("❌ Quote verification failed")
        
        # Final summary
        logger.info(f"\n🎉 Pipeline complete!")
        logger.info(f"📊 Final stats:")
        logger.info(f"   Total comments processed: {total_comments:,}")
        logger.info(f"   Unique text patterns: {unique_texts:,}")
        logger.info(f"   API calls saved: ~{total_comments - unique_texts:,} ({dedup_efficiency}%)")
        logger.info(f"📁 Output files in {args.output_dir}:")
        logger.info(f"   - raw_data.json (original comments + attachments)")
        logger.info(f"   - lookup_table.json (deduplicated patterns with analysis)")
        if not args.skip_analysis:
            logger.info(f"   - lookup_table_quote_verification.json")
            logger.info(f"   - lookup_table_quote_verification.txt")
        if not args.skip_clustering and unique_texts >= 2:
            logger.info(f"   - lookup_table_clustered.json (with clustering)")
            logger.info(f"   - clustering_*/")
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    main()