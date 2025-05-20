#!/bin/bash

SESSION_NAME="schedule_f_analysis"
PYTHON_SCRIPT="backend/pipeline.py"
BASE_RESULTS_DIR="results"
BATCH_SIZE=10  # Number of comments to process in parallel
VENV_PATH="./myenv/bin/activate"  # adjust path if needed

# Create results dir if it doesn't exist
mkdir -p "$BASE_RESULTS_DIR"

# Create a new timestamped results directory
TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
RESULTS_DIR="$BASE_RESULTS_DIR/results_$TIMESTAMP"
mkdir -p "$RESULTS_DIR"
echo "Using results directory: $RESULTS_DIR"

# Set up input file
RAW_DATA_FILE="$RESULTS_DIR/raw_data.json"

# Look for input files in order of preference
if [ -f "comments.json" ]; then
    cp comments.json "$RAW_DATA_FILE"
    echo "Copied comments.json to $RAW_DATA_FILE"
elif [ -f "raw_data.json" ]; then
    cp raw_data.json "$RAW_DATA_FILE"
    echo "Copied raw_data.json to $RAW_DATA_FILE"
elif [ -f "comments.csv" ]; then
    echo "Found comments.csv file, will use this as input"
    # Will set up pipeline to read from CSV instead of creating empty file
    CSV_FILE="comments.csv"
else
    echo "Warning: No input data found. Creating empty file."
    echo "[]" > "$RAW_DATA_FILE"
fi

# Create log file
LOG_FILE="$RESULTS_DIR/analyze.log"
touch "$LOG_FILE"

# Kill existing session if it exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$SESSION_NAME"
fi

# Create tmux session
echo "⚙️  Starting tmux session: $SESSION_NAME"
tmux new-session -d -s "$SESSION_NAME"

# Use heredoc style to ensure all commands are properly executed
tmux send-keys -t "$SESSION_NAME" "
echo '🔒 Activating virtualenv...'
source $VENV_PATH
echo '🚀 Running analysis...'
echo 'Python script: $PYTHON_SCRIPT'
echo 'Input file: $RAW_DATA_FILE'
echo 'Batch size: $BATCH_SIZE'

export PYTHONPATH=\$PYTHONPATH:\$(pwd)

# Run Python with unbuffered output
if [ -n "$CSV_FILE" ]; then
  # Use CSV file as input
  python -u $PYTHON_SCRIPT \\
    --csv_file "$CSV_FILE" \\
    --output_dir "$RESULTS_DIR" \\
    | tee $LOG_FILE
else
  # Use JSON file as input
  python -u $PYTHON_SCRIPT \\
    --input $RAW_DATA_FILE \\
    | tee $LOG_FILE
fi

echo '✅ Analysis finished. Log saved to $LOG_FILE'
" C-m

echo ""
echo "🚀 Analysis started in tmux session: $SESSION_NAME"
echo "📂 Results directory: $RESULTS_DIR"
echo "📺 To view logs: tail -f $LOG_FILE"
echo "📺 To view session: tmux attach -t $SESSION_NAME"
echo "🧼 To stop: tmux kill-session -t $SESSION_NAME"