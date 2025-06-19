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
# Update VERSION file from config.py
echo "Attempting to update VERSION file from config.py..."
python3 -c "import re, os; \
cfg_path='config.py'; v_path='VERSION'; version=None; \
script_dir = os.path.dirname(os.path.realpath('$0')); \
cfg_full_path=os.path.join(script_dir, cfg_path); v_full_path=os.path.join(script_dir, v_path); \
with open(cfg_full_path, 'r') as f: content = f.read(); \
match = re.search(r'^__version__\s*=\s*\"(.*?)\"', content, re.M); \
if match: version = match.group(1); \
if version: \
  with open(v_full_path, 'w') as f: f.write(version); \
  print(f'VERSION file ({v_full_path}) updated to {version}'); \
else: print(f'Error: Could not extract version from {cfg_full_path}. VERSION file not updated.');"

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
git commit -m "Update perks data (automated)" && \
git push
