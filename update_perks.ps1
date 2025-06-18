<#
.SYNOPSIS
    Updates the perks data by running a Python script and pushing changes to Git.
#>

# Navigate to the script's directory
Set-Location -To "$(Split-Path -Path $MyInvocation.MyCommand.Path -Parent)"

# Activate virtual environment if necessary (adjust path as needed)
# . .\venv\Scripts\Activate.ps1

# Run the Python script
python scrape_perks.py

# Commit and push changes (ensure git is initialized in your project and you have proper permissions)
git add perks_scraped.csv
git commit -m "Update perks data"
git push