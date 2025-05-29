#!/bin/bash
# Copy all files from the latest timestamped results folder to the data folder

# Get project root directory
PROJECT_ROOT="$(dirname "$(dirname "$0")")"
RESULTS_DIR="$PROJECT_ROOT/results"
DATA_DIR="$PROJECT_ROOT/data"

echo "📋 Copy Latest Results to Data Folder"
echo "===================================="
echo ""

# Check if results directory exists
if [ ! -d "$RESULTS_DIR" ]; then
    echo "❌ Error: No results directory found at $RESULTS_DIR"
    exit 1
fi

# Find the latest timestamped results folder
LATEST_DIR=$(ls -dt "$RESULTS_DIR"/results_* 2>/dev/null | head -1)

if [ -z "$LATEST_DIR" ]; then
    echo "❌ Error: No timestamped results folders found in $RESULTS_DIR"
    exit 1
fi

echo "📁 Latest results folder: $LATEST_DIR"
echo ""

# List files in the latest results folder
echo "📄 Files to copy:"
ls -la "$LATEST_DIR" | grep -v "^d" | grep -v "^total" | awk '{print "   - " $9}'
echo ""

# Ask for confirmation
read -p "⚠️  This will DELETE everything in the data/ folder and replace it. Continue? [y/N]: " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 0
fi

echo ""
echo "🗑️  Clearing data folder..."

# Create data directory if it doesn't exist
mkdir -p "$DATA_DIR"

# Remove all files in data folder (but keep the folder itself)
find "$DATA_DIR" -mindepth 1 -delete 2>/dev/null || rm -rf "$DATA_DIR"/*

echo "📦 Copying all files from $LATEST_DIR to $DATA_DIR..."

# Copy all files from latest results to data folder
cp -r "$LATEST_DIR"/* "$DATA_DIR/" 2>/dev/null

# Check what was copied
echo ""
echo "✅ Files copied to data/:"
ls -la "$DATA_DIR" | grep -v "^d" | grep -v "^total" | awk '{print "   - " $9}'

# Show file counts
echo ""
echo "📊 Summary:"
echo "   JSON files: $(find "$DATA_DIR" -name "*.json" -type f | wc -l | tr -d ' ')"
echo "   Log files: $(find "$DATA_DIR" -name "*.log" -type f | wc -l | tr -d ' ')"
echo "   Other files: $(find "$DATA_DIR" -type f ! -name "*.json" ! -name "*.log" | wc -l | tr -d ' ')"

# Special handling for key files
echo ""
if [ -f "$DATA_DIR/raw_data.json" ]; then
    COMMENT_COUNT=$(python -c "import json; print(len(json.load(open('$DATA_DIR/raw_data.json'))))" 2>/dev/null || echo "?")
    echo "✅ raw_data.json: $COMMENT_COUNT comments"
fi

if [ -f "$DATA_DIR/lookup_table.json" ]; then
    LOOKUP_COUNT=$(python -c "import json; print(len(json.load(open('$DATA_DIR/lookup_table.json'))))" 2>/dev/null || echo "?")
    echo "✅ lookup_table.json: $LOOKUP_COUNT entries"
fi

if [ -f "$DATA_DIR/analyzed_lookup_table.json" ]; then
    echo "✅ analyzed_lookup_table.json: found"
fi

# Run merge_lookup_to_raw script if both required files exist
echo ""
if [ -f "$DATA_DIR/raw_data.json" ] && [ -f "$DATA_DIR/lookup_table.json" ]; then
    echo "🔄 Running merge_lookup_to_raw.py to create data.json..."
    cd "$PROJECT_ROOT"
    python backend/utils/merge_lookup_to_raw.py
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully created merged data.json"
        if [ -f "$DATA_DIR/data.json" ]; then
            MERGED_COUNT=$(python -c "import json; print(len(json.load(open('$DATA_DIR/data.json'))))" 2>/dev/null || echo "?")
            echo "   Merged data.json: $MERGED_COUNT comments"
        fi
    else
        echo "❌ Error running merge_lookup_to_raw.py"
    fi
elif [ -f "$DATA_DIR/raw_data.json" ] && [ -f "$DATA_DIR/lookup_table.json" ]; then
    echo "⚠️  Note: Found lookup_table.json but not lookup_table_corrected.json"
    echo "   The merge script requires lookup_table_corrected.json"
    echo "   If you have corrections, create lookup_table_corrected.json first"
else
    echo "ℹ️  Skipping merge - required files not found:"
    echo "   Need: raw_data.json and lookup_table_corrected.json"
fi

echo ""
echo "✨ Done! The data/ folder now contains all files from:"
echo "   $LATEST_DIR" 