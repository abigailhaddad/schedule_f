#!/bin/bash

SESSION_NAME="schedule_f_analysis"
PYTHON_SCRIPT="backend/pipeline.py"
BASE_RESULTS_DIR="results"
BATCH_SIZE=10  # Number of comments to process in parallel
VENV_PATH="./myenv/bin/activate"  # adjust path if needed

# Parse arguments (supports both positional and flag-style)
SPECIFIC_RESULTS_DIR=""
TRUNCATE_CHARS=""
LIMIT_CHARS=""

# Process arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --truncate)
            if [ -n "$2" ] && [ "$2" -eq "$2" ] 2>/dev/null; then
                TRUNCATE_CHARS="--truncate $2"
                echo "Will truncate comments to $2 characters for analysis"
                shift 2
            else
                echo "Error: --truncate requires a numeric value"
                exit 1
            fi
            ;;
        --limit)
            if [ -n "$2" ] && [ "$2" -eq "$2" ] 2>/dev/null; then
                LIMIT_CHARS="--limit $2"
                echo "Will limit processing to $2 comments"
                shift 2
            else
                echo "Error: --limit requires a numeric value"
                exit 1
            fi
            ;;
        *)
            # If it's a directory and no specific dir set yet, use as results dir
            if [ -d "$1" ] && [ -z "$SPECIFIC_RESULTS_DIR" ]; then
                SPECIFIC_RESULTS_DIR="$1"
                echo "Using specified results directory: $SPECIFIC_RESULTS_DIR"
            # Otherwise check if it's a numeric value for backward compatibility
            elif [ -z "$SPECIFIC_RESULTS_DIR" ] && [ -z "$TRUNCATE_CHARS" ] && [ "$1" -eq "$1" ] 2>/dev/null; then
                TRUNCATE_CHARS="--truncate $1"
                echo "Will truncate comments to $1 characters for analysis"
            elif [ -z "$SPECIFIC_RESULTS_DIR" ] && [ -n "$TRUNCATE_CHARS" ] && [ -z "$LIMIT_CHARS" ] && [ "$1" -eq "$1" ] 2>/dev/null; then
                LIMIT_CHARS="--limit $1"
                echo "Will limit processing to $1 comments"
            else
                echo "Error: Unknown argument or invalid directory: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Create results dir if it doesn't exist
mkdir -p "$BASE_RESULTS_DIR"

# Look for most recent results directory to suggest as default output
LATEST_RESULTS=$(find "$BASE_RESULTS_DIR" -name "results_*" -type d | sort -r | head -1)

# Check for input files to set up pipeline arguments
PIPELINE_ARGS=""

if [ -n "$SPECIFIC_RESULTS_DIR" ] && [ -f "$SPECIFIC_RESULTS_DIR/raw_data.json" ]; then
    echo "Using existing results directory with raw_data.json: $SPECIFIC_RESULTS_DIR"
    echo "Will skip fetch and attachments (assuming already processed)"
    PIPELINE_ARGS="--output_dir $SPECIFIC_RESULTS_DIR --skip_fetch --skip_attachments $TRUNCATE_CHARS $LIMIT_CHARS"
elif [ -f "comments.csv" ]; then
    echo "Found comments.csv file, will use this as input"
    PIPELINE_ARGS="--csv_file comments.csv $TRUNCATE_CHARS $LIMIT_CHARS"
elif [ -n "$LATEST_RESULTS" ] && [ -f "$LATEST_RESULTS/raw_data.json" ]; then
    echo "Found recent results directory with data: $LATEST_RESULTS"
    echo "Will skip fetch and attachments (assuming already processed)"
    PIPELINE_ARGS="--output_dir $LATEST_RESULTS --skip_fetch --skip_attachments $TRUNCATE_CHARS $LIMIT_CHARS"
elif [ -f "comments.json" ]; then
    echo "Found comments.json file, will use this as input"
    PIPELINE_ARGS="--input_file comments.json"
elif [ -f "raw_data.json" ]; then
    echo "Found raw_data.json file, will use this as input"
    PIPELINE_ARGS="--input_file raw_data.json"
else
    echo "No input data found. Pipeline will fetch from API."
fi

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
echo 'Pipeline args: $PIPELINE_ARGS'

export PYTHONPATH=\$PYTHONPATH:\$(pwd)

# Run Python with unbuffered output - let pipeline handle all prompting
python -u $PYTHON_SCRIPT $PIPELINE_ARGS | tee pipeline.log

echo '✅ Analysis finished. Log saved to pipeline.log'
" C-m

echo ""
echo "🚀 Analysis started in tmux session: $SESSION_NAME"
echo "📺 To view logs: tail -f pipeline.log"
echo "📺 To view session: tmux attach -t $SESSION_NAME"
echo "🧼 To stop: tmux kill-session -t $SESSION_NAME"