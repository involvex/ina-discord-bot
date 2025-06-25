#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Navigate to the script's directory
cd "$(dirname "$0")" || exit
echo "INFO: Operating in script directory: $(pwd)"

# Activate virtual environment
VENV_PATH="./venv"
VENV_ACTIVATE_SCRIPT="$VENV_PATH/bin/activate"

if [ -f "$VENV_ACTIVATE_SCRIPT" ]; then
    echo "INFO: Activating virtual environment: $VENV_ACTIVATE_SCRIPT"
    source "$VENV_ACTIVATE_SCRIPT"
    if [ -z "$VIRTUAL_ENV" ]; then
        echo "WARNING: Virtual environment activation failed. Ensure 'source' command is available and path is correct." >&2
    else
        echo "INFO: Virtual environment activated."
    fi
else
    echo "ERROR: Virtual environment activate script not found at '$VENV_ACTIVATE_SCRIPT'. Cannot proceed with script execution." >&2
    exit 1
fi

# Run create_db.py to populate the database from perks_buddy.csv
echo "Attempting to update database from perks_buddy.csv using 'python3 create_db.py'..."
python3 create_db.py
echo "Database population script (create_db.py) completed successfully."

# Ensure VERSION file exists and read version
VERSION_FILE="VERSION"
if [ -f "$VERSION_FILE" ]; then
    VERSION=$(cat "$VERSION_FILE")
    echo "Current version from VERSION file: $VERSION"
else
    echo "Error: VERSION file not found. Please ensure it exists." >&2
    exit 1
fi

# Check for and remove .git/index.lock file if it exists
LOCK_FILE=".git/index.lock"
if [ -f "$LOCK_FILE" ]; then
    echo "Git index.lock file found. Attempting to remove it..."
    rm -f "$LOCK_FILE" # This command will exit if it fails due to set -e, unless it's a permission issue
    if [ ! -f "$LOCK_FILE" ]; then # Double check file is gone
        echo "index.lock removed successfully."
    else
        echo "Warning: Failed to remove index.lock. Git operations might still fail." >&2
    fi
fi

# Commit and push changes (ensure git is initialized in your project and you have proper permissions) - set -e will handle failures
git add perks_buddy.csv new_world_data.db VERSION
git commit -m "Update perks data (automated, version $VERSION)"
git push

echo "Perk update script finished."
