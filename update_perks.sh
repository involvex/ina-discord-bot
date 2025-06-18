#!/bin/bash

# Navigate to the script's directory
cd "$(dirname "$0")"

# Activate virtual environment if necessary (adjust path as needed)
# source venv/bin/activate

# Run the Python script
python3 scrape_perks.py # Using python3 explicitly is often a good practice

# Check for and remove .git/index.lock file if it exists
LOCK_FILE=".git/index.lock"
if [ -f "$LOCK_FILE" ]; then
    echo "Git index.lock file found. Attempting to remove it..."
    rm -f "$LOCK_FILE"
    if [ ! -f "$LOCK_FILE" ]; then
        echo "index.lock removed successfully."
    else
        echo "Warning: Failed to remove index.lock. Git operations might still fail." >&2
    fi
fi

# Commit and push changes (ensure git is initialized in your project and you have proper permissions)
git add perks_scraped.csv && \
git commit -m "Update perks data (automated)" && \
git push
