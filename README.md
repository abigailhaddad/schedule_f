# Regulatory Comments Fetcher and Analyzer

This project provides tools to fetch and analyze public comments on regulatory proposals from regulations.gov.

## Components

- **fetch_comments.py**: Fetches comments from regulations.gov API
- **analyze_comments.py**: Analyzes comments using LiteLLM (with OpenAI models)
- **verify_quotes.py**: Verifies if extracted quotes are present in original comments
- **pipeline.py**: Coordinates the fetching and analysis process

## Setup

1. Create a virtual environment:
   ```
   python -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate
   ```

2. Install requirements:
   ```
   pip install requests tqdm python-dotenv litellm pydantic PyPDF2
   ```

3. Set up API keys:
   - Create a `.env` file in the project root
   - Add your API keys:
     ```
     REGS_API_KEY=your_regulations_gov_api_key
     OPENAI_API_KEY=your_openai_api_key
     ```

## Usage

### Full Pipeline

To run the complete pipeline (fetch comments and analyze them):

```
python pipeline.py
```

This will:
1. Create a timestamped directory in the `results` folder
2. Fetch comments and save them as `raw_data.json`
3. Analyze the comments and save results as `data.json`

### Fetch Only

To only fetch comments:

```
python pipeline.py --fetch-only
```

This creates a new timestamped directory with `raw_data.json`.

### Analyze Only

To analyze the most recently fetched comments:

```
python pipeline.py --analyze-only
```

This finds the most recent timestamped directory containing `raw_data.json` and adds `data.json` to it.

### Running Components Independently

You can also run the individual scripts directly:

- **fetch_comments.py**: Creates a timestamped directory in `results` and saves `raw_data.json`
  ```
  python fetch_comments.py [--document_id ID] [--limit N] [--api_key KEY] [--no-attachments]
  ```

- **analyze_comments.py**: Finds most recent `raw_data.json` and saves analysis as `data.json` in the same directory
  ```
  python analyze_comments.py [--input FILE] [--top_n N] [--model MODEL] [--api_key KEY]
  ```

- **verify_quotes.py**: Verifies if quotes in the analysis are present in the original comments
  ```
  python verify_quotes.py [--results_dir DIR]
  ```

- **copy_latest_data.sh**: Copies the most recent data.json to the root directory
  ```
  ./copy_latest_data.sh
  ```

## Command-Line Options

### Pipeline Options

```
python pipeline.py --help
```

Options include:
- `--fetch-only`: Only fetch comments
- `--analyze-only`: Only analyze most recent comments
- `--base-dir`: Base directory for results (default: 'results')
- `--document-id`: Document ID to fetch comments for
- `--limit`: Limit number of comments to fetch
- `--no-attachments`: Skip downloading and processing attachments
- `--top-n`: Analyze only the top N comments
- `--model`: Model to use for analysis
- `--regs-api-key`: API key for regulations.gov
- `--openai-api-key`: API key for OpenAI

## Results

Results are organized in timestamped directories within the `results` folder:

```
results/
  results_20250519_123045/
    raw_data.json  # Raw fetched comments
    data.json      # Analysis results
```

Each directory contains:
- `raw_data.json`: Raw comments fetched from regulations.gov
- `data.json`: Analysis of the comments as a flat list of objects with properties:
  - id, title, category, agencyId, comment, original_comment, has_attachments, link, stance, key_quote, rationale, themes
  - The themes field is a comma-separated string of detected themes
  - The comment field includes both the original comment and any text extracted from attachments
  - The original_comment field contains just the comment without attachment text
  - The has_attachments field indicates if the comment had attached documents
  - The link field is a human-readable URL to the comment on regulations.gov
- `attachments/`: Directory containing downloaded attachments and extracted text
- `summary.json`: Aggregate statistics about the analysis results (for reference only)
- `quote_verification.txt`: Human-readable report on quote verification results
- `quote_verification.json`: Machine-readable data about verified quotes

## License

MIT