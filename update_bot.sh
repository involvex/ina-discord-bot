#!/bin/bash

# SYNOPSIS
#     Updates Ina's New World Bot by pulling the latest changes from the GitHub main branch.
# DESCRIPTION
#     This script navigates to its own directory (which should be the root of the
#     Git repository), fetches and pulls updates from the 'main' branch of the
#     'origin' remote.
# NOTES
#     Ensure Git is installed and in your PATH.
#     Make this script executable: chmod +x update_bot.sh
#     This script assumes it is located in the root directory of the git repository.

echo "==================================="
echo "Ina's New World Bot Updater (Linux)"
echo "==================================="
echo ""

# --- Configuration ---
# Determine the directory of this script, which is assumed to be the Git repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
BotDirectory="$SCRIPT_DIR"
GitBranch="main"

# --- Check for Git ---
if ! command -v git &> /dev/null
then
    echo "Error: Git is not installed or not found in PATH. Please install Git." >&2
    exit 1
fi
echo "Git installation found."
echo ""

# --- Navigate to Bot Directory (which is the script's directory) ---
echo "Ensuring execution in bot repository directory: $BotDirectory"
cd "$BotDirectory" || { echo "Error: Failed to navigate to bot repository directory: $BotDirectory. This script must be run from within the git repository." >&2; exit 1; }
echo "Successfully operating in bot repository directory: $(pwd)"
echo ""

# --- Fetch latest changes from all remotes ---
echo "Fetching latest updates from remote repository..."
git fetch --all --progress -f
if [ $? -ne 0 ]; then
    echo "Error: Git fetch failed. Check your internet connection and Git configuration." >&2
    exit 1
fi
echo "Fetch successful."
echo ""

# --- Ensure we are on the correct branch ---
echo "Ensuring you are on the '$GitBranch' branch..."
currentBranch=$(git rev-parse --abbrev-ref HEAD)
if [ "$currentBranch" != "$GitBranch" ]; then
    echo "Currently on branch '$currentBranch'. Attempting to checkout '$GitBranch'..."
    git checkout "$GitBranch"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to checkout branch '$GitBranch'. Update cannot proceed safely." >&2
        exit 1
    fi
fi
echo "Successfully on branch '$GitBranch'."
echo ""

# --- Pull changes from the main branch of origin ---
echo "Pulling changes from origin/$GitBranch..."

echo "Attempting to discard any local changes before pull..."
git reset --hard HEAD
if [ $? -ne 0 ]; then
    echo "Warning: 'git reset --hard HEAD' failed. Local changes might still exist and cause pull issues." >&2
    # Optionally, you could exit here if a clean state is mandatory
    # exit 1
fi
git pull origin "$GitBranch" --progress
if [ $? -ne 0 ]; then
    echo "Error: Git pull failed. You might have local changes that conflict. Please resolve conflicts manually or stash your changes (e.g., 'git stash') and try again." >&2
    exit 1
fi
echo "Successfully pulled latest changes."
echo ""

echo "==================================="
echo "Update Complete!"
echo "==================================="
echo ""
echo "Please restart Ina's New World Bot for the changes to take effect."
echo "If 'main.py', dependency files, or other critical code files were updated, a restart is necessary."
echo ""
