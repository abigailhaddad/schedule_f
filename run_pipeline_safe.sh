#!/bin/bash

SESSION_NAME="schedule_f_pipeline"
PYTHON_SCRIPT="pipeline.py"
BASE_RESULTS_DIR="results"
TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
RESULTS_DIR="$BASE_RESULTS_DIR/results_$TIMESTAMP"
LOG_FILE="$RESULTS_DIR/pipeline.log"
VENV_PATH="./myenv/bin/activate"  # adjust path if needed

mkdir -p "$RESULTS_DIR"

echo "⚙️  Starting tmux session: $SESSION_NAME"
tmux new-session -d -s "$SESSION_NAME"

tmux send-keys -t "$SESSION_NAME" "
echo '🔒 Activating virtualenv...';
source $VENV_PATH;
echo '🚀 Running pipeline with caffeinate and logging...';
caffeinate -i python3 $PYTHON_SCRIPT --resume --base-dir $BASE_RESULTS_DIR 2>&1 | tee $LOG_FILE
echo '✅ Pipeline finished. Log saved to $LOG_FILE'
" C-m

echo ""
echo "🚀 Pipeline started in tmux session: $SESSION_NAME"
echo "📂 Logs will be saved to: $LOG_FILE"
echo "📺 To view:     tmux attach -t $SESSION_NAME"
echo "🚪 To detach:   Ctrl+B then D"
echo "🧼 To stop:     tmux kill-session -t $SESSION_NAME"
