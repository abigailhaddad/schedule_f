#!/usr/bin/env python3
"""
Create a balanced test dataset for evaluating comment classification.

This script:
1. Reads from frontend/data.json
2. Deduplicates comments based on content
3. Selects an equal number of comments from each stance (For/Against/Neutral)
4. Creates a JSON file with the balanced dataset for testing
"""

import json
import random
import os
import hashlib
from collections import defaultdict

def create_balanced_dataset(input_file, output_file, samples_per_stance=30):
    """
    Create a balanced dataset with equal representation of stances.
    
    Args:
        input_file: Path to the source data.json file
        output_file: Path to save the balanced test dataset
        samples_per_stance: Number of samples to select for each stance
    """
    print(f"Reading data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Found {len(data)} total comments")
    
    # Deduplicate comments based on content
    content_hashes = {}
    deduplicated_data = []
    
    def normalize_text(text):
        """Normalize text for more robust deduplication:
        - Convert to lowercase
        - Remove punctuation
        - Remove extra whitespace
        - Remove common formatting patterns
        """
        import re
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation and special characters
        text = re.sub(r'[^\w\s]', '', text)
        
        # Remove extra whitespace, newlines, tabs
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common header/footer patterns
        text = re.sub(r'docket\s*id[\s\w\-]*', '', text)
        text = re.sub(r'office\s*of\s*personnel\s*management', '', text)
        text = re.sub(r'opm\s*\d+\s*\d+', '', text)
        text = re.sub(r'rin\s*\d+\s*\w+', '', text)
        
        # Trim whitespace
        text = text.strip()
        
        return text
    
    for comment in data:
        # Create a hash of the normalized comment content to identify duplicates
        comment_text = comment.get('comment', '')
            
        # Normalize the text before hashing
        normalized_text = normalize_text(comment_text)
            
        content_hash = hashlib.md5(normalized_text.encode('utf-8')).hexdigest()
        
        # Only keep comments with unique content
        if content_hash not in content_hashes:
            content_hashes[content_hash] = True
            deduplicated_data.append(comment)
    
    print(f"After deduplication: {len(deduplicated_data)} unique comments")
    
    # Group comments by stance
    stance_groups = defaultdict(list)
    for comment in deduplicated_data:
        stance = comment.get('stance', '')
        if stance:
            stance_groups[stance].append(comment)
    
    for stance, comments in stance_groups.items():
        print(f"  - {stance}: {len(comments)} unique comments")
    
    # Over-represent the less common stances (Neutral and For)
    # by selecting proportionally more of them
    stances = list(stance_groups.keys())
    min_stance_count = min(len(stance_groups.get('For', [])), 
                           len(stance_groups.get('Against', [])),
                           len(stance_groups.get('Neutral/Unclear', [])))
    
    # Select balanced samples
    balanced_dataset = []
    for stance, comments in stance_groups.items():
        # Determine how many to select (all if fewer than requested)
        count = min(samples_per_stance, len(comments))
        
        # Randomly select comments
        selected = random.sample(comments, count)
        balanced_dataset.extend(selected)
        
        print(f"Selected {count} comments for stance: {stance}")
    
    # Shuffle the final dataset
    random.shuffle(balanced_dataset)
    
    # Save to output file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(balanced_dataset, f, indent=2)
    
    print(f"Created balanced dataset with {len(balanced_dataset)} comments at {output_file}")
    return balanced_dataset

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create a balanced test dataset for classification testing")
    parser.add_argument(
        "--input", 
        default="/Users/abigailhaddad/Documents/repos/regs/frontend/data.json",
        help="Path to input data.json file"
    )
    parser.add_argument(
        "--output", 
        default="/Users/abigailhaddad/Documents/repos/regs/test/classification/test_data.json",
        help="Path to output balanced test data file"
    )
    parser.add_argument(
        "--samples", 
        type=int, 
        default=30,
        help="Number of samples to select per stance (default: 30)"
    )
    
    args = parser.parse_args()
    create_balanced_dataset(args.input, args.output, args.samples)