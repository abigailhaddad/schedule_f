#!/bin/bash

# Schedule F Comment Analysis Pipeline - Command Line Version
# Usage: ./run_pipeline_args.sh [--resume] [--skip-analysis] [--skip-clustering] [--truncate N]

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (parent of scripts)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

SESSION_NAME="schedule_f_analysis"
VENV_PATH="myenv/bin/activate"

# Default values
USE_RESUME=false
SKIP_ANALYSIS=false
SKIP_CLUSTERING=false
TRUNCATE=""
CSV_FILE="comments.csv"
RAW_DATA_FILE="data/raw_data.json"
LOOKUP_TABLE_FILE="data/lookup_table_corrected.json"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --resume)
            USE_RESUME=true
            shift
            ;;
        --skip-analysis)
            SKIP_ANALYSIS=true
            shift
            ;;
        --skip-clustering)
            SKIP_CLUSTERING=true
            shift
            ;;
        --truncate)
            TRUNCATE="$2"
            shift 2
            ;;
        --csv)
            CSV_FILE="$2"
            shift 2
            ;;
        --raw-data)
            RAW_DATA_FILE="$2"
            shift 2
            ;;
        --lookup-table)
            LOOKUP_TABLE_FILE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --resume              Use resume pipeline (requires existing data files)"
            echo "  --skip-analysis       Skip LLM analysis"
            echo "  --skip-clustering     Skip clustering analysis"
            echo "  --truncate N          Truncate text to N characters"
            echo "  --csv FILE            CSV file path (default: comments.csv)"
            echo "  --raw-data FILE       Raw data file for resume mode (default: data/raw_data.json)"
            echo "  --lookup-table FILE   Lookup table file for resume mode (default: data/lookup_table_corrected.json)"
            echo "  --help                Show this help message"
            echo ""
            echo "Examples:"
            echo "  # Fresh run with all steps:"
            echo "  $0"
            echo ""
            echo "  # Fresh run without LLM analysis:"
            echo "  $0 --skip-analysis --skip-clustering"
            echo ""
            echo "  # Resume with existing data:"
            echo "  $0 --resume"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set up pipeline script and arguments
if [ "$USE_RESUME" = true ]; then
    PYTHON_SCRIPT="backend.resume_pipeline"
    PIPELINE_MODE="Resume (incremental updates)"
    
    # Validate resume files exist
    if [ ! -f "$RAW_DATA_FILE" ]; then
        echo "❌ Error: Raw data file not found: $RAW_DATA_FILE"
        exit 1
    fi
    if [ ! -f "$LOOKUP_TABLE_FILE" ]; then
        echo "❌ Error: Lookup table file not found: $LOOKUP_TABLE_FILE"
        exit 1
    fi
    
    # Create output directory but DON'T copy files
    # The resume pipeline will handle reading from source and writing complete files to output
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    OUTPUT_DIR="results/results_$TIMESTAMP"
    mkdir -p "$OUTPUT_DIR"
    
    # Pass the original file paths, not the output directory paths
    RESUME_ARGS="--raw_data $RAW_DATA_FILE --lookup_table $LOOKUP_TABLE_FILE"
else
    PYTHON_SCRIPT="backend.pipeline"
    PIPELINE_MODE="Fresh analysis"
    RESUME_ARGS=""
    
    # Create output directory
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    OUTPUT_DIR="results/results_$TIMESTAMP"
    mkdir -p "$OUTPUT_DIR"
fi

# Validate CSV file
if [ ! -f "$CSV_FILE" ]; then
    echo "❌ Error: CSV file not found: $CSV_FILE"
    exit 1
fi

# Build pipeline arguments
PIPELINE_ARGS="--csv $CSV_FILE --output_dir $OUTPUT_DIR $RESUME_ARGS"

# Add optional arguments
if [ -n "$TRUNCATE" ]; then
    PIPELINE_ARGS="$PIPELINE_ARGS --truncate $TRUNCATE"
fi
if [ "$SKIP_ANALYSIS" = true ]; then
    PIPELINE_ARGS="$PIPELINE_ARGS --skip_analysis"
fi
if [ "$SKIP_CLUSTERING" = true ]; then
    PIPELINE_ARGS="$PIPELINE_ARGS --skip_clustering"
fi

echo "🚀 Schedule F Comment Analysis Pipeline"
echo "======================================"
echo "📍 Project root: $PROJECT_ROOT"
echo "📁 CSV file: $CSV_FILE"
echo "📁 Output directory: $OUTPUT_DIR"
echo "🔧 Mode: $PIPELINE_MODE"
if [ "$USE_RESUME" = true ]; then
    echo "📁 Raw data: $RAW_DATA_FILE"
    echo "📁 Lookup table: $LOOKUP_TABLE_FILE"
fi
if [ -n "$TRUNCATE" ]; then
    echo "✂️  Truncation: $TRUNCATE characters"
fi
if [ "$SKIP_ANALYSIS" = true ]; then
    echo "⏭️  Skipping: LLM Analysis"
fi
if [ "$SKIP_CLUSTERING" = true ]; then
    echo "⏭️  Skipping: Clustering"
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

# Send commands to tmux session
tmux send-keys -t "$SESSION_NAME" "cd $PROJECT_ROOT" C-m
sleep 0.5
tmux send-keys -t "$SESSION_NAME" "echo '🔒 Activating virtualenv...'" C-m
tmux send-keys -t "$SESSION_NAME" "source $VENV_PATH" C-m
sleep 0.5
tmux send-keys -t "$SESSION_NAME" "echo '🚀 Running pipeline...'" C-m
tmux send-keys -t "$SESSION_NAME" "echo 'Command: python -m $PYTHON_SCRIPT $PIPELINE_ARGS'" C-m
tmux send-keys -t "$SESSION_NAME" "python -m $PYTHON_SCRIPT $PIPELINE_ARGS 2>&1 | tee $OUTPUT_DIR/pipeline.log" C-m
# Add exit command so tmux session closes when pipeline finishes
tmux send-keys -t "$SESSION_NAME" "exit" C-m

echo ""
echo "✅ Pipeline started successfully!"
echo ""
echo "📊 Monitor progress:"
echo "   - View logs:    tail -f $OUTPUT_DIR/pipeline.log"
echo "   - Attach tmux:  tmux attach -t $SESSION_NAME"
echo "   - Stop:         tmux kill-session -t $SESSION_NAME"
echo ""
echo "📁 Results will be saved to: $OUTPUT_DIR"
echo ""

# Function to show live progress
show_progress() {
    # Get the last meaningful line from the log (skip empty lines and certain patterns)
    if [ -f "$OUTPUT_DIR/pipeline.log" ]; then
        # Look for key progress indicators
        local new_comments=$(grep -E "New to fetch: [0-9]+" "$OUTPUT_DIR/pipeline.log" | tail -1 | grep -oE "[0-9]+" | tail -1)
        local processing_batch=$(grep -E "Processing batch [0-9]+" "$OUTPUT_DIR/pipeline.log" | tail -1)
        local current_step=$(grep -E "=== STEP [0-9]+" "$OUTPUT_DIR/pipeline.log" | tail -1)
        
        # Build status line
        local status_line=""
        if [ -n "$current_step" ]; then
            status_line="$current_step"
        fi
        
        if [ -n "$new_comments" ] && [ "$new_comments" -gt 0 ]; then
            status_line="$status_line | New comments: $new_comments"
        fi
        
        if [ -n "$processing_batch" ]; then
            status_line="$status_line | $processing_batch"
        fi
        
        # If no specific status, show last meaningful line
        if [ -z "$status_line" ]; then
            local last_line=$(tail -n 20 "$OUTPUT_DIR/pipeline.log" | grep -E "^[0-9]{4}-|^Reading|^Saved|^✅|^📊|^🔄|^⚠️|^Creating|^Fetching|^=== STEP" | tail -n 1)
            if [ -n "$last_line" ]; then
                status_line="$last_line"
            fi
        fi
        
        if [ -n "$status_line" ]; then
            # Truncate long lines and add ellipsis if needed
            if [ ${#status_line} -gt 100 ]; then
                status_line="${status_line:0:97}..."
            fi
            printf "\r\033[K📊 %s" "$status_line"
        fi
    fi
}

# Function to check if pipeline is complete
wait_for_completion() {
    echo "⏳ Waiting for pipeline to complete..."
    echo "   (Press Ctrl+C to stop monitoring and let it run in background)"
    echo ""
    
    # Wait for log file to be created
    local dots=""
    while [ ! -f "$OUTPUT_DIR/pipeline.log" ]; do
        dots="${dots}."
        if [ ${#dots} -gt 3 ]; then dots="."; fi
        printf "\r\033[K⏳ Starting pipeline%s" "$dots"
        sleep 1
    done
    printf "\r\033[K"
    
    # Monitor for completion
    local pipeline_finished=false
    local last_progress_time=$(date +%s)
    
    while true; do
        # Check if tmux session is still running
        if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            # Session ended - could be normal completion or error
            pipeline_finished=true
            printf "\r\033[K"
            break
        fi
        
        # Check if pipeline completed successfully
        if grep -q "Pipeline complete!" "$OUTPUT_DIR/pipeline.log" 2>/dev/null; then
            printf "\r\033[K"
            echo "✅ Pipeline completed successfully!"
            pipeline_finished=true
            break
        fi
        
        # Check for errors
        if grep -q "Pipeline failed:" "$OUTPUT_DIR/pipeline.log" 2>/dev/null; then
            printf "\r\033[K"
            echo "❌ Pipeline failed! Check logs for details."
            pipeline_finished=true
            break
        fi
        
        # Show progress every 2 seconds
        local current_time=$(date +%s)
        if [ $((current_time - last_progress_time)) -ge 2 ]; then
            show_progress
            last_progress_time=$current_time
        fi
        
        sleep 0.5
    done
    
    # Clean up tmux session if still running
    if [ "$pipeline_finished" = true ]; then
        if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "🧹 Cleaning up tmux session..."
            tmux kill-session -t "$SESSION_NAME"
        fi
    fi
}

# Function to show results summary
show_results() {
    echo ""
    echo "📊 Pipeline Results Summary"
    echo "=========================="
    
    if [ "$USE_RESUME" = true ]; then
        # For resume pipeline, check for new comments fetched
        if grep -q "New to fetch:" "$OUTPUT_DIR/pipeline.log" 2>/dev/null; then
            NEW_COMMENTS=$(grep "New to fetch:" "$OUTPUT_DIR/pipeline.log" | grep -oE 'New to fetch: [0-9,]+' | grep -oE '[0-9,]+' | tail -1 | tr -d ',')
            if [ -n "$NEW_COMMENTS" ] && [ "$NEW_COMMENTS" -gt 0 ]; then
                echo "🆕 New comments fetched: $NEW_COMMENTS"
            else
                echo "✅ No new comments to fetch (all comments already in database)"
            fi
        elif grep -q "=== STEP 1: No New Comments to Fetch ===" "$OUTPUT_DIR/pipeline.log" 2>/dev/null; then
            echo "✅ No new comments to fetch (all comments already in database)"
        fi
        
        # Check for new lookup entries
        if grep -q "new entries created" "$OUTPUT_DIR/pipeline.log" 2>/dev/null; then
            NEW_ENTRIES=$(grep "new entries created" "$OUTPUT_DIR/pipeline.log" | grep -oE '[0-9]+' | tail -1)
            echo "🆕 New lookup entries created: $NEW_ENTRIES"
        fi
        
        # Check for comments added to existing entries
        if grep -q "comments added to existing" "$OUTPUT_DIR/pipeline.log" 2>/dev/null; then
            ADDED_TO_EXISTING=$(grep "comments added to existing" "$OUTPUT_DIR/pipeline.log" | grep -oE '[0-9]+' | tail -1)
            echo "➕ Comments added to existing entries: $ADDED_TO_EXISTING"
        fi
    else
        # For fresh pipeline, show total counts
        if grep -q "Total comments processed:" "$OUTPUT_DIR/pipeline.log" 2>/dev/null; then
            TOTAL_COMMENTS=$(grep "Total comments processed:" "$OUTPUT_DIR/pipeline.log" | grep -oE '[0-9,]+' | tail -1)
            echo "📄 Total comments processed: $TOTAL_COMMENTS"
        fi
        
        if grep -q "Unique text patterns:" "$OUTPUT_DIR/pipeline.log" 2>/dev/null; then
            UNIQUE_PATTERNS=$(grep "Unique text patterns:" "$OUTPUT_DIR/pipeline.log" | grep -oE '[0-9,]+' | tail -1)
            echo "🔍 Unique text patterns: $UNIQUE_PATTERNS"
        fi
        
        if grep -q "Deduplication efficiency:" "$OUTPUT_DIR/pipeline.log" 2>/dev/null; then
            DEDUP_EFFICIENCY=$(grep "Deduplication efficiency:" "$OUTPUT_DIR/pipeline.log" | grep -oE '[0-9.]+%' | tail -1)
            echo "📈 Deduplication efficiency: $DEDUP_EFFICIENCY"
        fi
    fi
    
    # Show validation results
    if grep -q "VALIDATION PASSED" "$OUTPUT_DIR/pipeline.log" 2>/dev/null; then
        echo "✅ Validation: PASSED"
    elif grep -q "VALIDATION FAILED" "$OUTPUT_DIR/pipeline.log" 2>/dev/null; then
        echo "❌ Validation: FAILED"
        # Show validation errors
        VALIDATION_ERRORS=$(grep -A10 "❌ Errors" "$OUTPUT_DIR/pipeline.log" | grep "   - " | head -3)
        if [ -n "$VALIDATION_ERRORS" ]; then
            echo "   Validation errors:"
            echo "$VALIDATION_ERRORS"
        fi
    fi
    
    # Show any warnings or errors
    WARNING_COUNT=$(grep -c "WARNING" "$OUTPUT_DIR/pipeline.log" 2>/dev/null || echo "0")
    if [ "$WARNING_COUNT" -gt 0 ]; then
        echo "⚠️  Warnings: $WARNING_COUNT"
    fi
    
    ERROR_COUNT=$(grep -c "ERROR" "$OUTPUT_DIR/pipeline.log" 2>/dev/null || echo "0")
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo "❌ Errors: $ERROR_COUNT"
    fi
    
    echo ""
    echo "📁 Full results in: $OUTPUT_DIR"
    echo "📄 Full log: $OUTPUT_DIR/pipeline.log"
}

# Wait for completion and show results
trap 'echo -e "\n⏸️  Stopped monitoring. Pipeline continues in background.\n📊 Check progress: tail -f $OUTPUT_DIR/pipeline.log"; exit 0' INT
wait_for_completion
show_results