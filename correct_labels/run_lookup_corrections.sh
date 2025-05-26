#!/bin/bash

# Script to run lookup table label corrections

VENV_PATH="../myenv/bin/activate"

# Check if lookup table file is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <lookup_table_analyzed.json> [port]"
    echo ""
    echo "Example:"
    echo "  $0 ../results/lookup_table_analyzed.json"
    echo "  $0 ../results/lookup_table_analyzed.json 8000"
    echo ""
    echo "This will start a web interface for correcting labels in the lookup table."
    echo "Corrections are saved separately and can be exported as a corrected lookup table."
    exit 1
fi

LOOKUP_FILE="$1"
PORT="${2:-5000}"

# Check if file exists
if [ ! -f "$LOOKUP_FILE" ]; then
    echo "Error: Lookup table file '$LOOKUP_FILE' not found."
    exit 1
fi

# Activate virtual environment
echo "🔒 Activating virtual environment..."
source $VENV_PATH

# Start the correction interface
echo "🚀 Starting lookup table correction interface..."
echo "📁 Lookup table: $LOOKUP_FILE"
echo "🌐 Interface will be available at: http://127.0.0.1:$PORT"
echo "💾 Corrections will be saved to: $(dirname "$LOOKUP_FILE")/lookup_corrections.json"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python app_lookup.py --data "$LOOKUP_FILE" --port "$PORT"