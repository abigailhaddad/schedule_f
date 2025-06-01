#!/usr/bin/env python3
"""
Main Pipeline for Schedule F Comment Analysis

This script orchestrates the complete analysis pipeline using the new lookup table approach:
1. Fetch comments from CSV → raw_data.json
2. Create deduplicated lookup table → lookup_table.json  
3. Run LLM analysis on unique texts (updates lookup_table.json in place)
4. Run semantic clustering (adds cluster data to lookup_table.json)

Usage:
python pipeline.py --csv comments.csv [--output_dir output] [--truncate 500] [--model gpt-4o-mini]
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Optional
from pathlib import Path

from .config import config
from .fetch import read_comments_from_csv, download_all_attachments
from .analysis import create_lookup_table, analyze_lookup_table_batch
from .analysis.verify_lookup_quotes import verify_lookup_quotes
from .utils import (
    CommentAnalyzer,
    PipelineLogger,
    FileManager,
    FileOperationError,
    ConfigurationError,
)
from .utils.validate_pipeline_output import validate_pipeline_output, print_validation_summary

# Set up logger
logger = PipelineLogger.get_logger(__name__)

def setup_pipeline_logging(output_dir: Path) -> None:
    """Set up logging for the pipeline using the centralized logger."""
    global logger
    logger = PipelineLogger.setup_logger(
        name="pipeline",
        output_dir=output_dir,
        log_file="pipeline.log",
        include_timestamp=False
    )

def main():
    """Main pipeline orchestration function."""
    parser = argparse.ArgumentParser(description='Schedule F comment analysis pipeline')
    parser.add_argument('--csv', type=str, required=True,
                       help='Path to comments.csv file')
    parser.add_argument('--output_dir', type=str, default=config.files.output_dir,
                       help=f'Output directory (default: {config.files.output_dir})')
    parser.add_argument('--truncate', type=int, default=None,
                       help='Truncate text to this many characters')
    parser.add_argument('--model', type=str, default=config.llm.model,
                       help=f'LLM model for analysis (default: {config.llm.model})')
    parser.add_argument('--skip_analysis', action='store_true',
                       help='Skip LLM analysis (only create lookup table)')
    parser.add_argument('--skip_clustering', action='store_true',
                       help='Skip clustering (only do data fetching and LLM analysis)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of comments to process (for testing)')
    
    args = parser.parse_args()
    
    try:
        # Setup paths
        output_dir = Path(args.output_dir)
        FileManager.ensure_directory(output_dir)
        
        # Set up logging
        setup_pipeline_logging(output_dir)
        
        raw_data_path = output_dir / config.files.raw_data_filename
        lookup_table_path = output_dir / config.files.lookup_table_filename
        
    except (FileOperationError, ConfigurationError) as e:
        print(f"❌ Setup failed: {e}")
        return 1
    
    logger.info(f"🚀 Starting Schedule F analysis pipeline...")
    logger.info(f"📁 CSV file: {args.csv}")
    logger.info(f"📁 Output directory: {args.output_dir}")
    logger.info(f"🎯 Truncation: {args.truncate or 'None'}")
    logger.info(f"🤖 Model: {args.model}")
    
    try:
        # Step 1: Fetch comments from CSV
        logger.info(f"\n=== STEP 1: Fetching Comments from CSV ===")
        
        logger.info(f"Reading comments from {args.csv}...")
        if args.limit:
            logger.info(f"Limiting to first {args.limit} comments")
        raw_data_file = read_comments_from_csv(args.csv, args.output_dir, limit=args.limit)
        logger.info(f"✅ Raw comments saved to {raw_data_file}")
        
        # Step 2: Download and analyze attachments BEFORE creating lookup table
        logger.info(f"\n=== STEP 2: Downloading and Analyzing Attachments ===")
        
        # Load raw data
        with open(raw_data_file, 'r') as f:
            raw_data = json.load(f)
        
        # Check if there are any attachments to download
        total_attachments = sum(comment.get('attributes', {}).get('attachmentCount', 0) for comment in raw_data)
        
        if total_attachments > 0:
            # Download attachments
            logger.info(f"Downloading {total_attachments} attachments to {args.output_dir}...")
            updated_data = download_all_attachments(raw_data, args.output_dir)
            
            # Save updated data back
            with open(raw_data_file, 'w') as f:
                json.dump(updated_data, f, indent=2)
            
            # Run attachment analysis
            attachments_dir = os.path.join(args.output_dir, "attachments")
            if os.path.exists(attachments_dir):
                logger.info(f"Analyzing attachment text extraction...")
                
                analyze_cmd = [
                    sys.executable,
                    os.path.join(os.path.dirname(__file__), 'fetch', 'analyze_attachments.py'),
                    '--results_dir', attachments_dir
                ]
                
                result = subprocess.run(analyze_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("✅ Attachment analysis complete")
                    logger.info(result.stdout)
                else:
                    logger.error("❌ Attachment analysis failed")
                    logger.error(result.stderr)
            
            # Reload the data with attachment text
            with open(raw_data_file, 'r') as f:
                raw_data = json.load(f)
        else:
            logger.info("No attachments to download")
        
        # Step 3: Create lookup table (AFTER attachments are processed)
        logger.info(f"\n=== STEP 3: Creating Deduplicated Lookup Table ===")
        
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
        
        # Step 4: LLM Analysis
        analyzed_path = lookup_table_path
        if not args.skip_analysis:
            logger.info(f"\n=== STEP 4: LLM Analysis ({unique_texts} unique texts) ===")
            
            # Initialize analyzer
            analyzer = CommentAnalyzer(model=args.model)
            
            # Analyze lookup table
            analyzed_lookup_table = analyze_lookup_table_batch(
                lookup_table=lookup_table,
                analyzer=analyzer,
                batch_size=config.llm.batch_size,
                use_parallel=True,
                checkpoint_file=f"{lookup_table_path}.checkpoint"
            )
            
            # Save analyzed lookup table back to the original file
            with open(lookup_table_path, 'w') as f:
                json.dump(analyzed_lookup_table, f, indent=2)
            
            logger.info(f"✅ Analysis complete, saved to {lookup_table_path}")
        else:
            logger.info(f"\n=== STEP 4: Skipping LLM Analysis ===")
        
        # Step 5: Semantic Clustering
        if not args.skip_clustering and unique_texts >= 2:
            logger.info(f"\n=== STEP 5: Semantic Clustering ===")
            
            logger.info(f"Running hierarchical clustering on {unique_texts} entries")
            
            # Run clustering
            
            # Get absolute path to the hierarchical_clustering script
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            clustering_script = os.path.join(script_dir, 'backend', 'analysis', 'hierarchical_clustering.py')
            
            clustering_cmd = [
                sys.executable, 
                clustering_script,
                '--input', lookup_table_path,
                '--output_dir', args.output_dir
            ]
            
            result = subprocess.run(clustering_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Clustering complete")
                logger.info(result.stdout)
            else:
                logger.error("❌ Clustering failed")
                logger.error(result.stderr)
        elif unique_texts < 2:
            logger.info(f"\n=== STEP 5: Skipping Clustering (too few entries: {unique_texts}) ===")
        else:
            logger.info(f"\n=== STEP 5: Skipping Clustering ===")
        
        # Step 6: Quote verification (always run if analysis was performed)
        if not args.skip_analysis and unique_texts > 0:
            logger.info(f"\n=== STEP 6: Quote Verification ===")
            
            # Run quote verification
            
            # Use the lookup table path for verification  
            verification_output = str(lookup_table_path).replace('.json', '_quote_verification.json')
            
            logger.info(f"Verifying quotes in {lookup_table_path}...")
            verification_results = verify_lookup_quotes(str(lookup_table_path), verification_output)
            
            if verification_results:
                logger.info(f"✅ Quote verification complete")
                logger.info(f"   Verification rate: {verification_results.get('verification_rate', 0)}%")
                logger.info(f"   Exact matches: {verification_results.get('exact_match_rate', 0)}%")
                logger.info(f"   Quotes not found: {verification_results.get('quotes_not_found', 0)} ({round(verification_results.get('quotes_not_found', 0) / max(1, verification_results.get('entries_with_quotes', 1)) * 100, 1)}%)")
                logger.info(f"   Results saved to: {verification_output}")
                logger.info(f"   Text report: {verification_output.replace('.json', '.txt')}")
            else:
                logger.error("❌ Quote verification failed")
        
        # Step 7: Validate output
        logger.info(f"\n=== STEP 7: Validating Pipeline Output ===")
        
        validation_results = validate_pipeline_output(
            csv_file=args.csv,
            raw_data_file=raw_data_path,
            data_file=None,  # No data.json created in pipeline anymore
            lookup_table_file=lookup_table_path,
            skip_analysis_validation=args.skip_analysis,
            skip_count_validation=bool(args.limit)  # Skip count validation if using --limit
        )
        
        # Print validation summary
        print_validation_summary(validation_results)
        
        if not validation_results['valid']:
            logger.error("❌ Pipeline validation failed! Check errors above.")
        
        # Final summary
        logger.info(f"\n{'='*60}")
        logger.info(f"🎉 PIPELINE COMPLETE!")
        logger.info(f"{'='*60}")
        logger.info(f"\n📊 Final stats:")
        logger.info(f"   Total comments processed: {total_comments:,}")
        logger.info(f"   Unique text patterns: {unique_texts:,}")
        logger.info(f"   Deduplication efficiency: {dedup_efficiency}%")
        logger.info(f"   API calls saved: ~{total_comments - unique_texts:,}")
        
        logger.info(f"\n📁 Output files in {args.output_dir}:")
        logger.info(f"   - {config.files.raw_data_filename} (original comments + attachments)")
        logger.info(f"   - {config.files.lookup_table_filename} (deduplicated patterns with analysis)")
        if total_attachments > 0:
            logger.info(f"   - attachments/ (downloaded attachment files with .extracted.txt)")
        if not args.skip_analysis:
            logger.info(f"   - lookup_table_quote_verification.json")
            logger.info(f"   - lookup_table_quote_verification.txt")
        if not args.skip_clustering and unique_texts >= 2:
            logger.info(f"   - cluster/ (clustering results directory)")
            logger.info(f"     - hierarchical_cluster_report.txt")
            logger.info(f"     - hierarchical_clusters_visualization.png")
            logger.info(f"     - main_dendrogram.png")
            logger.info(f"     - main_elbow_curve.png")
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    main()