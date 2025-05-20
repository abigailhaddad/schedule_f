#!/bin/bash
# This script finds the most recent data.json file from the results directory
# and copies it to the frontend folder as data.json

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

# Create the results directory if it doesn't exist
mkdir -p results

# Create the frontend directory if it doesn't exist
mkdir -p frontend

# Find all results directories sorted by most recent first
ALL_DIRS=$(find ./results -maxdepth 1 -type d -name "results_*" | sort -r)

if [ -z "$ALL_DIRS" ]; then
  echo "Error: No results directories found."
  exit 1
fi

# Iterate through directories until we find one with data.json
DATA_FOUND=false
for DIR in $ALL_DIRS; do
  if [ -f "$DIR/data.json" ]; then
    echo "Found data.json in $DIR"
    cp "$DIR/data.json" "./frontend/data.json"
    echo "Successfully copied data.json from $DIR to the frontend directory."
    echo "Timestamp: $(date)"
    DATA_FOUND=true
    break
  fi
done

# Check if we found a data.json file
if [ "$DATA_FOUND" = false ]; then
  echo "Error: No data.json file found in any results directory."
  exit 1
fi