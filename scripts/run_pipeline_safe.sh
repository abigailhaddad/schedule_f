#!/bin/bash

SESSION_NAME="schedule_f_analysis"
BASE_RESULTS_DIR="../results"
VENV_PATH="../myenv/bin/activate"

echo "🚀 Schedule F Comment Analysis Pipeline"
echo "======================================"
echo ""

# Function to prompt for yes/no input
ask_yes_no() {
    local prompt="$1"
    local default="$2"
    local response
    
    while true; do
        if [ "$default" = "y" ]; then
            echo -n "$prompt [Y/n]: "
        else
            echo -n "$prompt [y/N]: "
        fi
        read response
        
        # Use default if empty
        if [ -z "$response" ]; then
            response="$default"
        fi
        
        case "$response" in
            [Yy]|[Yy][Ee][Ss]) return 0 ;;
            [Nn]|[Nn][Oo]) return 1 ;;
            *) echo "Please answer yes or no." ;;
        esac
    done
}

# Function to prompt for input with default
ask_input() {
    local prompt="$1"
    local default="$2"
    local response
    
    if [ -n "$default" ]; then
        echo -n "$prompt [$default]: "
    else
        echo -n "$prompt: "
    fi
    read response
    
    if [ -z "$response" ] && [ -n "$default" ]; then
        response="$default"
    fi
    
    echo "$response"
}

# Ask about pipeline mode
echo "1. Pipeline Mode"
echo "=================="
if ask_yes_no "Are you resuming from existing files (vs starting fresh)" "n"; then
    USE_RESUME=true
    PYTHON_SCRIPT="../backend/resume_pipeline.py"
    echo "✓ Using resume pipeline"
    echo ""
    
    # Ask about existing files
    echo "2. Existing Files (for resume mode)"
    echo "==================================="
    RAW_DATA_FILE=$(ask_input "Raw data file path" "data/raw_data.json")
    LOOKUP_TABLE_FILE=$(ask_input "Lookup table file path" "data/lookup_table.json")
    
    # Validate files exist
    if [ ! -f "../$RAW_DATA_FILE" ]; then
        echo "Error: Raw data file not found: ../$RAW_DATA_FILE"
        exit 1
    fi
    if [ ! -f "../$LOOKUP_TABLE_FILE" ]; then
        echo "Error: Lookup table file not found: ../$LOOKUP_TABLE_FILE"
        exit 1
    fi
    
    RESUME_ARGS="--raw_data $RAW_DATA_FILE --lookup_table $LOOKUP_TABLE_FILE"
else
    USE_RESUME=false
    PYTHON_SCRIPT="../backend/pipeline.py"
    echo "✓ Using fresh pipeline"
    RESUME_ARGS=""
fi

echo ""

# Ask about CSV file
echo "3. Input Data"
echo "============="
CSV_FILE=$(ask_input "CSV file path" "comments.csv")

# Validate CSV exists
if [ ! -f "../$CSV_FILE" ]; then
    echo "Error: CSV file not found: ../$CSV_FILE"
    exit 1
fi

echo ""

# Ask about output directory
echo "4. Output Directory"
echo "==================="
if ask_yes_no "Use timestamped output directory" "y"; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    OUTPUT_DIR="$BASE_RESULTS_DIR/results_$TIMESTAMP"
else
    OUTPUT_DIR=$(ask_input "Custom output directory" "$BASE_RESULTS_DIR/custom")
fi

echo ""

# Ask about truncation
echo "5. Text Processing"
echo "=================="
TRUNCATE_ARGS=""
if ask_yes_no "Truncate text for analysis" "n"; then
    TRUNCATE_CHARS=$(ask_input "Truncation length (characters)" "1000")
    if [[ "$TRUNCATE_CHARS" =~ ^[0-9]+$ ]]; then
        TRUNCATE_ARGS="--truncate $TRUNCATE_CHARS"
    else
        echo "Error: Truncation length must be a number"
        exit 1
    fi
fi

echo ""

# Ask about analysis steps
echo "6. Processing Steps"
echo "==================="
SKIP_ARGS=""
if ask_yes_no "Skip LLM analysis (data processing only)" "n"; then
    SKIP_ARGS="$SKIP_ARGS --skip_analysis"
fi

if ask_yes_no "Skip clustering analysis" "n"; then
    SKIP_ARGS="$SKIP_ARGS --skip_clustering"
fi

if [ "$USE_RESUME" = true ] && ask_yes_no "Run quote verification" "n"; then
    SKIP_ARGS="$SKIP_ARGS --verify_quotes"
fi

echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Build pipeline arguments
PIPELINE_ARGS="--csv $CSV_FILE --output_dir $OUTPUT_DIR $RESUME_ARGS $TRUNCATE_ARGS $SKIP_ARGS"

echo "🔧 Final Configuration"
echo "======================"
echo "   Script: $PYTHON_SCRIPT"
echo "   CSV file: ../$CSV_FILE"
echo "   Output directory: $OUTPUT_DIR"
if [ "$USE_RESUME" = true ]; then
    echo "   Raw data: ../$RAW_DATA_FILE"
    echo "   Lookup table: ../$LOOKUP_TABLE_FILE"
    echo "   Mode: Resume (incremental updates)"
else
    echo "   Mode: Fresh analysis"
fi
if [ -n "$TRUNCATE_ARGS" ]; then
    echo "   Truncation: ${TRUNCATE_ARGS#--truncate } characters"
fi
if [[ "$SKIP_ARGS" == *"--skip_analysis"* ]]; then
    echo "   LLM Analysis: SKIPPED"
fi
if [[ "$SKIP_ARGS" == *"--skip_clustering"* ]]; then
    echo "   Clustering: SKIPPED"
fi
if [[ "$SKIP_ARGS" == *"--verify_quotes"* ]]; then
    echo "   Quote Verification: ENABLED"
fi
echo ""

# Final confirmation
if ! ask_yes_no "Start pipeline with these settings" "y"; then
    echo "Cancelled."
    exit 0
fi

echo ""

# Kill existing session if it exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "🔄 Killing existing tmux session..."
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

# Run Python with unbuffered output
python -u $PYTHON_SCRIPT $PIPELINE_ARGS | tee $OUTPUT_DIR/pipeline.log

echo '✅ Analysis finished. Log saved to $OUTPUT_DIR/pipeline.log'
echo '📁 Results saved to: $OUTPUT_DIR'
" C-m

echo ""
echo "🚀 Analysis started in tmux session: $SESSION_NAME"
echo "📺 To view logs: tail -f $OUTPUT_DIR/pipeline.log"
echo "📺 To view session: tmux attach -t $SESSION_NAME"
echo "🧼 To stop: tmux kill-session -t $SESSION_NAME"
echo "📁 Results will be saved to: $OUTPUT_DIR"