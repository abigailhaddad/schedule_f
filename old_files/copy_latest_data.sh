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

# Find the most recent results directory
LATEST_DIR=$(find ./results -maxdepth 1 -type d -name "results_*" | sort -r | head -n 1)

if [ -z "$LATEST_DIR" ]; then
  echo "Error: No results directories found."
  exit 1
fi

# Check if data.json exists in the latest directory
if [ ! -f "$LATEST_DIR/data.json" ]; then
  echo "Error: data.json not found in $LATEST_DIR."
  exit 1
fi

# Copy the file to the frontend directory
cp "$LATEST_DIR/data.json" "./frontend/data.json"

echo "Successfully copied latest data.json from $LATEST_DIR to the frontend directory."
echo "Timestamp: $(date)"