#!/usr/bin/env python3
"""
Full Data Pipeline for Schedule F Analysis

This script provides a unified pipeline that:
1. Fetches comments from regulations.gov
2. Analyzes comments using LiteLLM
3. Indexes comments for search in frontend

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
from backend.fetch.fetch_comments import fetch_comments
from backend.analysis.analyze_comments import analyze_comments
from backend.utils.common import create_directory, create_timestamped_dir, get_latest_results_dir

def run_pipeline(document_id: str = "OPM-2025-0004-0001", 
                limit: Optional[int] = None, 
                skip_fetch: bool = False,
                skip_analyze: bool = False,
                skip_index: bool = False,
                resume: bool = False,
                input_file: Optional[str] = None,
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
        resume: Resume from last checkpoint if available
        input_file: Input file with comments (used if skip_fetch=True)
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
        output_dir = create_timestamped_dir(os.path.join(project_root, "data", "results"))
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

    # Step 1: Fetch comments
    if not skip_fetch:
        print("\n=== Step 1: Fetching comments ===")
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
    
    # Step 2: Analyze comments
    if not skip_analyze:
        print("\n=== Step 2: Analyzing comments ===")
        analyze_comments(
            input_file=raw_data_file,
            output_file=analyzed_data_file,
            model=model,
            resume=resume
        )
    else:
        print("\n=== Step 2: Skipping analysis as requested ===")

    # Step 3: Build search index
    if not skip_index:
        print("\n=== Step 3: Building search index ===")
        try:
            # Run the build_search_index.sh script
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            script_path = os.path.join(project_root, "scripts", "build_search_index.sh")
            
            # Check if script exists, if not, create it from build_search_index.sh
            if not os.path.exists(script_path):
                original_script = os.path.join(project_root, "build_search_index.sh")
                if os.path.exists(original_script):
                    # Create scripts directory if needed
                    os.makedirs(os.path.dirname(script_path), exist_ok=True)
                    # Copy the script
                    shutil.copy2(original_script, script_path)
                    print(f"Copied build_search_index.sh to {script_path}")
                else:
                    print(f"Warning: Could not find build_search_index.sh at {original_script}")
                    print("Will try to run the script directly")
            
            # Run the script
            if os.path.exists(script_path):
                # Make it executable
                os.chmod(script_path, 0o755)
                
                # Run the script
                import subprocess
                result = subprocess.run([script_path, analyzed_data_file], 
                                     cwd=project_root,
                                     check=True,
                                     text=True,
                                     capture_output=True)
                print(result.stdout)
                if result.stderr:
                    print(f"Warnings/Errors during indexing:\n{result.stderr}")
            else:
                # Run the Node.js script directly
                js_script = os.path.join(project_root, "build_search_index.js")
                if os.path.exists(js_script):
                    import subprocess
                    result = subprocess.run(["node", js_script, analyzed_data_file], 
                                        cwd=project_root,
                                        check=True,
                                        text=True,
                                        capture_output=True)
                    print(result.stdout)
                    if result.stderr:
                        print(f"Warnings/Errors during indexing:\n{result.stderr}")
                else:
                    print(f"Error: Could not find build_search_index.js at {js_script}")
                    print("Search indexing step failed")
        except Exception as e:
            print(f"Error during search indexing: {e}")
    else:
        print("\n=== Step 3: Skipping index building as requested ===")
    
    print(f"\n=== Pipeline completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    print(f"All results saved to: {output_dir}")
    
    # Copy the results to the frontend directory
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        frontend_data_dir = os.path.join(project_root, "frontend", "public", "data")
        create_directory(frontend_data_dir)
        
        if os.path.exists(analyzed_data_file):
            print(f"\nCopying data.json to frontend directory...")
            shutil.copy2(analyzed_data_file, os.path.join(frontend_data_dir, "data.json"))
            print(f"Copied to {os.path.join(frontend_data_dir, 'data.json')}")
        
        # If search index was built, copy it too
        search_index_file = os.path.join(project_root, "frontend", "public", "search-index.json")
        if os.path.exists(search_index_file):
            shutil.copy2(search_index_file, os.path.join(frontend_data_dir, "search-index.json"))
            print(f"Copied search index to {os.path.join(frontend_data_dir, 'search-index.json')}")
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
    parser.add_argument('--resume', action='store_true',
                      help='Resume from last checkpoint if available')
    
    # Input/Output options
    parser.add_argument('--input_file', type=str, default=None,
                      help='Input file with comments (used if skip_fetch=True)')
    parser.add_argument('--output_dir', type=str, default=None,
                      help='Directory to save all results (default: data/results/results_TIMESTAMP)')
    
    # Analysis options
    parser.add_argument('--model', type=str, default='gpt-4o-mini',
                      help='Model to use for analysis (default: gpt-4o-mini)')
    parser.add_argument('--api_key', type=str, default=None,
                      help='OpenAI API key (optional, will use environment variable if not provided)')
    
    args = parser.parse_args()
    
    try:
        # If skipping fetch but no input file provided or raw_data.json doesn't exist,
        # try to find the latest results directory
        if args.skip_fetch and not args.input_file and not args.output_dir:
            # Try to find the latest results directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            latest_dir = get_latest_results_dir(os.path.join(project_root, "data", "results"))
            
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
            resume=args.resume,
            input_file=args.input_file,
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