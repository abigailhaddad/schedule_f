/**
 * Build Search Index from Analyzed Comments
 * 
 * This script builds a search index from analyzed comments for use in the frontend.
 * It creates a JSON file with indexed comments for full-text search.
 * 
 * Usage: node scripts/build_search_index.js [input_file]
 */

const fs = require('fs');
const path = require('path');

// Get command line arguments
const inputFile = process.argv[2];

// If no input file provided, try to find the most recent data.json
let dataPath = inputFile;
if (!dataPath) {
  // Try to find the most recent data.json
  const projectRoot = path.resolve(__dirname, '..');
  const resultsDir = path.join(projectRoot, 'data', 'results');
  
  try {
    if (fs.existsSync(resultsDir)) {
      // Find most recent results directory
      const resultDirs = fs.readdirSync(resultsDir)
        .filter(dir => dir.startsWith('results_'))
        .map(dir => path.join(resultsDir, dir))
        .filter(dir => fs.statSync(dir).isDirectory())
        .sort((a, b) => fs.statSync(b).mtime.getTime() - fs.statSync(a).mtime.getTime());
      
      if (resultDirs.length > 0) {
        const latestDir = resultDirs[0];
        const dataJsonPath = path.join(latestDir, 'data.json');
        
        if (fs.existsSync(dataJsonPath)) {
          dataPath = dataJsonPath;
          console.log(`Auto-detected most recent data file: ${dataPath}`);
        }
      }
    }
  } catch (error) {
    console.error('Error finding most recent data file:', error.message);
  }
  
  // If still not found, use default
  if (!dataPath) {
    dataPath = path.join(projectRoot, 'frontend', 'public', 'data', 'data.json');
    console.log(`Using default data file: ${dataPath}`);
  }
}

// Check if data file exists
if (!fs.existsSync(dataPath)) {
  console.error(`Error: Input file ${dataPath} not found`);
  process.exit(1);
}

console.log(`Building search index from: ${dataPath}`);

// Load data
let data;
try {
  const rawData = fs.readFileSync(dataPath, 'utf8');
  data = JSON.parse(rawData);
  console.log(`Loaded ${data.length} comments`);
} catch (error) {
  console.error('Error loading data:', error.message);
  process.exit(1);
}

// Build search index
const searchIndex = [];

for (const comment of data) {
  // Skip comments with errors or missing data
  if (!comment.id || !comment.stance || comment.error) {
    continue;
  }
  
  // Create search document
  const searchDoc = {
    id: comment.id,
    title: comment.title || '',
    quote: comment.key_quote || '',
    stance: comment.stance || '',
    themes: comment.themes || '',
    agency: comment.agencyId || '',
    comment: comment.comment || '',
    link: comment.link || `https://www.regulations.gov/comment/${comment.id}`,
    has_attachments: !!comment.has_attachments
  };
  
  searchIndex.push(searchDoc);
}

console.log(`Created search index with ${searchIndex.length} entries`);

// Save search index
const projectRoot = path.resolve(__dirname, '..');
const outputPath = path.join(projectRoot, 'frontend', 'public', 'search-index.json');

try {
  fs.writeFileSync(outputPath, JSON.stringify(searchIndex));
  console.log(`Search index saved to: ${outputPath}`);
} catch (error) {
  console.error('Error saving search index:', error.message);
  process.exit(1);
}

console.log('Search index built successfully!');
process.exit(0); 