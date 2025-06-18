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

# --- Configuration (from the original script's intent) ---
SCRIPT_DIR_CONF="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)" # Renamed to avoid conflict
BotDirectory="$SCRIPT_DIR_CONF" # BotDirectory is essentially SCRIPT_DIR
GitBranch="main"

# Get the directory of the script
SCRIPT_DIR_ACTUAL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" # This is the effective script directory

# Navigate to the script's directory (root of your Git repo)
cd "$SCRIPT_DIR_ACTUAL" || { echo "ERROR: Failed to navigate to script directory $SCRIPT_DIR_ACTUAL. Update aborted." >&2; exit 1; }
echo "INFO: Operating in bot repository directory: $(pwd)"
echo ""

# Check for and remove .git/index.lock file if it exists
LOCK_FILE=".git/index.lock"
if [ -f "$LOCK_FILE" ]; then
    echo "INFO: Git index.lock file found at '$PWD/$LOCK_FILE'. Attempting to remove it..."
    rm -f "$LOCK_FILE"
    if [ $? -eq 0 ]; then # Check rm exit status
        if [ ! -f "$LOCK_FILE" ]; then # Double check file is gone
            echo "INFO: index.lock removed successfully."
        else
            # This case means rm reported success but file is still there - very odd, maybe recreated instantly
            echo "WARNING: rm command succeeded but index.lock still exists. Git operations might still fail." >&2
        fi
    else
        # rm command itself failed
        echo "ERROR: Failed to remove index.lock (rm command failed with exit code $?). Check permissions for '$PWD/$LOCK_FILE'. Update aborted." >&2
        exit 1 # Exit if lock removal fails, as subsequent git commands will likely fail
    fi
else
    echo "INFO: No .git/index.lock file found. Proceeding with update."
fi
echo ""

echo "INFO: Starting forceful update from origin/$GitBranch..."

echo "INFO: Fetching all remote branches and tags (shallow fetch)..."
# Fetch all remote branches and tags
# Using --depth 1 to reduce memory usage, which can help prevent "signal 9" errors.
git fetch --all --depth 1
if [ $? -ne 0 ]; then
  echo "ERROR: git fetch --all --depth 1 failed. Update aborted." >&2
  exit 1
fi
echo "INFO: Fetch successful."

# Hard reset the local main branch to match the remote origin/main
# Replace 'main' with your default branch name if it's different (e.g., master)
echo "INFO: Resetting local branch to origin/$GitBranch..."
git reset --hard "origin/$GitBranch" # Use variable and quote
if [ $? -ne 0 ]; then
  echo "ERROR: git reset --hard origin/$GitBranch failed. Update aborted." >&2
  exit 1
fi
echo "INFO: Reset to origin/$GitBranch successful."

# Remove untracked files and directories, including those in .gitignore
# Use with caution: -x also removes ignored files. If you don't want that, remove the 'x'.
echo "INFO: Cleaning untracked files and directories..."
git clean -fd # Changed -fdx to -fd to preserve ignored files like .env
if [ $? -ne 0 ]; then
  echo "ERROR: git clean -fd failed. Update aborted." >&2
  exit 1
fi
echo "INFO: Clean successful."

echo "INFO: Local repository forcefully updated to origin/$GitBranch and cleaned."

# Optional: Reinstall dependencies if requirements.txt might have changed
# Make sure pip is available or use the full path to your virtual environment's pip
if [ -f "requirements.txt" ]; then
  echo "INFO: Reinstalling dependencies from requirements.txt..."
  # Consider using 'python3 -m pip' for clarity if multiple pythons/pips exist
  python3 -m pip install -U -r requirements.txt
  if [ $? -ne 0 ]; then
    echo "Warning: pip install -r requirements.txt failed. Dependencies might be outdated."
  else
    echo "INFO: Dependencies reinstalled successfully."
  fi
fi

echo ""
echo "==================================="
echo "Update Script Completed"
echo "==================================="
echo "Bot will be restarted by the main Python script if update was successful."
exit 0
