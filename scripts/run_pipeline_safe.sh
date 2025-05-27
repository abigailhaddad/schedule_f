#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (parent of scripts)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

SESSION_NAME="schedule_f_analysis"
BASE_RESULTS_DIR="results"
VENV_PATH="myenv/bin/activate"

echo "🚀 Schedule F Comment Analysis Pipeline"
echo "======================================"
echo ""
echo "📍 Working from project root: $(pwd)"
echo ""
echo "ℹ️  IMPORTANT: All file paths should be relative to the project root"
echo "   Example: 'data/raw_data.json' NOT '/Users/.../data/raw_data.json'"
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
        echo -n "$prompt [$default]: " >&2
    else
        echo -n "$prompt: " >&2
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
    PYTHON_SCRIPT="backend/resume_pipeline.py"
    echo "✓ Using resume pipeline"
    echo ""
    
    # Ask about existing files
    echo "2. Existing Files (for resume mode)"
    echo "==================================="
    echo ""
    
    # Select raw data file
    echo "Step 2a: Select raw data file"
    echo "-----------------------------"
    
    # Find available raw data files
    raw_files=()
    if [ -d "data" ]; then
        while IFS= read -r file; do
            raw_files+=("$file")
        done < <(find data -name "*raw_data*.json" -type f 2>/dev/null | sort)
    fi
    
    if [ ${#raw_files[@]} -gt 0 ]; then
        echo "Available raw data files:"
        for i in "${!raw_files[@]}"; do
            echo "  $((i+1))) ${raw_files[$i]}"
        done
        echo "  0) Enter custom path"
        echo ""
        
        read -p "Select option [1]: " raw_choice
        raw_choice=${raw_choice:-1}
        
        if [ "$raw_choice" = "0" ]; then
            RAW_DATA_FILE=$(ask_input "Enter raw data file path" "data/raw_data.json")
        elif [[ "$raw_choice" =~ ^[0-9]+$ ]] && [ "$raw_choice" -gt 0 ] && [ "$raw_choice" -le "${#raw_files[@]}" ]; then
            RAW_DATA_FILE="${raw_files[$((raw_choice-1))]}"
        else
            echo "Invalid selection, using default"
            RAW_DATA_FILE="data/raw_data.json"
        fi
    else
        echo "No raw data files found in data/ directory"
        RAW_DATA_FILE=$(ask_input "Enter raw data file path" "data/raw_data.json")
    fi
    
    # Remove any accidental quotes from user input
    RAW_DATA_FILE=$(echo "$RAW_DATA_FILE" | tr -d "'\"")
    
    # Validate raw data file exists
    if [ ! -f "$RAW_DATA_FILE" ]; then
        echo ""
        echo "❌ Error: Raw data file not found!"
        echo "   Looking for: $RAW_DATA_FILE"
        echo "   Full path: $(pwd)/$RAW_DATA_FILE"
        exit 1
    fi
    echo "✓ Selected raw data file: $RAW_DATA_FILE"
    echo ""
    
    # Select lookup table file
    echo "Step 2b: Select lookup table file"
    echo "---------------------------------"
    
    # Find available lookup table files
    lookup_files=()
    if [ -d "data" ]; then
        while IFS= read -r file; do
            lookup_files+=("$file")
        done < <(find data -name "*lookup*.json" -type f 2>/dev/null | sort)
    fi
    
    if [ ${#lookup_files[@]} -gt 0 ]; then
        echo "Available lookup table files:"
        for i in "${!lookup_files[@]}"; do
            echo "  $((i+1))) ${lookup_files[$i]}"
        done
        echo "  0) Enter custom path"
        echo ""
        
        read -p "Select option [1]: " lookup_choice
        lookup_choice=${lookup_choice:-1}
        
        if [ "$lookup_choice" = "0" ]; then
            LOOKUP_TABLE_FILE=$(ask_input "Enter lookup table file path" "data/lookup_table.json")
        elif [[ "$lookup_choice" =~ ^[0-9]+$ ]] && [ "$lookup_choice" -gt 0 ] && [ "$lookup_choice" -le "${#lookup_files[@]}" ]; then
            LOOKUP_TABLE_FILE="${lookup_files[$((lookup_choice-1))]}"
        else
            echo "Invalid selection, using default"
            LOOKUP_TABLE_FILE="data/lookup_table.json"
        fi
    else
        echo "No lookup table files found in data/ directory"
        LOOKUP_TABLE_FILE=$(ask_input "Enter lookup table file path" "data/lookup_table.json")
    fi
    
    # Remove any accidental quotes from user input
    LOOKUP_TABLE_FILE=$(echo "$LOOKUP_TABLE_FILE" | tr -d "'\"")
    
    # Validate lookup table file exists
    if [ ! -f "$LOOKUP_TABLE_FILE" ]; then
        echo ""
        echo "❌ Error: Lookup table file not found!"
        echo "   Looking for: $LOOKUP_TABLE_FILE"
        echo "   Full path: $(pwd)/$LOOKUP_TABLE_FILE"
        exit 1
    fi
    echo "✓ Selected lookup table file: $LOOKUP_TABLE_FILE"
    
    RESUME_ARGS="--raw_data $RAW_DATA_FILE --lookup_table $LOOKUP_TABLE_FILE"
else
    USE_RESUME=false
    PYTHON_SCRIPT="backend/pipeline.py"
    echo "✓ Using fresh pipeline"
    RESUME_ARGS=""
fi

echo ""

# Ask about CSV file
echo "3. Input Data"
echo "============="

# Find available CSV files
csv_files=()
while IFS= read -r file; do
    csv_files+=("$file")
done < <(find . -maxdepth 2 -name "*.csv" -type f 2>/dev/null | sed 's|^\./||' | sort)

if [ ${#csv_files[@]} -gt 0 ]; then
    echo "Available CSV files:"
    for i in "${!csv_files[@]}"; do
        echo "  $((i+1))) ${csv_files[$i]}"
    done
    echo "  0) Enter custom path"
    echo ""
    
    read -p "Select option [1]: " csv_choice
    csv_choice=${csv_choice:-1}
    
    if [ "$csv_choice" = "0" ]; then
        CSV_FILE=$(ask_input "Enter CSV file path" "comments.csv")
    elif [[ "$csv_choice" =~ ^[0-9]+$ ]] && [ "$csv_choice" -gt 0 ] && [ "$csv_choice" -le "${#csv_files[@]}" ]; then
        CSV_FILE="${csv_files[$((csv_choice-1))]}"
    else
        echo "Invalid selection, using default"
        CSV_FILE="comments.csv"
    fi
else
    echo "No CSV files found in project root"
    CSV_FILE=$(ask_input "Enter CSV file path" "comments.csv")
fi

# Remove any accidental quotes from user input
CSV_FILE=$(echo "$CSV_FILE" | tr -d "'\"")

# Validate CSV exists
if [ ! -f "$CSV_FILE" ]; then
    echo ""
    echo "❌ Error: CSV file not found!"
    echo "   Looking for: $CSV_FILE"
    echo "   Full path: $(pwd)/$CSV_FILE"
    exit 1
fi

echo "✓ Selected CSV file: $CSV_FILE"

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
echo "   CSV file: $CSV_FILE"
echo "   Output directory: $OUTPUT_DIR"
if [ "$USE_RESUME" = true ]; then
    echo "   Raw data: $RAW_DATA_FILE"
    echo "   Lookup table: $LOOKUP_TABLE_FILE"
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

# Function to show monitoring menu after exiting log viewer
show_monitoring_menu() {
    trap - INT  # Reset trap
    echo ""
    echo "📊 Monitoring Options:"
    echo "======================================"
    echo "📺 View logs:    tail -f $OUTPUT_DIR/pipeline.log"
    echo "📺 View session: tmux attach -t $SESSION_NAME"
    echo "📊 Check status: tmux list-sessions | grep $SESSION_NAME"
    echo "🧼 Stop pipeline: tmux kill-session -t $SESSION_NAME"
    echo "📁 Results location: $OUTPUT_DIR"
    echo ""
}

# Function to check and clean up old sessions
check_existing_sessions() {
    local existing_sessions=$(tmux list-sessions 2>/dev/null | grep "$SESSION_NAME" | wc -l)
    if [ "$existing_sessions" -gt 0 ]; then
        echo "⚠️  Found $existing_sessions existing session(s) with name '$SESSION_NAME'"
        echo ""
        echo "Existing sessions:"
        tmux list-sessions 2>/dev/null | grep "$SESSION_NAME"
        echo ""
        
        if ask_yes_no "Kill existing session(s) before starting new one" "y"; then
            tmux kill-session -t "$SESSION_NAME" 2>/dev/null
            echo "✅ Killed existing session(s)"
        else
            echo "❌ Cannot proceed with existing session. Please kill it manually:"
            echo "   tmux kill-session -t $SESSION_NAME"
            exit 1
        fi
    fi
}

# Check for existing sessions
check_existing_sessions

# Create tmux session
echo "⚙️  Starting tmux session: $SESSION_NAME"
tmux new-session -d -s "$SESSION_NAME"

# Send commands to tmux session
# Note: We need to properly escape variables
tmux send-keys -t "$SESSION_NAME" "cd $PROJECT_ROOT" C-m
sleep 0.5
tmux send-keys -t "$SESSION_NAME" "echo '🔒 Activating virtualenv...'" C-m
tmux send-keys -t "$SESSION_NAME" "source $VENV_PATH" C-m
sleep 0.5
tmux send-keys -t "$SESSION_NAME" "echo '🚀 Running analysis...'" C-m
tmux send-keys -t "$SESSION_NAME" "echo 'Python script: $PYTHON_SCRIPT'" C-m
tmux send-keys -t "$SESSION_NAME" "echo 'Pipeline args: $PIPELINE_ARGS'" C-m
tmux send-keys -t "$SESSION_NAME" "echo 'Output dir: $OUTPUT_DIR'" C-m

# Convert script path to module name
MODULE_NAME=$(echo $PYTHON_SCRIPT | sed 's|/|.|g' | sed 's|\.py$||')
tmux send-keys -t "$SESSION_NAME" "python -u -m $MODULE_NAME $PIPELINE_ARGS 2>&1 | tee $OUTPUT_DIR/pipeline.log" C-m

echo ""
echo "🚀 Analysis started in tmux session: $SESSION_NAME"
echo ""

# Wait a moment for the process to start and check status
echo "⏳ Waiting for pipeline to start..."
sleep 2

# Check if tmux session is still running
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo ""
    echo "❌ Error: Pipeline failed to start!"
    echo "The tmux session died immediately. This usually means:"
    echo "  - Python environment activation failed"
    echo "  - Python script has syntax errors"
    echo "  - Missing dependencies"
    echo ""
    echo "Try running the command manually to see the error:"
    echo "  cd $PROJECT_ROOT"
    echo "  source $VENV_PATH"
    echo "  python $PYTHON_SCRIPT $PIPELINE_ARGS"
    exit 1
fi

# Check if log file exists
if [ ! -f "$OUTPUT_DIR/pipeline.log" ]; then
    echo "⏳ Waiting for log file to be created..."
    # Give it up to 10 seconds for log file to appear
    for i in {1..10}; do
        sleep 1
        if [ -f "$OUTPUT_DIR/pipeline.log" ]; then
            break
        fi
    done
fi

# Show current status
echo ""
echo "📊 Pipeline Status:"
echo "=================="
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "✅ Tmux session is running"
    
    # Show last few lines of tmux pane
    echo ""
    echo "📺 Recent output from tmux session:"
    echo "-----------------------------------"
    tmux capture-pane -t "$SESSION_NAME" -p | tail -n 10
    echo "-----------------------------------"
else
    echo "❌ Tmux session is not running"
fi

if [ -f "$OUTPUT_DIR/pipeline.log" ]; then
    echo "✅ Log file exists: $OUTPUT_DIR/pipeline.log"
    log_size=$(wc -l < "$OUTPUT_DIR/pipeline.log" 2>/dev/null || echo "0")
    echo "   Lines written: $log_size"
else
    echo "⚠️  Log file not yet created"
fi

# Check for running Python processes
echo ""
echo "🔍 Python processes:"
python_procs=$(ps aux | grep -E "python.*$PYTHON_SCRIPT" | grep -v grep | wc -l)
if [ "$python_procs" -gt 0 ]; then
    echo "✅ Found $python_procs Python process(es) running the pipeline"
else
    echo "⚠️  No Python processes found running the pipeline"
fi

echo ""
echo "What would you like to do?"
echo "  1) View live logs (press Ctrl+C to exit log viewer)"
echo "  2) Attach to tmux session (press Ctrl+B then D to detach)"
echo "  3) Show all tmux sessions"
echo "  4) Exit and let it run in background"
echo ""
read -p "Select option [1]: " view_choice
view_choice=${view_choice:-1}

case "$view_choice" in
    1)
        echo ""
        if [ -f "$OUTPUT_DIR/pipeline.log" ]; then
            echo "📺 Viewing live logs (press Ctrl+C to stop viewing)..."
            echo "====================================================="
            echo ""
            # Use tail -f to show logs, trap Ctrl+C to show menu again
            trap 'echo -e "\n\n✋ Stopped viewing logs. Pipeline is still running in background."; show_monitoring_menu' INT
            tail -f "$OUTPUT_DIR/pipeline.log"
        else
            echo "⚠️  Log file not found. The pipeline may still be initializing."
            echo "Try option 2 to attach to the tmux session and see what's happening."
        fi
        ;;
    2)
        echo ""
        echo "📺 Attaching to tmux session..."
        echo "  - Press Ctrl+B then D to detach and return to shell"
        echo "  - Press Ctrl+C to stop the pipeline"
        echo ""
        sleep 2
        tmux attach -t "$SESSION_NAME"
        ;;
    3)
        echo ""
        echo "📺 All tmux sessions:"
        echo "===================="
        tmux list-sessions 2>/dev/null || echo "No tmux sessions found"
        echo ""
        show_monitoring_menu
        ;;
    4)
        echo ""
        echo "✅ Pipeline running in background"
        ;;
    *)
        echo ""
        echo "✅ Pipeline running in background"
        ;;
esac

# Show monitoring menu if not attaching to tmux
if [ "$view_choice" != "2" ]; then
    show_monitoring_menu
fi