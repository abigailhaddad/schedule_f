# Label Correction Interface

A simple web-based interface for reviewing and correcting comment stance labels.

## Features

- **Review Comments**: View comments with their current stance labels
- **Correct Labels**: Click buttons to change labels (For, Against, Neutral/Unclear)
- **Filter by Stance**: Only show comments with specific stances
- **Filter by Status**: Show only corrected/uncorrected comments
- **Persistent Corrections**: All corrections are saved to `corrections.json`
- **No Duplicates**: Won't ask you to review comments you've already corrected

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the interface:
   ```bash
   python app.py --data path/to/your/data.json
   ```

3. Open your browser to: http://127.0.0.1:5000

## Usage

### Basic Usage
```bash
python app.py --data /path/to/results/data.json
```

### Custom Port/Host
```bash
python app.py --data /path/to/results/data.json --port 8080 --host 0.0.0.0
```

### Command Line Options
- `--data`: Path to the data.json file to review (required)
- `--port`: Port to run on (default: 5000)
- `--host`: Host to run on (default: 127.0.0.1)

## Data Files

- **Input**: `data.json` - The analyzed comments from your pipeline
- **Output**: `corrections.json` - Stores all your label corrections

The corrections file is created in the same directory as your data.json file.

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