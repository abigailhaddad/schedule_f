# Schedule F Comments Analysis

A tool for analyzing public comments on the proposed "Schedule F" rule.

## Project Structure

```
schedule_f/
  ├── backend/             # Backend Python code
  │   ├── fetch/           # Code for fetching comments from regulations.gov
  │   ├── analysis/        # Code for analyzing comments with LLMs
  │   ├── utils/           # Shared utilities
  │   └── pipeline.py      # Full data pipeline
  ├── data/                # Data storage
  │   ├── raw/             # Raw data from regulations.gov
  │   ├── processed/       # Processed analysis results
  │   └── results/         # Pipeline results (timestamped directories)
  ├── frontend/            # Next.js frontend for viewing comments
  ├── scripts/             # Various utility scripts
  └── README.md            # This file
```

## Setup

### Install Requirements

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
```

### Environment Variables

Create a `.env` file in the project root with:

```
# For fetching comments
REGS_API_KEY=your_regulations_gov_api_key

# For analyzing comments
OPENAI_API_KEY=your_openai_api_key
```

## Usage

### Fetching Comments

```bash
# Fetch all comments
python -m backend.fetch.fetch_comments

# Fetch with a limit (useful for testing)
python -m backend.fetch.fetch_comments --limit 10
```

### Analyzing Comments

```bash
# Analyze the most recent fetched comments
python -m backend.analysis.analyze_comments

# Analyze with a specific model
python -m backend.analysis.analyze_comments --model gpt-4o
```

### Full Pipeline

```bash
# Run the complete pipeline interactively
./scripts/run_pipeline_safe.sh

# Deploy results to data folder and optionally push to git
./scripts/deploy_results.sh
```

### Verify Quotes

```bash
# Verify that extracted quotes appear in the original comments
python -m backend.analysis.verify_quotes
```

### Frontend Development

```bash
# Start development server
cd frontend
npm run dev
```

## Common Tasks

### Copy Latest Data to Frontend

To quickly view the latest data in the frontend:

```bash
./scripts/copy_latest_data.sh
```

### Building Search Index

If you need to rebuild the search index separately:

```bash
./scripts/build_search_index.sh path/to/data.json
```

## Architecture

This project has three main components:

1. **Data Fetching**: Python scripts to fetch comments from regulations.gov API
2. **Analysis**: Python scripts using LLMs to analyze comments 
3. **Frontend**: Next.js application to view and search comments

The data flows through the pipeline as follows:

1. Fetch comments → `raw_data.json`
2. Analyze comments → `lookup_table.json` (deduplicated) + `raw_data.json` (all comments)
3. Build search index → `search-index.json`
4. View in frontend

### Lookup Table Architecture

The system uses a deduplication strategy where:
- **`raw_data.json`**: Contains all individual comments with references to lookup entries
- **`lookup_table.json`**: Contains unique text patterns with analysis results
- This reduces redundant analysis by ~27% while maintaining comment-level tracking

### Manual Label Correction

To manually correct analysis labels:

```bash
# Start the label correction interface
cd correct_labels
./run_lookup_corrections.sh

# Or run directly
python app_lookup.py
```

The correction interface allows you to:
- Review and edit analysis labels for lookup table entries
- Push corrections back to the original lookup table file
- Automatic backup creation before updates

## License

MIT