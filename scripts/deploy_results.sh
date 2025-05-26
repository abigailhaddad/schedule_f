#!/bin/bash

echo "📦 Deploy Results to Git"
echo "========================"
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

# Ask about source directory
echo "1. Source Results"
echo "================="
echo "Available results directories:"
ls -la ../results/ 2>/dev/null | grep "^d" | grep "results_" | awk '{print "   " $9}' || echo "   No results directories found"
echo ""

SOURCE_DIR=$(ask_input "Source results directory (relative to project root)" "results/$(ls ../results/ 2>/dev/null | grep 'results_' | sort -r | head -n 1)")

# Validate source directory
if [ ! -d "../$SOURCE_DIR" ]; then
    echo "Error: Source directory not found: ../$SOURCE_DIR"
    exit 1
fi

echo ""

# Ask about cleaning data folder first
echo "2. Data Folder"
echo "=============="
CLEAN_DATA_FIRST=false
if ask_yes_no "Clear data/ folder first (removes everything)" "y"; then
    CLEAN_DATA_FIRST=true
fi

echo ""

# Ask about git operations
echo "3. Git Operations"
echo "================="
PUSH_TO_GIT=false
if ask_yes_no "Push to schedule_f repo data branch" "n"; then
    PUSH_TO_GIT=true
    
    # Ask for commit message
    COMMIT_MSG=$(ask_input "Commit message" "Update data files - $(date '+%Y-%m-%d %H:%M')")
fi

echo ""

# Show configuration
echo "🔧 Configuration"
echo "================"
echo "   Source: ../$SOURCE_DIR"
echo "   Target: data/ folder"
if [ "$CLEAN_DATA_FIRST" = true ]; then
    echo "   Clean data folder: YES (removes everything)"
else
    echo "   Clean data folder: NO (merge with existing)"
fi
if [ "$PUSH_TO_GIT" = true ]; then
    echo "   Git push: YES to schedule_f/data branch"
    echo "   Commit message: \"$COMMIT_MSG\""
else
    echo "   Git push: NO"
fi
echo ""

# Final confirmation
if ! ask_yes_no "Proceed with deployment" "y"; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🚀 Starting deployment..."

# Step 1: Clean data folder if requested
if [ "$CLEAN_DATA_FIRST" = true ]; then
    echo "🧹 Cleaning data/ folder..."
    cd ..
    rm -rf data/*
    cd scripts
    echo "✅ Data folder cleaned"
fi

# Step 2: Copy results to data folder
echo "📋 Copying results from $SOURCE_DIR to data/..."
cd ..
cp -r $SOURCE_DIR/* data/ 2>/dev/null || true
echo "✅ Files copied"

# Show what was copied
echo ""
echo "📁 Files now in data/:"
ls -la data/
echo ""

# Step 3: Git operations if requested
if [ "$PUSH_TO_GIT" = true ]; then
    echo "📤 Pushing to schedule_f repo data branch..."
    
    # Check if we're in a git repo
    if [ ! -d ".git" ]; then
        echo "Error: Not in a git repository"
        exit 1
    fi
    
    # Check current branch and repo
    CURRENT_REPO=$(git remote -v | grep origin | head -n 1 | awk '{print $2}')
    CURRENT_BRANCH=$(git branch --show-current)
    
    echo "Current repo: $CURRENT_REPO"
    echo "Current branch: $CURRENT_BRANCH"
    
    # Add data files to git
    echo "Adding data files to git..."
    git add data/
    
    # Check if there are changes to commit
    if git diff --staged --quiet; then
        echo "⚠️  No changes to commit"
    else
        # Commit changes
        echo "Committing changes..."
        git commit -m "$COMMIT_MSG"
        
        # Push to current branch (assuming it's set up correctly)
        echo "Pushing to origin..."
        git push origin $CURRENT_BRANCH
        
        echo "✅ Successfully pushed to git"
    fi
else
    echo "ℹ️  Skipping git operations"
fi

echo ""
echo "🎉 Deployment complete!"
echo "📁 Data files are now in the data/ folder"
if [ "$PUSH_TO_GIT" = true ]; then
    echo "📤 Changes have been pushed to git"
fi