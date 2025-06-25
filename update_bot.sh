#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
# Ensure the script itself is executable. This helps if permissions are lost.
chmod +x "$0"

set -e

echo "==================================="
echo "Ina's New World Bot Updater (Linux)"
echo "==================================="
echo ""

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
BotDirectory="$SCRIPT_DIR"
GitRepoURL="https://github.com/involvex/ina-discord-bot.git"
GitBranch="main"
VENV_PATH="./venv"
VenvActivateScript="$VENV_PATH/bin/activate"

# Navigate to the script's directory (root of your bot)
cd "$BotDirectory" || { echo "ERROR: Failed to navigate to bot directory $BotDirectory. Update aborted." >&2; exit 1; }
echo "INFO: Operating in directory: $(pwd)"
echo ""

# --- Git Repository Management ---
# Check if .git directory exists AND if it's a valid Git repository
if [ ! -d ".git" ]; then
    echo "INFO: .git directory not found. This is not a Git repository."
    echo "INFO: Cloning repository from $GitRepoURL..."

    # Clone into a temporary directory
    TEMP_CLONE_DIR=$(mktemp -d)
    git clone --branch "$GitBranch" "$GitRepoURL" "$TEMP_CLONE_DIR"

    echo "INFO: Moving cloned files into the current directory..."
    # Enable dotglob to move hidden files like .git and .gitignore
    shopt -s dotglob
    mv "$TEMP_CLONE_DIR"/* .
    shopt -u dotglob

    # Clean up the temporary directory
    rm -rf "$TEMP_CLONE_DIR"
    echo "INFO: Repository successfully cloned and set up."
else
    # .git directory exists, now check if it's a valid repository
    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "WARNING: .git directory found but it's not a valid Git repository. Removing and re-cloning."
        rm -rf .git
        # Ensure the script is executable before trying to re-run it.
        chmod +x "$0"
        # Recursively call this script to re-run the cloning logic
        exec "$0" "$@"
    fi
    echo "INFO: .git directory found. Proceeding with update..."

    # Check for and remove .git/index.lock file if it exists
    LOCK_FILE=".git/index.lock"
    if [ -f "$LOCK_FILE" ]; then
        echo "INFO: Git index.lock file found at '$PWD/$LOCK_FILE'. Attempting to remove it..."
        rm -f "$LOCK_FILE"
        if [ $? -eq 0 ]; then
            if [ ! -f "$LOCK_FILE" ]; then
                echo "INFO: index.lock removed successfully."
            else
                echo "WARNING: rm command succeeded but index.lock still exists. Git operations might still fail." >&2
            fi
        else
            echo "ERROR: Failed to remove index.lock (rm command failed with exit code $?). Check permissions. Update aborted." >&2
            exit 1
        fi
    else
        echo "INFO: No .git/index.lock file found."
    fi

    echo "INFO: Starting forceful update from origin/$GitBranch..."
    echo "INFO: Fetching all remote branches and tags (shallow fetch)..."
    git fetch --all --depth 1

    echo "INFO: Resetting local branch to origin/$GitBranch..."
    git reset --hard "origin/$GitBranch"

    echo "INFO: Cleaning untracked and ignored files and directories..."
    git clean -fdx

    echo "INFO: Local repository forcefully updated to origin/$GitBranch and cleaned."
fi
echo ""

# --- Virtual Environment & Dependencies ---
echo "INFO: Setting up Python virtual environment..."
if [ ! -d "$VENV_PATH" ]; then
  echo "INFO: Virtual environment not found. Creating one at '$VENV_PATH'..."
  python3 -m venv "$VENV_PATH"
else
  echo "INFO: Virtual environment already exists at '$VENV_PATH'."
fi

# Activate virtual environment
if [ -f "$VenvActivateScript" ]; then
  echo "INFO: Activating virtual environment: $VenvActivateScript"
  # shellcheck disable=SC1090
  source "$VenvActivateScript"
  if [ -z "$VIRTUAL_ENV" ]; then
    echo "WARNING: Virtual environment activation failed. Ensure 'source' command is available." >&2
  else
    echo "INFO: Virtual environment activated."
  fi
else
  echo "ERROR: Virtual environment activate script not found. Cannot proceed." >&2
  exit 1
fi

# Upgrade pip and build tools
echo "INFO: Upgrading pip, setuptools, and wheel..."
python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Install/update dependencies
if [ -f "requirements.txt" ]; then
  echo "INFO: Installing/updating dependencies from requirements.txt..."
  python3 -m pip install --no-cache-dir -U -r requirements.txt
  echo "INFO: Dependencies installed/updated successfully."
else
  echo "WARNING: requirements.txt not found. Skipping dependency installation." >&2
fi
echo ""

# --- Sanity Check for Python Packages ---
echo "INFO: Verifying essential package structure..."
if [ -d "commands" ] && [ ! -f "commands/__init__.py" ]; then
    echo "ERROR: 'commands' directory is missing '__init__.py'. It cannot be imported." >&2
    exit 1
fi
if [ -d "commands/new_world" ] && [ ! -f "commands/new_world/__init__.py" ]; then
    echo "ERROR: 'commands/new_world' directory is missing '__init__.py'. It cannot be imported." >&2
    exit 1
fi
DB_NAME="new_world_data.db"
if [ ! -f "$DB_NAME" ]; then
    echo "ERROR: Database file '$DB_NAME' not found after update." >&2
    echo "ERROR: The bot will likely fail by running out of memory trying to build it." >&2
    echo "ERROR: Please ensure '$DB_NAME' is committed to the Git repository." >&2
    exit 1
fi

# --- Start the Bot ---
echo "INFO: Starting the bot (main.py)..."
if [ -f "main.py" ]; then
    # Explicitly use the Python from the activated virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
      echo "INFO: Running bot using Python from virtual environment: $VIRTUAL_ENV/bin/python3"
      "$VIRTUAL_ENV/bin/python3" main.py
    else
      echo "ERROR: Virtual environment not detected or activated. Attempting to run bot with system python3 (may fail)." >&2
      python3 main.py
    fi
else
    echo "ERROR: main.py not found. Cannot start the bot." >&2
    exit 1
fi
echo ""
echo "==================================="
echo "Update Script Completed"
echo "==================================="
echo "Bot will be restarted by the main Python script if update was successful."
exit 0
