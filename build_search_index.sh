#!/bin/bash

echo "🔍 Building search index..."

# Run the Node script (make sure to chmod +x this .sh if needed)
node ./build_search_index.js

echo "✅ Done! Files generated:"
echo " - frontend/search_index.json"
echo " - frontend/result_map.json"
