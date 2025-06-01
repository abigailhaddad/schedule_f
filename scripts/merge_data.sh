#!/bin/bash
# Merge lookup table with raw data to create data.json
# Usage: ./merge_data.sh [output_dir]
#   - If no output_dir is provided, uses the data/ folder
#   - Looks for raw_data.json and lookup_table.json in the specified directory
#   - Validates data against JSON schemas before and after merge

# Get project root directory
PROJECT_ROOT="$(dirname "$(dirname "$0")")"

# Set default output directory to data/
OUTPUT_DIR="${1:-$PROJECT_ROOT/data}"

echo "🔄 Merge Lookup Table with Raw Data"
echo "==================================="
echo ""
echo "📁 Directory: $OUTPUT_DIR"

# Check if directory exists
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "❌ Error: Directory not found: $OUTPUT_DIR"
    exit 1
fi

# Check for required files
RAW_DATA_FILE="$OUTPUT_DIR/raw_data.json"
LOOKUP_TABLE_FILE="$OUTPUT_DIR/lookup_table.json"

echo ""
echo "🔍 Checking for required files..."

if [ ! -f "$RAW_DATA_FILE" ]; then
    echo "❌ Error: raw_data.json not found at: $RAW_DATA_FILE"
    exit 1
fi

if [ ! -f "$LOOKUP_TABLE_FILE" ]; then
    echo "❌ Error: lookup_table.json not found at: $LOOKUP_TABLE_FILE"
    exit 1
fi

echo "✅ Found raw_data.json"
echo "✅ Found lookup_table.json"

# Check for schema files for later validation
SCHEMA_DIR="$PROJECT_ROOT/json-schemas"
DATA_SCHEMA="$SCHEMA_DIR/data.schema.json"
LOOKUP_SCHEMA="$SCHEMA_DIR/lookup_table.schema.json"

# Get counts from files
RAW_COUNT=$(python -c "import json; print(len(json.load(open('$RAW_DATA_FILE'))))" 2>/dev/null || echo "?")
LOOKUP_COUNT=$(python -c "import json; print(len(json.load(open('$LOOKUP_TABLE_FILE'))))" 2>/dev/null || echo "?")

echo ""
echo "📊 File statistics:"
echo "   - raw_data.json: $RAW_COUNT comments"
echo "   - lookup_table.json: $LOOKUP_COUNT unique entries"

# Run the merge
echo ""
echo "🔄 Running merge_lookup_to_raw.py..."
cd "$PROJECT_ROOT"

# Run the merge with explicit paths
python -c "
import sys
sys.path.insert(0, '.')
from backend.utils.merge_lookup_to_raw import merge_lookup_to_raw

raw_data_path = '$RAW_DATA_FILE'
lookup_table_path = '$LOOKUP_TABLE_FILE'
output_path = '$OUTPUT_DIR/data.json'

print(f'   Input raw data: {raw_data_path}')
print(f'   Input lookup table: {lookup_table_path}')
print(f'   Output data.json: {output_path}')
print()

merge_lookup_to_raw(raw_data_path, lookup_table_path, output_path)
"

# Check if merge was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully created data.json"
    
    echo ""
    echo "🔧 Running schema compliance cleanup..."
    
    # Schema compliance cleanup for lookup_table.json
    python3 << EOF
import json
import os
import sys

lookup_file = "$LOOKUP_TABLE_FILE"
raw_data_file = "$RAW_DATA_FILE"
attachments_dir = "$OUTPUT_DIR/attachments"

print(f"🔧 Cleaning up lookup table: {lookup_file}")

# Load lookup table
try:
    with open(lookup_file, 'r') as f:
        lookup_table = json.load(f)
    print(f"   Loaded {len(lookup_table):,} lookup entries")
except:
    print(f"   ⚠️ Could not load lookup table, skipping cleanup")
    sys.exit(0)

# Load raw data for missing field population
raw_data_map = {}
if os.path.exists(raw_data_file):
    try:
        with open(raw_data_file, 'r') as f:
            raw_data = json.load(f)
        raw_data_map = {comment['id']: comment for comment in raw_data}
        print(f"   Loaded {len(raw_data_map):,} raw data entries")
    except:
        print(f"   ⚠️ Could not load raw data")

# Fix 1: Populate missing required fields
required_fields = ['comment_text', 'attachment_text', 'full_text_length', 'truncated_text_length']
missing_fields_count = 0
fixed_fields_count = 0

for entry in lookup_table:
    if any(field not in entry for field in required_fields):
        missing_fields_count += 1
        
        # Get comment IDs for this entry
        comment_ids = entry.get('comment_ids', [])
        
        # Extract text from all comments in this entry
        all_comment_texts = []
        all_attachment_texts = []
        
        for comment_id in comment_ids:
            if comment_id in raw_data_map:
                # Get comment text
                comment_text = raw_data_map[comment_id].get('attributes', {}).get('comment', '')
                if comment_text:
                    all_comment_texts.append(comment_text)
                
                # Get attachment text
                comment_attachments_dir = os.path.join(attachments_dir, comment_id)
                if os.path.exists(comment_attachments_dir):
                    try:
                        for filename in sorted(os.listdir(comment_attachments_dir)):
                            if filename.endswith('.extracted.txt'):
                                extracted_path = os.path.join(comment_attachments_dir, filename)
                                try:
                                    with open(extracted_path, 'r', encoding='utf-8') as f:
                                        attachment_text = f.read().strip()
                                        if attachment_text and not attachment_text.startswith('['):
                                            all_attachment_texts.append(attachment_text)
                                except:
                                    pass
                    except:
                        pass
        
        # Combine texts
        combined_comment_text = '\n\n'.join(all_comment_texts)
        combined_attachment_text = '\n\n--- NEXT ATTACHMENT ---\n\n'.join(all_attachment_texts)
        
        # Create full text
        full_text_parts = []
        if combined_comment_text:
            full_text_parts.append(combined_comment_text)
        if combined_attachment_text:
            full_text_parts.extend(['--- ATTACHMENT CONTENT ---', combined_attachment_text])
        
        full_text = '\n\n'.join(full_text_parts)
        
        # Update entry with missing fields
        entry['comment_text'] = combined_comment_text
        entry['attachment_text'] = combined_attachment_text
        entry['full_text_length'] = len(full_text)
        entry['truncated_text_length'] = len(entry.get('truncated_text', ''))
        
        fixed_fields_count += 1

if missing_fields_count > 0:
    print(f"   ✅ Populated missing fields in {fixed_fields_count:,} entries")

# Fix 2: Remove non-schema fields
corrected_removed = 0
for entry in lookup_table:
    if 'corrected' in entry:
        del entry['corrected']
        corrected_removed += 1

if corrected_removed > 0:
    print(f"   ✅ Removed 'corrected' field from {corrected_removed:,} entries")

# Fix 3: Fix truncated text length violations
length_fixes = 0
for entry in lookup_table:
    length = entry.get('truncated_text_length', 0)
    if length > 1003:
        # Truncate the text to 1003 characters and update length
        truncated_text = entry.get('truncated_text', '')
        if len(truncated_text) > 1003:
            entry['truncated_text'] = truncated_text[:1003]
        entry['truncated_text_length'] = min(1003, len(entry['truncated_text']))
        length_fixes += 1

if length_fixes > 0:
    print(f"   ✅ Fixed truncation length in {length_fixes:,} entries")

# Save updated lookup table only if we made changes
if missing_fields_count > 0 or corrected_removed > 0 or length_fixes > 0:
    with open(lookup_file, 'w') as f:
        json.dump(lookup_table, f, indent=2)
    print(f"   ✅ Updated lookup table saved")

print(f"   ✅ Schema compliance cleanup complete")
EOF
    
    # Validate merged data.json against schema
    if [ -f "$DATA_SCHEMA" ] && [ -f "$OUTPUT_DIR/data.json" ]; then
        echo ""
        echo "🔍 Validating merged data.json against schema..."
        python -c "
import json
import jsonschema
import sys

try:
    with open('$OUTPUT_DIR/data.json', 'r') as f:
        data = json.load(f)
    with open('$DATA_SCHEMA', 'r') as f:
        schema = json.load(f)
    
    jsonschema.validate(data, schema)
    print('   ✅ Merged data.json is valid')
except jsonschema.ValidationError as e:
    print('   🚨 SCHEMA VALIDATION FAILED FOR MERGED DATA.JSON!')
    print(f'   ERROR: {e.message}')
    print(f'   PATH: {\"->\" if e.absolute_path else \"root\"}{\".\".join(map(str, e.absolute_path))}')
    print('   🚨 THIS IS A CRITICAL ERROR - THE MERGE PRODUCED INVALID DATA!')
    sys.exit(1)
except Exception as e:
    print(f'   ❌ Error validating merged data.json: {e}')
    sys.exit(1)
" || exit 1
    fi
    
    # Show merged file statistics
    if [ -f "$OUTPUT_DIR/data.json" ]; then
        MERGED_COUNT=$(python -c "import json; print(len(json.load(open('$OUTPUT_DIR/data.json'))))" 2>/dev/null || echo "?")
        echo "📊 Merged data.json: $MERGED_COUNT comments with lookup data"
    fi
else
    echo ""
    echo "❌ Error running merge_lookup_to_raw.py"
    exit 1
fi

echo ""
echo "✨ Done! Created: $OUTPUT_DIR/data.json"