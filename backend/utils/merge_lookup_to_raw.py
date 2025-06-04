#!/usr/bin/env python3
"""
Script to merge raw_data.json with lookup_table.json
Creates a data.json file with row-level data including LLM info
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define lookup fields with their default values
LOOKUP_FIELDS = {
    'lookup_id': None,
    'truncated_text': None,
    'text_source': None,
    'comment_text': None,
    'attachment_text': None,
    'comment_count': None,
    'stance': None,
    'key_quote': None,
    'rationale': None,
    'themes': [],
    'corrected': False,
    'cluster_id': None,
    'pca_x': None,
    'pca_y': None
}

# Define expected fields schema with types and requirements
EXPECTED_FIELDS_SCHEMA = {
    # Core fields (required)
    'id': {'type': str, 'required': True, 'nullable': False},
    'title': {'type': str, 'required': True, 'nullable': False},
    'comment': {'type': str, 'required': True, 'nullable': False},
    'original_comment': {'type': str, 'required': True, 'nullable': False},
    'agency_id': {'type': str, 'required': True, 'nullable': False},
    
    # Date fields (required, specific format)
    'posted_date': {'type': str, 'required': True, 'nullable': False, 'date_format': True},
    'received_date': {'type': str, 'required': True, 'nullable': False, 'date_format': True},
    
    # Optional string fields
    'category': {'type': str, 'required': False, 'nullable': True},
    'submitter_name': {'type': str, 'required': False, 'nullable': True},
    'organization': {'type': str, 'required': False, 'nullable': True},
    'city': {'type': str, 'required': False, 'nullable': True},
    'state': {'type': str, 'required': False, 'nullable': True},
    'country': {'type': str, 'required': False, 'nullable': True},
    'comment_on': {'type': str, 'required': False, 'nullable': True},
    'document_type': {'type': str, 'required': False, 'nullable': True},
    'link': {'type': str, 'required': False, 'nullable': True},
    
    # Boolean/numeric fields
    'has_attachments': {'type': bool, 'required': True, 'nullable': False},
    'attachment_count': {'type': int, 'required': False, 'nullable': True},
    
    # Attachment details (flattened)
    'attachment_urls': {'type': str, 'required': False, 'nullable': True},
    'attachment_titles': {'type': str, 'required': False, 'nullable': True},
    'attachment_local_paths': {'type': str, 'required': False, 'nullable': True},
    
    # Lookup fields (from LOOKUP_FIELDS)
    'lookup_id': {'type': str, 'required': True, 'nullable': True},
    'truncated_text': {'type': str, 'required': False, 'nullable': True},
    'text_source': {'type': str, 'required': False, 'nullable': True},
    'comment_text': {'type': str, 'required': False, 'nullable': True},
    'attachment_text': {'type': str, 'required': False, 'nullable': True},
    'comment_count': {'type': int, 'required': False, 'nullable': True},
    'stance': {'type': str, 'required': False, 'nullable': True, 'allowed_values': ['For', 'Against', 'Neutral', 'Mixed', 'Neutral/Unclear', '', None]},
    'key_quote': {'type': str, 'required': False, 'nullable': True},
    'rationale': {'type': str, 'required': False, 'nullable': True},
    'themes': {'type': (list, str), 'required': False, 'nullable': True},  # Can be list or string
    'corrected': {'type': bool, 'required': False, 'nullable': True},
    'cluster_id': {'type': (str, int), 'required': False, 'nullable': True},
    'pca_x': {'type': float, 'required': False, 'nullable': True},
    'pca_y': {'type': float, 'required': False, 'nullable': True}
}

def load_json_file(filepath: Path) -> Any:
    """Load JSON data from file"""
    logger.info(f"Loading {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_lookup_mapping(lookup_data: List[Dict]) -> Dict[str, Dict]:
    """Create a mapping from comment_id to lookup info"""
    logger.info("Creating lookup mapping...")
    mapping = {}
    duplicate_ids = []
    
    for lookup_entry in lookup_data:
        # Extract fields using the defined LOOKUP_FIELDS as reference
        lookup_info = {}
        for field, default_value in LOOKUP_FIELDS.items():
            lookup_info[field] = lookup_entry.get(field, default_value)
        
        # Map to all comment IDs associated with this lookup entry
        comment_ids = lookup_entry.get('comment_ids', [])
        if not comment_ids:
            logger.warning(f"Lookup entry {lookup_entry.get('lookup_id')} has no comment_ids")
        
        for comment_id in comment_ids:
            if comment_id in mapping:
                duplicate_ids.append(comment_id)
                logger.warning(f"Comment ID {comment_id} appears in multiple lookup entries - keeping first occurrence")
                # Skip adding this duplicate - keep the first occurrence
                continue
            mapping[comment_id] = lookup_info
    
    if duplicate_ids:
        unique_duplicates = list(set(duplicate_ids))
        logger.warning(f"Found {len(unique_duplicates)} comment IDs that appear in multiple lookup entries")
        logger.warning(f"Duplicate IDs: {unique_duplicates[:10]}{'...' if len(unique_duplicates) > 10 else ''}")
        logger.warning("Kept only the first occurrence of each duplicate")
    
    logger.info(f"Created mapping for {len(mapping)} comments")
    return mapping

def validate_date_format(date_str: str) -> bool:
    """Check if string is in ISO 8601 format"""
    if not date_str:
        return False
    try:
        # Check basic ISO format YYYY-MM-DDTHH:MMZ
        if 'T' in date_str and date_str.endswith('Z'):
            datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return True
        return False
    except:
        return False

def validate_comment_fields(comment: Dict, comment_id: str) -> List[str]:
    """Validate that comment has all required fields with correct types"""
    issues = []
    
    for field_name, field_spec in EXPECTED_FIELDS_SCHEMA.items():
        # Check if field exists
        if field_name not in comment:
            if field_spec.get('required', False):
                issues.append(f"Missing required field '{field_name}'")
            continue
        
        field_value = comment[field_name]
        
        # Check nullable constraint
        if field_value is None:
            if not field_spec.get('nullable', True):
                issues.append(f"Field '{field_name}' cannot be null")
            continue
        
        # Check type
        expected_type = field_spec.get('type')
        if expected_type:
            # Handle tuple of types (like for themes which can be list or str)
            if isinstance(expected_type, tuple):
                if not isinstance(field_value, expected_type):
                    issues.append(f"Field '{field_name}' has wrong type: expected {expected_type}, got {type(field_value)}")
            else:
                if not isinstance(field_value, expected_type):
                    issues.append(f"Field '{field_name}' has wrong type: expected {expected_type.__name__}, got {type(field_value).__name__}")
        
        # Check date format
        if field_spec.get('date_format') and field_value:
            if not validate_date_format(field_value):
                issues.append(f"Field '{field_name}' has invalid date format: {field_value} (expected ISO 8601)")
        
        # Check allowed values
        allowed_values = field_spec.get('allowed_values')
        if allowed_values and field_value is not None:
            if field_value not in allowed_values:
                issues.append(f"Field '{field_name}' has invalid value: {field_value} (allowed: {allowed_values})")
    
    return issues

def validate_merged_data(merged_data: List[Dict]) -> Dict[str, Any]:
    """Validate all comments in merged data and return validation report"""
    logger.info("Validating merged data...")
    
    total_comments = len(merged_data)
    comments_with_issues = 0
    all_issues = {}
    field_coverage = {}
    
    # Initialize field coverage tracking
    for field_name in EXPECTED_FIELDS_SCHEMA:
        field_coverage[field_name] = {
            'present_count': 0,
            'non_null_count': 0,
            'type_errors': 0
        }
    
    # Validate each comment
    for comment in merged_data:
        comment_id = comment.get('id', 'UNKNOWN')
        issues = validate_comment_fields(comment, comment_id)
        
        if issues:
            comments_with_issues += 1
            all_issues[comment_id] = issues
        
        # Track field coverage
        for field_name in EXPECTED_FIELDS_SCHEMA:
            if field_name in comment:
                field_coverage[field_name]['present_count'] += 1
                if comment[field_name] is not None:
                    field_coverage[field_name]['non_null_count'] += 1
    
    # Create validation report
    report = {
        'total_comments': total_comments,
        'comments_with_issues': comments_with_issues,
        'validation_passed': comments_with_issues == 0,
        'field_coverage': field_coverage,
        'sample_issues': dict(list(all_issues.items())[:10]) if all_issues else {}
    }
    
    # Log summary
    logger.info(f"Validation complete: {total_comments} comments checked")
    if comments_with_issues > 0:
        logger.warning(f"Found {comments_with_issues} comments with validation issues")
        logger.warning("Sample issues:")
        for comment_id, issues in list(all_issues.items())[:5]:
            logger.warning(f"  Comment {comment_id}:")
            for issue in issues[:3]:  # Show first 3 issues per comment
                logger.warning(f"    - {issue}")
    else:
        logger.info("All comments passed validation!")
    
    # Log field coverage summary
    logger.info("Field coverage summary:")
    for field_name, coverage in field_coverage.items():
        coverage_pct = (coverage['present_count'] / total_comments * 100) if total_comments > 0 else 0
        non_null_pct = (coverage['non_null_count'] / total_comments * 100) if total_comments > 0 else 0
        logger.info(f"  {field_name}: {coverage_pct:.1f}% present, {non_null_pct:.1f}% non-null")
    
    return report

def flatten_comment(comment: Dict) -> Dict:
    """Flatten comment structure if it has nested attributes"""
    # If comment has 'attributes' field, flatten it
    if 'attributes' in comment and isinstance(comment['attributes'], dict):
        # Start with the ID
        flattened = {'id': comment.get('id')}
        
        # Add all fields from attributes
        attributes = comment['attributes']
        flattened.update({
            'title': attributes.get('title'),
            'comment_on': attributes.get('commentOn'),
            'posted_date': attributes.get('postedDate'),
            'received_date': attributes.get('receivedDate'),
            'submitter_name': attributes.get('submitterName', ''),
            'organization': attributes.get('organization', ''),
            'city': attributes.get('city', ''),
            'state': attributes.get('state', ''),
            'country': attributes.get('country', ''),
            'comment': attributes.get('comment'),
            'original_comment': attributes.get('comment'),  # Keep original_comment same as comment
            'document_type': attributes.get('documentType'),
            'agency_id': attributes.get('agencyId'),
            'category': attributes.get('category', ''),
            'attachment_count': attributes.get('attachmentCount', 0),
            'has_attachments': attributes.get('attachmentCount', 0) > 0
        })
        
        # Flatten attachments if they exist
        attachments = attributes.get('attachments', [])
        if attachments:
            # Extract lists of values
            urls = []
            titles = []
            local_paths = []
            
            for att in attachments:
                urls.append(att.get('fileUrl', ''))
                titles.append(att.get('title', ''))
                local_paths.append(att.get('localPath', ''))
            
            # Join with semicolons for easy parsing
            flattened['attachment_urls'] = '; '.join(urls)
            flattened['attachment_titles'] = '; '.join(titles)
            flattened['attachment_local_paths'] = '; '.join(local_paths)
        else:
            flattened['attachment_urls'] = ''
            flattened['attachment_titles'] = ''
            flattened['attachment_local_paths'] = ''
        
        # Add any other top-level fields that aren't 'attributes'
        for key, value in comment.items():
            if key not in ['id', 'attributes']:
                flattened[key] = value
                
        return flattened
    else:
        # Already flat structure
        return comment

def merge_data(raw_data: List[Dict], lookup_mapping: Dict[str, Dict]) -> List[Dict]:
    """Merge raw data with lookup information"""
    logger.info("Merging data...")
    merged_data = []
    matched_count = 0
    unmatched_comments = []
    
    # Track all comment IDs from raw data
    raw_comment_ids = set()
    
    for comment in raw_data:
        # First flatten the comment if needed
        flattened_comment = flatten_comment(comment)
        
        comment_id = flattened_comment.get('id')
        if not comment_id:
            logger.error(f"Comment without ID found: {flattened_comment}")
            raise ValueError("Found comment without ID in raw_data")
        
        raw_comment_ids.add(comment_id)
        merged_comment = flattened_comment.copy()
        
        # Add lookup info if available
        if comment_id in lookup_mapping:
            merged_comment.update(lookup_mapping[comment_id])
            matched_count += 1
        else:
            # Track unmatched comments
            unmatched_comments.append(comment_id)
            # Add empty lookup fields for comments without lookup data
            merged_comment.update(LOOKUP_FIELDS.copy())
        
        merged_data.append(merged_comment)
    
    # Check for lookup entries that don't have corresponding raw data
    lookup_comment_ids = set(lookup_mapping.keys())
    orphaned_lookup_ids = lookup_comment_ids - raw_comment_ids
    
    # Report any issues
    if unmatched_comments:
        logger.warning(f"Found {len(unmatched_comments)} comments in raw_data without lookup entries:")
        for i, comment_id in enumerate(unmatched_comments[:10]):  # Show first 10
            logger.warning(f"  - {comment_id}")
        if len(unmatched_comments) > 10:
            logger.warning(f"  ... and {len(unmatched_comments) - 10} more")
    
    if orphaned_lookup_ids:
        logger.error(f"Found {len(orphaned_lookup_ids)} lookup entries without corresponding raw data:")
        for i, comment_id in enumerate(list(orphaned_lookup_ids)[:10]):  # Show first 10
            logger.error(f"  - {comment_id}")
        if len(orphaned_lookup_ids) > 10:
            logger.error(f"  ... and {len(orphaned_lookup_ids) - 10} more")
        raise ValueError(f"Found {len(orphaned_lookup_ids)} lookup entries that reference non-existent comments")
    
    logger.info(f"Merged {len(merged_data)} comments, {matched_count} with lookup data")
    if unmatched_comments:
        logger.info(f"Note: {len(unmatched_comments)} comments have no lookup data (this may be expected)")
    
    return merged_data

def main():
    """Main function to merge raw data with lookup table"""
    # Define file paths
    base_dir = Path(__file__).parent.parent.parent
    data_dir = base_dir / 'data'
    
    raw_data_path = data_dir / 'raw_data.json'
    lookup_path = data_dir / 'lookup_table.json'
    output_path = data_dir / 'data.json'
    
    try:
        # Load data
        raw_data = load_json_file(raw_data_path)
        lookup_data = load_json_file(lookup_path)
        
        # Create lookup mapping
        lookup_mapping = create_lookup_mapping(lookup_data)
        
        # Merge data
        merged_data = merge_data(raw_data, lookup_mapping)
        
        # Validate merged data
        validation_report = validate_merged_data(merged_data)
        
        # Save validation report
        validation_report_path = data_dir / 'data_validation_report.json'
        logger.info(f"Saving validation report to {validation_report_path}")
        with open(validation_report_path, 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, indent=2, ensure_ascii=False)
        
        # Save merged data
        logger.info(f"Saving merged data to {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)
        
        # Log final status
        if validation_report['validation_passed']:
            logger.info("Merge completed successfully - all data validated!")
        else:
            logger.warning(f"Merge completed with {validation_report['comments_with_issues']} validation issues - check validation report")
        
    except Exception as e:
        logger.error(f"Error during merge: {e}")
        raise

def merge_lookup_to_raw(raw_data_path: str, lookup_path: str, output_path: str) -> None:
    """
    Merge raw data with lookup table - callable from other modules
    
    Args:
        raw_data_path: Path to raw_data.json file
        lookup_path: Path to lookup_table.json file
        output_path: Path to save merged data.json file
    """
    try:
        # Load data
        raw_data = load_json_file(Path(raw_data_path))
        lookup_data = load_json_file(Path(lookup_path))
        
        # Create lookup mapping
        lookup_mapping = create_lookup_mapping(lookup_data)
        
        # Merge data
        merged_data = merge_data(raw_data, lookup_mapping)
        
        # Validate merged data
        validation_results = validate_merged_data(merged_data)
        
        # Save merged data
        with open(output_path, 'w') as f:
            json.dump(merged_data, f, indent=2)
        
        logger.info(f"✅ Successfully merged {len(merged_data)} comments to {output_path}")
        
        # Save validation report
        validation_report_path = Path(output_path).parent / 'data_validation_report.json'
        with open(validation_report_path, 'w') as f:
            json.dump(validation_results, f, indent=2)
        
        # Print validation summary
        if validation_results['validation_passed']:
            logger.info("✅ VALIDATION PASSED")
        else:
            logger.warning("❌ VALIDATION FAILED")
            logger.warning(f"Total comments with issues: {validation_results['comments_with_issues']}")
            
        return validation_results['validation_passed']
            
    except Exception as e:
        logger.error(f"Error during merge: {e}")
        raise

if __name__ == "__main__":
    main()