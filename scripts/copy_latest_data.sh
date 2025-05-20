#!/bin/bash
# Copy latest data files to frontend for testing

# Get project root directory
PROJECT_ROOT="$(dirname "$(dirname "$0")")"
RESULTS_DIR="$PROJECT_ROOT/data/results"
FRONTEND_DATA_DIR="$PROJECT_ROOT/frontend/public/data"

# Create frontend data directory if it doesn't exist
mkdir -p "$FRONTEND_DATA_DIR"

# Find most recent results directory
if [ -d "$RESULTS_DIR" ]; then
  LATEST_DIR=$(find "$RESULTS_DIR" -type d -name "results_*" | sort -r | head -n 1)
  
  if [ -n "$LATEST_DIR" ]; then
    echo "Found latest results directory: $LATEST_DIR"
    
    # Check for data.json
    DATA_JSON="$LATEST_DIR/data.json"
    if [ -f "$DATA_JSON" ]; then
      echo "Copying $DATA_JSON to frontend"
      cp "$DATA_JSON" "$FRONTEND_DATA_DIR/data.json"
      echo "Copied to $FRONTEND_DATA_DIR/data.json"
    else
      echo "Warning: data.json not found in $LATEST_DIR"
    fi
    
    # Check for search-index.json in frontend/public
    SEARCH_INDEX="$PROJECT_ROOT/frontend/public/search-index.json"
    if [ -f "$SEARCH_INDEX" ]; then
      echo "Copying search-index.json to frontend data directory"
      cp "$SEARCH_INDEX" "$FRONTEND_DATA_DIR/search-index.json"
      echo "Copied to $FRONTEND_DATA_DIR/search-index.json"
    else
      echo "Warning: search-index.json not found"
    fi
  else
    echo "No results directories found in $RESULTS_DIR"
  fi
else
  echo "Results directory not found: $RESULTS_DIR"
fi

# Also look in processed directory for analyzed comments
PROCESSED_DIR="$PROJECT_ROOT/data/processed"
if [ -d "$PROCESSED_DIR" ]; then
  LATEST_ANALYSIS=$(find "$PROCESSED_DIR" -name "comment_analysis_*.json" | sort -r | head -n 1)
  
  if [ -n "$LATEST_ANALYSIS" ] && [ ! -f "$FRONTEND_DATA_DIR/data.json" ]; then
    echo "No data.json found in results, but found analysis file: $LATEST_ANALYSIS"
    echo "Copying to frontend"
    cp "$LATEST_ANALYSIS" "$FRONTEND_DATA_DIR/data.json"
    echo "Copied to $FRONTEND_DATA_DIR/data.json"
    
    # Run build_search_index script to create search index
    echo "Building search index from $LATEST_ANALYSIS"
    "$PROJECT_ROOT/scripts/build_search_index.sh" "$LATEST_ANALYSIS"
  fi
fi

echo "Done!"
exit 0 