#!/bin/bash

SESSION_NAME="schedule_f_analysis"
PYTHON_SCRIPT="../backend/pipeline.py"  # Default to main pipeline
BASE_RESULTS_DIR="results"
VENV_PATH="../myenv/bin/activate"  # adjust path if needed

# Parse arguments (supports both positional and flag-style)
SPECIFIC_OUTPUT_DIR=""
TRUNCATE_CHARS=""
LIMIT_CHARS=""
USE_RESUME=false
CSV_FILE=""

# Process arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --resume)
            USE_RESUME=true
            PYTHON_SCRIPT="../backend/resume_pipeline.py"
            echo "Using resume pipeline (incremental updates)"
            shift
            ;;
        --csv)
            CSV_FILE="$2"
            echo "Using CSV file: $CSV_FILE"
            shift 2
            ;;
        --output_dir)
            SPECIFIC_OUTPUT_DIR="$2"
            echo "Using output directory: $SPECIFIC_OUTPUT_DIR"
            shift 2
            ;;
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
                echo "Will limit processing to $2 comments (only for legacy support)"
                shift 2
            else
                echo "Error: --limit requires a numeric value"
                exit 1
            fi
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --resume                Use resume pipeline for incremental updates"
            echo "  --csv FILE             CSV file to process"
            echo "  --output_dir DIR       Output directory"
            echo "  --truncate NUM         Truncate text to NUM characters"
            echo "  --help, -h             Show this help"
            echo ""
            echo "Examples:"
            echo "  $0 --csv comments.csv --output_dir results --truncate 500"
            echo "  $0 --resume --csv new_comments.csv --output_dir results --truncate 500"
            exit 0
            ;;
        *)
            # Backward compatibility: treat as CSV file if it exists
            if [ -f "$1" ] && [ -z "$CSV_FILE" ]; then
                CSV_FILE="$1"
                echo "Using CSV file: $CSV_FILE"
            # Otherwise check if it's a numeric value for backward compatibility
            elif [ -z "$TRUNCATE_CHARS" ] && [ "$1" -eq "$1" ] 2>/dev/null; then
                TRUNCATE_CHARS="--truncate $1"
                echo "Will truncate comments to $1 characters for analysis"
            else
                echo "Error: Unknown argument: $1"
                echo "Use --help for usage information"
                exit 1
            fi
            shift
            ;;
    esac
done

# Set up default values if not specified
if [ -z "$CSV_FILE" ]; then
    if [ -f "comments.csv" ]; then
        CSV_FILE="comments.csv"
        echo "Found comments.csv file, will use this as input"
    else
        echo "Error: No CSV file specified and comments.csv not found"
        echo "Use --csv FILE or --help for usage information"
        exit 1
    fi
fi

if [ -z "$SPECIFIC_OUTPUT_DIR" ]; then
    # Create timestamped results directory
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    SPECIFIC_OUTPUT_DIR="$BASE_RESULTS_DIR/results_$TIMESTAMP"
    echo "Using timestamped output directory: $SPECIFIC_OUTPUT_DIR"
fi

# Create output directory
mkdir -p "$SPECIFIC_OUTPUT_DIR"

# Build pipeline arguments
PIPELINE_ARGS="--csv $CSV_FILE --output_dir $SPECIFIC_OUTPUT_DIR $TRUNCATE_CHARS"

echo ""
echo "🔧 Pipeline configuration:"
echo "   Script: $PYTHON_SCRIPT"
echo "   CSV file: $CSV_FILE"
echo "   Output directory: $SPECIFIC_OUTPUT_DIR"
if [ -n "$TRUNCATE_CHARS" ]; then
    echo "   Truncation: ${TRUNCATE_CHARS#--truncate } characters"
fi
if [ "$USE_RESUME" = true ]; then
    echo "   Mode: Resume (incremental updates)"
else
    echo "   Mode: Fresh analysis"
fi
echo ""

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
python -u $PYTHON_SCRIPT $PIPELINE_ARGS | tee $SPECIFIC_OUTPUT_DIR/pipeline.log

echo '✅ Analysis finished. Log saved to $SPECIFIC_OUTPUT_DIR/pipeline.log'
" C-m

echo ""
echo "🚀 Analysis started in tmux session: $SESSION_NAME"
echo "📺 To view logs: tail -f $SPECIFIC_OUTPUT_DIR/pipeline.log"
echo "📺 To view session: tmux attach -t $SESSION_NAME"
echo "🧼 To stop: tmux kill-session -t $SESSION_NAME"
echo "📁 Results will be saved to: $SPECIFIC_OUTPUT_DIR"