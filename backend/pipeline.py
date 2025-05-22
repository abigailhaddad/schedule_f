#!/usr/bin/env python3
"""
Full Data Pipeline for Schedule F Analysis

This script provides a unified pipeline that:
1. Fetches comments from regulations.gov or reads from CSV
2. Downloads attachments with robust retry logic
3. Analyzes comments using LiteLLM
4. Indexes comments for search in frontend

Usage: python -m backend.pipeline --help
"""

import os
import argparse
import time
import glob
import json
import shutil
from datetime import datetime
from typing import Optional
from pathlib import Path

# Import from backend packages
from fetch.fetch_comments import fetch_comments, read_comments_from_csv, download_all_attachments
from analysis.analyze_comments import analyze_comments
from utils.common import create_directory, create_timestamped_dir, get_latest_results_dir

def run_pipeline(document_id: str = "OPM-2025-0004-0001", 
                limit: Optional[int] = None, 
                skip_fetch: bool = False,
                skip_analyze: bool = False,
                skip_index: bool = False,
                skip_attachments: bool = False,
                resume: bool = False,
                input_file: Optional[str] = None,
                csv_file: Optional[str] = None,
                output_dir: Optional[str] = None,
                model: str = "gpt-4o-mini",
                api_key: Optional[str] = None):
    """
    Run the complete comment processing pipeline.
    
    Args:
        document_id: Document ID to fetch comments for (default: OPM-2025-0004-0001)
        limit: Maximum number of comments to process (default: process all)
        skip_fetch: Skip fetching comments and use existing data
        skip_analyze: Skip analyzing comments
        skip_index: Skip building the search index
        skip_attachments: Skip downloading attachments
        resume: Resume from last checkpoint if available
        input_file: Input file with comments (used if skip_fetch=True)
        csv_file: CSV file with comments (used instead of API calls)
        output_dir: Directory to save all results (default: data/results/results_TIMESTAMP)
        model: Model to use for analysis
        api_key: OpenAI API key (optional, will use environment variable if not provided)
    
    Returns:
        Path to the results directory
    """
    # Set up output directory
    if output_dir is None:
        # Create timestamped directory for results
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = create_timestamped_dir(os.path.join(project_root, "results"))
    else:
        # Use provided directory
        create_directory(output_dir)
    
    print(f"\n=== Pipeline starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    print(f"Results will be saved to: {output_dir}")
    
    # Setup files
    raw_data_file = os.path.join(output_dir, "raw_data.json")
    analyzed_data_file = os.path.join(output_dir, "data.json")
    
    # Set API key in environment if provided
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

    # Step 1: Process comments (either from API or CSV)
    if not skip_fetch:
        print("\n=== Step 1: Processing comments ===")
        if csv_file:
            # Read comments from CSV file
            print(f"Using CSV file: {csv_file}")
            read_comments_from_csv(csv_file, output_dir, limit)
        else:
            # Fetch comments from API
            print(f"Fetching comments from API for document ID: {document_id}")
            fetch_comments(
                document_id=document_id,
                output_dir=output_dir,
                limit=limit,
                resume=resume
            )
    else:
        print("\n=== Step 1: Skipping fetch as requested ===")
        # If we're skipping fetch but provided an input file, copy it to the output directory
        if input_file:
            if not os.path.exists(input_file):
                raise FileNotFoundError(f"Input file not found: {input_file}")
            
            print(f"Copying input file {input_file} to {raw_data_file}")
            shutil.copy2(input_file, raw_data_file)
        else:
            # Check if the raw_data.json exists in the output directory
            if not os.path.exists(raw_data_file):
                raise FileNotFoundError(f"No raw_data.json found in {output_dir} and no input file provided")
    
    # Step 1.5: Download attachments
    if not skip_attachments:
        print("\n=== Step 1.5: Downloading attachments ===")
        # Load the raw data file
        with open(raw_data_file, 'r') as f:
            comments_data = json.load(f)
        
        # Download all attachments
        updated_comments = download_all_attachments(comments_data, output_dir)
        
        # Save the updated comments with local paths to attachments
        with open(raw_data_file, 'w') as f:
            json.dump(updated_comments, f, indent=2)
    else:
        print("\n=== Step 1.5: Skipping attachment download as requested ===")
    
    # Step 2: Analyze comments
    if not skip_analyze:
        print("\n=== Step 2: Analyzing comments ===")
        analyze_comments(
            input_file=raw_data_file,
            output_file=analyzed_data_file,
            model=model,
            resume=resume,
            batch_size=10,  # Process 10 comments in parallel
            no_delay=True   # Remove artificial delays
        )
    else:
        print("\n=== Step 2: Skipping analysis as requested ===")


    # Step 3: Build search index - DISABLED
    if not skip_index:
        print("\n=== Step 3: Skipping index building (feature disabled) ===")
    else:
        print("\n=== Step 3: Skipping index building as requested ===")
    
    print(f"\n=== Pipeline completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    print(f"All results saved to: {output_dir}")
    
    # Copy the results to the frontend directory
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        frontend_data_dir = os.path.join(project_root, "frontend")
        
        # Create frontend directory if it doesn't exist (no subdirectories)
        if not os.path.exists(frontend_data_dir):
            os.makedirs(frontend_data_dir, exist_ok=True)
        
        if os.path.exists(analyzed_data_file):
            print(f"\nCopying data.json to frontend directory...")
            shutil.copy2(analyzed_data_file, os.path.join(frontend_data_dir, "data.json"))
            print(f"Copied to {os.path.join(frontend_data_dir, 'data.json')}")
    except Exception as e:
        print(f"Error copying results to frontend directory: {e}")
    
    return output_dir

def main():
    """Main function to parse arguments and run the pipeline."""
    parser = argparse.ArgumentParser(description='Run the full comment processing pipeline')
    
    # Document selection options
    parser.add_argument('--document_id', type=str, default="OPM-2025-0004-0001",
                      help='Document ID to fetch comments for (default: OPM-2025-0004-0001)')
    parser.add_argument('--limit', type=int, default=None,
                      help='Limit number of comments to process (default: process all)')
    
    # Pipeline control options
    parser.add_argument('--skip_fetch', action='store_true',
                      help='Skip fetching comments and use existing data')
    parser.add_argument('--skip_analyze', action='store_true',
                      help='Skip analyzing comments')
    parser.add_argument('--skip_index', action='store_true',
                      help='Skip building the search index')
    parser.add_argument('--skip_attachments', action='store_true',
                      help='Skip downloading attachments')
    parser.add_argument('--resume', action='store_true',
                      help='Resume from last checkpoint if available')
    
    # Input/Output options
    parser.add_argument('--input_file', type=str, default=None,
                      help='Input file with comments (used if skip_fetch=True)')
    parser.add_argument('--csv_file', type=str, default=None,
                      help='CSV file with comments (used instead of API calls)')
    parser.add_argument('--output_dir', type=str, default=None,
                      help='Directory to save all results (default: data/results/results_TIMESTAMP)')
    
    # Analysis options
    parser.add_argument('--model', type=str, default='gpt-4.1-mini',
                      help='Model to use for analysis (default: gpt-4.1-mini)')
    parser.add_argument('--api_key', type=str, default=None,
                      help='OpenAI API key (optional, will use environment variable if not provided)')
    
    args = parser.parse_args()
    
    try:
        # If skipping fetch but no input file provided or raw_data.json doesn't exist,
        # try to find the latest results directory
        if args.skip_fetch and not args.input_file and not args.output_dir and not args.csv_file:
            # Try to find the latest results directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            latest_dir = get_latest_results_dir(os.path.join(project_root, "results"))
            
            if latest_dir:
                raw_data_path = os.path.join(latest_dir, "raw_data.json")
                if os.path.exists(raw_data_path):
                    print(f"Found latest results directory: {latest_dir}")
                    print(f"Will use raw_data.json from this directory")
                    args.output_dir = latest_dir
        
        run_pipeline(
            document_id=args.document_id,
            limit=args.limit,
            skip_fetch=args.skip_fetch,
            skip_analyze=args.skip_analyze,
            skip_index=args.skip_index,
            skip_attachments=args.skip_attachments,
            resume=args.resume,
            input_file=args.input_file,
            csv_file=args.csv_file,
            output_dir=args.output_dir,
            model=args.model,
            api_key=args.api_key
        )
    except Exception as e:
        print(f"Error during pipeline execution: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())