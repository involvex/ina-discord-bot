#!/bin/bash

# Navigate to the script's directory
cd "$(dirname "$0")"

# Activate virtual environment if necessary (adjust path as needed)
# source venv/bin/activate

# Run the Python script
python scrape_perks.py

# Commit and push changes (ensure git is initialized in your project and you have proper permissions)
git add perks_scraped.csv
git commit -m "Update perks data"
git push
