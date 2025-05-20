#!/usr/bin/env python3
"""
Pipeline Script for Comment Fetching and Analysis

This script coordinates the fetching and analysis of regulatory comments:
1. Creates a timestamped results folder
2. Runs fetch_comments.py to fetch comments and save as raw_data.json
3. Runs analyze_comments.py to analyze the comments and save as data.json

Can be run in three modes:
- Full pipeline: python pipeline.py
- Fetch only: python pipeline.py --fetch-only
- Analyze only: python pipeline.py --analyze-only (uses most recent timestamped folder)
"""

import os
import sys
import glob
import json
import argparse
import importlib.util
import subprocess
from datetime import datetime
from pathlib import Path


def get_latest_results_dir(base_dir):
    """Find the most recent timestamped results directory."""
    result_dirs = glob.glob(os.path.join(base_dir, "results_*"))
    if not result_dirs:
        return None
    # Sort by creation time (newest first)
    result_dirs.sort(key=os.path.getctime, reverse=True)
    return result_dirs[0]


def create_timestamped_dir(base_dir="results"):
    """Create a timestamped directory for results."""
    # Ensure base directory exists
    os.makedirs(base_dir, exist_ok=True)
    
    # Create timestamped directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_dir = os.path.join(base_dir, f"results_{timestamp}")
    os.makedirs(result_dir, exist_ok=True)
    
    print(f"Created results directory: {result_dir}")
    return result_dir


def run_fetch(output_dir, **kwargs):
    """Run the fetch script to pull comments."""
    # Import the fetch_comments.py module
    spec = importlib.util.spec_from_file_location("fetch_comments", "fetch_comments.py")
    fetch_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch_module)
    
    # Define output path for raw data
    raw_data_path = os.path.join(output_dir, "raw_data.json")
    
    print(f"Fetching comments to {raw_data_path}...")
    
    # Call the fetch_comments function with the output directory
    try:
        # Extract document_id, limit, and api_key from kwargs if provided
        document_id = kwargs.get('document_id', "OPM-2025-0004-0001")
        limit = kwargs.get('limit', None)
        api_key = kwargs.get('api_key', None)
        
        # Call the fetch function
        result_path = fetch_module.fetch_comments(
            document_id=document_id,
            output_dir=output_dir,  # Use the timestamped directory
            limit=limit,
            api_key=api_key
        )
        
        # Move/rename the output file to raw_data.json if needed
        if result_path != raw_data_path:
            os.rename(result_path, raw_data_path)
            print(f"Renamed output to {raw_data_path}")
        
        return raw_data_path
    except Exception as e:
        print(f"Error fetching comments: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_analysis(input_path, output_dir, **kwargs):
    """Run the analysis script on fetched comments."""
    # Import the analyze_comments.py module
    spec = importlib.util.spec_from_file_location("analyze_comments", "analyze_comments.py")
    analyze_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analyze_module)
    
    # Define output path
    output_path = os.path.join(output_dir, "data.json")
    
    print(f"Analyzing comments from {input_path}...")
    print(f"Results will be saved to {output_path}")
    
    try:
        # Extract parameters from kwargs if provided
        top_n = kwargs.get('top_n', None)
        model = kwargs.get('model', "gpt-4o-mini")
        api_key = kwargs.get('api_key', None)
        resume = kwargs.get('resume', False)
        
        # Call the analyze function
        analyze_module.analyze_comments(
            input_file=input_path,
            output_file=output_path,
            top_n=top_n,
            model=model,
            api_key=api_key,
            resume=resume
        )
        
        # Run quote verification after analysis is complete
        print("Running quote verification...")
        verify_quotes_module = importlib.util.spec_from_file_location("verify_quotes", "verify_quotes.py")
        verify_module = importlib.util.module_from_spec(verify_quotes_module)
        verify_quotes_module.loader.exec_module(verify_module)
        
        verification_path = os.path.join(output_dir, "quote_verification.txt")
        verify_module.verify_quotes(input_path, output_path, verification_path)
        
        return output_path
    except Exception as e:
        print(f"Error analyzing comments: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function to run the pipeline."""
    parser = argparse.ArgumentParser(description='Pipeline for fetching and analyzing comments')
    parser.add_argument('--fetch-only', action='store_true', help='Only fetch comments, don\'t analyze')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze comments from most recent fetch')
    parser.add_argument('--base-dir', type=str, default='results', help='Base directory for results')
    
    # Fetch parameters
    parser.add_argument('--document-id', type=str, default="OPM-2025-0004-0001", 
                        help='Document ID to fetch comments for')
    parser.add_argument('--limit', type=int, default=None, 
                        help='Limit number of comments to fetch')
    parser.add_argument('--no-attachments', action='store_true',
                        help='Do not download and extract text from attachments')
    parser.add_argument('--start-page', type=int, default=1,
                    help='Start page number for fetching comments (default: 1)')

    
    # Analysis parameters
    parser.add_argument('--top-n', type=int, default=None, 
                        help='Analyze only the top N comments')
    parser.add_argument('--model', type=str, default='gpt-4o-mini', 
                        help='Model to use for analysis')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from checkpoints if available for fetch and/or analyze')
    
    # API keys
    parser.add_argument('--regs-api-key', type=str, default=None, 
                        help='API key for regulations.gov (if not in environment)')
    parser.add_argument('--openai-api-key', type=str, default=None, 
                        help='API key for OpenAI (if not in environment)')
    
    args = parser.parse_args()
    
    # Extract parameters
    fetch_params = {
    'document_id': args.document_id,
    'limit': args.limit,
    'api_key': args.regs_api_key,
    'download_attachments': not args.no_attachments,
    'resume': args.resume,
    'start_page': args.start_page,
}

    
    analyze_params = {
        'top_n': args.top_n,
        'model': args.model,
        'api_key': args.openai_api_key,
        'resume': args.resume
    }
    
    # Handle fetch-only mode
    if args.fetch_only:
        result_dir = create_timestamped_dir(args.base_dir)
        raw_data_path = run_fetch(result_dir, **fetch_params)
        if raw_data_path:
            print(f"✅ Fetch completed successfully. Results saved to {raw_data_path}")
        else:
            print("❌ Fetch failed")
            return 1
        return 0
    
    # Handle analyze-only mode
    if args.analyze_only:
        # Find most recent result directory
        result_dir = get_latest_results_dir(args.base_dir)
        if not result_dir:
            print(f"❌ No results directories found in {args.base_dir}")
            return 1
        
        # Look for raw_data.json in that directory
        raw_data_path = os.path.join(result_dir, "raw_data.json")
        if not os.path.exists(raw_data_path):
            print(f"❌ No raw_data.json found in {result_dir}")
            return 1
        
        # Run analysis
        data_path = run_analysis(raw_data_path, result_dir, **analyze_params)
        if data_path:
            print(f"✅ Analysis completed successfully. Results saved to {data_path}")
        else:
            print("❌ Analysis failed")
            return 1
        return 0
    
    # Full pipeline mode
    result_dir = create_timestamped_dir(args.base_dir)
    
    # Step 1: Fetch comments
    raw_data_path = run_fetch(result_dir, **fetch_params)
    if not raw_data_path:
        print("❌ Fetch failed, stopping pipeline")
        return 1
    
    # Step 2: Analyze comments
    data_path = run_analysis(raw_data_path, result_dir, **analyze_params)
    if not data_path:
        print("❌ Analysis failed")
        return 1
    
    print("\n===== Pipeline Execution Summary =====")
    print(f"Results directory: {result_dir}")
    print(f"Raw data: {raw_data_path}")
    print(f"Analysis results: {data_path}")
    print("✅ Pipeline completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())