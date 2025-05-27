#!/bin/bash

# Deploy Results to Git - Simplified version that only handles git operations
# Assumes copy_latest_data.sh has already been run to update the data folder

echo "📤 Deploy Data to Git"
echo "===================="
echo ""

# Get project root directory (parent of scripts)
PROJECT_ROOT="$(dirname "$(dirname "$0")")"
cd "$PROJECT_ROOT"

# Configuration
DATA_BRANCH="data"  # The branch where we want to push data files
DEFAULT_COMMIT_MSG="Update data files - $(date '+%Y-%m-%d %H:%M')"

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

# Check if we're in a git repo
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Check if data folder exists and has content
if [ ! -d "data" ] || [ -z "$(ls -A data 2>/dev/null)" ]; then
    echo "❌ Error: data/ folder is empty or doesn't exist"
    echo "   Run copy_latest_data.sh first to populate the data folder"
    exit 1
fi

# Show current git status
echo "📊 Current Git Status"
echo "===================="
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"
echo ""

# Check if there are uncommitted changes in data/
if ! git diff --quiet data/ || ! git diff --cached --quiet data/; then
    echo "📝 Uncommitted changes in data/:"
    git status -s data/ | head -10
    if [ $(git status -s data/ | wc -l) -gt 10 ]; then
        echo "... and $(($(git status -s data/ | wc -l) - 10)) more files"
    fi
else
    echo "✅ No uncommitted changes in data/"
fi
echo ""

# Ask for commit message
COMMIT_MSG=$(ask_input "Commit message" "$DEFAULT_COMMIT_MSG")
echo ""

# Ask which branch to push to
echo "📌 Target Branch"
echo "================"
echo "Available options:"
echo "  1) Push to data branch (recommended)"
echo "  2) Push to current branch ($CURRENT_BRANCH)"
echo ""
read -p "Select option [1]: " branch_choice
branch_choice=${branch_choice:-1}

case "$branch_choice" in
    1)
        TARGET_BRANCH="$DATA_BRANCH"
        USE_DATA_BRANCH=true
        ;;
    2)
        TARGET_BRANCH="$CURRENT_BRANCH"
        USE_DATA_BRANCH=false
        ;;
    *)
        echo "Invalid selection, using data branch"
        TARGET_BRANCH="$DATA_BRANCH"
        USE_DATA_BRANCH=true
        ;;
esac

echo ""
echo "🔧 Configuration"
echo "================"
echo "   Source branch: $CURRENT_BRANCH"
echo "   Target branch: $TARGET_BRANCH"
echo "   Commit message: \"$COMMIT_MSG\""
echo ""

# Final confirmation
if ! ask_yes_no "Proceed with git operations" "y"; then
    echo "❌ Cancelled"
    exit 0
fi

echo ""
echo "🚀 Starting git operations..."
echo ""

# Save current branch name for later
ORIGINAL_BRANCH="$CURRENT_BRANCH"

# If using data branch, we need to handle branch switching
if [ "$USE_DATA_BRANCH" = true ]; then
    echo "📋 Preparing data branch..."
    
    # Check if data branch exists locally
    if git show-ref --verify --quiet refs/heads/$DATA_BRANCH; then
        echo "✅ Data branch exists locally"
    else
        # Check if it exists on remote
        if git ls-remote --heads schedule_f $DATA_BRANCH | grep -q $DATA_BRANCH; then
            echo "📥 Creating local data branch from schedule_f/$DATA_BRANCH..."
            git branch $DATA_BRANCH schedule_f/$DATA_BRANCH
        else
            echo "🆕 Creating new data branch..."
            git branch $DATA_BRANCH
        fi
    fi
    
    # Stash any uncommitted changes (not in data/)
    echo "📦 Stashing any uncommitted changes..."
    STASH_OUTPUT=$(git stash push -m "deploy_results temporary stash" -- . ':!data/')
    STASHED=false
    if [[ "$STASH_OUTPUT" != *"No local changes to save"* ]]; then
        STASHED=true
        echo "✅ Changes stashed"
    else
        echo "ℹ️  No changes to stash"
    fi
    
    # Switch to data branch
    echo "🔄 Switching to $DATA_BRANCH branch..."
    git checkout $DATA_BRANCH
    
    # Update data branch to be current with the original branch
    echo "🔄 Updating $DATA_BRANCH to match $ORIGINAL_BRANCH..."
    git merge $ORIGINAL_BRANCH --no-edit -m "Merge $ORIGINAL_BRANCH into $DATA_BRANCH"
    
    if [ $? -ne 0 ]; then
        echo "❌ Error: Merge failed. Please resolve conflicts manually."
        echo "   After resolving, you can run this script again."
        # Switch back to original branch
        git checkout $ORIGINAL_BRANCH
        # Restore stash if we stashed
        if [ "$STASHED" = true ]; then
            git stash pop
        fi
        exit 1
    fi
fi

# Add all changes in data/
echo "📝 Staging data/ changes..."
git add data/

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "⚠️  No changes to commit"
    
    # If we switched branches, switch back
    if [ "$USE_DATA_BRANCH" = true ]; then
        echo "🔄 Switching back to $ORIGINAL_BRANCH..."
        git checkout $ORIGINAL_BRANCH
        
        # Restore stash if we stashed
        if [ "$STASHED" = true ]; then
            echo "📦 Restoring stashed changes..."
            git stash pop
        fi
    fi
    
    echo "✅ Done (no changes to deploy)"
    exit 0
fi

# Commit changes
echo "💾 Committing changes..."
git commit -m "$COMMIT_MSG"

if [ $? -ne 0 ]; then
    echo "❌ Error: Commit failed"
    
    # If we switched branches, switch back
    if [ "$USE_DATA_BRANCH" = true ]; then
        git checkout $ORIGINAL_BRANCH
        if [ "$STASHED" = true ]; then
            git stash pop
        fi
    fi
    exit 1
fi

# Push to remote
echo "📤 Pushing to schedule_f/$TARGET_BRANCH..."
git push schedule_f $TARGET_BRANCH

if [ $? -ne 0 ]; then
    echo "❌ Error: Push failed"
    echo "   You may need to pull first or resolve conflicts"
    
    # If we switched branches, switch back
    if [ "$USE_DATA_BRANCH" = true ]; then
        git checkout $ORIGINAL_BRANCH
        if [ "$STASHED" = true ]; then
            git stash pop
        fi
    fi
    exit 1
fi

echo "✅ Successfully pushed to schedule_f/$TARGET_BRANCH"

# If we used data branch, switch back to original branch
if [ "$USE_DATA_BRANCH" = true ]; then
    echo "🔄 Switching back to $ORIGINAL_BRANCH..."
    git checkout $ORIGINAL_BRANCH
    
    # Restore stash if we stashed
    if [ "$STASHED" = true ]; then
        echo "📦 Restoring stashed changes..."
        git stash pop
    fi
fi

echo ""
echo "🎉 Deployment complete!"
echo "📤 Data has been pushed to: schedule_f/$TARGET_BRANCH"
echo "🌐 View on GitHub: $(git remote get-url schedule_f | sed 's/\.git$//' | sed 's/git@github.com:/https:\/\/github.com\//')/tree/$TARGET_BRANCH"
