#!/usr/bin/env python3
"""
Common Utilities for Schedule F Analysis

This module contains utility functions shared across multiple components
of the Schedule F comment analysis pipeline.
"""

import os
import glob
import re
import html
from datetime import datetime

def create_directory(directory_path):
    """Create a directory if it doesn't exist."""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Created directory: {directory_path}")
    return directory_path

def get_latest_results_dir(base_dir="results"):
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

def strip_html_tags(text):
    """Remove HTML tags and decode HTML entities from text."""
    if not text:
        return text
    # First remove HTML tags
    text = re.sub(r'<[^>]*>', '', text)
    # Then decode HTML entities like &rsquo; and &ldquo;
    text = html.unescape(text)
    return text 