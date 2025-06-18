#!/bin/bash

# SYNOPSIS
#     Updates Ina's New World Bot by pulling the latest changes from the GitHub main branch.
# DESCRIPTION
#     This script navigates to the bot's directory, fetches and pulls updates from
#     the 'main' branch of the 'origin' remote. It also provides an option to
#     update Python dependencies if a requirements.txt file exists.
# NOTES
#     Ensure Git is installed and in your PATH.
#     Make this script executable: chmod +x update_bot.sh

# --- Configuration ---
BotDirectory="/home/container/interactions.py" # Your bot's local Git repository path
GitBranch="main"

# Optional: Path to your Python executable (if not in PATH or for specific venv)
# PythonExecutable="/path/to/your/python"
# Optional: Path to your virtual environment's activate script (for pip in venv)
# VenvActivateScript="/path/to/your/venv/bin/activate"

echo "==================================="
echo "Ina's New World Bot Updater (Linux)"
echo "==================================="
echo ""

# --- Check for Git ---
if ! command -v git &> /dev/null
then
    echo "Error: Git is not installed or not found in PATH. Please install Git." >&2
    exit 1
fi
echo "Git installation found."
echo ""

# --- Navigate to Bot Directory ---
echo "Navigating to bot directory: $BotDirectory"
if [ ! -d "$BotDirectory" ]; then
    echo "Error: Bot directory not found: $BotDirectory" >&2
    exit 1
fi

cd "$BotDirectory" || { echo "Error: Failed to navigate to bot directory: $BotDirectory" >&2; exit 1; }
echo "Successfully navigated to bot directory: $(pwd)"
echo ""

# --- Fetch latest changes from all remotes ---
echo "Fetching latest updates from remote repository..."
git fetch --all --progress
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
git pull origin "$GitBranch" --progress
if [ $? -ne 0 ]; then
    echo "Error: Git pull failed. You might have local changes that conflict. Please resolve conflicts manually or stash your changes (e.g., 'git stash') and try again." >&2
    exit 1
fi
echo "Successfully pulled latest changes."
echo ""

# --- (Optional) Update Python Dependencies ---
# echo "Checking for requirements.txt..."
# if [ -f "requirements.txt" ]; then
#     echo "Updating Python dependencies from requirements.txt..."
#     # If using a specific python executable or virtual environment:
#     # $PythonExecutable -m pip install -r requirements.txt
#     # Or if pip is in PATH and for the correct environment:
#     # pip install -r requirements.txt
#     # if [ $? -ne 0 ]; then echo "Warning: Failed to update Python dependencies." >&2; fi
#     echo "Python dependency update step (if implemented) would run here."
# else
#     echo "No requirements.txt found, skipping dependency update."
# fi
# echo ""

echo "==================================="
echo "Update Complete!"
echo "==================================="
echo ""
echo "Please restart Ina's New World Bot for the changes to take effect."
echo "If 'main.py', dependency files, or other critical code files were updated, a restart is necessary."
echo ""