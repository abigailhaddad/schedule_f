#!/bin/bash
# Build search index from analyzed comments

# Get the input file from command line argument or use default
INPUT_FILE=$1
if [ -z "$INPUT_FILE" ]; then
  # Try to find the most recent data.json file
  PROJECT_ROOT="$(dirname "$(dirname "$0")")"
  RESULTS_DIR="$PROJECT_ROOT/data/results"
  
  if [ -d "$RESULTS_DIR" ]; then
    # Find most recent results directory
    LATEST_DIR=$(find "$RESULTS_DIR" -type d -name "results_*" | sort -r | head -n 1)
    
    if [ -n "$LATEST_DIR" ]; then
      INPUT_FILE="$LATEST_DIR/data.json"
      echo "Auto-detected most recent data file: $INPUT_FILE"
    fi
  fi
  
  # If still not found, use default
  if [ -z "$INPUT_FILE" ]; then
    INPUT_FILE="$PROJECT_ROOT/frontend/public/data/data.json"
    echo "Using default data file: $INPUT_FILE"
  fi
fi

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
  echo "Error: Input file $INPUT_FILE not found"
  exit 1
fi

echo "Building search index from: $INPUT_FILE"

# Run the Node.js script to build the search index
PROJECT_ROOT="$(dirname "$(dirname "$0")")"
NODE_SCRIPT="$PROJECT_ROOT/scripts/build_search_index.js"

# Check if Node.js script exists
if [ ! -f "$NODE_SCRIPT" ]; then
  # Try to find it in the original location
  NODE_SCRIPT="$PROJECT_ROOT/build_search_index.js"
  
  if [ ! -f "$NODE_SCRIPT" ]; then
    echo "Error: build_search_index.js not found"
    exit 1
  fi
  
  # Copy it to the scripts directory for future use
  mkdir -p "$PROJECT_ROOT/scripts"
  cp "$NODE_SCRIPT" "$PROJECT_ROOT/scripts/"
  NODE_SCRIPT="$PROJECT_ROOT/scripts/build_search_index.js"
  echo "Copied build_search_index.js to scripts directory"
fi

# Make sure frontend/public/data directory exists
mkdir -p "$PROJECT_ROOT/frontend/public/data"

# Run the Node.js script
node "$NODE_SCRIPT" "$INPUT_FILE"

# Check if successful
if [ $? -eq 0 ]; then
  echo "Search index built successfully"
else
  echo "Error building search index"
  exit 1
fi

# Copy the search index to the frontend public directory if needed
SEARCH_INDEX="$PROJECT_ROOT/frontend/public/search-index.json"
FRONTEND_DATA_DIR="$PROJECT_ROOT/frontend/public/data"

if [ -f "$SEARCH_INDEX" ]; then
  cp "$SEARCH_INDEX" "$FRONTEND_DATA_DIR/"
  echo "Copied search index to $FRONTEND_DATA_DIR/"
fi

echo "Done!"
exit 0 