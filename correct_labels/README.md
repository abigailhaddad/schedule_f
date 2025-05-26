# Label Correction Interface

A web-based interface for reviewing and correcting stance labels in both individual comments and lookup tables.

## Two Interfaces Available

### 1. Lookup Table Correction (Recommended)
- **Works with**: `lookup_table_analyzed.json` files from the new pipeline
- **Benefits**: Review unique text patterns, high-impact corrections
- **Filter by comment count**: Focus on patterns affecting many comments
- **Export corrected table**: Ready to use in pipeline

### 2. Individual Comment Correction (Legacy)  
- **Works with**: `data.json` files from old pipeline
- **Use case**: Legacy data or individual comment review

## Features

- **Smart Filtering**: By stance, correction status, and comment count
- **High Impact**: Focus on patterns affecting the most comments
- **Persistent Corrections**: All corrections saved and tracked
- **Export Ready**: Generate corrected lookup tables for pipeline use
- **No Duplicates**: Won't ask you to review the same patterns twice

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Lookup Table Correction (Recommended)

1. **Easy Start**:
   ```bash
   ./run_lookup_corrections.sh path/to/lookup_table_analyzed.json
   ```

2. **Manual Start**:
   ```bash
   python app_lookup.py --data path/to/lookup_table_analyzed.json
   ```

3. **Custom Port**:
   ```bash
   ./run_lookup_corrections.sh path/to/lookup_table_analyzed.json 8000
   ```

### Individual Comment Correction (Legacy)

```bash
python app.py --data /path/to/results/data.json
```

### Command Line Options
- `--data`: Path to the lookup table or data file (required)
- `--port`: Port to run on (default: 5000)
- `--host`: Host to run on (default: 127.0.0.1)

## Data Files

### Lookup Table Workflow
- **Input**: `lookup_table_analyzed.json` - Deduplicated text patterns with analysis
- **Corrections**: `lookup_corrections.json` - Stores corrections by lookup_id
- **Output**: `lookup_table_analyzed_corrected.json` - Ready for pipeline use

### Legacy Workflow  
- **Input**: `data.json` - Individual analyzed comments
- **Output**: `corrections.json` - Stores corrections by comment_id

Correction files are created in the same directory as your input file.

## Interface Features

### Filtering
- **By Stance**: Filter to show only For/Against/Neutral comments
- **By Status**: Filter to show only corrected or uncorrected comments

### Correcting Labels
- Click the colored buttons to assign new labels
- Green "Mark as For" for support
- Red "Mark as Against" for opposition  
- Yellow "Mark as Neutral" for unclear/neutral
- Gray "Revert to Original" to undo corrections

### Visual Indicators
- Green left border = comment has been corrected
- Blue left border = original comment
- Badge shows current stance with color coding
- "✓ CORRECTED" indicator for corrected comments

## Data Format

The corrections.json file stores:
```json
{
  "comment_id": {
    "original_stance": "Against",
    "corrected_stance": "For", 
    "timestamp": "2025-05-24T10:15:30",
    "corrected_by": "user"
  }
}
```