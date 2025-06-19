#!/bin/bash

# Navigate to the script's directory
cd "$(dirname "$0")"

# Activate virtual environment if necessary (adjust path as needed)
# source venv/bin/activate

# Run create_db.py to populate the database from perks_buddy.csv
echo "Attempting to update database from perks_buddy.csv using 'python3 create_db.py'..."
python3 create_db.py
CREATE_DB_EXIT_CODE=$?
if [ $CREATE_DB_EXIT_CODE -ne 0 ]; then
    echo "Error: Python script 'create_db.py' failed with exit code: $CREATE_DB_EXIT_CODE. Database might not be up-to-date. Aborting Git operations." >&2
    exit 1
fi
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
    rm -f "$LOCK_FILE"
    if [ ! -f "$LOCK_FILE" ]; then
        echo "index.lock removed successfully."
    else
        echo "Warning: Failed to remove index.lock. Git operations might still fail." >&2
    fi
fi

# Commit and push changes (ensure git is initialized in your project and you have proper permissions)
git add perks_buddy.csv new_world_data.db VERSION && \
git commit -m "Update perks data (automated, version $VERSION)" && \
git push
