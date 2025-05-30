#!/bin/bash

echo "🏷️  Lookup Table Label Correction Interface"
echo "==========================================="
echo ""

# Determine data file to use
if [ -n "$1" ]; then
    DATA_FILE="$1"
elif [ -f "../data/lookup_table_corrected.json" ]; then
    DATA_FILE="../data/lookup_table_corrected.json"
else
    echo "❌ Error: No lookup table file found"
    echo ""
    echo "Please ensure you have one of these files:"
    echo "   data/analyzed_lookup_table.json"
    echo "   data/lookup_table.json"
    echo ""
    echo "Or specify a file path as an argument:"
    echo "   ./run_lookup_corrections.sh /path/to/lookup_table.json"
    exit 1
fi

echo "📁 Found data file: $DATA_FILE"
echo ""

# Get file stats
ENTRIES=$(python3 -c "import json; data=json.load(open('$DATA_FILE')); print(len(data))")
COMMENTS=$(python3 -c "import json; data=json.load(open('$DATA_FILE')); print(sum(entry.get('comment_count', 0) for entry in data))")

echo "📊 Data Summary:"
echo "   Lookup entries: $ENTRIES"
echo "   Total comments: $COMMENTS"
echo ""

echo "🚀 Starting correction interface..."
echo "   URL: http://127.0.0.1:5000"
echo ""
echo "💡 Usage:"
echo "   • Filter by stance, correction status, or comment count"
echo "   • Click on any stance to correct it"
echo "   • Use 'Export Corrected Table' to create a new file with corrections"
echo "   • Use 'Update Original File' to apply corrections to the source file"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the Flask app
python3 app_lookup.py --data "$DATA_FILE"