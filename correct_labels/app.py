#!/usr/bin/env python3
"""
Label Correction Web Interface

A simple Flask app for reviewing and correcting comment labels.
"""

import os
import json
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import argparse

app = Flask(__name__)

# Global variables to store data
comments_data = []
corrections = {}
data_file_path = None

def calculate_duplicates():
    """Calculate duplicate occurrences for data that doesn't have occurrence_number field."""
    comment_text_map = {}
    
    # First pass: map normalized text to comment IDs
    for comment in comments_data:
        comment_id = comment.get('id')
        if not comment_id:
            continue
            
        comment_text = comment.get('comment', comment.get('original_comment', ''))
        normalized_text = comment_text.strip().lower()
        
        if normalized_text not in comment_text_map:
            comment_text_map[normalized_text] = []
        comment_text_map[normalized_text].append(comment_id)
    
    # Second pass: assign occurrence numbers
    for comment in comments_data:
        comment_id = comment.get('id')
        if not comment_id:
            continue
            
        comment_text = comment.get('comment', comment.get('original_comment', ''))
        normalized_text = comment_text.strip().lower()
        
        matching_ids = comment_text_map[normalized_text]
        occurrence_number = matching_ids.index(comment_id) + 1
        
        # Add calculated fields
        comment['occurrence_number'] = occurrence_number
        if occurrence_number == 1:
            comment['duplicate_of'] = ""
        else:
            comment['duplicate_of'] = matching_ids[0]  # First occurrence
    
    # Log statistics
    unique_texts = sum(1 for ids in comment_text_map.values() if len(ids) == 1)
    duplicate_texts = len(comment_text_map) - unique_texts
    total_duplicates = sum(len(ids) - 1 for ids in comment_text_map.values() if len(ids) > 1)
    
    print(f"Calculated duplicates: {unique_texts} unique texts, {duplicate_texts} texts with duplicates")
    print(f"Total duplicate instances: {total_duplicates}")

def load_data(data_file):
    """Load comments data from JSON file."""
    global comments_data, data_file_path
    data_file_path = data_file
    
    with open(data_file, 'r', encoding='utf-8') as f:
        comments_data = json.load(f)
    
    print(f"Loaded {len(comments_data)} comments from {data_file}")
    
    # Debug: Check the structure of the first few comments
    if comments_data:
        sample_comment = comments_data[0]
        print(f"Sample comment keys: {list(sample_comment.keys())}")
        print(f"Sample comment ID: {sample_comment.get('id')}")
        print(f"Sample comment stance: {sample_comment.get('stance')}")
        
        # Count comments with stance field
        with_stance = sum(1 for c in comments_data if c.get('stance'))
        print(f"Comments with stance field: {with_stance}/{len(comments_data)}")
        
        # Check if occurrence_number field exists
        has_occurrence_field = any(c.get('occurrence_number') is not None for c in comments_data)
        print(f"Data has occurrence_number field: {has_occurrence_field}")
        
        # If no occurrence_number field, calculate duplicates dynamically
        if not has_occurrence_field:
            print("Calculating duplicates dynamically...")
            calculate_duplicates()

def load_corrections():
    """Load existing corrections from file."""
    global corrections
    corrections_file = os.path.join(os.path.dirname(data_file_path), 'corrections.json')
    
    if os.path.exists(corrections_file):
        with open(corrections_file, 'r', encoding='utf-8') as f:
            corrections = json.load(f)
        print(f"Loaded {len(corrections)} existing corrections")
    else:
        corrections = {}
        print("No existing corrections found")

def save_corrections():
    """Save corrections to file."""
    corrections_file = os.path.join(os.path.dirname(data_file_path), 'corrections.json')
    with open(corrections_file, 'w', encoding='utf-8') as f:
        json.dump(corrections, f, indent=2)

def get_filtered_comments(stance_filter=None, corrected_filter=None, count_filter=None):
    """Get comments filtered by stance, correction status, and count."""
    filtered = []
    
    for comment in comments_data:
        # Skip comments without required fields
        comment_id = comment.get('id')
        if not comment_id:
            continue
            
        original_stance = comment.get('stance', 'Unknown')
        occurrence_number = comment.get('occurrence_number', 1)
        
        # Apply count filter
        if count_filter and count_filter != 'all':
            if count_filter == 'unique' and occurrence_number > 1:
                continue
            elif count_filter == 'duplicates' and occurrence_number == 1:
                continue
            elif count_filter.startswith('min_') and occurrence_number < int(count_filter.split('_')[1]):
                continue
        
        # Check if this comment has been corrected
        is_corrected = comment_id in corrections
        corrected_stance = corrections.get(comment_id, {}).get('corrected_stance', original_stance)
        
        # Apply stance filter
        if stance_filter and stance_filter != 'all':
            # Use corrected stance if available, otherwise original
            current_stance = corrected_stance if is_corrected else original_stance
            if current_stance != stance_filter:
                continue
        
        # Apply corrected filter
        if corrected_filter == 'corrected' and not is_corrected:
            continue
        elif corrected_filter == 'uncorrected' and is_corrected:
            continue
        
        # Add metadata for display
        comment_data = comment.copy()
        comment_data['is_corrected'] = is_corrected
        comment_data['corrected_stance'] = corrected_stance if is_corrected else None
        comment_data['display_stance'] = corrected_stance if is_corrected else original_stance
        comment_data['occurrence_number'] = occurrence_number
        
        # Ensure we have a comment text to display
        if not comment_data.get('comment'):
            comment_data['comment'] = comment_data.get('original_comment', 'No comment text available')
        
        filtered.append(comment_data)
    
    # Sort by occurrence number descending (highest count first), then by ID for consistency
    filtered.sort(key=lambda x: (-x.get('occurrence_number', 1), x.get('id', '')))
    
    return filtered

@app.route('/')
def index():
    """Main page."""
    stance_filter = request.args.get('stance', 'all')
    corrected_filter = request.args.get('corrected', 'all')
    count_filter = request.args.get('count', 'all')
    
    print(f"Filtering with stance={stance_filter}, corrected={corrected_filter}, count={count_filter}")
    filtered_comments = get_filtered_comments(stance_filter, corrected_filter, count_filter)
    print(f"Found {len(filtered_comments)} filtered comments")
    
    # Get unique stances for filter dropdown
    all_stances = set()
    for comment in comments_data:
        if comment.get('stance'):
            all_stances.add(comment['stance'])
        comment_id = comment.get('id')
        if comment_id in corrections:
            all_stances.add(corrections[comment_id]['corrected_stance'])
    
    # Get count statistics
    occurrence_counts = [comment.get('occurrence_number', 1) for comment in comments_data]
    max_count = max(occurrence_counts) if occurrence_counts else 1
    unique_count = sum(1 for count in occurrence_counts if count == 1)
    duplicate_count = len(occurrence_counts) - unique_count
    
    print(f"Available stances: {sorted(list(all_stances))}")
    print(f"Count stats: max={max_count}, unique={unique_count}, duplicates={duplicate_count}")
    
    return render_template('index.html', 
                         comments=filtered_comments,
                         stances=sorted(list(all_stances)),
                         current_stance_filter=stance_filter,
                         current_corrected_filter=corrected_filter,
                         current_count_filter=count_filter,
                         total_comments=len(comments_data),
                         total_corrections=len(corrections),
                         max_occurrence_count=max_count,
                         unique_comments=unique_count,
                         duplicate_comments=duplicate_count)

@app.route('/api/correct', methods=['POST'])
def correct_label():
    """API endpoint to save a label correction."""
    data = request.json
    comment_id = data.get('comment_id')
    corrected_stance = data.get('corrected_stance')
    original_stance = data.get('original_stance')
    
    if not comment_id or not corrected_stance:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Save correction
    corrections[comment_id] = {
        'original_stance': original_stance,
        'corrected_stance': corrected_stance,
        'timestamp': datetime.now().isoformat(),
        'corrected_by': 'user'  # Could be extended to track different users
    }
    
    save_corrections()
    
    return jsonify({'success': True, 'message': f'Corrected {comment_id} to {corrected_stance}'})

@app.route('/api/uncorrect', methods=['POST'])
def uncorrect_label():
    """API endpoint to remove a correction (revert to original)."""
    data = request.json
    comment_id = data.get('comment_id')
    
    if not comment_id:
        return jsonify({'error': 'Missing comment_id'}), 400
    
    if comment_id in corrections:
        del corrections[comment_id]
        save_corrections()
        return jsonify({'success': True, 'message': f'Reverted {comment_id} to original label'})
    else:
        return jsonify({'error': 'No correction found for this comment'}), 404

@app.route('/api/stats')
def get_stats():
    """Get statistics about corrections."""
    stats = {
        'total_comments': len(comments_data),
        'total_corrections': len(corrections),
        'correction_rate': len(corrections) / len(comments_data) * 100 if comments_data else 0
    }
    
    # Count by stance
    stance_counts = {}
    corrected_stance_counts = {}
    
    for comment in comments_data:
        original_stance = comment.get('stance', 'Unknown')
        stance_counts[original_stance] = stance_counts.get(original_stance, 0) + 1
        
        comment_id = comment.get('id')
        if comment_id in corrections:
            corrected_stance = corrections[comment_id]['corrected_stance']
            corrected_stance_counts[corrected_stance] = corrected_stance_counts.get(corrected_stance, 0) + 1
    
    stats['original_stance_counts'] = stance_counts
    stats['corrected_stance_counts'] = corrected_stance_counts
    
    return jsonify(stats)

def main():
    """Main function to run the app."""
    parser = argparse.ArgumentParser(description='Label Correction Web Interface')
    parser.add_argument('--data', type=str, required=True,
                        help='Path to the data.json file to review')
    parser.add_argument('--port', type=int, default=5000,
                        help='Port to run the web server on (default: 5000)')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help='Host to run the web server on (default: 127.0.0.1)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.data):
        print(f"Error: Data file '{args.data}' not found.")
        return 1
    
    # Load data
    load_data(args.data)
    load_corrections()
    
    print(f"Starting label correction interface...")
    print(f"Open your browser to: http://{args.host}:{args.port}")
    print(f"Data file: {args.data}")
    print(f"Corrections will be saved to: {os.path.join(os.path.dirname(args.data), 'corrections.json')}")
    
    app.run(host=args.host, port=args.port, debug=True)

if __name__ == '__main__':
    main()