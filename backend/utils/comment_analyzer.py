#!/usr/bin/env python3
"""
Comment Analyzer Utility

Shared CommentAnalyzer class for analyzing comments using LiteLLM.
Used by both the old and new analysis workflows.
"""

import os
import json
import threading
import logging
from enum import Enum
from dotenv import load_dotenv
from litellm import completion
from pydantic import BaseModel, Field
from typing import List, Optional

# Load environment variables
load_dotenv()

# Import config constants
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.config import DEFAULT_MODEL, DEFAULT_TIMEOUT

# Setup logging
logger = logging.getLogger(__name__)

class TimeoutException(Exception):
    """Custom exception for timeout handling"""
    pass

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
    def __init__(self, model=None, timeout_seconds=None):
        self.model = model or DEFAULT_MODEL
        self.timeout_seconds = timeout_seconds or DEFAULT_TIMEOUT
        
        # Ensure API key is available
        if "OPENAI_API_KEY" not in os.environ:
            raise ValueError("OPENAI_API_KEY not found in environment variables or .env file")
    
    def get_system_prompt(self):
        return """You are analyzing public comments submitted regarding a proposed rule to implement "Schedule F" (or "Schedule Policy/Career").

This proposed rule would allow federal agencies to reclassify career civil servants in policy-influencing positions into a new employment category where they could be removed without the standard due process protections normally afforded to career federal employees.

1. Stance: Determine if the comment is "For" (supporting the rule), "Against" (opposing the rule), or "Neutral/Unclear" by examining both explicit statements and underlying intent.

Classification guidelines with special attention to boundary cases:

- "For": Comment supports the rule, defends its merits, or argues for implementation. Look for: praise of accountability, presidential authority, removing bureaucratic obstacles, or making it easier to remove poor performers. Comments which oppose the deep state or support the president are almost certainty also in support of the regulation, even if they don't explicitly say so. 

- "Against": Comment opposes the rule, including indirect opposition through thematic alignment. Critical indicators include:
  * Questions about constitutionality or legal concerns, even without explicit opposition
  * Support for current merit-based systems or civil service protections
  * Concerns about politicization of civil service
  * Emphasis on nonpartisan governance, constitutional loyalty, or professional integrity (these themes inherently oppose politicization)
  * Anti-Trump or anti-administration sentiment, EVEN if not combined with any explicit comments about the regulation
  * Comments about job performance standards that emphasize merit/fairness over political considerations
  Again, if this is talking about how the president or government is doing bad things, it's almost certainly in opposition, unless it's talking about the civil service or deep state doing bad things. Like, if the comment is about how Trump is acting like a king, or it just says NO or fuck doge or something like that, it's against. 

- "Neutral/Unclear": Reserve this classification ONLY for:
  * Comments purely requesting information without revealing stance
  * Comments discussing completely unrelated topics which don't involve support or opposition to the president
  * Comments that are genuinely ambiguous after considering thematic context

IMPORTANT DISTINCTIONS:
- Comments supporting easier removal of poor performers are "For" if they align with the rule's efficiency goals
- Comments emphasizing constitutional duty, integrity, or nonpartisan service are "Against" (they oppose politicization)
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
            raise TimeoutException(f"Analysis timed out after {self.timeout_seconds + 5} seconds")
        
        # Check if there was an error
        if result_container['error']:
            raise result_container['error']
        
        return result_container['result']
    
    def analyze(self, comment_text, comment_id=None, max_retries=3):
        """
        Analyze a comment with retries for robustness.
        
        Args:
            comment_text: The text to analyze
            comment_id: Optional comment ID for logging
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary with analysis results
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = self.analyze_with_timeout(comment_text, comment_id)
                
                # Validate the result has required fields
                if not isinstance(result, dict):
                    raise ValueError("Result is not a dictionary")
                
                required_fields = ['stance', 'themes', 'key_quote', 'rationale']
                for field in required_fields:
                    if field not in result:
                        raise ValueError(f"Missing required field: {field}")
                
                return result
                
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(f"Analysis attempt {attempt + 1} failed for comment{f' (ID: {comment_id})' if comment_id else ''}: {e}. Retrying...")
                    continue
                else:
                    logger.error(f"Analysis failed after {max_retries + 1} attempts for comment{f' (ID: {comment_id})' if comment_id else ''}: {e}")
                    
        # If we get here, all retries failed
        raise last_error