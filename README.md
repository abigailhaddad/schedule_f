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

#### Fresh Analysis (from scratch)
```bash
# Run complete pipeline on CSV file
python -m backend.pipeline --csv comments.csv --output_dir results_2024

# With options
python -m backend.pipeline --csv comments.csv --output_dir results_2024 \
  --model gpt-4o-mini --truncate 1000 --skip-clustering
```

#### Incremental Updates (resume)
```bash
# Resume from existing data
python -m backend.resume_pipeline --csv comments.csv \
  --raw_data data/raw_data.json --lookup_table data/lookup_table.json \
  --truncate 1003

# Skip analysis (just fetch new comments)
python -m backend.resume_pipeline --csv comments.csv \
  --raw_data data/raw_data.json --lookup_table data/lookup_table.json \
  --skip-analysis
```

#### Individual Analysis Steps
```bash
# Just create lookup table
python -m backend.analysis.create_lookup_table --input raw_data.json \
  --output lookup_table.json --truncate 1000

# Just run LLM analysis
python -m backend.analysis.analyze_lookup_table --input lookup_table.json

# Just run clustering
python -m backend.analysis.semantic_lookup --input lookup_table.json
```

### Pipeline Options

#### Common Options
- `--csv comments.csv` - Input CSV file with comment data
- `--output_dir results/` - Output directory for results
- `--model gpt-4o-mini` - LLM model for analysis (default: gpt-4o-mini)
- `--truncate 1000` - Truncate text to N characters for analysis
- `--limit 100` - Process only first N comments (for testing)

#### Fresh Pipeline Options
- `--skip-analysis` - Skip LLM analysis (only fetch and deduplicate)
- `--skip-clustering` - Skip semantic clustering step

#### Resume Pipeline Options  
- `--raw_data path/to/raw_data.json` - Existing raw data file
- `--lookup_table path/to/lookup_table.json` - Existing lookup table
- `--skip-analysis` - Only fetch new comments (no LLM analysis)
- `--skip-clustering` - Skip clustering step

**Note**: Quote verification runs automatically after LLM analysis to verify extracted quotes exist in original text.

### Manual Corrections

After running the pipeline, you can manually correct analysis labels:

```bash
# Start the correction interface
cd correct_labels
./run_lookup_corrections.sh

# This will:
# 1. Launch a web interface at http://localhost:5000
# 2. Allow you to review and edit stance/themes/quotes
# 3. Save corrections back to the lookup table
```

### Frontend Development

```bash
# Start development server
cd frontend
npm run dev
```

## Architecture

This project has three main components:

1. **Data Fetching**: Python scripts to fetch comments and attachments from regulations.gov API
2. **Text Extraction**: Smart extraction from PDFs, DOCX, images with Gemini API fallback  
3. **Analysis**: Python scripts using LLMs to analyze deduplicated comment text
4. **Clustering**: Semantic clustering to group similar comments
5. **Frontend**: Next.js application to view and search comments

### Data Flow

1. **Fetch**: Comments from regulations.gov → `raw_data.json` (all comments with metadata)
2. **Deduplicate**: Create `lookup_table.json` with unique text patterns
3. **Analyze**: LLM analysis adds stance, themes, quotes directly to `lookup_table.json`
4. **Cluster**: Semantic clustering adds cluster information to `lookup_table.json`
5. **Verify**: Quote verification creates separate verification reports
6. **Merge**: (Optional) Combine raw + lookup → `data.json` for legacy frontend compatibility
7. **View**: Frontend displays merged data

### Key Files

- **`raw_data.json`**: All fetched comments with full metadata and attachment text
- **`lookup_table.json`**: Deduplicated text patterns with complete analysis (stance, themes, quotes, clusters)
- **`lookup_table_quote_verification.json`**: Quote verification results
- **`data.json`**: (Optional) Final merged dataset for legacy frontend compatibility

### Deduplication Strategy

The system reduces redundant LLM analysis significantly:
- Comments with identical/similar text (after normalization) share one lookup entry
- Each lookup entry has a `comment_ids` array listing all matching comments  
- Analysis (expensive LLM calls) only happens once per unique text pattern
- Typical efficiency: Analyze ~21,000 unique patterns instead of ~28,000 total comments
- Speed improvement: ~25% reduction in API calls and analysis time

## Pipeline Details

### Fresh Pipeline (`pipeline.py`)
1. Fetches all comments from CSV → `raw_data.json`
2. Downloads and extracts attachments (PDF, DOCX, images)
3. Creates deduplicated `lookup_table.json` from scratch
4. Runs LLM analysis on unique text patterns (updates `lookup_table.json` in place)
5. Performs semantic clustering (adds cluster data to `lookup_table.json`)
6. Runs quote verification and creates verification reports
7. Outputs to specified directory

### Resume Pipeline (`resume_pipeline.py`)
1. Compares CSV with existing `raw_data.json` to find new comments
2. Fetches only new comments and appends to `raw_data.json`
3. Downloads attachments for new comments
4. Updates existing `lookup_table.json` with new text patterns
5. Preserves all existing analysis and only analyzes new patterns
6. Runs clustering and verification on the complete dataset
7. Maintains perfect consistency with existing deduplication

### Output Structure

Each pipeline run creates output in the specified directory containing:
- `raw_data.json` - All comments with attachment text
- `lookup_table.json` - Deduplicated entries with complete analysis (stance, themes, quotes, clusters)
- `lookup_table_quote_verification.json` - Quote verification results
- `lookup_table_quote_verification.txt` - Human-readable verification report
- `pipeline.log` or `resume_pipeline.log` - Execution log
- `attachments/` - Downloaded attachment files with extracted text
- `clustering_*/` - Clustering visualizations and reports (if clustering enabled)

## License

MIT