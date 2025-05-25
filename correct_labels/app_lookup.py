#!/usr/bin/env python3
"""
Label Correction Web Interface for Lookup Tables

A Flask app for reviewing and correcting labels in the new lookup table format.
This version works with lookup_table_analyzed.json and allows corrections that
can be merged back into the pipeline.
"""

import os
import json
import shutil
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import argparse

app = Flask(__name__)

# Global variables to store data
lookup_data = []
corrections = {}
data_file_path = None

def load_data(data_file):
    """Load lookup table data from JSON file."""
    global lookup_data, data_file_path
    data_file_path = data_file
    
    with open(data_file, 'r', encoding='utf-8') as f:
        lookup_data = json.load(f)
    
    print(f"Loaded {len(lookup_data)} lookup entries from {data_file}")
    
    # Debug: Check the structure
    if lookup_data:
        sample_entry = lookup_data[0]
        print(f"Sample entry keys: {list(sample_entry.keys())}")
        print(f"Sample lookup_id: {sample_entry.get('lookup_id')}")
        print(f"Sample stance: {sample_entry.get('stance')}")
        print(f"Sample comment_count: {sample_entry.get('comment_count')}")
        
        # Count entries with stance field
        with_stance = sum(1 for entry in lookup_data if entry.get('stance'))
        print(f"Entries with stance field: {with_stance}/{len(lookup_data)}")
        
        # Calculate total comments represented
        total_comments = sum(entry.get('comment_count', 0) for entry in lookup_data)
        print(f"Total comments represented: {total_comments}")

def load_corrections():
    """Load existing corrections from file."""
    global corrections
    corrections_file = os.path.join(os.path.dirname(data_file_path), 'lookup_corrections.json')
    
    if os.path.exists(corrections_file):
        with open(corrections_file, 'r', encoding='utf-8') as f:
            corrections = json.load(f)
        print(f"Loaded {len(corrections)} existing lookup corrections")
    else:
        corrections = {}
        print("No existing lookup corrections found")

def save_corrections():
    """Save corrections to file."""
    corrections_file = os.path.join(os.path.dirname(data_file_path), 'lookup_corrections.json')
    with open(corrections_file, 'w', encoding='utf-8') as f:
        json.dump(corrections, f, indent=2)

def get_filtered_entries(stance_filter=None, corrected_filter=None, count_filter=None):
    """Get lookup entries filtered by stance, correction status, and count."""
    filtered = []
    
    for entry in lookup_data:
        lookup_id = entry.get('lookup_id')
        if not lookup_id:
            continue
            
        original_stance = entry.get('stance', 'Unknown')
        comment_count = entry.get('comment_count', 1)
        
        # Apply count filter
        if count_filter and count_filter != 'all':
            if count_filter == 'unique' and comment_count > 1:
                continue
            elif count_filter == 'duplicates' and comment_count == 1:
                continue
            elif count_filter.startswith('min_'):
                min_count = int(count_filter.split('_')[1])
                if comment_count < min_count:
                    continue
        
        # Check if this entry has been corrected
        is_corrected = lookup_id in corrections
        corrected_stance = corrections.get(lookup_id, {}).get('corrected_stance', original_stance)
        
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
        entry_data = entry.copy()
        entry_data['is_corrected'] = is_corrected
        entry_data['corrected_stance'] = corrected_stance if is_corrected else None
        entry_data['display_stance'] = corrected_stance if is_corrected else original_stance
        
        # Ensure we have text to display (truncated)
        if not entry_data.get('truncated_text'):
            entry_data['truncated_text'] = 'No text available'
        
        # Add comment IDs for reference (first few)
        comment_ids = entry.get('comment_ids', [])
        entry_data['sample_comment_ids'] = comment_ids[:3] if len(comment_ids) > 3 else comment_ids
        entry_data['has_more_comments'] = len(comment_ids) > 3
        
        filtered.append(entry_data)
    
    # Sort by comment count descending (highest impact first), then by lookup_id for consistency
    filtered.sort(key=lambda x: (-x.get('comment_count', 1), x.get('lookup_id', '')))
    
    return filtered

@app.route('/')
def index():
    """Main page."""
    stance_filter = request.args.get('stance', 'all')
    corrected_filter = request.args.get('corrected', 'all')
    count_filter = request.args.get('count', 'all')
    
    print(f"Filtering with stance={stance_filter}, corrected={corrected_filter}, count={count_filter}")
    filtered_entries = get_filtered_entries(stance_filter, corrected_filter, count_filter)
    print(f"Found {len(filtered_entries)} filtered entries")
    
    # Get unique stances for filter dropdown
    all_stances = set()
    for entry in lookup_data:
        if entry.get('stance'):
            all_stances.add(entry['stance'])
        lookup_id = entry.get('lookup_id')
        if lookup_id in corrections:
            all_stances.add(corrections[lookup_id]['corrected_stance'])
    
    # Get count statistics
    comment_counts = [entry.get('comment_count', 1) for entry in lookup_data]
    max_count = max(comment_counts) if comment_counts else 1
    unique_count = sum(1 for count in comment_counts if count == 1)
    duplicate_count = len(comment_counts) - unique_count
    total_comments = sum(comment_counts)
    
    print(f"Available stances: {sorted(list(all_stances))}")
    print(f"Count stats: max={max_count}, unique={unique_count}, duplicates={duplicate_count}")
    
    return render_template('index_lookup.html', 
                         entries=filtered_entries,
                         stances=sorted(list(all_stances)),
                         current_stance_filter=stance_filter,
                         current_corrected_filter=corrected_filter,
                         current_count_filter=count_filter,
                         total_entries=len(lookup_data),
                         total_comments=total_comments,
                         total_corrections=len(corrections),
                         max_comment_count=max_count,
                         unique_entries=unique_count,
                         duplicate_entries=duplicate_count)

@app.route('/api/correct', methods=['POST'])
def correct_label():
    """API endpoint to save a label correction."""
    data = request.json
    lookup_id = data.get('lookup_id')
    corrected_stance = data.get('corrected_stance')
    original_stance = data.get('original_stance')
    
    if not lookup_id or not corrected_stance:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Save correction
    corrections[lookup_id] = {
        'original_stance': original_stance,
        'corrected_stance': corrected_stance,
        'timestamp': datetime.now().isoformat(),
        'corrected_by': 'user'
    }
    
    save_corrections()
    
    return jsonify({'success': True, 'message': f'Corrected {lookup_id} to {corrected_stance}'})

@app.route('/api/uncorrect', methods=['POST'])
def uncorrect_label():
    """API endpoint to remove a correction (revert to original)."""
    data = request.json
    lookup_id = data.get('lookup_id')
    
    if not lookup_id:
        return jsonify({'error': 'Missing lookup_id'}), 400
    
    if lookup_id in corrections:
        del corrections[lookup_id]
        save_corrections()
        return jsonify({'success': True, 'message': f'Reverted {lookup_id} to original label'})
    else:
        return jsonify({'error': 'No correction found for this entry'}), 404

@app.route('/api/export_corrected', methods=['POST'])
def export_corrected():
    """Export a corrected version of the lookup table."""
    try:
        # Create corrected version of lookup table
        corrected_lookup = []
        corrections_applied = 0
        
        for entry in lookup_data:
            entry_copy = entry.copy()
            lookup_id = entry.get('lookup_id')
            
            # Apply correction if it exists
            if lookup_id in corrections:
                correction = corrections[lookup_id]
                entry_copy['stance'] = correction['corrected_stance']
                entry_copy['corrected'] = True
                entry_copy['correction_timestamp'] = correction['timestamp']
                entry_copy['original_stance'] = correction['original_stance']
                corrections_applied += 1
            else:
                entry_copy['corrected'] = False
            
            corrected_lookup.append(entry_copy)
        
        # Save corrected lookup table
        base_path = os.path.splitext(data_file_path)[0]
        corrected_file = f"{base_path}_corrected.json"
        
        with open(corrected_file, 'w', encoding='utf-8') as f:
            json.dump(corrected_lookup, f, indent=2)
        
        return jsonify({
            'success': True, 
            'message': f'Exported corrected lookup table with {corrections_applied} corrections',
            'file': corrected_file,
            'corrections_applied': corrections_applied,
            'total_entries': len(corrected_lookup)
        })
        
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@app.route('/api/update_original', methods=['POST'])
def update_original():
    """Update the original lookup table file with corrections."""
    try:
        # Create backup of original file
        backup_file = f"{data_file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(data_file_path, backup_file)
        
        # Apply corrections to lookup data
        corrections_applied = 0
        
        for entry in lookup_data:
            lookup_id = entry.get('lookup_id')
            
            # Apply correction if it exists
            if lookup_id in corrections:
                correction = corrections[lookup_id]
                entry['stance'] = correction['corrected_stance']
                entry['corrected'] = True
                entry['correction_timestamp'] = correction['timestamp']
                entry['original_stance'] = correction['original_stance']
                corrections_applied += 1
        
        # Save updated lookup table to original file
        with open(data_file_path, 'w', encoding='utf-8') as f:
            json.dump(lookup_data, f, indent=2)
        
        # Clear corrections since they're now applied
        corrections.clear()
        save_corrections()
        
        return jsonify({
            'success': True, 
            'message': f'Updated original file with {corrections_applied} corrections',
            'backup_file': backup_file,
            'corrections_applied': corrections_applied,
            'total_entries': len(lookup_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Update failed: {str(e)}'}), 500

@app.route('/api/stats')
def get_stats():
    """Get statistics about corrections."""
    total_comments = sum(entry.get('comment_count', 0) for entry in lookup_data)
    corrected_entries = len(corrections)
    corrected_comments = sum(
        entry.get('comment_count', 0) 
        for entry in lookup_data 
        if entry.get('lookup_id') in corrections
    )
    
    stats = {
        'total_entries': len(lookup_data),
        'total_comments': total_comments,
        'total_corrections': corrected_entries,
        'corrected_comments': corrected_comments,
        'entry_correction_rate': corrected_entries / len(lookup_data) * 100 if lookup_data else 0,
        'comment_correction_rate': corrected_comments / total_comments * 100 if total_comments else 0
    }
    
    # Count by stance
    stance_counts = {}
    corrected_stance_counts = {}
    
    for entry in lookup_data:
        original_stance = entry.get('stance', 'Unknown')
        comment_count = entry.get('comment_count', 1)
        stance_counts[original_stance] = stance_counts.get(original_stance, 0) + comment_count
        
        lookup_id = entry.get('lookup_id')
        if lookup_id in corrections:
            corrected_stance = corrections[lookup_id]['corrected_stance']
            corrected_stance_counts[corrected_stance] = corrected_stance_counts.get(corrected_stance, 0) + comment_count
    
    stats['original_stance_counts'] = stance_counts
    stats['corrected_stance_counts'] = corrected_stance_counts
    
    return jsonify(stats)

def main():
    """Main function to run the app."""
    parser = argparse.ArgumentParser(description='Lookup Table Label Correction Interface')
    parser.add_argument('--data', type=str, required=True,
                        help='Path to the analyzed_lookup_table.json file to review')
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
    
    print(f"Starting lookup table correction interface...")
    print(f"Open your browser to: http://{args.host}:{args.port}")
    print(f"Data file: {args.data}")
    print(f"Corrections will be saved to: {os.path.join(os.path.dirname(args.data), 'lookup_corrections.json')}")
    print(f"Use 'Export Corrected' button to create a corrected lookup table for pipeline use")
    
    app.run(host=args.host, port=args.port, debug=True)

if __name__ == '__main__':
    main()