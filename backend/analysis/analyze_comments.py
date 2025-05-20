#!/usr/bin/env python3
"""
Comment Analyzer for Schedule F Proposal

This script analyzes public comments on the proposed Schedule F rule using LiteLLM.
It categorizes comments by stance (For/Against/Neutral), identifies key themes,
and extracts important quotes.

Requirements:
- Python 3.8+
- litellm
- pydantic
- tqdm
- python-dotenv

Quick usage:
1. Place 'comments.json' in the current directory or use a previous fetch result
2. Set OPENAI_API_KEY in environment or .env file
3. Run: python -m backend.analysis.analyze_comments

For more options:
python -m backend.analysis.analyze_comments --help
"""

import os
import json
import glob
import argparse
import time
import html
from dotenv import load_dotenv
from litellm import completion
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Union, Set
from tqdm import tqdm
from enum import Enum

# Import from backend utils
from backend.utils.common import strip_html_tags, get_latest_results_dir, create_directory

class Stance(str, Enum):
    FOR = "For"
    AGAINST = "Against"
    NEUTRAL = "Neutral/Unclear"

class Theme(str, Enum):
    MERIT = "Merit-based system concerns"
    DUE_PROCESS = "Due process/employee rights"
    POLITICIZATION = "Politicization concerns"
    SCIENTIFIC = "Scientific integrity"
    INSTITUTIONAL = "Institutional knowledge loss"

class CommentAnalysisResult(BaseModel):
    """Pydantic model for comment analysis results"""
    stance: Stance = Field(
        description="Whether the comment is for, against, or neutral about the proposed rule"
    )
    themes: List[Theme] = Field(
        description="Key themes present in the comment (select all that apply)"
    )
    key_quote: str = Field(
        description="The most important quote or statement from the comment that captures its essence (max 100 words)"
    )
    rationale: str = Field(
        description="Brief explanation of the stance classification (1-2 sentences)"
    )

class CommentAnalyzer:
    """LiteLLM-based analyzer for public comments using Pydantic models for structured output."""
    def __init__(self, model="gpt-4o-mini"):
        self.model = model
        
        # Ensure API key is available
        if "OPENAI_API_KEY" not in os.environ:
            raise ValueError("OPENAI_API_KEY not found in environment variables or .env file")
    
    def get_system_prompt(self):
        return f"""You are analyzing public comments submitted regarding a proposed rule to implement "Schedule F" (or "Schedule Policy/Career").

This proposed rule would allow federal agencies to reclassify career civil servants in policy-influencing positions into a new employment category where they could be removed without the standard due process protections normally afforded to career federal employees.

For each comment (including any attached documents), provide:

1. Stance: Determine if the comment is "{Stance.FOR.value}" (supporting the rule), "{Stance.AGAINST.value}" (opposing the rule), or "{Stance.NEUTRAL.value}. If it says to do something else instead, it's against it.".

2. Themes: Identify which of these themes are present (select all that apply):
   - {Theme.MERIT.value} (mentions civil service protections, merit system, etc.)
   - {Theme.DUE_PROCESS.value} (mentions worker protections, procedural rights, etc.)
   - {Theme.POLITICIZATION.value} (mentions political interference, partisan influence, etc.)
   - {Theme.SCIENTIFIC.value} (mentions concerns about scientific research, grant-making, etc.)
   - {Theme.INSTITUTIONAL.value} (mentions expertise, continuity, experience, etc.)
   
Note: Some comments include text from attached documents. Please consider ALL text in your analysis, including text from attachments if present.

3. Key Quote: Select the most important quote (max 100 words) that best captures the essence of the comment. Important requirements:
   - The quote must be exactly present in the original text - do not paraphrase or modify
   - Copy the text exactly as it appears, maintaining the original punctuation
   - Do not use any special characters, HTML entities (like &rsquo;), or Unicode symbols
   - Use plain ASCII characters only (regular quotes, apostrophes, hyphens, etc.)

4. Rationale: Briefly explain (1-2 sentences) why you classified the stance as you did.

Analyze objectively and avoid inserting personal opinions or biases."""

    def analyze(self, comment_text, comment_id=None):
        """Analyze a comment using LiteLLM with Pydantic for response formatting"""
        identifier = f" (ID: {comment_id})" if comment_id else ""
        try:
            response = completion(temperature=0.0,
                model=self.model,
                messages=[
                    {"role": "system", "content": self.get_system_prompt()},
                    {"role": "user", "content": f"Analyze the following public comment{identifier}:\n\n{comment_text}"}
                ],
                response_format=CommentAnalysisResult
            )
            
            # Process the response based on its format
            if hasattr(response.choices[0].message, 'content') and response.choices[0].message.content:
                if isinstance(response.choices[0].message.content, str):
                    result = json.loads(response.choices[0].message.content)
                else:
                    result = response.choices[0].message.content
            elif hasattr(response.choices[0].message, 'model_dump'):
                result = response.choices[0].message.model_dump()
            else:
                raise ValueError("Unexpected response format")
                
            return result
        except Exception as e:
            print(f"Error analyzing comment{identifier}: {str(e)}")
            raise
# --- Add these new functions to analyze_comments.py ---

def extract_comment_text(comment_data):
    """Extract text and metadata from a comment."""
    if isinstance(comment_data, dict) and 'id' in comment_data:
        comment_id = comment_data['id']
        
        # Check if comment text is directly accessible or in an attributes property
        if 'attributes' in comment_data and isinstance(comment_data['attributes'], dict):
            comment_text = strip_html_tags(comment_data['attributes'].get('comment', ''))
            title = comment_data['attributes'].get('title', '')
            category = comment_data['attributes'].get('category', '')
            
            # Look for attachment texts
            attachment_texts = comment_data['attributes'].get('attachment_texts', [])
            
            # Add attachment text if available
            if attachment_texts:
                for attachment in attachment_texts:
                    attachment_text = strip_html_tags(attachment.get('text', ''))
                    if attachment_text:
                        comment_text += f"\n\n[ATTACHMENT: {attachment.get('title', 'Untitled')}]\n"
                        comment_text += attachment_text
        else:
            comment_text = strip_html_tags(comment_data.get('comment', ''))
            title = comment_data.get('title', '')
            category = comment_data.get('category', '')
            attachment_texts = []
        
        return {
            'id': comment_id,
            'text': comment_text,
            'title': title,
            'category': category,
            'has_attachments': bool(attachment_texts)
        }
    return None

def process_single_comment(comment_data, analyzer, temp_dir, max_retries=3):
    """Process a single comment and return its analysis result."""
    # Extract comment data
    extracted = extract_comment_text(comment_data)
    if not extracted:
        return None
    
    comment_id = extracted['id']
    comment_text = extracted['text']
    title = extracted['title']
    category = extracted['category']
    
    # Skip if already processed (check in temp directory)
    result_file = os.path.join(temp_dir, f"{comment_id}.json")
    if os.path.exists(result_file):
        # Load existing result
        with open(result_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Analyze the comment
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            analysis = analyzer.analyze(comment_text, comment_id)
            
            # Add metadata
            result = {
                "id": comment_id,
                "title": title,
                "category": category,
                "analysis": analysis
            }
            
            # Save individual result to temp directory
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            
            return result
                
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Error analyzing {comment_id} (attempt {attempt+1}/{max_retries}): {e}")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Failed to analyze {comment_id} after {max_retries} attempts: {e}")
                # Add a placeholder result with error information
                error_result = {
                    "id": comment_id,
                    "title": title,
                    "category": category,
                    "analysis": {
                        "status": "error",
                        "error": str(e)
                    }
                }
                # Still save the error result
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(error_result, f, indent=2)
                return error_result

def process_comments_batch(comments_batch, analyzer, temp_dir):
    """Process a batch of comments in parallel."""
    import concurrent.futures
    
    results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_comment = {
            executor.submit(process_single_comment, comment, analyzer, temp_dir): comment
            for comment in comments_batch
        }
        
        for future in concurrent.futures.as_completed(future_to_comment):
            result = future.result()
            if result:
                results.append(result)
    
    return results

def save_checkpoint(results, processed_ids, error_count, checkpoint_file):
    """Save progress to a checkpoint file."""
    checkpoint_data = {
        'results': results,
        'processed_ids': list(processed_ids),
        'error_count': error_count
    }
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump(checkpoint_data, f)
    print(f"✅ Checkpoint saved with {len(results)} processed comments")

def load_checkpoint(checkpoint_file):
    """Load progress from a checkpoint file."""
    try:
        print(f"Resuming from checkpoint: {checkpoint_file}")
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
            results = checkpoint_data.get('results', {})
            already_processed = set(checkpoint_data.get('processed_ids', []))
            error_count = checkpoint_data.get('error_count', 0)
            print(f"Loaded {len(results)} results from checkpoint")
            print(f"Skipping {len(already_processed)} already processed comment IDs")
            return results, already_processed, error_count
    except Exception as e:
        print(f"Error loading checkpoint, starting from beginning: {e}")
        return {}, set(), 0

def generate_summary(results, comments_data):
    """Generate summary statistics from analysis results."""
    successful_analyses = sum(1 for v in results.values() if "status" not in v.get("analysis", {}))
    
    # Initialize counters with zero values to handle empty cases
    stance_distribution = {
        Stance.FOR.value: 0,
        Stance.AGAINST.value: 0,
        Stance.NEUTRAL.value: 0
    }
    theme_occurrences = {
        Theme.MERIT.value: 0,
        Theme.DUE_PROCESS.value: 0,
        Theme.POLITICIZATION.value: 0,
        Theme.SCIENTIFIC.value: 0,
        Theme.INSTITUTIONAL.value: 0
    }
    
    # Count occurrences
    for result in results.values():
        analysis = result.get("analysis", {})
        if "status" not in analysis:  # Skip failed analyses
            stance = analysis.get("stance")
            if stance in stance_distribution:
                stance_distribution[stance] += 1
            
            themes = analysis.get("themes", [])
            for theme in themes:
                if theme in theme_occurrences:
                    theme_occurrences[theme] += 1
    
    summary = {
        "total_comments": len(comments_data),
        "successfully_analyzed": successful_analyses,
        "error_count": len(results) - successful_analyses,
        "completion_rate": round(successful_analyses / len(comments_data) * 100, 1) if len(comments_data) > 0 else 0,
        "stance_distribution": stance_distribution,
        "theme_occurrences": theme_occurrences
    }
    
    return summary

def build_comment_lookup(comments_data):
    """Build a lookup of original comment text and metadata."""
    original_comments = {}
    for comment_data in comments_data:
        if isinstance(comment_data, dict) and 'id' in comment_data:
            comment_id = comment_data['id']
            
            # Get the original comment text and metadata
            if 'attributes' in comment_data and isinstance(comment_data['attributes'], dict):
                attributes = comment_data['attributes']
                comment_text = strip_html_tags(attributes.get('comment', ''))
                agency_id = attributes.get('agencyId', '')
                
                # Look for attachment texts
                attachment_texts = attributes.get('attachment_texts', [])
                attachment_content = ""
                if attachment_texts:
                    attachment_content = "\n\n--- ATTACHMENTS ---\n\n"
                    for attachment in attachment_texts:
                        attachment_content += f"[ATTACHMENT: {attachment.get('title', 'Untitled')}]\n"
                        attachment_content += strip_html_tags(attachment.get('text', '[No text extracted]'))
                        attachment_content += "\n\n"
                
                # Create human-readable link from the comment ID
                link = f"https://www.regulations.gov/comment/{comment_id}"
                
                # Combine main comment and attachment text
                full_text = comment_text
                if attachment_content:
                    full_text += "\n\n" + attachment_content
                
                original_comments[comment_id] = {
                    'comment': full_text,  # Combined text from comment and attachments
                    'original_comment': comment_text,  # Just the main comment
                    'link': link,
                    'agencyId': agency_id,
                    'has_attachments': bool(attachment_texts)
                }
    
    return original_comments

def format_results_for_output(results, original_comments):
    """Format results into a flat structure for output."""
    flat_results = []
    
    for comment_id, result in results.items():
        if "status" not in result.get("analysis", {}):  # Skip failed analyses
            # Create a flat dictionary for each comment
            flat_item = {
                "id": comment_id,
                "title": result.get("title", ""),
                "category": result.get("category", ""),
                "agencyId": original_comments.get(comment_id, {}).get('agencyId', ''),
                "comment": original_comments.get(comment_id, {}).get('comment', ''),
                "original_comment": original_comments.get(comment_id, {}).get('original_comment', ''),
                "has_attachments": original_comments.get(comment_id, {}).get('has_attachments', False),
                "link": original_comments.get(comment_id, {}).get('link', ''),
                "stance": result.get("analysis", {}).get("stance", ""),
                "key_quote": result.get("analysis", {}).get("key_quote", ""),
                "rationale": result.get("analysis", {}).get("rationale", "")
            }
            
            # Convert themes to a comma-separated string
            themes = result.get("analysis", {}).get("themes", [])
            if themes:
                flat_item["themes"] = ", ".join(themes)
            else:
                flat_item["themes"] = ""
            
            flat_results.append(flat_item)
        else:
            # Include failed analyses with error info
            flat_item = {
                "id": comment_id,
                "title": result.get("title", ""),
                "category": result.get("category", ""),
                "agencyId": original_comments.get(comment_id, {}).get('agencyId', ''),
                "comment": original_comments.get(comment_id, {}).get('comment', ''),
                "original_comment": original_comments.get(comment_id, {}).get('original_comment', ''),
                "has_attachments": original_comments.get(comment_id, {}).get('has_attachments', False),
                "link": original_comments.get(comment_id, {}).get('link', ''),
                "error": result.get("analysis", {}).get("error", "Unknown error"),
                "stance": "",
                "key_quote": "",
                "rationale": "",
                "themes": ""
            }
                
            flat_results.append(flat_item)
    
    return flat_results

def print_summary(summary):
    """Print a human-readable summary of analysis results."""
    print(f"\n===== Summary =====")
    print(f"Total comments: {summary['total_comments']}")
    print(f"Successfully analyzed: {summary['successfully_analyzed']} ({summary['completion_rate']}%)")
    print(f"Errors: {summary['error_count']}")
    
    print("\nStance Distribution:")
    for stance, count in summary['stance_distribution'].items():
        percentage = round(count / summary['successfully_analyzed'] * 100, 1) if summary['successfully_analyzed'] > 0 else 0
        print(f"  {stance}: {count} ({percentage}%)")
    
    print("\nTheme Occurrences:")
    for theme, count in summary['theme_occurrences'].items():
        percentage = round(count / summary['successfully_analyzed'] * 100, 1) if summary['successfully_analyzed'] > 0 else 0
        print(f"  {theme}: {count} ({percentage}%)")


def analyze_comments(input_file, output_file=None, top_n=None, model="gpt-4o-mini", 
                  api_key=None, resume=False, batch_size=10, no_delay=True):
    """
    Analyze comments from JSON file and save structured results with parallel processing.
    
    Args:
        input_file: Path to the JSON file containing comments to analyze
        output_file: Path to save analyzed results (default: generates timestamped file)
        top_n: Optional limit on number of comments to process
        model: Model to use for analysis
        api_key: API key to use for LiteLLM calls (if not in environment)
        resume: Whether to resume from a previous checkpoint if available
        batch_size: Number of comments to process in parallel (default: 10)
        no_delay: If True, removes artificial delays between API calls (default: True)
    
    Returns:
        Path to the final results file
    """
    # Set API key in environment if provided
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    
    # Load the input JSON file
    print(f"Loading comments from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        comments_data = json.load(f)
    
    print(f"Found {len(comments_data)} comments in the file")
    
    # Limit the number of comments if specified
    if top_n and top_n < len(comments_data):
        print(f"Limiting analysis to first {top_n} comments as requested")
        comments_data = comments_data[:top_n]
    
    # Determine where to save the results
    if output_file is None:
        # Check if input file is in a results directory
        input_dir = os.path.dirname(input_file)
        if os.path.basename(input_dir).startswith("results_") and os.path.basename(input_file) == "raw_data.json":
            # If called by pipeline or standalone on raw_data.json, save to the same directory
            output_file = os.path.join(input_dir, "data.json")
        else:
            # Default behavior: create a timestamped file in analyzed_comments directory
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(project_root, 'results', 'processed')
            os.makedirs(output_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(output_dir, f"comment_analysis_{timestamp}.json")
    
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)
    
    # Setup checkpoint file
    checkpoint_file = os.path.join(output_dir, "analyze_checkpoint.json")
    
    # Create a temp directory for intermediate results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    temp_dir = os.path.join(output_dir, f"temp_{timestamp}")
    os.makedirs(temp_dir, exist_ok=True)
    print(f"Saving intermediate results to {temp_dir}")
    
    # Initialize analyzer
    analyzer = CommentAnalyzer(model=model)
    
    # Initialize or load from checkpoint
    if resume and os.path.exists(checkpoint_file):
        results, already_processed, error_count = load_checkpoint(checkpoint_file)
    else:
        results = {}
        already_processed = set()
        error_count = 0
    
    # Filter comments to process
    comments_to_process = [c for c in comments_data if c.get('id') not in already_processed]
    print(f"Processing {len(comments_to_process)} of {len(comments_data)} comments")
    
    # Process in batches with progress bar
    with tqdm(total=len(comments_to_process), desc="Analyzing comments") as pbar:
        for i in range(0, len(comments_to_process), batch_size):
            # Get current batch
            batch = comments_to_process[i:i+batch_size]
            
            # Process batch in parallel
            batch_results = process_comments_batch(batch, analyzer, temp_dir)
            
            # Update results dictionary and progress tracking
            for result in batch_results:
                if result:
                    results[result['id']] = result
                    already_processed.add(result['id'])
                    if "status" in result.get("analysis", {}) and result["analysis"]["status"] == "error":
                        error_count += 1
            
            pbar.update(len(batch))
            
            # Save checkpoint after each batch
            save_checkpoint(results, already_processed, error_count, checkpoint_file)
            
            # Optional delay between batches
            if not no_delay:
                time.sleep(0.5)
    
    # Build lookup of original comment text and metadata
    original_comments = build_comment_lookup(comments_data)
    
    # Generate summary statistics
    summary = generate_summary(results, comments_data)
    
    # Format results for output
    flat_results = format_results_for_output(results, original_comments)
    
    # Save the flat results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(flat_results, f, indent=2)
    
    # Create a separate summary file for reference
    summary_file = os.path.join(os.path.dirname(output_file), "summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nAnalysis complete! Results saved to: {output_file}")
    print(f"Summary stats saved to: {summary_file}")
    
    # Print summary to console
    print_summary(summary)
    
    # Clean up the checkpoint file when analysis is successfully completed
    try:
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            print(f"Checkpoint file removed: {checkpoint_file}")
    except Exception as e:
        print(f"Failed to remove checkpoint file: {e}")
    
    return output_file

def main():
    """Main function to parse arguments and run the script."""
    parser = argparse.ArgumentParser(description='Analyze comments on Schedule F proposal')
    parser.add_argument('--input', type=str, default=None, 
                        help='Path to input JSON file containing comments (default: auto-detect most recent raw_data.json)')
    parser.add_argument('--output', type=str, default=None,
                        help='Path to save analysis results (default: auto-generated based on timestamp)')
    parser.add_argument('--top_n', type=int, default=None, 
                        help='Analyze only the top N comments')
    parser.add_argument('--model', type=str, default='gpt-4o-mini', 
                        help='Model to use for analysis (default: gpt-4o-mini)')
    parser.add_argument('--api_key', type=str, 
                        help='API key to use for LiteLLM calls (if not in environment)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from checkpoint if available')
    parser.add_argument('--batch_size', type=int, default=10,
                        help='Number of comments to process in parallel (default: 10)')
    parser.add_argument('--no_delay', action='store_true', default=True,
                        help='Remove artificial delays between API calls (default: True)')
    args = parser.parse_args()
    
    # Auto-detect most recent raw_data.json if no input file specified
    input_file = args.input
    if input_file is None:
        # Find most recent results directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        results_base = os.path.join(project_root, "results")
        if os.path.exists(results_base):
            # Find the most recent results directory with raw_data.json
            result_dirs = glob.glob(os.path.join(results_base, "results_*"))
            if result_dirs:
                # Sort by creation time (newest first)
                result_dirs.sort(key=os.path.getctime, reverse=True)
                for result_dir in result_dirs:
                    raw_data_path = os.path.join(result_dir, "raw_data.json")
                    if os.path.exists(raw_data_path):
                        input_file = raw_data_path
                        print(f"Auto-detected most recent raw_data.json: {input_file}")
                        break
        
        # Fallback to checking for comments.csv in the root directory
        if input_file is None:
            csv_file = os.path.join(project_root, 'comments.csv')
            if os.path.exists(csv_file):
                print(f"No results directory found, but found comments.csv in root directory.")
                print(f"Please run the pipeline with --csv_file parameter or use run_pipeline_safe.sh")
                input_file = None
            else:
                # Last resort - check for comments.json
                input_file = os.path.join(project_root, 'comments.json')
                if not os.path.exists(input_file):
                    input_file = None
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        print("Make sure the file exists or specify the correct path with --input")
        return
    
    print(f"Starting analysis of '{input_file}' using model '{args.model}'")
    if args.top_n:
        print(f"Processing only the first {args.top_n} comments")
    if args.batch_size > 1:
        print(f"Using parallel processing with batch size of {args.batch_size}")
    
    analyze_comments(
        input_file=input_file,
        output_file=args.output,
        top_n=args.top_n,
        model=args.model,
        api_key=args.api_key,
        resume=args.resume,
        batch_size=args.batch_size,
        no_delay=args.no_delay
    )