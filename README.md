# Schedule F Comments Analysis

A tool for analyzing public comments on the proposed "Schedule F" rule.

## Project Structure

```
regs/
  ├── backend/             # Backend Python code
  │   ├── fetch/           # Code for fetching comments from regulations.gov
  │   ├── analysis/        # Code for analyzing comments with LLMs
  │   ├── utils/           # Shared utilities
  │   ├── pipeline.py      # Fresh analysis pipeline
  │   └── resume_pipeline.py # Incremental update pipeline
  ├── data/                # Current data files
  ├── results/             # Pipeline outputs (timestamped directories)
  ├── correct_labels/      # Manual correction interface
  ├── frontend/            # Next.js frontend for viewing comments
  ├── scripts/             # Utility scripts for running pipelines
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

### Running the Analysis Pipeline

The main workflow uses three scripts:

1. **Run the pipeline** (choose between fresh or incremental):
   ```bash
   # Interactive pipeline with guided options
   ./scripts/run_pipeline_safe.sh
   
   # Or command-line version for automation
   ./scripts/run_pipeline_args.sh [--resume] [--skip-analysis] [--skip-clustering]
   ```

2. **Copy results to data folder**:
   ```bash
   # Copies latest results to data/ and creates merged data.json
   ./scripts/copy_latest_data.sh
   ```

3. **Deploy to git** (optional):
   ```bash
   # Commit and push data files to git (data branch or current branch)
   ./scripts/deploy_results.sh
   ```

### Pipeline Options

- **Fresh pipeline**: Fetches all comments and analyzes from scratch
- **Resume pipeline**: Only fetches new comments and preserves existing analysis
- **Skip analysis**: Only fetch and deduplicate (no LLM calls)
- **Skip clustering**: Skip semantic clustering step

Note: Quote verification runs automatically after analysis to check if extracted quotes appear in the original text.

### Manual Corrections

After running the pipeline, you can manually correct analysis labels:

```bash
# Start the correction interface
cd correct_labels
./run_lookup_corrections.sh

# This will:
# 1. Launch a web interface at http://localhost:5000
# 2. Allow you to review and edit stance/themes/quotes
# 3. Save corrections to lookup_table_corrected.json
```

### Frontend Development

```bash
# Start development server
cd frontend
npm run dev
```

## Architecture

This project has three main components:

1. **Data Fetching**: Python scripts to fetch comments from regulations.gov API
2. **Analysis**: Python scripts using LLMs to analyze comments 
3. **Frontend**: Next.js application to view and search comments

### Data Flow

1. **Fetch**: Comments from regulations.gov → `raw_data.json` (all comments with metadata)
2. **Deduplicate**: Create `lookup_table.json` with unique text patterns
3. **Analyze**: LLM analysis adds stance, themes, quotes to lookup table
4. **Correct**: Manual corrections → `lookup_table_corrected.json`
5. **Merge**: Combine raw + corrected lookup → `data.json` (final dataset)
6. **View**: Frontend displays merged data

### Key Files

- **`raw_data.json`**: All fetched comments with full metadata
- **`lookup_table.json`**: Deduplicated text patterns for analysis
- **`lookup_table_corrected.json`**: Lookup table with manual corrections
- **`data.json`**: Final merged dataset for frontend (created by merge script)

### Deduplication Strategy

The system reduces redundant analysis by ~27%:
- Comments with identical/similar text share one lookup entry
- Each lookup entry has a `comment_ids` array listing all matching comments
- Analysis (LLM calls) only happens once per unique text pattern

## Pipeline Details

### Fresh Pipeline (`pipeline.py`)
1. Fetches all comments from CSV
2. Downloads attachments
3. Creates lookup table from scratch
4. Runs LLM analysis on all entries
5. Performs semantic clustering
6. Outputs to timestamped results folder

### Resume Pipeline (`resume_pipeline.py`)
1. Identifies new comments in CSV
2. Fetches only new comments
3. Updates existing lookup table
4. Preserves all existing analysis
5. Only analyzes truly new text patterns
6. Maintains consistent deduplication

### Output Structure

Each pipeline run creates a timestamped folder in `results/` containing:
- `raw_data.json` - All comments
- `lookup_table.json` - Deduplicated entries  
- `lookup_table_corrected.json` - With analysis
- `lookup_table_corrected_quote_verification.json` - Quote verification results
- `lookup_table_corrected_quote_verification.txt` - Human-readable report of quotes not found
- `pipeline.log` or `resume_pipeline.log` - Execution log
- `clustering_*/` - Clustering visualizations (if clustering enabled)

## License

MIT