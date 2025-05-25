#!/usr/bin/env python3
"""
Comment Analyzer for Schedule F Proposal - Fixed Version

This script analyzes public comments on the proposed Schedule F rule using LiteLLM.
It categorizes comments by stance (For/Against/Neutral), identifies key themes,
and extracts important quotes.

Key fixes:
- Added timeout handling for API calls
- Better error recovery and logging
- Fixed concurrent processing issues
- Added deadlock detection
"""

import os
import sys
import json
import glob
import argparse
import time
import html
import signal
import threading
from contextlib import contextmanager
from dotenv import load_dotenv
from litellm import completion
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Union, Set
from tqdm import tqdm
from enum import Enum
import concurrent.futures
import traceback
import logging

# Import from backend utils
from backend.utils.common import strip_html_tags, get_latest_results_dir, create_directory

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comment_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Suppress verbose logging from litellm
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

class TimeoutException(Exception):
    """Custom exception for timeout handling"""
    pass

@contextmanager
def timeout(seconds):
    """Context manager for timeout handling"""
    def timeout_handler(signum, frame):
        raise TimeoutException(f"Operation timed out after {seconds} seconds")
    
    # Set the signal handler and a timeout alarm
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        # Disable the alarm
        signal.alarm(0)

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
    def __init__(self, model="gpt-4o-mini", timeout_seconds=30):
        self.model = model
        self.timeout_seconds = timeout_seconds
        
        # Ensure API key is available
        if "OPENAI_API_KEY" not in os.environ:
            raise ValueError("OPENAI_API_KEY not found in environment variables or .env file")
    
    def get_system_prompt(self):
        return """You are analyzing public comments submitted regarding a proposed rule to implement "Schedule F" (or "Schedule Policy/Career").

This proposed rule would allow federal agencies to reclassify career civil servants in policy-influencing positions into a new employment category where they could be removed without the standard due process protections normally afforded to career federal employees.

1. Stance: Determine if the comment is "For" (supporting the rule), "Against" (opposing the rule), or "Neutral/Unclear" by examining both explicit statements and underlying intent.

Classification guidelines with special attention to boundary cases:

- "For": Comment explicitly supports the rule, defends its merits, or argues for implementation. Look for: praise of accountability, presidential authority, removing bureaucratic obstacles, or making it easier to remove poor performers.

- "Against": Comment opposes the rule, including indirect opposition through thematic alignment. Critical indicators include:
  * Questions about constitutionality or legal concerns, even without explicit opposition
  * Support for current merit-based systems or civil service protections
  * Concerns about politicization of civil service
  * Emphasis on nonpartisan governance, constitutional loyalty, or professional integrity (these themes inherently oppose politicization)
  * Anti-Trump or anti-administration sentiment
  * Comments about job performance standards that emphasize merit/fairness over political considerations

- "Neutral/Unclear": Reserve this classification ONLY for:
  * Comments purely requesting information without revealing stance
  * Comments discussing completely unrelated topics
  * Vague political statements that don't connect to civil service themes
  * Comments that are genuinely ambiguous after considering thematic context

IMPORTANT DISTINCTIONS:
- Comments supporting easier removal of poor performers are "For" if they align with the rule's efficiency goals
- Comments emphasizing constitutional duty, integrity, or nonpartisan service are "Against" (they oppose politicization)
- General political complaints without civil service context should remain "Neutral/Unclear"
- When in doubt between "Against" and "Neutral/Unclear", consider if the comment's themes would logically oppose politicizing civil service

2. Themes: Identify which of these themes are present (select all that apply):
   - Merit-based system concerns (mentions civil service protections, merit system, etc.)
   - Due process/employee rights (mentions worker protections, procedural rights, etc.)
   - Politicization concerns (mentions political interference, partisan influence, etc.)
   - Scientific integrity (mentions concerns about scientific research, grant-making, etc.)
   - Institutional knowledge loss (mentions expertise, continuity, experience, etc.)

3. Key Quote: Select the most important quote (max 100 words) that best captures the essence of the comment. The quote must be exactly present in the original text - do not paraphrase or modify.

4. Rationale: Briefly explain (1-2 sentences) why you classified the stance as you did.

Analyze objectively and avoid inserting personal opinions or biases."""

    def analyze_with_timeout(self, comment_text, comment_id=None):
        """Analyze a comment with timeout protection"""
        identifier = f" (ID: {comment_id})" if comment_id else ""
        
        # Create a thread-safe container for the result
        result_container = {'result': None, 'error': None}
        
        def api_call():
            try:
                response = completion(
                    temperature=0.0,
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.get_system_prompt()},
                        {"role": "user", "content": f"Analyze the following public comment{identifier}:\n\n{comment_text}"}
                    ],
                    response_format=CommentAnalysisResult,
                    timeout=self.timeout_seconds  # Add timeout to API call
                )
                
                # Process the response based on its format
                if hasattr(response.choices[0].message, 'content') and response.choices[0].message.content:
                    if isinstance(response.choices[0].message.content, str):
                        result_container['result'] = json.loads(response.choices[0].message.content)
                    else:
                        result_container['result'] = response.choices[0].message.content
                elif hasattr(response.choices[0].message, 'model_dump'):
                    result_container['result'] = response.choices[0].message.model_dump()
                else:
                    raise ValueError("Unexpected response format")
                    
            except Exception as e:
                result_container['error'] = e
        
        # Run API call in a thread
        thread = threading.Thread(target=api_call)
        thread.daemon = True
        thread.start()
        
        # Wait for thread to complete with timeout
        thread.join(timeout=self.timeout_seconds + 5)  # Give extra time for API timeout
        
        if thread.is_alive():
            # Thread is still running, it's stuck
            logger.error(f"API call timed out for comment{identifier}")
            raise TimeoutException(f"API call timed out after {self.timeout_seconds} seconds")
        
        if result_container['error']:
            raise result_container['error']
        
        return result_container['result']

    def analyze(self, comment_text, comment_id=None):
        """Analyze a comment using LiteLLM with Pydantic for response formatting"""
        try:
            return self.analyze_with_timeout(comment_text, comment_id)
        except Exception as e:
            logger.error(f"Error analyzing comment{f' {comment_id}' if comment_id else ''}: {str(e)}")
            raise

def extract_comment_text(comment_data, truncate_chars=None):
    """Extract text and metadata from a comment."""
    try:
        if isinstance(comment_data, dict) and 'id' in comment_data:
            comment_id = comment_data['id']
            
            # Debug logging
            logger.debug(f"Extracting text for comment {comment_id}")
            
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
            
            # Create truncated version if specified
            truncated_text = comment_text
            if truncate_chars and len(comment_text) > truncate_chars:
                truncated_text = comment_text[:truncate_chars]
                logger.debug(f"Comment {comment_id} truncated from {len(comment_text)} to {truncate_chars} chars")
            
            # Log if comment is empty
            if not comment_text.strip():
                logger.warning(f"Comment {comment_id} has empty text")
            
            return {
                'id': comment_id,
                'text': comment_text,  # Full original text
                'truncated_text': truncated_text,  # Text to use for analysis (may be truncated)
                'title': title,
                'category': category,
                'has_attachments': bool(attachment_texts)
            }
    except Exception as e:
        logger.error(f"Error extracting comment text: {str(e)}")
        logger.error(f"Comment data: {json.dumps(comment_data, indent=2)[:500]}...")  # Log first 500 chars
    return None

def process_single_comment(comment_data, analyzer, temp_dir, duplicate_map=None, processed_results=None, max_retries=3):
    """Process a single comment and return its analysis result."""
    # Add comprehensive diagnostics for comment processing (debug level)
    logger.debug(f"=== PROCESSING SINGLE COMMENT ===")
    logger.debug(f"Comment data type: {type(comment_data)}")
    logger.debug(f"Comment data keys: {list(comment_data.keys()) if isinstance(comment_data, dict) else 'N/A'}")
    
    # Extract comment data with enhanced error handling
    try:
        extracted = extract_comment_text(comment_data)
        if not extracted:
            logger.error(f"Failed to extract comment data - extracted is None")
            logger.error(f"Raw comment data: {json.dumps(comment_data, indent=2)[:500]}...")
            return None
        
        comment_id = extracted['id']
        logger.debug(f"Processing comment {comment_id}")
        full_text = extracted['text']  # Full original text
        analysis_text = extracted['truncated_text']  # Text to send to API (may be truncated)
        title = extracted['title']
        category = extracted['category']
        
        # Add safety checks
        logger.debug(f"Comment {comment_id} - full text length: {len(full_text)} chars")
        if analysis_text != full_text:
            logger.debug(f"Comment {comment_id} - analysis text length: {len(analysis_text)} chars (truncated)")
        logger.debug(f"Comment {comment_id} - title: {title[:100]}..." if len(title) > 100 else f"Comment {comment_id} - title: {title}")
        
        # Check for duplicates and get occurrence number (using analysis text for consistency)
        occurrence_number = 0
        normalized_text = analysis_text.strip().lower()
        
        duplicate_of = ""
        if duplicate_map and normalized_text in duplicate_map:
            # Find this comment's occurrence number and get all duplicate IDs
            for cid, onum in duplicate_map[normalized_text]['occurrences']:
                if cid == comment_id:
                    occurrence_number = onum
                    break
            
            # Get all duplicate comment IDs (excluding this one)
            all_duplicate_ids = [cid for cid, _ in duplicate_map[normalized_text]['occurrences']]
            if len(all_duplicate_ids) > 1:
                duplicate_of = ",".join(all_duplicate_ids)
            
            # If this is not the first occurrence, check if we can reuse results
            if occurrence_number > 1:
                first_id = duplicate_map[normalized_text]['first_id']
                logger.debug(f"Comment {comment_id} is duplicate #{occurrence_number} of {first_id}")
                
                # Check if first occurrence has been processed
                if processed_results and first_id in processed_results:
                    logger.debug(f"Reusing analysis from first occurrence {first_id}")
                    # Copy the result from the first occurrence
                    original_result = processed_results[first_id]
                    if "status" not in original_result.get("analysis", {}):  # Only reuse successful analyses
                        result = {
                            "id": comment_id,
                            "title": title,
                            "category": category,
                            "analysis": original_result.get("analysis", {}),
                            "occurrence_number": occurrence_number,
                            "duplicate_of": duplicate_of
                        }
                        
                        # Save individual result to temp directory
                        result_file = os.path.join(temp_dir, f"{comment_id}.json")
                        with open(result_file, 'w', encoding='utf-8') as f:
                            json.dump(result, f, indent=2)
                        
                        logger.debug(f"Successfully reused analysis for duplicate {comment_id}")
                        return result
                else:
                    logger.debug(f"First occurrence {first_id} not yet processed, will analyze normally")
            else:
                logger.debug(f"Comment {comment_id} is the first occurrence of this text")
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR in extract_comment_text: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.error(f"Comment data causing error: {json.dumps(comment_data, indent=2)[:1000]}...")
        return None
    
    # Skip if already processed (check in temp directory)
    result_file = os.path.join(temp_dir, f"{comment_id}.json")
    if os.path.exists(result_file):
        # Load existing result
        try:
            with open(result_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load existing result for {comment_id}: {e}")
    
    # Skip if comment text is too long (potential cause of hanging)
    # Note: This is for the analysis text, which may already be truncated
    MAX_COMMENT_LENGTH = 50000  # Adjust as needed
    if len(analysis_text) > MAX_COMMENT_LENGTH:
        logger.warning(f"Comment {comment_id} analysis text is too long ({len(analysis_text)} chars), truncating...")
        analysis_text = analysis_text[:MAX_COMMENT_LENGTH] + "\n\n[TRUNCATED DUE TO LENGTH]"
    
    # Additional safety checks
    if not analysis_text.strip():
        logger.warning(f"Comment {comment_id} has empty text after processing")
        error_result = {
            "id": comment_id,
            "title": title,
            "category": category,
            "analysis": {
                "status": "error",
                "error": "Empty comment text"
            },
            "occurrence_number": occurrence_number,
            "duplicate_of": duplicate_of
        }
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(error_result, f, indent=2)
        return error_result
    
    # Check for potentially problematic characters or encoding
    try:
        analysis_text.encode('utf-8')
    except UnicodeEncodeError as e:
        logger.warning(f"Comment {comment_id} has encoding issues: {e}")
        # Clean the text
        analysis_text = analysis_text.encode('utf-8', errors='ignore').decode('utf-8')
    
    # Analyze the comment
    retry_delay = 5  # seconds
    
    logger.debug(f"Starting analysis for comment {comment_id} with {len(analysis_text)} chars")
    
    for attempt in range(max_retries):
        try:
            analysis = analyzer.analyze(analysis_text, comment_id)
            
            # Add metadata
            result = {
                "id": comment_id,
                "title": title,
                "category": category,
                "analysis": analysis,
                "occurrence_number": occurrence_number,
                "duplicate_of": duplicate_of
            }
            
            # Save individual result to temp directory
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            
            logger.debug(f"Successfully analyzed {comment_id}")
            return result
                
        except TimeoutException as e:
            logger.error(f"Timeout analyzing {comment_id} (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to analyze {comment_id} after {max_retries} attempts due to timeout")
                # Add a placeholder result with error information
                error_result = {
                    "id": comment_id,
                    "title": title,
                    "category": category,
                    "analysis": {
                        "status": "error",
                        "error": "Timeout - comment may be too long or complex"
                    },
                    "occurrence_number": occurrence_number,
                    "duplicate_of": duplicate_of
                }
                # Still save the error result
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(error_result, f, indent=2)
                return error_result
                
        except Exception as e:
            logger.error(f"Error analyzing {comment_id} (attempt {attempt+1}/{max_retries}): {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to analyze {comment_id} after {max_retries} attempts: {e}")
                # Add a placeholder result with error information
                error_result = {
                    "id": comment_id,
                    "title": title,
                    "category": category,
                    "analysis": {
                        "status": "error",
                        "error": str(e)
                    },
                    "occurrence_number": occurrence_number,
                    "duplicate_of": duplicate_of
                }
                # Still save the error result
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(error_result, f, indent=2)
                return error_result

def process_comments_batch(comments_batch, analyzer, temp_dir, duplicate_map=None, processed_results=None, use_parallel=True):
    """Process a batch of comments with configurable parallel processing."""
    results = []
    
    if not use_parallel or len(comments_batch) == 1:
        # Process sequentially for small batches or when parallel is disabled
        logger.debug(f"Processing batch of {len(comments_batch)} comments sequentially")
        for comment in comments_batch:
            try:
                result = process_single_comment(comment, analyzer, temp_dir, duplicate_map, processed_results)
                if result:
                    results.append(result)
                    logger.debug(f"Successfully processed comment {result.get('id', 'unknown')}")
                else:
                    logger.warning(f"No result returned for comment")
            except Exception as e:
                comment_id = comment.get('id', 'unknown') if isinstance(comment, dict) else 'unknown'
                logger.error(f"Error processing comment {comment_id}: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Create error result
                error_result = {
                    "id": comment_id,
                    "title": comment.get('title', '') if isinstance(comment, dict) else '',
                    "category": comment.get('category', '') if isinstance(comment, dict) else '',
                    "analysis": {
                        "status": "error",
                        "error": str(e)
                    }
                }
                results.append(error_result)
    else:
        # Process in parallel using ThreadPoolExecutor
        logger.debug(f"Processing batch of {len(comments_batch)} comments in parallel")
        
        def safe_process_comment(comment):
            """Wrapper for safe parallel processing."""
            try:
                return process_single_comment(comment, analyzer, temp_dir, duplicate_map, processed_results)
            except Exception as e:
                comment_id = comment.get('id', 'unknown') if isinstance(comment, dict) else 'unknown'
                logger.error(f"Error in parallel processing for comment {comment_id}: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                return {
                    "id": comment_id,
                    "title": comment.get('title', '') if isinstance(comment, dict) else '',
                    "category": comment.get('category', '') if isinstance(comment, dict) else '',
                    "analysis": {
                        "status": "error",
                        "error": str(e)
                    }
                }
        
        # Use ThreadPoolExecutor for parallel processing
        max_workers = min(len(comments_batch), 5)  # Limit to 5 concurrent workers
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_comment = {
                    executor.submit(safe_process_comment, comment): comment 
                    for comment in comments_batch
                }
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_comment, timeout=300):  # 5 min timeout
                    try:
                        result = future.result(timeout=60)  # 1 min timeout per task
                        if result:
                            results.append(result)
                            logger.debug(f"Successfully processed comment {result.get('id', 'unknown')} in parallel")
                    except concurrent.futures.TimeoutError:
                        comment = future_to_comment[future]
                        comment_id = comment.get('id', 'unknown') if isinstance(comment, dict) else 'unknown'
                        logger.error(f"Timeout processing comment {comment_id} in parallel")
                        
                        error_result = {
                            "id": comment_id,
                            "title": comment.get('title', '') if isinstance(comment, dict) else '',
                            "category": comment.get('category', '') if isinstance(comment, dict) else '',
                            "analysis": {
                                "status": "error",
                                "error": "Processing timeout"
                            }
                        }
                        results.append(error_result)
                    except Exception as e:
                        comment = future_to_comment[future]
                        comment_id = comment.get('id', 'unknown') if isinstance(comment, dict) else 'unknown'
                        logger.error(f"Error getting result for comment {comment_id}: {e}")
                        
                        error_result = {
                            "id": comment_id,
                            "title": comment.get('title', '') if isinstance(comment, dict) else '',
                            "category": comment.get('category', '') if isinstance(comment, dict) else '',
                            "analysis": {
                                "status": "error",
                                "error": str(e)
                            }
                        }
                        results.append(error_result)
                        
        except Exception as e:
            logger.error(f"Error in parallel batch processing: {e}")
            logger.warning("Falling back to sequential processing")
            # Fallback to sequential processing
            return process_comments_batch(comments_batch, analyzer, temp_dir, use_parallel=False)
    
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
    logger.debug(f"✅ Checkpoint saved with {len(results)} processed comments")

def load_checkpoint(checkpoint_file):
    """Load progress from a checkpoint file."""
    try:
        logger.info(f"Resuming from checkpoint: {checkpoint_file}")
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
            results = checkpoint_data.get('results', {})
            already_processed = set(checkpoint_data.get('processed_ids', []))
            error_count = checkpoint_data.get('error_count', 0)
            logger.info(f"Loaded {len(results)} results from checkpoint")
            logger.info(f"Skipping {len(already_processed)} already processed comment IDs")
            return results, already_processed, error_count
    except Exception as e:
        logger.error(f"Error loading checkpoint, starting from beginning: {e}")
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
        try:
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
                        'category': attributes.get('category', ''),
                        'has_attachments': bool(attachment_texts),
                        'postedDate': attributes.get('postedDate', ''),
                        'receivedDate': attributes.get('receivedDate', '')
                    }
        except Exception as e:
            logger.error(f"Error building lookup for comment: {e}")
    
    return original_comments

def format_results_for_output(results, original_comments):
    """Format results into a flat structure for output."""
    flat_results = []
    
    for comment_id, result in results.items():
        try:
            if "status" not in result.get("analysis", {}):  # Skip failed analyses
                # Create a flat dictionary for each comment
                flat_item = {
                    "id": comment_id,
                    "title": result.get("title", ""),
                    "category": original_comments.get(comment_id, {}).get('category', ''),
                    "agency_id": original_comments.get(comment_id, {}).get('agencyId', ''),
                    "comment": original_comments.get(comment_id, {}).get('comment', ''),
                    "original_comment": original_comments.get(comment_id, {}).get('original_comment', ''),
                    "has_attachments": original_comments.get(comment_id, {}).get('has_attachments', False),
                    "link": original_comments.get(comment_id, {}).get('link', ''),
                    "stance": result.get("analysis", {}).get("stance", ""),
                    "key_quote": result.get("analysis", {}).get("key_quote", ""),
                    "rationale": result.get("analysis", {}).get("rationale", ""),
                    "posted_date": original_comments.get(comment_id, {}).get('postedDate', ''),
                    "received_date": original_comments.get(comment_id, {}).get('receivedDate', ''),
                    "occurrence_number": result.get("occurrence_number", 0),
                    "duplicate_of": result.get("duplicate_of", "")
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
                    "category": original_comments.get(comment_id, {}).get('category', ''),
                    "agency_id": original_comments.get(comment_id, {}).get('agencyId', ''),
                    "comment": original_comments.get(comment_id, {}).get('comment', ''),
                    "original_comment": original_comments.get(comment_id, {}).get('original_comment', ''),
                    "has_attachments": original_comments.get(comment_id, {}).get('has_attachments', False),
                    "link": original_comments.get(comment_id, {}).get('link', ''),
                    "error": result.get("analysis", {}).get("error", "Unknown error"),
                    "stance": "",
                    "key_quote": "",
                    "rationale": "",
                    "themes": "",
                    "posted_date": original_comments.get(comment_id, {}).get('postedDate', ''),
                    "received_date": original_comments.get(comment_id, {}).get('receivedDate', ''),
                    "occurrence_number": result.get("occurrence_number", 0),
                    "duplicate_of": result.get("duplicate_of", "")
                }
                    
                flat_results.append(flat_item)
        except Exception as e:
            logger.error(f"Error formatting result for comment {comment_id}: {e}")
    
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

def create_duplicate_mapping(comments_data, truncate_chars=None):
    """
    Create a mapping of comment text to track duplicates and occurrence numbers.
    
    Args:
        comments_data: List of comment data objects
        truncate_chars: If specified, use truncated text for duplicate detection
    
    Returns:
        duplicate_map: dict mapping normalized comment text to {
            'first_id': comment_id of first occurrence,
            'occurrences': list of (comment_id, occurrence_number) tuples
        }
    """
    duplicate_map = {}
    
    logger.info(f"Creating duplicate mapping{' with truncation to ' + str(truncate_chars) + ' chars' if truncate_chars else ''}...")
    
    for comment_data in comments_data:
        try:
            extracted = extract_comment_text(comment_data, truncate_chars)
            if not extracted:
                continue
                
            comment_id = extracted['id']
            # Use truncated text for duplicate detection
            comment_text = extracted['truncated_text'] if truncate_chars else extracted['text']
            
            # Normalize text for comparison (strip whitespace, convert to lowercase)
            normalized_text = comment_text.strip().lower()
            
            # Skip empty comments
            if not normalized_text:
                continue
                
            if normalized_text not in duplicate_map:
                # First occurrence of this text
                duplicate_map[normalized_text] = {
                    'first_id': comment_id,
                    'occurrences': [(comment_id, 1)]
                }
            else:
                # Duplicate occurrence
                occurrence_number = len(duplicate_map[normalized_text]['occurrences']) + 1
                duplicate_map[normalized_text]['occurrences'].append((comment_id, occurrence_number))
                
        except Exception as e:
            logger.error(f"Error processing comment for duplicate mapping: {e}")
            continue
    
    # Log statistics
    total_unique_texts = len(duplicate_map)
    total_comments = sum(len(entry['occurrences']) for entry in duplicate_map.values())
    duplicate_texts = sum(1 for entry in duplicate_map.values() if len(entry['occurrences']) > 1)
    duplicate_comments = sum(len(entry['occurrences']) - 1 for entry in duplicate_map.values())
    
    logger.info(f"Duplicate mapping complete:")
    logger.info(f"  Unique comment texts: {total_unique_texts}")
    logger.info(f"  Total comments: {total_comments}")
    logger.info(f"  Texts with duplicates: {duplicate_texts}")
    logger.info(f"  Duplicate comment instances: {duplicate_comments}")
    
    return duplicate_map

def analyze_comments(input_file, output_file=None, top_n=None, model="gpt-4o-mini", 
                  api_key=None, resume=False, batch_size=5, no_delay=True, 
                  timeout_seconds=30, start_from=None, end_at=None, chunk_size=None,
                  use_parallel=True, truncate_chars=None):
    """
    Analyze comments from JSON file and save structured results with parallel processing.
    
    Args:
        input_file: Path to the JSON file containing comments to analyze
        output_file: Path to save analyzed results (default: generates timestamped file)
        top_n: Optional limit on number of comments to process
        model: Model to use for analysis
        api_key: API key to use for LiteLLM calls (if not in environment)
        resume: Whether to resume from a previous checkpoint if available
        batch_size: Number of comments to process in parallel (default: 5, reduced from 10)
        no_delay: If True, removes artificial delays between API calls (default: True)
        timeout_seconds: Timeout for each API call in seconds (default: 30)
        start_from: Optional index to start processing from
        end_at: Optional index to end processing at (for chunks)
        chunk_size: If specified, process only this many comments starting from start_from
        use_parallel: Whether to use parallel processing for batches (default: True)
        truncate_chars: If specified, truncate comment text to this many characters for analysis
    
    Returns:
        Path to the final results file
    """
    # Set API key in environment if provided
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    
    # Load the input JSON file
    logger.info(f"Loading comments from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        comments_data = json.load(f)
    
    logger.info(f"Found {len(comments_data)} comments in the file")
    
    # Add comprehensive diagnostics before slicing
    logger.info(f"=== DIAGNOSTIC INFO ===")
    logger.info(f"Original data length: {len(comments_data)}")
    logger.info(f"start_from: {start_from}")
    logger.info(f"end_at: {end_at}")
    logger.info(f"chunk_size: {chunk_size}")
    logger.info(f"top_n: {top_n}")
    
    # Validate first few comments structure
    for i in range(min(3, len(comments_data))):
        comment = comments_data[i]
        logger.info(f"Comment {i} structure:")
        logger.info(f"  Type: {type(comment)}")
        logger.info(f"  Keys: {list(comment.keys()) if isinstance(comment, dict) else 'N/A'}")
        logger.info(f"  ID: {comment.get('id', 'NO_ID') if isinstance(comment, dict) else 'NO_ID'}")
        
        # Log structure for early comments to help with debugging
        if i < 10:
            logger.info(f"Comment {i} structure sample: {json.dumps(comment, indent=2)[:500]}...")
    
    # Apply chunking logic with extensive logging
    original_length = len(comments_data)
    
    if chunk_size is not None:
        # Chunk mode: process exactly chunk_size comments starting from start_from
        start_idx = start_from if start_from is not None else 0
        end_idx = start_idx + chunk_size
        logger.info(f"CHUNK MODE: Processing comments {start_idx} to {end_idx-1} (chunk_size={chunk_size})")
        comments_data = comments_data[start_idx:end_idx]
        
    elif start_from is not None or end_at is not None:
        # Range mode: process from start_from to end_at
        start_idx = start_from if start_from is not None else 0
        end_idx = end_at if end_at is not None else len(comments_data)
        logger.info(f"RANGE MODE: Processing comments {start_idx} to {end_idx-1}")
        comments_data = comments_data[start_idx:end_idx]
        
    elif top_n and top_n < len(comments_data):
        # Top N mode: process first top_n comments
        logger.info(f"TOP_N MODE: Processing first {top_n} comments")
        comments_data = comments_data[:top_n]
    
    logger.info(f"After slicing: {len(comments_data)} comments to process")
    logger.info(f"=== END DIAGNOSTIC INFO ===")
    
    # Validate post-slice data
    if len(comments_data) == 0:
        logger.error("No comments to process after applying filters!")
        return None
        
    # Validate the first few comments in the sliced data
    for i in range(min(len(comments_data), 5)):
        comment = comments_data[i]
        original_idx = (start_from or 0) + i
        logger.info(f"Validating sliced comment {i} (original idx {original_idx})")
        logger.info(f"Comment ID: {comment.get('id', 'NO_ID')}")
        logger.info(f"Comment type: {type(comment)}")
        if isinstance(comment, dict):
            logger.info(f"Comment keys: {list(comment.keys())[:5]}...")  # First 5 keys
            # Log comment text length if available
            extracted = extract_comment_text(comment, truncate_chars)
            if extracted:
                text_len = len(extracted.get('text', ''))
                analysis_len = len(extracted.get('truncated_text', ''))
                logger.info(f"Comment text length: {text_len} chars")
                if truncate_chars and analysis_len < text_len:
                    logger.info(f"Analysis text length: {analysis_len} chars (truncated)")
                if text_len > 40000:
                    logger.warning(f"Very long comment detected (may cause processing delays)")
            else:
                logger.warning(f"Failed to extract comment text - potential data issue")
    
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
    logger.info(f"Saving intermediate results to {temp_dir}")
    
    # Initialize analyzer with timeout
    analyzer = CommentAnalyzer(model=model, timeout_seconds=timeout_seconds)
    
    # Initialize or load from checkpoint
    if resume and os.path.exists(checkpoint_file):
        results, already_processed, error_count = load_checkpoint(checkpoint_file)
    else:
        results = {}
        already_processed = set()
        error_count = 0
    
    # Create duplicate mapping for all comments (not just the slice being processed)
    # This ensures we can detect duplicates even if the original is outside the current slice
    duplicate_map = create_duplicate_mapping(comments_data, truncate_chars)
    
    # Filter comments to process
    comments_to_process = [c for c in comments_data if c.get('id') not in already_processed]
    logger.info(f"Processing {len(comments_to_process)} of {len(comments_data)} comments")
    
    # Process in batches with progress bar  
    sys.stdout.flush()  # Ensure any previous output is flushed
    with tqdm(total=len(comments_to_process), desc="Analyzing comments", 
              file=sys.stdout, disable=False, dynamic_ncols=True, 
              miniters=1, mininterval=0.1) as pbar:
        for i in range(0, len(comments_to_process), batch_size):
            # Get current batch
            batch = comments_to_process[i:i+batch_size]
            
            # Log batch info
            batch_ids = [c.get('id', 'unknown') for c in batch]
            logger.debug(f"Processing batch {i//batch_size + 1}: {batch_ids}")
            
            # Add diagnostics before processing
            logger.debug(f"Batch size: {len(batch)}")
            for idx, comment in enumerate(batch):
                comment_id = comment.get('id', 'unknown')
                logger.debug(f"Batch item {idx}: {comment_id}, type: {type(comment)}")
                if isinstance(comment, dict):
                    logger.debug(f"  Keys: {list(comment.keys())[:10]}")  # First 10 keys
            
            # Process batch
            try:
                logger.debug(f"Starting batch processing (parallel={use_parallel})...")
                batch_results = process_comments_batch(batch, analyzer, temp_dir, duplicate_map, results, use_parallel)
                logger.debug(f"Batch processing completed with {len(batch_results)} results")
                
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
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error processing batch: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Try to process comments using sequential batch processing
                logger.info("Attempting to process batch comments sequentially...")
                try:
                    sequential_results = process_comments_batch(batch, analyzer, temp_dir, duplicate_map, results, use_parallel=False)
                    for result in sequential_results:
                        if result:
                            results[result['id']] = result
                            already_processed.add(result['id'])
                            if "status" in result.get("analysis", {}) and result["analysis"]["status"] == "error":
                                error_count += 1
                except Exception as sequential_error:
                    logger.error(f"Sequential batch processing also failed: {sequential_error}")
                    # Final fallback: process individually
                    logger.info("Final fallback: processing comments individually...")
                    for comment in batch:
                        try:
                            result = process_single_comment(comment, analyzer, temp_dir, duplicate_map, processed_results)
                            if result:
                                results[result['id']] = result
                                already_processed.add(result['id'])
                                if "status" in result.get("analysis", {}) and result["analysis"]["status"] == "error":
                                    error_count += 1
                        except Exception as individual_error:
                            comment_id = comment.get('id', 'unknown')
                            logger.error(f"Failed to process comment {comment_id} individually: {individual_error}")
                
                pbar.update(len(batch))
                save_checkpoint(results, already_processed, error_count, checkpoint_file)
    
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
    
    logger.info(f"\nAnalysis complete! Results saved to: {output_file}")
    logger.info(f"Summary stats saved to: {summary_file}")
    
    # Print summary to console
    print_summary(summary)
    
    # Clean up the checkpoint file when analysis is successfully completed
    try:
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            logger.info(f"Checkpoint file removed: {checkpoint_file}")
    except Exception as e:
        logger.error(f"Failed to remove checkpoint file: {e}")
    
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
    parser.add_argument('--batch_size', type=int, default=5,
                        help='Number of comments to process in parallel (default: 5)')
    parser.add_argument('--no_delay', action='store_true', default=True,
                        help='Remove artificial delays between API calls (default: True)')
    parser.add_argument('--timeout', type=int, default=30,
                        help='Timeout for each API call in seconds (default: 30)')
    parser.add_argument('--start_from', type=int, default=None,
                        help='Start processing from this comment index (useful for debugging)')
    parser.add_argument('--end_at', type=int, default=None,
                        help='End processing at this comment index (useful for debugging)')
    parser.add_argument('--chunk_size', type=int, default=None,
                        help='Process exactly this many comments starting from start_from')
    parser.add_argument('--start_from_id', type=str, default=None,
                        help='Start processing from this comment ID (e.g., OPM-2025-0004-0183)')
    parser.add_argument('--no_parallel', action='store_true',
                        help='Disable parallel processing (process all comments sequentially)')
    parser.add_argument('--truncate', type=int, default=None,
                        help='Truncate comment text to this many characters for analysis (saves API costs)')
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
                        logger.info(f"Auto-detected most recent raw_data.json: {input_file}")
                        break
        
        # Fallback to checking for comments.csv in the root directory
        if input_file is None:
            csv_file = os.path.join(project_root, 'comments.csv')
            if os.path.exists(csv_file):
                logger.error(f"No results directory found, but found comments.csv in root directory.")
                logger.error(f"Please run the pipeline with --csv_file parameter or use run_pipeline_safe.sh")
                return
            else:
                # Last resort - check for comments.json
                input_file = os.path.join(project_root, 'comments.json')
                if not os.path.exists(input_file):
                    logger.error("No input file found. Please specify with --input")
                    return
    
    # Check if input file exists
    if not os.path.exists(input_file):
        logger.error(f"Error: Input file '{input_file}' not found.")
        logger.error("Make sure the file exists or specify the correct path with --input")
        return
    
    logger.info(f"Starting analysis of '{input_file}' using model '{args.model}'")
    if args.top_n:
        logger.info(f"Processing only the first {args.top_n} comments")
    if args.truncate:
        logger.info(f"Truncating comments to {args.truncate} characters for analysis")
    if args.chunk_size:
        logger.info(f"Processing chunk of {args.chunk_size} comments starting from index {args.start_from or 0}")
    elif args.start_from_id:
        logger.info(f"Starting from comment ID: {args.start_from_id}")
    elif args.start_from or args.end_at:
        start_msg = f"from index {args.start_from}" if args.start_from else "from beginning"
        end_msg = f"to index {args.end_at}" if args.end_at else "to end"
        logger.info(f"Processing range {start_msg} {end_msg}")
    if args.batch_size > 1:
        logger.info(f"Using parallel processing with batch size of {args.batch_size}")
    
    analyze_comments(
        input_file=input_file,
        output_file=args.output,
        top_n=args.top_n,
        model=args.model,
        api_key=args.api_key,
        resume=args.resume,
        batch_size=args.batch_size,
        no_delay=args.no_delay,
        timeout_seconds=args.timeout,
        start_from=args.start_from,
        end_at=args.end_at,
        chunk_size=args.chunk_size,
        use_parallel=not args.no_parallel,
        truncate_chars=args.truncate
    )

if __name__ == "__main__":
    main()