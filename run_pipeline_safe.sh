#!/bin/bash

SESSION_NAME="schedule_f_analysis"
PYTHON_SCRIPT="backend/pipeline.py"
BASE_RESULTS_DIR="results"
BATCH_SIZE=10  # Number of comments to process in parallel
VENV_PATH="./myenv/bin/activate"  # adjust path if needed

# Create results dir if it doesn't exist
mkdir -p "$BASE_RESULTS_DIR"

# Look for most recent results directory to suggest as default output
LATEST_RESULTS=$(find "$BASE_RESULTS_DIR" -name "results_*" -type d | sort -r | head -1)

# Check for input files to set up pipeline arguments
PIPELINE_ARGS=""

if [ -f "comments.csv" ]; then
    echo "Found comments.csv file, will use this as input"
    PIPELINE_ARGS="--csv_file comments.csv"
elif [ -n "$LATEST_RESULTS" ] && [ -f "$LATEST_RESULTS/raw_data.json" ]; then
    echo "Found recent results directory with data: $LATEST_RESULTS"
    PIPELINE_ARGS="--output_dir $LATEST_RESULTS"
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