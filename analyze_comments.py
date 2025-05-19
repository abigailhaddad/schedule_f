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
3. Run: python analyze_comments.py

For more options:
python analyze_comments.py --help
"""

import os
import json
import glob
import argparse
from dotenv import load_dotenv
from litellm import completion
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Union, Set
from tqdm import tqdm
import time
from enum import Enum

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

For each comment, provide:

1. Stance: Determine if the comment is "{Stance.FOR.value}" (supporting the rule), "{Stance.AGAINST.value}" (opposing the rule), or "{Stance.NEUTRAL.value}".

2. Themes: Identify which of these themes are present (select all that apply):
   - {Theme.MERIT.value} (mentions civil service protections, merit system, etc.)
   - {Theme.DUE_PROCESS.value} (mentions worker protections, procedural rights, etc.)
   - {Theme.POLITICIZATION.value} (mentions political interference, partisan influence, etc.)
   - {Theme.SCIENTIFIC.value} (mentions concerns about scientific research, grant-making, etc.)
   - {Theme.INSTITUTIONAL.value} (mentions expertise, continuity, experience, etc.)

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
            response = completion(
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

def analyze_comments(input_file, output_file=None, top_n=None, model="gpt-4o-mini", api_key=None):
    """
    Analyze comments from JSON file and save structured results with robust error handling.
    
    Args:
        input_file: Path to the JSON file containing comments to analyze
        output_file: Path to save analyzed results (default: generates timestamped file)
        top_n: Optional limit on number of comments to process
        model: Model to use for analysis
        api_key: API key to use for LiteLLM calls (if not in environment)
    
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
        # Check if input file is in a results directory (from pipeline)
        input_dir = os.path.dirname(input_file)
        if os.path.basename(input_dir).startswith("results_") and os.path.basename(input_file) == "raw_data.json":
            # If called by pipeline or standalone on raw_data.json, save to the same directory
            output_file = os.path.join(input_dir, "data.json")
        else:
            # Default behavior: create a timestamped file in analyzed_comments directory
            output_dir = os.path.join(os.getcwd(), 'analyzed_comments')
            os.makedirs(output_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(output_dir, f"comment_analysis_{timestamp}.json")
    
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a temp directory for intermediate results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    temp_dir = os.path.join(output_dir, f"temp_{timestamp}")
    os.makedirs(temp_dir, exist_ok=True)
    print(f"Saving intermediate results to {temp_dir}")
    
    # Initialize analyzer
    analyzer = CommentAnalyzer(model=model)
    
    # Process comments
    results = {}
    error_count = 0
    with tqdm(total=len(comments_data), desc="Analyzing comments") as pbar:
        for comment_data in comments_data:
            # Handle possible different formats in raw_data.json
            if isinstance(comment_data, dict) and 'id' in comment_data:
                comment_id = comment_data['id']
                
                # Check if comment text is directly accessible or in an attributes property
                if 'attributes' in comment_data and isinstance(comment_data['attributes'], dict):
                    comment_text = comment_data['attributes'].get('comment', '')
                    title = comment_data['attributes'].get('title', '')
                    category = comment_data['attributes'].get('category', '')
                else:
                    comment_text = comment_data.get('comment', '')
                    title = comment_data.get('title', '')
                    category = comment_data.get('category', '')
            else:
                # Skip invalid comment data
                pbar.update(1)
                continue
            
            # Skip if already processed (check in temp directory)
            result_file = os.path.join(temp_dir, f"{comment_id}.json")
            if os.path.exists(result_file):
                # Load existing result
                with open(result_file, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                results[comment_id] = result
                pbar.update(1)
                continue
            
            # Analyze the comment
            max_retries = 3
            retry_delay = 10  # seconds
            
            for attempt in range(max_retries):
                try:
                    analysis = analyzer.analyze(comment_text, comment_id)
                    
                    # Add metadata (use the title and category we extracted above)
                    result = {
                        "id": comment_id,
                        "title": title,
                        "category": category,
                        "analysis": analysis
                    }
                    
                    # Save individual result to temp directory
                    with open(result_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2)
                    
                    # Add to results
                    results[comment_id] = result
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"Error analyzing {comment_id} (attempt {attempt+1}/{max_retries}): {e}")
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        print(f"Failed to analyze {comment_id} after {max_retries} attempts: {e}")
                        error_count += 1
                        # Add a placeholder result with error information
                        results[comment_id] = {
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
                            json.dump(results[comment_id], f, indent=2)
            
            pbar.update(1)
            
            # Optional: Add a small delay between API calls to avoid rate limits
            time.sleep(0.5)
    
    # Generate a summary of the results
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
        "error_count": error_count,
        "completion_rate": round(successful_analyses / len(comments_data) * 100, 1) if len(comments_data) > 0 else 0,
        "stance_distribution": stance_distribution,
        "theme_occurrences": theme_occurrences
    }
    
    # Build a lookup dictionary for original comment text and links
    original_comments = {}
    for comment_data in comments_data:
        if isinstance(comment_data, dict) and 'id' in comment_data:
            comment_id = comment_data['id']
            
            # Get the original comment text
            if 'attributes' in comment_data and isinstance(comment_data['attributes'], dict):
                comment_text = comment_data['attributes'].get('comment', '')
                
                # Get the link to the comment if available
                link = ""
                if 'links' in comment_data and isinstance(comment_data['links'], dict):
                    link = comment_data['links'].get('self', '')
                
                original_comments[comment_id] = {
                    'comment': comment_text,
                    'link': link
                }
    
    # Convert to flat format - a list of dictionaries
    flat_results = []
    
    for comment_id, result in results.items():
        if "status" not in result.get("analysis", {}):  # Skip failed analyses
            # Create a flat dictionary for each comment
            flat_item = {
                "id": comment_id,
                "title": result.get("title", ""),
                "category": result.get("category", ""),
                "comment": original_comments.get(comment_id, {}).get('comment', ''),
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
                "comment": original_comments.get(comment_id, {}).get('comment', ''),
                "link": original_comments.get(comment_id, {}).get('link', ''),
                "error": result.get("analysis", {}).get("error", "Unknown error"),
                "stance": "",
                "key_quote": "",
                "rationale": "",
                "themes": ""
            }
                
            flat_results.append(flat_item)
    
    # Generate output filename if not provided
    if not output_file:
        output_file = os.path.join(output_dir, f"comment_analysis_{timestamp}.json")
    
    # Save the flat results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(flat_results, f, indent=2)
    
    # Create a separate summary file for reference
    summary_file = os.path.join(os.path.dirname(output_file), "summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nAnalysis complete! Results saved to: {output_file}")
    print(f"Summary stats saved to: {summary_file}")
    print("\n===== Summary =====")
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
    
    print("\nTop quotes by stance:")
    for stance in [Stance.FOR.value, Stance.AGAINST.value, Stance.NEUTRAL.value]:
        stance_comments = [r for r in results.values() 
                         if "status" not in r.get("analysis", {}) 
                         and r.get("analysis", {}).get("stance") == stance]
        if stance_comments:
            print(f"\n{stance} (sample quote):")
            # Get a representative quote
            sample = stance_comments[min(2, len(stance_comments)-1)]  # Skip the first entry to get more variety
            print(f"  \"{sample['analysis']['key_quote']}\"")
    
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
    args = parser.parse_args()
    
    # Auto-detect most recent raw_data.json if no input file specified
    input_file = args.input
    if input_file is None:
        # Look for results directories
        results_base = os.path.join(os.getcwd(), "results")
        if os.path.exists(results_base):
            # Find all results directories
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
        
        # Fallback to comments.json if no results directory found
        if input_file is None:
            input_file = 'comments.json'
            print(f"No results directory found, using default: {input_file}")
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        print("Make sure the file exists or specify the correct path with --input")
        return
    
    print(f"Starting analysis of '{input_file}' using model '{args.model}'")
    if args.top_n:
        print(f"Processing only the first {args.top_n} comments")
    
    analyze_comments(
        input_file=input_file,
        output_file=args.output,
        top_n=args.top_n,
        model=args.model,
        api_key=args.api_key
    )

if __name__ == "__main__":
    try:
        # Check for API key
        if "OPENAI_API_KEY" not in os.environ:
            # Try loading from .env file first
            if os.path.exists('.env'):
                load_dotenv()
            
            # If still not available, prompt user
            if "OPENAI_API_KEY" not in os.environ:
                print("Warning: OPENAI_API_KEY not found in environment variables or .env file.")
                print("You will be prompted to enter it as a parameter or create a .env file.")
        
        main()
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user. Partial results may have been saved.")
    except Exception as e:
        print(f"\nError during analysis: {str(e)}")
        import traceback
        traceback.print_exc()